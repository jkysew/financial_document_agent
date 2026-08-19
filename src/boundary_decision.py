"""
Structural boundary decision layer for Financial Document Agent v4.

This module interprets existing BoundaryEvidence. It does not extract PDF
content, create new evidence, or use document-specific rules.
"""

from dataclasses import dataclass
from typing import List, Literal

from src.models import BoundaryEvidence


Decision = Literal["JOIN", "SPLIT", "AMBIGUOUS"]


@dataclass
class BoundaryDecision:
    """Traceable structural interpretation of a BoundaryEvidence record."""

    decision: Decision
    supporting_evidence: List[str]
    conflicting_evidence: List[str]
    unresolved_evidence: List[str]
    reason: str


class BoundaryDecisionEngine:
    """
    Conservative structural decision engine.

    Version 1 intentionally avoids numeric scoring, weighted voting,
    document-specific thresholds, and forced decisions when the existing
    evidence is insufficient.
    """

    def decide(self, evidence: BoundaryEvidence) -> BoundaryDecision:
        split_support: List[str] = []
        unresolved: List[str] = []

        # Strongest currently available structural discontinuity:
        # the rows occupy completely separate horizontal regions.
        if evidence.horizontal_overlap == 0.0:
            split_support.append("rows_have_no_horizontal_overlap")

        # A simultaneous typography transition adds independent structural
        # evidence, but typography by itself is not sufficient.

        # Current v1 cannot safely establish JOIN from visual evidence alone.
        # Matching geometry/typography is contextual evidence, not proof of
        # structural continuity (see B1/B2 and B11/B12).
        if (
            evidence.horizontal_overlap == 1.0
            and evidence.left_margin_similarity == 1.0
            and evidence.font_family_similarity == 1.0
            and evidence.font_size_similarity == 1.0
            and evidence.bold_relationship == "both_regular"
        ):
            unresolved.append(
                "matching_visual_evidence_does_not_prove_structural_continuity"
            )

        # These signals are intentionally non-authoritative.
        if evidence.raw_vertical_gap > 0:
            unresolved.append("vertical_gap_is_context_only")

        if evidence.left_margin_similarity < 1.0:
            unresolved.append("margin_difference_is_context_only")

        if (
            evidence.font_family_similarity < 1.0
            or evidence.font_size_similarity < 1.0
            or evidence.bold_relationship != "both_regular"
        ):
            unresolved.append("typography_difference_is_context_only")

        # v1 can make a conservative SPLIT decision only when there is
        # complete horizontal separation between the adjacent rows.
        if split_support:
            return BoundaryDecision(
                decision="SPLIT",
                supporting_evidence=split_support,
                conflicting_evidence=[],
                unresolved_evidence=unresolved,
                reason=(
                    "Deterministic evidence shows a structural discontinuity "
                    "that can be supported without relying on a single gap "
                    "or typography rule."
                ),
            )

        # v1 deliberately leaves JOIN unresolved because the current
        # BoundaryEvidence model does not yet contain sufficiently strong,
        # validated continuation evidence to prove a JOIN safely.
        return BoundaryDecision(
            decision="AMBIGUOUS",
            supporting_evidence=[],
            conflicting_evidence=[],
            unresolved_evidence=(
                unresolved
                or ["insufficient_validated_evidence_for_structural_decision"]
            ),
            reason=(
                "Current evidence is insufficient to make a defensible "
                "deterministic JOIN/SPLIT decision."
            ),
        )