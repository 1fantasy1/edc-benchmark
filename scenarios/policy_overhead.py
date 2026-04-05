from __future__ import annotations

from typing import Any

from scenarios.base import ScenarioBase, EDCError, render_template


class PolicyOverheadScenario(ScenarioBase):
    scenario_name = "policy_overhead"

    def run_once(self, run_index: int) -> dict[str, Any]:
        result: dict[str, Any] = {
            "scenario": self.scenario_name,
            "run_index": run_index,
            "success": False,
            "policy_mode": self.config.get("policy_mode", "unknown"),
        }

        run_ids = self.build_run_ids(run_index)
        result.update(
            {
                "asset_id": run_ids["ASSET_ID"],
                "policy_id": run_ids["POLICY_ID"],
                "contract_definition_id": run_ids["CONTRACT_DEFINITION_ID"],
            }
        )

        try:
            # ----------------------------------------------------------
            # 0) 创建公共资源：asset / policy / contract definition
            # ----------------------------------------------------------
            common_resources = self.create_common_resources(run_ids)
            result["asset_response"] = common_resources.get("asset_response")
            result["policy_response"] = common_resources.get("policy_response")
            result["contract_definition_response"] = common_resources.get(
                "contract_definition_response"
            )

            # ----------------------------------------------------------
            # 1) Catalog Request
            # ----------------------------------------------------------
            dataset_request_payload = render_template(
                self.config["dataset_request_template_path"],
                run_ids,
            )
            dataset_response, catalog_latency_s = self.measure_catalog_request(
                dataset_request_payload
            )
            result["catalog_request_latency_s"] = catalog_latency_s
            result["dataset_response"] = dataset_response

            offer_id = self.extract_offer_id(dataset_response)
            result["offer_id"] = offer_id

            # ----------------------------------------------------------
            # 2) Contract Offer Negotiation
            # ----------------------------------------------------------
            negotiation_vars = dict(run_ids)
            negotiation_vars["CONTRACT_OFFER_ID"] = offer_id

            negotiation_payload = render_template(
                self.config["negotiation_template_path"],
                negotiation_vars,
            )

            negotiation_response, negotiation_request_latency_s = (
                self.measure_contract_offer_negotiation(negotiation_payload)
            )
            result["contract_offer_negotiation_latency_s"] = (
                negotiation_request_latency_s
            )
            result["negotiation_response"] = negotiation_response

            negotiation_id = negotiation_response["@id"]
            result["negotiation_id"] = negotiation_id

            # ----------------------------------------------------------
            # 3) Contract Agreement / Negotiation Completion
            # ----------------------------------------------------------
            final_negotiation, agreement_latency_s = self.measure_contract_agreement(
                negotiation_id
            )
            result["contract_agreement_latency_s"] = agreement_latency_s
            result["final_negotiation"] = final_negotiation
            result["negotiation_state"] = final_negotiation.get("state")

            agreement_id = self.extract_agreement_id(final_negotiation)
            if agreement_id:
                result["contract_agreement_id"] = agreement_id

            # ----------------------------------------------------------
            # 4) 核心指标计算
            # ----------------------------------------------------------
            result["negotiation_end_to_end_latency_s"] = round(
                result["contract_offer_negotiation_latency_s"]
                + result["contract_agreement_latency_s"],
                6,
            )

            # 第一版口径：
            # 如果 provider 侧还没有额外埋点输出真实 policy evaluation 时间，
            # 就先用“agreement 等待时间”作为近似值。
            #
            # 后续你如果在 provider 的 ConstraintFunction / PolicyFunctionsExtension
            # 里打点并通过日志或接口回传，可以把这里替换成真实值。
            result["policy_evaluation_latency_s"] = result[
                "contract_agreement_latency_s"
            ]

            result["control_plane_total_latency_s"] = (
                self.compute_control_plane_total_latency(
                    catalog_request_latency_s=result["catalog_request_latency_s"],
                    contract_offer_negotiation_latency_s=result[
                        "contract_offer_negotiation_latency_s"
                    ],
                    contract_agreement_latency_s=result[
                        "contract_agreement_latency_s"
                    ],
                    transfer_initiation_latency_s=None,
                )
            )

            # ----------------------------------------------------------
            # 5) 成功判定
            # ----------------------------------------------------------
            success_states = {"FINALIZED", "CONFIRMED"}
            if result["negotiation_state"] in success_states and agreement_id:
                result["success"] = True
            else:
                result["success"] = False
                result["error"] = final_negotiation.get("errorDetail") or (
                    f"Negotiation ended in state={result['negotiation_state']}"
                )

            return result

        except Exception as exc:
            result["error"] = str(exc)
            return result
