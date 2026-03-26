from __future__ import annotations

import time

from scenarios.base import ScenarioBase, render_template, timer
from scripts.fault_injectors.network_faults import ToxiproxyClient


class TransferInterruptionScenario(ScenarioBase):
    scenario_name = "transfer_interruption"

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
        interruption_timeout_ms = int(self.config.get("interruption_timeout_ms", 30000))

        try:
            toxiproxy.clear_toxics(proxy_name)

            self.create_common_resources(run_ids)

            dataset_request_payload = render_template(
                self.config["dataset_request_template_path"],
                run_ids,
            )
            dataset_response = self.consumer.request_dataset(dataset_request_payload)
            offer_id = self.extract_offer_id(dataset_response)
            result["offer_id"] = offer_id

            negotiation_vars = dict(run_ids)
            negotiation_vars["CONTRACT_OFFER_ID"] = offer_id
            negotiation_payload = render_template(
                self.config["negotiation_template_path"],
                negotiation_vars,
            )

            negotiation_response = self.consumer.start_negotiation(negotiation_payload)
            negotiation_id = negotiation_response["@id"]
            final_negotiation = self.wait_for_negotiation(negotiation_id)

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

            transfer_id = transfer_response["@id"]
            result["transfer_id"] = transfer_id
            result["transfer_initiation_latency_s"] = round(t_transfer_init["duration_s"], 6)

            # 等待几秒后，中断传输链路
            fault_delay_s = float(self.config.get("fault_injection_delay_s", 2.0))
            time.sleep(fault_delay_s)
            toxiproxy.create_timeout(proxy_name, timeout_ms=interruption_timeout_ms)

            result["fault_type"] = "transfer_interruption"

            retry_attempts = int(self.config.get("retry_attempts", 3))
            retry_interval_s = float(self.config.get("retry_interval_s", 5.0))
            recovered = False
            final_transfer = None

            for _ in range(retry_attempts):
                try:
                    final_transfer = self.wait_for_transfer(transfer_id)
                    recovered = True
                    break
                except Exception:
                    time.sleep(retry_interval_s)

            result["retry_success_rate"] = round(
                (1.0 if recovered else 0.0),
                6,
            )

            if final_transfer is None:
                result["failed_transactions"] = 1
                result["degraded_mode_success_rate"] = 0.0
                result["error"] = "Transfer interrupted and did not recover"
                return result

            result["transfer_state"] = final_transfer.get("state")
            success_states = {"COMPLETED", "FINISHED", "DEPROVISIONED"}

            if final_transfer.get("state") in success_states:
                result["success"] = True
                result["failed_transactions"] = 0
                result["degraded_mode_success_rate"] = 1.0
            else:
                result["failed_transactions"] = 1
                result["degraded_mode_success_rate"] = 0.0
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
