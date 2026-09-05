"""Ollama-backed provider for evidence-based investigations.

All Ollama-specific HTTP and prompt handling lives in this module. The
provider does not perform PDF extraction, retrieval, or document parsing.
"""

from dataclasses import dataclass
import json
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.agent_investigation import (
    AgentInvestigationRequest,
    AgentInvestigationResult,
    ContractValidationError,
)
from src.agent_investigation_provider import (
    AgentInvestigationProvider,
    InvestigationProviderError,
    InvalidInvestigationResultError,
)


class MalformedOllamaResultError(InvestigationProviderError):
    """Raised when Ollama returns content that is not a valid result document."""


@dataclass(frozen=True)
class OllamaProviderConfig:
    """Configurable Ollama connection settings."""

    base_url: str
    model_name: str
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise ValueError("Ollama base_url is required")
        if not self.model_name.strip():
            raise ValueError("Ollama model_name is required")
        if self.timeout_seconds <= 0:
            raise ValueError("Ollama timeout_seconds must be positive")


OllamaTransport = Callable[[str, Dict[str, Any], float], Dict[str, Any]]


class OllamaInvestigationProvider(AgentInvestigationProvider):
    """Execute investigation requests through Ollama's chat API."""

    def __init__(
        self,
        *,
        base_url: str,
        model_name: str,
        timeout_seconds: float = 120.0,
        transport: Optional[OllamaTransport] = None,
    ) -> None:
        self.config = OllamaProviderConfig(
            base_url=base_url.rstrip("/"),
            model_name=model_name,
            timeout_seconds=timeout_seconds,
        )
        self._transport = transport or self._default_transport

    def investigate(
        self,
        request: AgentInvestigationRequest,
    ) -> AgentInvestigationResult:
        request.validate()
        payload = {
            "model": self.config.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": self._system_prompt(),
                },
                {
                    "role": "user",
                    "content": self.build_prompt(request),
                },
            ],
            "stream": False,
            "format": "json",
        }

        try:
            response = self._transport(
                f"{self.config.base_url}/api/chat",
                payload,
                self.config.timeout_seconds,
            )
        except InvestigationProviderError:
            raise
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise InvestigationProviderError(
                "Ollama request failed"
            ) from exc
        except Exception as exc:
            raise InvestigationProviderError(
                "Ollama transport failed"
            ) from exc

        result_data = self._extract_result_data(response)
        try:
            result = AgentInvestigationResult.from_dict(result_data)
        except (ContractValidationError, KeyError, TypeError, ValueError) as exc:
            raise MalformedOllamaResultError(
                "Ollama returned malformed investigation result JSON"
            ) from exc

        try:
            result.validate_against(request)
        except ContractValidationError as exc:
            raise InvalidInvestigationResultError(
                "Ollama returned investigation result with invalid provenance"
            ) from exc

        return result

    @staticmethod
    def build_prompt(request: AgentInvestigationRequest) -> str:
        """Build a controlled prompt with explicit evidence boundaries."""
        request.validate()
        data = request.to_dict()
        raw_evidence = {
            "physical_rows": data["physical_rows"],
            "target_row_ids": data["target_row_ids"],
        }
        deterministic_observations = {
            "trigger_reasons": data["trigger_reasons"],
            "logical_blocks": data["logical_blocks"],
            "boundary_assessments": data["boundary_assessments"],
            "target_block_ids": data["target_block_ids"],
            "fee_items": data["fee_items"],
        }
        hypotheses = data["hypotheses"]

        return """You are an evidence investigator, not a replacement parser.

Use only the supplied evidence. Do not invent, rewrite, normalize, or delete
physical rows, VisualSpans, coordinates, boundary observations, or source text.
Do not treat proximity alone as proof. Preserve competing interpretations when
the evidence is insufficient. Every resolved conclusion must cite one or more
provenance references to supplied row, block, boundary, or fee-item evidence.
You may return observational follow-up evidence requests, but do not perform
retrieval or vision yourself.

Return only one JSON object matching this shape:
{
  "request_id": "same request_id",
  "status": "RESOLVED | UNRESOLVED | INSUFFICIENT_EVIDENCE",
  "conclusions": [],
  "alternatives": [],
  "unresolved_reason": null,
  "missing_or_conflicting_evidence": [],
  "follow_up_requests": [],
  "limitations": []
}

For RESOLVED, each conclusion must include evidence_references. Use only
source IDs, row IDs, block IDs, pages, and coordinates present below.

=== RAW EVIDENCE: physical rows and VisualSpans ===
""" + json.dumps(raw_evidence, ensure_ascii=False, indent=2) + """

=== DETERMINISTIC OBSERVATIONS AND DECISIONS ===
""" + json.dumps(
            deterministic_observations,
            ensure_ascii=False,
            indent=2,
        ) + """

=== COMPETING INTERPRETATION HYPOTHESES ===
""" + json.dumps(hypotheses, ensure_ascii=False, indent=2) + """
"""

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You produce contract-valid JSON for an evidence-first document "
            "investigation. Never invent source evidence or provenance."
        )

    @staticmethod
    def _extract_result_data(response: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(response, dict):
            raise MalformedOllamaResultError("Ollama response must be a JSON object")

        message = response.get("message")
        if not isinstance(message, dict):
            raise MalformedOllamaResultError("Ollama response has no message object")
        content = message.get("content")

        if isinstance(content, str):
            try:
                result_data = json.loads(content)
            except json.JSONDecodeError as exc:
                raise MalformedOllamaResultError(
                    "Ollama message content is not valid JSON"
                ) from exc
        elif isinstance(content, dict):
            result_data = content
        else:
            raise MalformedOllamaResultError(
                "Ollama message content must be a JSON object or JSON string"
            )

        if not isinstance(result_data, dict):
            raise MalformedOllamaResultError(
                "Ollama result content must be a JSON object"
            )
        return result_data

    @staticmethod
    def _default_transport(
        url: str,
        payload: Dict[str, Any],
        timeout_seconds: float,
    ) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
