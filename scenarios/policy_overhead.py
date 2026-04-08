from __future__ import annotations

from typing import Any

from scenarios.base import (
    ScenarioBase,
    EDCError,
    render_template,
)


class PolicyOverheadScenario(ScenarioBase):
    """
    PolicyOverheadScenario 用于测试不同复杂度政策对EDC性能的影响。
    
    支持三个政策复杂度级别：
    - simple: 单个地点约束（Location ConstraintFunction）
    - medium: 时间范围约束（TimeRangeConstraintFunction）
    - advanced: 多层级数据保护级别约束（DataProtectionLevelConstraintFunction）
    
    配置参数：
    - policy_mode: 政策模式（simple/medium/advanced），默认为simple
    """

    scenario_name = "policy_overhead"

    def get_policy_template_path(self) -> str:
        """
        根据配置的 policy_mode 返回对应的政策模板路径。
        """
        policy_mode = self.config.get("policy_mode", "simple").lower()
        
        if policy_mode == "simple":
            return self.config.get(
                "policy_template_simple_path",
                "policy/policy-01-policy-enforcement/resources/create-policy-simple.json",
            )
        elif policy_mode == "medium":
            return self.config.get(
                "policy_template_medium_path",
                "policy/policy-01-policy-enforcement/resources/create-policy-medium.json",
            )
        elif policy_mode == "advanced":
            return self.config.get(
                "policy_template_advanced_path",
                "policy/policy-01-policy-enforcement/resources/create-policy-advanced.json",
            )
        else:
            raise ValueError(f"Unsupported policy_mode: {policy_mode}")

    def get_negotiation_template_path(self) -> str:
        """
        根据配置的 policy_mode 返回对应的合同请求模板路径。
        """
        policy_mode = self.config.get("policy_mode", "simple").lower()
        
        if policy_mode == "simple":
            return self.config.get(
                "negotiation_template_simple_path",
                "policy/policy-01-policy-enforcement/resources/contract-request-simple.json",
            )
        elif policy_mode == "medium":
            return self.config.get(
                "negotiation_template_medium_path",
                "policy/policy-01-policy-enforcement/resources/contract-request-medium.json",
            )
        elif policy_mode == "advanced":
            return self.config.get(
                "negotiation_template_advanced_path",
                "policy/policy-01-policy-enforcement/resources/contract-request-advanced.json",
            )
        else:
            raise ValueError(f"Unsupported policy_mode: {policy_mode}")

    def run_once(self, run_index: int) -> dict[str, Any]:
        """
        执行一次政策开销测试。
        
        四段测试：
        1. 资源创建（Asset / Policy / Contract Definition）
        2. Catalog 请求 - 测试Catalog API性能
        3. Contract 谈判 - 测试政策评估在谈判报价阶段的开销
        4. Agreement 等待 - 测试政策评估在agreement阶段的开销
        """
        policy_mode = self.config.get("policy_mode", "simple").lower()
        
        result: dict[str, Any] = {
            "scenario": self.scenario_name,
            "run_index": run_index,
            "success": False,
            "policy_mode": policy_mode,
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
            #    这个阶段不计入主要指标
            # ----------------------------------------------------------
            common_resources = self.create_common_resources(run_ids)
            result["asset_response"] = common_resources.get("asset_response")
            result["policy_response"] = common_resources.get("policy_response")
            result["contract_definition_response"] = common_resources.get(
                "contract_definition_response"
            )

            # ----------------------------------------------------------
            # 1) Catalog Request - 测试性能
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
            # 2) Contract Offer Negotiation - 测试政策评估开销
            # ----------------------------------------------------------
            negotiation_vars = dict(run_ids)
            negotiation_vars["CONTRACT_OFFER_ID"] = offer_id

            # 使用对应政策模式的合同请求模板
            negotiation_template_path = self.get_negotiation_template_path()
            negotiation_payload = render_template(
                negotiation_template_path,
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
            #    轮询等待直到达到最终状态
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
            # Policy 评估开销 = Agreement等待时间
            # （Policy 评估主要发生在Provider的Agreement验证阶段）
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
