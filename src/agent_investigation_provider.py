"""Provider-neutral execution boundary for agent investigations.

No external provider or runtime is connected here. Providers implement the
small protocol and the executor enforces the investigation contract.
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Protocol, runtime_checkable

from src.agent_investigation import (
    AgentInvestigationRequest,
    AgentInvestigationResult,
    ContractValidationError,
)


class InvestigationProviderError(RuntimeError):
    """Raised when a provider fails to execute an investigation."""


class InvalidInvestigationResultError(InvestigationProviderError):
    """Raised when a provider returns a result without valid provenance."""


@runtime_checkable
class AgentInvestigationProvider(Protocol):
    """Provider-neutral interface for future investigation backends."""

    def investigate(
        self,
        request: AgentInvestigationRequest,
    ) -> AgentInvestigationResult:
        """Return an evidence-backed result for the supplied request."""
        ...


def execute_investigation(
    provider: AgentInvestigationProvider,
    request: AgentInvestigationRequest,
) -> AgentInvestigationResult:
    """Execute and contract-validate one provider investigation."""
    request.validate()
    try:
        result = provider.investigate(request)
    except InvestigationProviderError:
        raise
    except Exception as exc:
        raise InvestigationProviderError(
            "Investigation provider failed"
        ) from exc

    if not isinstance(result, AgentInvestigationResult):
        raise InvalidInvestigationResultError(
            "Investigation provider returned an invalid result type"
        )

    try:
        result.validate_against(request)
    except ContractValidationError as exc:
        raise InvalidInvestigationResultError(
            "Investigation provider returned invalid provenance"
        ) from exc

    return result


@dataclass
class MockInvestigationProvider:
    """Deterministic provider used to test the provider boundary."""

    result_factory: Optional[
        Callable[
            [AgentInvestigationRequest],
            AgentInvestigationResult,
        ]
    ] = None
    calls: List[AgentInvestigationRequest] = field(default_factory=list)

    def investigate(
        self,
        request: AgentInvestigationRequest,
    ) -> AgentInvestigationResult:
        self.calls.append(request)
        if self.result_factory is not None:
            return self.result_factory(request)
        return AgentInvestigationResult(
            request_id=request.request_id,
            status="INSUFFICIENT_EVIDENCE",
            missing_or_conflicting_evidence=[
                "Mock provider does not perform semantic investigation."
            ],
            limitations=["deterministic mock provider"],
        )
