# Financial Document Agent v3 — Evidence-Driven Document Agent

## 1. Purpose

v3 replaces the v2 fixed row-based extraction pipeline with an evidence-driven document agent.

The fundamental problem is:

> PDF physical rows do not necessarily correspond to logical fee entities.

A logical fee may:

* span multiple physical rows
* contain multiple pricing components
* have pricing separated from its description
* have footnotes modifying one or more fees
* reference another section or tariff
* contain variable pricing such as `€75/hour + VAT`
* contain non-numeric pricing such as reinvoicing the customer at cost
* contain constraints such as `cannot exceed 10% of assets`
* contain a maximum such as `EUR 25,000`

The agent must therefore reason over evidence rather than assume that physical rows equal fees.

---

## 2. Scope

This document describes the target architecture for Financial Document Agent v3 and the current validated implementation state.

The implementation is a prototype that demonstrates the architecture incrementally. Some target components do not yet exist or are still experimental.

The architectural goal is not to make deterministic extraction increasingly clever.

The goal is to:

1. preserve reliable physical evidence
2. expose structural observations deterministically
3. reason semantically over those observations
4. preserve provenance
5. validate conclusions against evidence
6. investigate uncertainty rather than guess

---

## 3. High-Level Architecture

The target architecture is:

```text
PDF
 ↓
Physical Evidence
 ↓
DocumentAgent
 ↓
Logical Block Hypotheses
 ↓
Fee Candidate Hypotheses
 ↓
Evidence Gathering
 ↓
Validation
 ↓
Revision / Investigation
 ↓
Final Structured Records
```

The `DocumentAgent` is the semantic orchestrator.

Deterministic tools provide observations.

The agent interprets those observations.

---

## 4. Core Architectural Principles

### 4.1 Deterministic tools are evidence providers

Deterministic tools may:

* extract text
* extract coordinates
* extract words
* render pages
* inspect regions
* return page dimensions
* identify physical rows
* associate VisualSpans with physical rows
* retrieve source evidence
* locate text occurrences
* retrieve nearby rows
* retrieve neighboring pages
* calculate structural relationships
* expose boundary evidence

Deterministic evidence components must remain observational and inspectable.

They must not silently encode semantic conclusions such as:

* what constitutes a fee
* what a fee means
* whether a pricing statement applies to a particular fee
* what a legal constraint means
* what an unresolved cross-reference means

A structural evidence component may measure the relationship between physical rows, but a later decision layer must make any explicit `JOIN`, `SPLIT`, or `AMBIGUOUS` structural decision.

### 4.2 No unsupported semantic inference

The system must not:

* invent missing values
* invent amounts
* invent currencies
* invent pricing models
* silently resolve unknown references
* assume nearby text automatically belongs to a fee
* hide ambiguity
* discard source coordinates
* discard source text
* allow an LLM-generated conclusion to become authoritative without evidence

The central principle is:

> **Observe deterministically. Reason semantically. Preserve evidence. Validate conclusions. Investigate uncertainty.**

---

# Part I — Current Implementation

## 5. Current Implementation Characteristics

The original prototype currently:

* stores physical rows as evidence
* creates logical blocks through `LogicalBlockGenerator`
* extracts fee candidates using deterministic demonstration rules
* validates candidates using simple status rules
* produces structured dictionary output
* contains an `OutputFormatter` capable of producing JSON

The original prototype did not actually infer logical document blocks. Its simplified behavior was effectively page-based.

The current working tree contains experimental row-grouping work that is intended to replace this simplified behavior, but that work is not yet considered the final grouping architecture.

The prototype does not yet fully implement:

* a `DocumentAgent` orchestrator
* LLM-based semantic interpretation
* production logical-block hypothesis generation
* production fee-candidate hypothesis generation
* evidence-gathering loops
* evidence sufficiency evaluation
* revision/investigation loops
* iterative hypothesis validation
* semantic interpretation of cross-references
* semantic interpretation of legal constraints
* a persistent evidence graph or evidence store
* production-grade end-to-end processing
* a final consolidated output path

---

## 6. DocumentProcessor

**File:** `src/document_processor.py`

`DocumentProcessor` is the current top-level prototype orchestrator.

Its current sequence is:

1. Store supplied `PhysicalRow` objects through `EvidenceManager`.
2. Create logical blocks through `LogicalBlockGenerator`.
3. Extract fee candidates through `FeeCandidateExtractor`.
4. Validate blocks through `Validator`.
5. Format the result into a dictionary.

The target architecture will eventually replace this role with `DocumentAgent`.

---

## 7. EvidenceManager

**File:** `src/evidence_manager.py`

`EvidenceManager` manages physical evidence.

Current responsibilities:

* store `PhysicalRow` objects
* store `EvidenceSource` objects
* retrieve all rows belonging to a page
* return all stored evidence

It does not perform semantic interpretation.

This is consistent with the evidence-first architecture.

---

## 8. LogicalBlockGenerator

**File:** `src/logical_block_generator.py`

`LogicalBlockGenerator` creates and stores `LogicalDocumentBlock` objects.

Current responsibilities include:

* create logical blocks
* assign sequential block IDs such as `block_000`
* create `EvidenceSource` objects from physical rows
* associate physical rows with blocks
* store blocks
* retrieve blocks by page
* retrieve all blocks

### Experimental status

The current working tree contains experimental logical-row grouping logic, including `_BlockSplitter` and relationship/evidence calculations.

This work is exploratory and is **not yet the final logical-grouping architecture**.

The current gap-based splitter is an experimental baseline only.

Do not treat its current output as authoritative logical-block truth.

---

## 9. BoundaryEvidence

**File:** `src/boundary_evidence.py`

`BoundaryEvidence` is the current experimental evidence layer for relationships between adjacent physical rows.

Its purpose is to expose observable structural evidence such as:

* raw vertical gap
* relative/local spacing
* horizontal relationship
* left-margin relationship
* typography relationship
* font-family relationship
* bold/regular relationship
* VisualSpan composition
* local neighborhood context

BoundaryEvidence is an **evidence producer**, not a semantic decision maker.

It must not independently determine:

```text
JOIN
SPLIT
AMBIGUOUS
```

unless and until a separate structural decision layer is explicitly introduced.

---

## 10. FeeCandidateExtractor

**File:** `src/fee_candidate_extractor.py`

The current extractor is deterministic and rule-based.

It is a prototype demonstration, not a production fee extraction engine.

### Demonstrated rules

#### Research fee

If the block contains:

```text
research fee
```

the prototype creates:

* description: Research fee
* amount: `75.0`
* currency: EUR
* unit: hour
* VAT status: additional
* pricing type: variable
* evidence text: Research fee € 75/hour + VAT*
* initial status: `PARTIALLY_SUPPORTED`
* initial confidence: `0.7`

The amount and other values are hard-coded demonstration values.

#### External research fee

If the block contains:

```text
external research fee
```

the prototype creates a candidate with:

* description: External research fee
* pricing type: reinvoicing
* evidence text describing reinvoicing at cost
* status: `AMBIGUOUS`
* confidence: `0.4`

#### Combined research fee constraint

If the block contains both:

```text
cannot exceed
```

and:

```text
10%
```

the prototype creates a constraint candidate representing:

* maximum percentage: 10%
* maximum amount: EUR 25,000

These are demonstration rules.

#### Standard pricing cross-reference

If the block contains:

```text
cf standard pricing
```

the prototype creates a candidate representing an unresolved reference to standard pricing.

It is marked ambiguous with a low confidence score.

### Architectural significance

These rules demonstrate the kinds of semantic facts that the target agent must eventually discover.

They should not evolve into a large collection of hard-coded string rules.

The target system should use deterministic tools to expose evidence and allow the agent to interpret that evidence.

---

## 11. Validator

**File:** `src/validator.py`

The current validator applies simple deterministic rules.

### Candidate validation

If both amount and currency exist:

```text
SUPPORTED
```

and confidence is increased by `0.2`, bounded to `[0.0, 1.0]`.

If neither amount nor currency exists:

* reinvoicing or cost → `PARTIALLY_SUPPORTED`
* otherwise → `AMBIGUOUS`

If only partial pricing information exists:

```text
PARTIALLY_SUPPORTED
```

and confidence is increased by `0.1`.

### Block validation

Block status is derived from candidate statuses.

Priority:

1. any `SUPPORTED` candidate → block `SUPPORTED`
2. otherwise any `PARTIALLY_SUPPORTED` candidate → block `PARTIALLY_SUPPORTED`
3. otherwise any `AMBIGUOUS` candidate → block `AMBIGUOUS`
4. otherwise → `UNSUPPORTED`

### Target limitation

This validator does not determine whether an interpretation is actually supported by sufficient evidence.

The target architecture requires evidence-aware validation rather than field-population rules.

---

## 12. OutputFormatter

**File:** `src/output_formatter.py`

`OutputFormatter` formats logical blocks and fee candidates into structured JSON.

It includes:

* document analysis metadata
* logical blocks
* fee candidates
* evidence sources
* source coordinates
* status
* confidence

It removes `None` values from fee candidate output.

### Current architectural inconsistency

The supplied `DocumentProcessor` has its own output-formatting method and does not currently use `OutputFormatter`.

There are therefore two output-formatting paths in the prototype.

This should be consolidated during implementation.

---

## 13. test_pipeline.py

**File:** `src/test_pipeline.py`

The current test harness creates mock `PhysicalRow` objects representing extracted PDF data.

It then passes them to `DocumentProcessor` and prints the resulting blocks and candidates.

It demonstrates:

* research fee extraction
* external research fee extraction
* combined research fee constraint extraction
* standard pricing cross-reference extraction

It does not perform actual PDF extraction.

It is therefore a demonstration/test harness rather than an end-to-end document-processing test.

---

# Part II — Current Evidence Pipeline

## 14. Authoritative Physical Evidence Pipeline

The authoritative physical evidence pipeline is:

```text
PDF
 ↓
PDFEvidenceRetriever / evidence_tools.py
 ↓
PhysicalRow
 ↓
VisualSpan enrichment
 ↓
data/visual_span_inspection.json
```

`data/visual_span_inspection.json` is a validated snapshot of the PhysicalRows produced by the live PDF extraction pipeline.

---

## 15. Live Extraction Validation

The live `PDFEvidenceRetriever` output has been compared against:

```text
data/visual_span_inspection.json
```

for all 20 pages of the current ING Luxembourg PDF evidence set.

Validated results:

```text
Pages: 20
PhysicalRows: 572

Row count mismatches: 0
Text mismatches: 0
Coordinate mismatches: 0
VisualSpan-count mismatches: 0
```

Therefore the JSON evidence artifact and the live extraction currently represent the same PhysicalRow dataset.

This validation is important because downstream analysis and ground truth can safely use the JSON artifact as a stable evidence snapshot of the current extraction pipeline.

---

## 16. VisualSpan Status

VisualSpan extraction and association are complete and validated.

Every PhysicalRow in the current 20-page evidence set has VisualSpan data.

VisualSpan data is observational evidence only.

It does not by itself determine:

* semantic meaning
* fee structure
* logical grouping
* pricing interpretation

---

## 17. Authoritative Boundary Ground Truth

The current machine-readable ground truth is:

```text
data/authoritative_boundary_ground_truth.json
```

It contains:

```text
12 boundaries
5 JOIN
6 SPLIT
1 AMBIGUOUS
```

Every boundary:

* references an existing page
* references valid rows
* uses adjacent rows
* uses 1-based row numbering

The file contains structural decisions and qualitative reasons only.

Measurements such as:

* gaps
* coordinates
* fonts
* margins
* overlap

are always derived from:

```text
data/visual_span_inspection.json
```

and must not be duplicated as authoritative ground-truth measurements.

This ground truth is frozen and should not be regenerated or replaced without an explicit architectural decision.

---

## 18. Current Logical-Grouping Baseline

The current `_BlockSplitter` is an experimental baseline.

It has been measured against the current 572-row evidence set across all 20 pages.

The observed behavior demonstrates why a simple gap threshold is insufficient.

Examples include pages where:

* intra-block gaps and inter-block gaps overlap
* the same local gap size can represent either continuation or a structural boundary
* horizontal layout changes occur at very small vertical gaps
* large margin shifts can still represent fee continuation
* different typography may indicate a structural transition
* neighborhood context is required to interpret a boundary

Therefore:

> A single absolute gap threshold is not considered a viable final logical-grouping algorithm.

The baseline remains useful as a comparison and regression reference.

---

# Part III — Current Domain Model

## 19. PhysicalRow

`PhysicalRow` represents a physical observation extracted from a PDF.

Current fields include:

* `page_number`
* `coordinates`
* `text`
* `words`

The target architecture should additionally provide a stable `row_id`.

A physical row is evidence, not a semantic fee entity.

---

## 20. EvidenceSource

`EvidenceSource` represents traceable source evidence.

Current fields:

* `source_type`
* `page_number`
* `coordinates`
* `content`
* `context`

The target model should additionally support:

* stable evidence identifiers
* extensible metadata
* explicit provenance relationships

Possible evidence types include:

* text
* coordinate region
* image
* page

Evidence must remain traceable to the original document location.

---

## 21. LogicalDocumentBlock

`LogicalDocumentBlock` is the central semantic abstraction.

A block may contain:

* multiple physical rows
* multiple fee candidates
* descriptions
* amounts
* currencies
* units
* pricing rules
* footnotes
* constraints
* cross-references

Current fields include:

* `block_id`
* `type`
* `page_number`
* `coordinates`
* `text_content`
* `physical_rows`
* `evidence_sources`
* `fee_candidates`
* `status`
* `ambiguities`
* `confidence_score`
* `interpretation_notes`

The target architecture should preserve all physical evidence supporting the block.

Possible semantic block types include:

* fee section
* description block
* pricing rule
* footnote block
* cross-reference block
* other semantic document unit

Semantic classification belongs to the agent, not the extraction layer.

---

## 22. FeeCandidate

`FeeCandidate` represents a hypothesis about a fee or pricing rule.

The current model includes:

* description
* amount
* currency
* unit
* vat_status
* pricing_type
* references
* constraints
* source_page
* source_coordinates
* evidence_text
* status
* confidence_score

The target model should support additional concepts such as:

* candidate_id
* evidence IDs
* footnotes
* ambiguities
* explicit provenance
* relationships to other candidates
* validation findings

Pricing must not be forced into a simple numeric amount.

Supported conceptual pricing types include:

* fixed
* variable
* reinvoicing
* cost
* reference
* percentage
* unknown

---

## 23. Status and Confidence

The prototype currently defines:

* `SUPPORTED`
* `PARTIALLY_SUPPORTED`
* `AMBIGUOUS`
* `UNSUPPORTED`

The target architecture should retain these concepts but make their meanings evidence-driven.

### SUPPORTED

The interpretation is directly supported by sufficient evidence.

### PARTIALLY_SUPPORTED

Some important aspects are supported, but one or more required details remain unresolved.

### AMBIGUOUS

Multiple interpretations remain plausible or the available evidence is insufficient to choose one.

### UNSUPPORTED

The proposed interpretation cannot be justified by available evidence.

Confidence should reflect evidence quality and completeness, not merely whether fields are populated.

---

# Part IV — Target Architecture

## 24. Target High-Level Flow

The target architecture is:

```text
PDF
 ↓
Physical Evidence
 ↓
DocumentAgent
 ↓
Logical Block Hypotheses
 ↓
Fee Candidate Hypotheses
 ↓
Evidence Gathering
 ↓
Validation
 ↓
Revision / Investigation
 ↓
Final Structured Records
```

The `DocumentAgent` is the semantic orchestrator.

Deterministic tools provide observations.

The agent interprets those observations.

---

## 25. DocumentAgent

The target `DocumentAgent` should:

* inspect available physical evidence
* identify candidate logical regions
* form logical block hypotheses
* identify possible fee candidates
* determine what evidence is sufficient
* request additional evidence when necessary
* interpret pricing
* interpret footnotes
* interpret constraints
* identify cross-references
* validate interpretations against evidence
* revise hypotheses when evidence conflicts
* preserve ambiguity when evidence is insufficient
* produce final structured records with provenance

The agent should not directly perform low-level PDF extraction when a deterministic tool can provide the observation.

---

## 26. Hypothesis-Driven Processing

Semantic extraction should be treated as hypothesis generation followed by evidence validation.

A typical cycle is:

```text
Observe
 ↓
Hypothesize
 ↓
Gather Evidence
 ↓
Validate
 ↓
Accept / Revise / Investigate
```

A candidate should not be considered final merely because an LLM produced a plausible interpretation.

---

## 27. Structural Grouping and Logical-Block Hypotheses

The target grouping architecture must distinguish:

```text
physical evidence
```

from:

```text
structural grouping
```

and:

```text
semantic interpretation
```

A structural grouping layer may determine whether adjacent physical rows are likely to belong to the same structural region.

That decision should be evidence-backed and inspectable.

Possible outputs are conceptually:

```text
JOIN
SPLIT
AMBIGUOUS
```

An `AMBIGUOUS` result is valid and should not be treated as a failure.

The LLM may later be used to resolve genuinely ambiguous structural cases, but it should not replace deterministic evidence collection.

A logical block may span:

* several rows
* multiple pages
* a fee description and a separate pricing row
* a fee and its footnote
* a pricing statement and its legal limitation

The system must preserve the evidence used to justify the grouping.

---

## 28. Fee Candidate Hypotheses

A fee candidate is an interpretation of one or more pieces of evidence.

The candidate should identify:

* what is being charged
* pricing model
* amount, if explicitly supported
* currency, if explicitly supported
* unit, if supported
* VAT treatment
* constraints
* references
* applicable footnotes
* supporting evidence
* unresolved ambiguity

The agent must not invent values simply to populate a schema.

---

# Part V — Evidence Gathering

## 29. Evidence-Gathering Tools

The target system should provide deterministic tools that the agent can invoke when current evidence is insufficient.

### Page evidence

Retrieve:

* page text
* page dimensions
* all physical rows
* page image

### Region evidence

Retrieve:

* text within a coordinate region
* rows intersecting a region
* rendered image of a region

### Neighborhood evidence

Retrieve:

* rows above and below a selected row
* nearby structural evidence
* adjacent pages

### Search evidence

Find:

* occurrences of a phrase
* references to a tariff
* repeated fee names
* definitions elsewhere in the document

The tools return observations.

The agent decides what those observations mean.

---

## 30. Evidence Sufficiency

The target architecture should explicitly distinguish:

* evidence available
* evidence interpreted
* evidence sufficient
* evidence conflicting
* evidence missing

A candidate should be marked ambiguous when available evidence does not justify a stronger conclusion.

This is preferable to guessing.

---

# Part VI — Validation and Revision

## 31. Validation

Validation should answer questions such as:

* Is the fee description supported?
* Is the amount explicitly supported?
* Is the currency supported?
* Is the unit supported?
* Is VAT treatment supported?
* Is the pricing model supported?
* Are constraints supported?
* Are footnotes correctly associated?
* Are cross-references resolved?
* Does the candidate have sufficient provenance?
* Does evidence conflict with the interpretation?

Validation should be evidence-based rather than field-population-based.

---

## 32. Revision / Investigation Loop

When validation identifies insufficient or conflicting evidence, the agent should investigate.

Conceptually:

```text
Candidate
 ↓
Validate
 ↓
Sufficient? ── Yes → Finalize
 │
 No
 ↓
Identify Missing Evidence
 ↓
Invoke Evidence Tool
 ↓
Update Hypothesis
 ↓
Validate Again
```

The loop should terminate when:

* the interpretation is sufficiently supported
* the evidence remains ambiguous
* a configured investigation limit is reached
* no additional useful evidence can be obtained

The system should preserve the reason for ambiguity rather than silently failing.

---

# Part VII — Provenance

## 33. Evidence Traceability

Every semantic conclusion should be traceable back to source evidence.

At minimum, final records should identify:

* source document
* page
* coordinates
* evidence text
* related physical rows
* supporting evidence IDs

For example:

```text
Research fee — EUR 75/hour + VAT
```

should be traceable to the exact source region containing that statement.

A constraint such as:

```text
maximum 10% of assets, maximum EUR 25,000
```

should likewise retain its own source evidence.

---

## 34. No Unsupported Inference

If the document says:

```text
Cf standard pricing
```

the agent should not invent the standard price.

Instead it should produce a cross-reference and record that the referenced pricing remains unresolved unless evidence elsewhere in the document resolves it.

---

# Part VIII — Target Component Structure

A future implementation should evolve toward components conceptually similar to:

```text
src/
├── agent/
│   └── document_agent.py
│
├── evidence/
│   ├── evidence_manager.py
│   └── evidence_tools.py
│
├── extraction/
│   └── pdf_extractor.py
│
├── domain/
│   ├── models.py
│   ├── hypotheses.py
│   └── provenance.py
│
├── reasoning/
│   ├── block_reasoner.py
│   ├── fee_reasoner.py
│   └── investigation.py
│
├── validation/
│   └── validator.py
│
├── output/
│   └── output_formatter.py
│
└── tests/
```

This is a target organizational concept, not a requirement to create all files immediately.

Existing files should be refactored incrementally rather than discarded.

---

# Part IX — Current-to-Target Gap

## 35. Major Gaps

| Area                    | Current Prototype               | Target v3                               |
| ----------------------- | ------------------------------- | --------------------------------------- |
| Orchestrator            | `DocumentProcessor`             | `DocumentAgent`                         |
| Block creation          | Experimental row grouping       | Evidence-backed structural hypotheses   |
| Semantic interpretation | Hard-coded rules                | Agent reasoning                         |
| Fee extraction          | String rules                    | Evidence-backed hypotheses              |
| Evidence gathering      | Limited                         | Tool-driven investigation               |
| Validation              | Field-based rules               | Evidence-based validation               |
| Revision                | None                            | Iterative investigation/revision        |
| Cross-references        | Flagged only                    | Investigated and resolved when possible |
| Constraints             | Hard-coded demonstration        | Agent interpretation with provenance    |
| Provenance              | Partial                         | Explicit evidence graph/links           |
| PDF extraction          | Deterministic evidence pipeline | Deterministic extraction tools          |
| Output                  | Two formatting paths            | Single canonical formatter              |

---

## 36. Architectural Direction

The existing prototype should be treated as the foundation rather than as production architecture.

The implementation strategy should be incremental:

1. preserve current domain concepts
2. establish robust evidence and provenance
3. maintain deterministic PDF evidence tools
4. establish validated structural evidence
5. introduce structural grouping decisions
6. introduce the `DocumentAgent`
7. replace hard-coded fee rules with agent reasoning
8. introduce evidence-gathering tools
9. introduce evidence-aware validation
10. introduce revision/investigation loops
11. consolidate output formatting
12. build end-to-end tests against real documents
13. validate on additional document types

The goal is not to make deterministic extraction increasingly clever.

The goal is to give the agent reliable observations and make semantic conclusions traceable.

---

# Part X — Non-Goals and Guardrails

## 37. Guardrails

The target architecture must not:

* hallucinate fees
* invent amounts
* invent currencies
* silently resolve unknown references
* treat every physical row as a fee
* assume nearby text automatically belongs to a fee
* hide ambiguity
* discard source coordinates
* discard source text
* allow an LLM-generated conclusion to become authoritative without evidence

---

# Part XI — Current Validated Implementation State

## 38. Authoritative Files for Agents

When beginning work related to physical rows, boundary analysis, or logical grouping, agents should start with:

```text
AGENTS.md
ARCHITECTURE.md

src/evidence_tools.py
src/models.py
src/logical_block_generator.py
src/boundary_evidence.py

data/visual_span_inspection.json
data/authoritative_boundary_ground_truth.json
```

Agents should NOT recreate:

* the PhysicalRow extraction pipeline
* the VisualSpan inspection artifact
* the boundary ground truth
* duplicate BoundaryEvidence implementations

Broad repository exploration should only be performed when the specific task requires it.

---

## 39. Validated Physical Evidence Pipeline

The authoritative physical evidence pipeline is:

```text
PDF
 ↓
PDFEvidenceRetriever / evidence_tools.py
 ↓
PhysicalRow
 ↓
VisualSpan enrichment
 ↓
data/visual_span_inspection.json
```

`data/visual_span_inspection.json` is a validated snapshot of the PhysicalRows produced by the live PDF extraction pipeline.

---

## 40. Live Extraction Validation

The live `PDFEvidenceRetriever` output has been compared against:

```text
data/visual_span_inspection.json
```

for all 20 pages of the current ING Luxembourg PDF evidence set.

Validated results:

```text
Pages: 20
PhysicalRows: 572

Row count mismatches: 0
Text mismatches: 0
Coordinate mismatches: 0
VisualSpan-count mismatches: 0
```

Therefore the JSON evidence artifact and the live extraction currently represent the same PhysicalRow dataset.

---

## 41. VisualSpan Status

VisualSpan extraction and association are complete and validated.

Every PhysicalRow in the current 20-page evidence set has VisualSpan data.

VisualSpan data is observational evidence only.

It does not by itself determine:

* semantic meaning
* fee structure
* logical grouping
* pricing interpretation

---

## 42. Authoritative Boundary Ground Truth

The current machine-readable ground truth is:

```text
data/authoritative_boundary_ground_truth.json
```

It contains:

```text
12 boundaries
5 JOIN
6 SPLIT
1 AMBIGUOUS
```

Every boundary:

* references an existing page
* references valid rows
* uses adjacent rows
* uses 1-based row numbering

The file contains structural decisions and qualitative reasons only.

Measurements such as:

* gaps
* coordinates
* fonts
* margins
* overlap

are always derived from:

```text
data/visual_span_inspection.json
```

and must not be duplicated as authoritative ground-truth measurements.

This ground truth is frozen and should not be regenerated or replaced without an explicit architectural decision.

---

## 43. BoundaryEvidence Status

The project is currently developing a deterministic `BoundaryEvidence` layer.

Its responsibility is to observe and expose structural evidence about an adjacent PhysicalRow boundary.

It may calculate observations such as:

* vertical gap
* relative/local spacing
* horizontal relationship
* left-margin relationship
* typography relationship
* VisualSpan composition
* local neighborhood context

BoundaryEvidence is an evidence producer, not a semantic decision maker.

It must not independently determine:

```text
JOIN
SPLIT
AMBIGUOUS
```

unless and until a separate structural decision layer is explicitly introduced.

---

## 44. Logical Block Status

`src/logical_block_generator.py` currently contains experimental logical-grouping work.

That work is NOT yet considered the final grouping architecture.

The current gap-based `_BlockSplitter` is an experimental baseline only.

Do not assume that its current output represents the desired final logical-block structure.

---

## 45. Current Design Direction

The intended future flow is:

```text
PhysicalRows
    ↓
VisualSpan evidence
    ↓
BoundaryEvidence
    ↓
Deterministic structural interpretation
    ↓
JOIN / SPLIT / AMBIGUOUS
    ↓
LLM assistance only for unresolved semantic ambiguity
    ↓
Logical structural groups / hypotheses
    ↓
Fee candidate reasoning
    ↓
Evidence-backed validation
```

The distinction between:

```text
structural evidence
```

and:

```text
semantic interpretation
```

must be preserved.

---

## 46. Development Status

```text
PhysicalRow extraction: validated
VisualSpan extraction: validated
Evidence JSON: validated
Live-vs-JSON consistency: validated
Boundary ground truth: frozen
BoundaryEvidence: in development
Logical block grouping: experimental
Semantic LLM reasoning: not yet integrated
```

Only add implementation details to this section after they have been verified.

---

## 47. Empirical Boundary Evidence Findings

Geometry and typography alone are insufficient to determine all JOIN/SPLIT/AMBIGUOUS boundaries.

The 12 frozen boundary cases include visually similar cases with different structural outcomes.

Candidate text-structure evidence such as numeric-token count, currency/amount presence, and table/separator patterns provides useful contextual observations.

These text features do not independently determine JOIN/SPLIT/AMBIGUOUS.

Text-structure features must remain observational evidence and must not become hard-coded boundary rules without further validation.

B11 and B12 are particularly important because their visual evidence is highly similar while their ground-truth outcomes differ (SPLIT vs AMBIGUOUS).

# Appendix A — Supplied Prototype Files

The initial prototype consists of:

```text
src/document_processor.py
src/evidence_manager.py
src/fee_candidate_extractor.py
src/logical_block_generator.py
src/models.py
src/output_formatter.py
src/validator.py
src/test_pipeline.py
```

The supplied test data includes:

```text
documents/ing_luxembourg.pdf
```
