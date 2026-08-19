"""
Fee section assembler for Financial Document Agent v4.

Builds a higher-level category -> fee-item structure from the existing
LogicalDocumentBlock output.

This component does not modify physical/logical block generation and does not
invoke an LLM. It is intentionally conservative and document-oriented for
the current ING tariff PDF.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import re

from src.models import LogicalDocumentBlock


@dataclass
class FeeItem:
    """A single fee-bearing item within a category."""

    description: str
    source_blocks: List[str] = field(default_factory=list)
    source_text: str = ""
    fee_text: Optional[str] = None
    occurrence_text: Optional[str] = None
    continuation_text: List[str] = field(default_factory=list)


@dataclass
class FeeSection:
    """A category/section containing fee items."""

    heading: Optional[str]
    source_blocks: List[str] = field(default_factory=list)
    fee_items: List[FeeItem] = field(default_factory=list)


class FeeSectionAssembler:
    """
    Assemble logical blocks into fee sections.

    Existing LogicalDocumentBlocks are not changed.

    Within a logical block, physical rows are examined individually:

        fee row
        fee row
        fee row

    becomes three FeeItems.

        fee row
        continuation row
        continuation row

    becomes one FeeItem with continuation_text.

    Numbered footnotes are treated as explanatory material rather than
    fee items. A footnote may span multiple physical rows.
    """

    CURRENCY_MARKERS = ("€", "$", "£", "EUR", "USD", "GBP", "CHF")

    FEE_MARKERS = (
        "%",
        "per transaction",
        "per occurrence",
        "per account",
        "per month",
        "per quarter",
        "per year",
        "per item",
        "per batch",
        "per hour",
        "per client number",
        "free",
        "at cost",
    )

    NON_FEE_PREFIXES = (
        "tariff brochure",
    )

    # Exact structural headings observed in this tariff.
    # Matching is against normalized full text, not substrings.
    HEADING_TEXTS = {
        "accounts",
        "current account",
        "credit card - ing group offer",
        "account, transaction and fee reporting",
        "account, transaction and fee reporting electronic reporting",
        "electronic reporting",
        "interactive channel (insidebusiness payments, multiline)",
        "insidebusiness connect (file transfer, ebics, swift)",
        "third party bank reporting",
        "additional reporting services",
        "additional services",
        "paper reporting",
        "transfers - outgoing",
        "transfers - incoming",
        "without foreign exchange transaction",
        "electronic transfers",
        "additional charges",
        "single credit transfers and direct debits",
        "direct debit",
        "sepa direct debit",
        "sepa direct debit as creditor",
        "sepa direct debit as debtor",
        "other services",
        "certificates (excl. vat)",
        "cash management",
        "cards",
        "custody account charges",
        "custody account charges (excl. vat)",
        "securities transactions",
        "payment of coupons & repayment of securities",
        "cut-off times",
        "cut-off times - value dating - other information",
        "currency conversion",
        "general principle",
        "definitions",
        "complaint procedure",
        "complaint procedure lodge a complaint against ing luxembourg s.a.",
        "additional services and fees",
        "debit interest rate",
        "debit interest rates for current accounts without arranged overdrafts (per annum)",
        "credit interest rate",
        "pledge agreements (by third parties)",
        "ing purchase control",
        "ing corporate card offer",
        "card offer",
    }

    HEADING_MARKERS = (
        "(per annum)",
        "(excl. vat)",
    )

    def assemble(
        self,
        blocks: List[LogicalDocumentBlock],
        page_number: Optional[int] = None,
    ) -> List[FeeSection]:
        """
        Assemble logical blocks into fee sections.

        Blocks are expected to be in document reading order.
        """
        if page_number is not None:
            blocks = [b for b in blocks if b.page_number == page_number]

        sections: List[FeeSection] = []
        current_section: Optional[FeeSection] = None
        current_fee_item: Optional[FeeItem] = None

        current_footnote_number: Optional[str] = None
        current_page: Optional[int] = None

        for block in blocks:
            block_page = block.page_number

            if current_page is None:
                current_page = block_page
            elif block_page != current_page:
                current_page = block_page
                current_footnote_number = None

            block_text = self._normalize_text(block.text_content)

            if not block_text or self._is_footer(block_text):
                current_footnote_number = None
                current_fee_item = None
                continue

            physical_rows = getattr(block, "physical_rows", None) or []

            if physical_rows:
                for row in physical_rows:
                    row_text = self._normalize_text(row.text)

                    if not row_text:
                        continue

                    if self._is_footer(row_text):
                        current_footnote_number = None
                        current_fee_item = None
                        continue

                    # A numbered footnote starts a non-fee explanatory region.
                    footnote_number = self._extract_footnote_number(row_text)
                    if footnote_number is not None:
                        current_footnote_number = footnote_number
                        current_fee_item = None
                        continue

                    # Consume continuation lines belonging to a footnote.
                    if current_footnote_number is not None:
                        if self._looks_like_section_heading(row_text):
                            current_footnote_number = None
                        else:
                            continue

                    # Explicit pricing-condition continuation.
                    if self._is_continuation_row(row_text):
                        if current_fee_item is not None:
                            self._append_continuation(
                                current_fee_item,
                                row_text,
                            )
                        continue

                    # A row with its own fee always takes priority over
                    # heading detection.
                    fee_info = self._extract_fee_info(row_text)

                    if fee_info is not None:
                        description, fee_text, occurrence_text = fee_info

                        if current_section is None:
                            current_section = FeeSection(
                                heading=None
                            )
                            sections.append(current_section)

                        if block.block_id not in current_section.source_blocks:
                            current_section.source_blocks.append(
                                block.block_id
                            )

                        current_fee_item = FeeItem(
                            description=description,
                            source_blocks=[block.block_id],
                            source_text=row_text,
                            fee_text=fee_text,
                            occurrence_text=occurrence_text,
                        )

                        current_section.fee_items.append(current_fee_item)
                        continue

                    # Only explicit/validated headings become sections here.
                    if self._looks_like_section_heading(row_text):
                        current_section = FeeSection(
                            heading=row_text,
                            source_blocks=[block.block_id],
                        )
                        sections.append(current_section)
                        current_fee_item = None
                        continue

                    # Do not guess that arbitrary non-fee text is a
                    # continuation. Leave it outside the current fee item.
                    current_fee_item = None

                continue

            # ----------------------------------------------------------------
            # Fallback for blocks without physical-row detail.
            # ----------------------------------------------------------------

            footnote_number = self._extract_footnote_number(block_text)
            if footnote_number is not None:
                current_footnote_number = footnote_number
                current_fee_item = None
                continue

            if current_footnote_number is not None:
                if self._looks_like_section_heading(block_text):
                    current_footnote_number = None
                else:
                    continue

            fee_info = self._extract_fee_info(block_text)

            if fee_info is not None:
                description, fee_text, occurrence_text = fee_info

                if current_section is None:
                    current_section = FeeSection(heading=None)
                    sections.append(current_section)

                if block.block_id not in current_section.source_blocks:
                    current_section.source_blocks.append(
                        block.block_id
                    )

                current_fee_item = FeeItem(
                    description=description,
                    source_blocks=[block.block_id],
                    source_text=block_text,
                    fee_text=fee_text,
                    occurrence_text=occurrence_text,
                )

                current_section.fee_items.append(current_fee_item)
                continue

            if self._looks_like_section_heading(block_text):
                current_section = FeeSection(
                    heading=block_text,
                    source_blocks=[block.block_id],
                )
                sections.append(current_section)
                current_fee_item = None
                continue

            if self._looks_like_heading(block_text):
                current_section = FeeSection(
                    heading=block_text,
                    source_blocks=[block.block_id],
                )
                sections.append(current_section)
                current_fee_item = None
                continue

            current_fee_item = None

        return sections

    def _extract_fee_info(
        self,
        text: str,
    ) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        """
        Detect whether a row contains fee-like content.

        This identifies fee candidates; it does not claim full semantic
        extraction.
        """
        if not text:
            return None

        lower = text.lower()

        if lower.startswith(self.NON_FEE_PREFIXES):
            return None

        has_currency = any(
            marker.lower() in lower
            for marker in self.CURRENCY_MARKERS
        )

        has_percent = "%" in text

        has_fee_marker = any(
            marker in lower
            for marker in self.FEE_MARKERS
        )

        if not (has_currency or has_percent or has_fee_marker):
            return None

        fee_text = self._extract_fee_text(text)
        occurrence_text = self._extract_occurrence(text)

        description = self._build_description(
            text,
            fee_text,
            occurrence_text,
        )

        return description, fee_text, occurrence_text

    def _build_description(
        self,
        text: str,
        fee_text: Optional[str],
        occurrence_text: Optional[str],
    ) -> str:
        """Remove obvious pricing/occurrence suffixes from a row."""
        description = text

        if occurrence_text:
            description = description.replace(
                occurrence_text,
                "",
            ).strip()

        if fee_text:
            description = description.replace(
                fee_text,
                "",
            ).strip()

        description = re.sub(r"\s+", " ", description).strip()

        return description or text

    def _extract_fee_text(
        self,
        text: str,
    ) -> Optional[str]:
        """
        Extract a conservative pricing fragment.

        Supports the PDF's space-separated thousands format, e.g. € 2 000.
        """
        patterns = [
            r"(€\s*[\d\s.,]+(?:\s*/\s*[A-Za-z]+)?)",
            r"(\b(?:EUR|USD|GBP|CHF)\s*[\d.,]+)",
            r"(%\s*[\d.,]+)",
            r"(\b[\d.,]+\s*%)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()

        match = re.search(
            r"\bfree\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(0)

        match = re.search(
            r"\bat cost\b",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(0)

        return None

    def _extract_occurrence(
        self,
        text: str,
    ) -> Optional[str]:
        """Extract an obvious occurrence phrase."""
        patterns = [
            (
                r"\bper\s+"
                r"(?:transaction|occurrence|account|month|quarter|year|"
                r"item|batch|hour|client number|format|channel)\b"
                r"(?:\s*,\s*per\s+\w+)*"
            ),
            r"\bper\s+\w+(?:\s*,\s*per\s+\w+)+",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            if match:
                return match.group(0).strip()

        return None

    def _looks_like_section_heading(
        self,
        text: str,
    ) -> bool:
        """
        Recognize an explicit structural heading.

        Matching is against the complete normalized text.
        """
        normalized = self._normalize_heading_text(text)

        if not normalized:
            return False

        return normalized in self.HEADING_TEXTS

    def _looks_like_heading(
        self,
        text: str,
    ) -> bool:
        """
        Conservative fallback heading detection for blocks without
        physical-row detail.
        """
        words = text.split()

        if len(words) <= 7:
            return True

        lower = text.lower()

        return any(
            marker in lower
            for marker in self.HEADING_MARKERS
        )

    def _is_continuation_row(
        self,
        text: str,
    ) -> bool:
        """
        Identify clear continuation/condition rows.

        These are deterministic and deliberately narrow.
        """
        lower = text.lower().strip()

        continuation_prefixes = (
            "with min.",
            "with max.",
            "min.",
            "max.",
            "minimum of",
            "maximum of",
            "plus ",
            "additional ",
        )

        return lower.startswith(continuation_prefixes)

    def _extract_footnote_number(
        self,
        text: str,
    ) -> Optional[str]:
        """
        Return a leading footnote number.

        Examples:
            '1 Trust, Offshore, Foundation...'
            '4 The paper payment service...'
            '10 The exchange commission...'
        """
        match = re.match(
            r"^(\d+)\s+",
            text.strip(),
        )

        if match:
            return match.group(1)

        return None

    @staticmethod
    def _append_continuation(
        fee_item: FeeItem,
        text: str,
    ) -> None:
        fee_item.continuation_text.append(text)
        fee_item.source_text = (
            f"{fee_item.source_text} {text}"
        ).strip()

    @staticmethod
    def _is_footer(
        text: str,
    ) -> bool:
        return text.lower().startswith("tariff brochure")

    @staticmethod
    def _normalize_heading_text(
        text: str,
    ) -> str:
        """
        Normalize heading text for exact comparison.

        Removes trailing footnote markers attached directly to headings,
        e.g. 'Transfers - Outgoing4' -> 'Transfers - outgoing'.
        """
        normalized = re.sub(
            r"\s+",
            " ",
            text,
        ).strip().lower()

        normalized = re.sub(
            r"\d+$",
            "",
            normalized,
        ).strip()

        return normalized

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()