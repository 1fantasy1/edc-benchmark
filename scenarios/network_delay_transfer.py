from __future__ import annotations

import time

from scenarios.base import ScenarioBase, render_template, timer
from scripts.fault_injectors.network_faults import ToxiproxyClient


class NetworkDelayTransferScenario(ScenarioBase):
    scenario_name = "network_delay_transfer"

    def run_once(self, run_index: int) -> dict[str, object]:
        result: dict[str, object] = {
            "scenario": self.scenario_name,
            "run_index": run_index,
            "success": False,
        }

        run_ids = self.build_run_ids(run_index)
        result.update(
            {
                "asset_id": run_ids["ASSET_ID"],
                "policy_id": run_ids["POLICY_ID"],
                "contract_definition_id": run_ids["CONTRACT_DEFINITION_ID"],
                "data_size_mb": self.config.get("data_size_mb", 1),
            }
        )

        toxiproxy = ToxiproxyClient(self.config["toxiproxy_base_url"])
        proxy_name = self.config["toxiproxy_proxy_name"]
        latency_ms = int(self.config.get("latency_ms", 200))

        try:
            toxiproxy.clear_toxics(proxy_name)
            toxiproxy.create_latency(proxy_name, latency_ms=latency_ms, jitter_ms=0)

            result["fault_type"] = "network_delay"
            result["latency_ms"] = latency_ms

            self.create_common_resources(run_ids)

            dataset_request_payload = render_template(
                self.config["dataset_request_template_path"],
                run_ids,
            )
            with timer() as t_catalog:
                dataset_response = self.consumer.request_dataset(dataset_request_payload)
            result["catalog_request_latency_s"] = round(t_catalog["duration_s"], 6)

            offer_id = self.extract_offer_id(dataset_response)
            result["offer_id"] = offer_id

            negotiation_vars = dict(run_ids)
            negotiation_vars["CONTRACT_OFFER_ID"] = offer_id
            negotiation_payload = render_template(
                self.config["negotiation_template_path"],
                negotiation_vars,
            )

            with timer() as t_neg:
                negotiation_response = self.consumer.start_negotiation(negotiation_payload)
            result["contract_offer_negotiation_latency_s"] = round(t_neg["duration_s"], 6)

            negotiation_id = negotiation_response["@id"]

            with timer() as t_agreement:
                final_negotiation = self.wait_for_negotiation(negotiation_id)
            result["contract_agreement_latency_s"] = round(t_agreement["duration_s"], 6)

            agreement_id = self.extract_agreement_id(final_negotiation)
            if not agreement_id:
                result["failed_transactions"] = 1
                result["retry_success_rate"] = 0.0
                result["degraded_mode_success_rate"] = 0.0
                result["error"] = final_negotiation.get("errorDetail") or "No contract agreement id found"
                return result

            result["contract_agreement_id"] = agreement_id

            transfer_vars = dict(run_ids)
            transfer_vars["CONTRACT_AGREEMENT_ID"] = agreement_id
            transfer_payload = render_template(
                self.config["transfer_template_path"],
                transfer_vars,
            )

            with timer() as t_transfer_init:
                transfer_response = self.consumer.start_transfer(transfer_payload)
            result["transfer_initiation_latency_s"] = round(t_transfer_init["duration_s"], 6)

            transfer_id = transfer_response["@id"]
            result["transfer_id"] = transfer_id

            with timer() as t_transfer_completion:
                final_transfer = self.wait_for_transfer(transfer_id)
            result["transfer_completion_latency_s"] = round(
                t_transfer_completion["duration_s"], 6
            )
            result["transfer_end_to_end_latency_s"] = round(
                result["transfer_initiation_latency_s"] + result["transfer_completion_latency_s"],
                6,
            )
            result["transfer_state"] = final_transfer.get("state")

            result["control_plane_total_latency_s"] = round(
                result["catalog_request_latency_s"]
                + result["contract_offer_negotiation_latency_s"]
                + result["contract_agreement_latency_s"]
                + result["transfer_initiation_latency_s"],
                6,
            )

            success_states = {"COMPLETED", "FINISHED", "DEPROVISIONED"}
            if final_transfer.get("state") in success_states:
                result["success"] = True
                result["retry_success_rate"] = 1.0
                result["degraded_mode_success_rate"] = 1.0
                result["failed_transactions"] = 0
            else:
                result["retry_success_rate"] = 0.0
                result["degraded_mode_success_rate"] = 0.0
                result["failed_transactions"] = 1
                result["error"] = final_transfer.get("errorDetail") or f"Transfer ended in state={final_transfer.get('state')}"

            return result

        except Exception as exc:
            result["retry_success_rate"] = 0.0
            result["degraded_mode_success_rate"] = 0.0
            result["failed_transactions"] = 1
            result["error"] = str(exc)
            return result
        finally:
            try:
                toxiproxy.clear_toxics(proxy_name)
            except Exception:
                pass
