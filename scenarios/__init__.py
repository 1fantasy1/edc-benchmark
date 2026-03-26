from .base import EDCManagementClient, MetricsRecorder, ScenarioBase
from .negotiation_baseline import NegotiationBaselineScenario
from .transfer_baseline import TransferBaselineScenario
from .policy_overhead import PolicyOverheadScenario
from .provider_restart_during_transfer import ProviderRestartDuringTransferScenario
#from .network_delay_transfer import NetworkDelayTransferScenario
#from .transfer_interruption import TransferInterruptionScenario


SCENARIO_REGISTRY = {
    "negotiation_baseline": NegotiationBaselineScenario,
    "transfer_baseline": TransferBaselineScenario,
    "policy_overhead": PolicyOverheadScenario,
    "provider_restart_during_transfer": ProviderRestartDuringTransferScenario,
   # "network_delay_transfer": NetworkDelayTransferScenario,
    #"transfer_interruption": TransferInterruptionScenario,
}
