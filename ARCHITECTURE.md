# Financial Document Agent v3 — Evidence-Driven Document Agent

## Purpose
v3 replaces the v2 fixed row-based extraction pipeline with an evidence-driven agent.

The fundamental problem is:
PDF physical rows do not necessarily correspond to logical fee entities.
A logical fee may:
- span multiple physical rows
- contain multiple pricing components
- have pricing separated from its description
- have footnotes modifying one or more fees
- reference another section or tariff
- contain variable pricing such as €75/hour + VAT
- contain non-numeric pricing such as reinvoicing the customer at cost
- contain constraints such as cannot exceed 10% of assets, maximum EUR 25,000

The agent must therefore reason over evidence rather than assume that rows equal fees.

## Scope
This document describes the target architecture for Financial Document Agent v3. It outlines the conceptual design, components, and principles that should guide the implementation. The current implementation is a prototype that demonstrates some concepts but does not yet fully implement all architectural elements described here.

## High-Level Architecture
The architecture is:
PDF → Physical Evidence → Document Agent → Logical Block Hypotheses → Fee Candidate Hypotheses → Evidence Gathering → Validation → Revision / Investigation → Final Structured Records

The DocumentAgent is the orchestrator. Deterministic tools provide observations only. The LLM/agent interprets those observations.

### Core Design Principle
Deterministic tools are "dumb observers."
They may:
- extract text
- extract coordinates
- render pages
- inspect regions
- return page dimensions
- identify physical rows
- return raw evidence

They must NOT:
- decide what constitutes a fee
- assign semantic meaning
- decide that two rows belong together
- invent missing values
- interpret legal constraints
- determine the meaning of a cross-reference

Those decisions belong to the agent.


4. Current Implementation Characteristics

The prototype currently:

stores physical rows as evidence
creates one logical block per page
assigns every logical block the type fee_section
extracts fee candidates using deterministic hard-coded rules
validates candidates using simple status rules
produces structured dictionary output
contains an OutputFormatter capable of producing JSON, although the supplied DocumentProcessor does not currently use it

The prototype does not currently implement:

a DocumentAgent orchestrator
LLM-based semantic interpretation
logical-block hypothesis generation
fee-candidate hypothesis generation
evidence-gathering loops
evidence sufficiency evaluation
revision/investigation loops
iterative hypothesis validation
semantic interpretation of cross-references
semantic interpretation of legal constraints
production PDF extraction
a persistent evidence graph or evidence store
Part II — Current Pipeline Components
5. DocumentProcessor

File: src/document_processor.py

DocumentProcessor is the current top-level orchestrator.

Its current sequence is:

Store each supplied PhysicalRow through EvidenceManager.
Create logical blocks through LogicalBlockGenerator.
Extract fee candidates through FeeCandidateExtractor.
Validate all blocks through Validator.
Format the result into a dictionary.
Current logical block behavior

The current logical-block creation is explicitly simplified.

It:

identifies the distinct page numbers in the physical evidence
retrieves all rows for each page
calculates a bounding rectangle covering those rows
concatenates all row text with spaces
creates one logical block per page

Therefore, the current implementation does not actually infer logical document blocks.

This is an important prototype limitation.

6. EvidenceManager

File: src/evidence_manager.py

EvidenceManager manages physical evidence.

Current responsibilities:

store PhysicalRow objects
store EvidenceSource objects
retrieve all rows belonging to a page
return all stored evidence

It does not currently perform semantic interpretation.

The manager is therefore consistent with the architectural principle that physical evidence should be preserved independently from semantic interpretation.

7. LogicalBlockGenerator

File: src/logical_block_generator.py

LogicalBlockGenerator creates and stores LogicalDocumentBlock objects.

Current responsibilities:

create logical blocks
assign sequential block IDs such as block_000
create EvidenceSource objects from physical rows
associate physical rows with the block
store blocks
retrieve blocks by page
retrieve all blocks
Current limitation

Every block is currently created with:

type = "fee_section"

This is not semantic inference.

The target architecture requires the agent to determine whether evidence represents a fee section, description block, pricing rule, footnote, cross-reference, or another semantic unit.

8. FeeCandidateExtractor

File: src/fee_candidate_extractor.py

The current extractor is deterministic and rule-based.

It is a prototype demonstration, not a production fee extraction engine.

Current demonstrated rules
Research fee

If the block contains:

research fee

the prototype creates:

description: Research fee
amount: 75.0
currency: EUR
unit: hour
VAT status: additional
pricing type: variable
evidence text: Research fee € 75/hour + VAT*
initial status: PARTIALLY_SUPPORTED
initial confidence: 0.7

The amount and other values are hard-coded demonstration values.

External research fee

If the block contains:

external research fee

the prototype creates a candidate with:

description: External research fee
pricing type: reinvoicing
evidence text describing reinvoicing at cost
status: AMBIGUOUS
confidence: 0.4
Combined research fee constraint

If the block contains both:

cannot exceed

and:

10%

the prototype creates a constraint candidate representing:

maximum percentage: 10%
maximum amount: EUR 25,000

The evidence text records the stated constraint that internal plus external research fees cannot exceed 10% of assets, subject to the legal limit.

Standard pricing cross-reference

If the block contains:

cf standard pricing

the prototype creates a candidate representing an unresolved reference to standard pricing.

It is marked ambiguous with a low confidence score.

Architectural significance

These rules demonstrate the kinds of semantic facts that the target agent must eventually discover.

They should not become a large collection of hard-coded string rules.

The target system should use deterministic tools to expose evidence and allow the agent to interpret that evidence.

9. Validator

File: src/validator.py

The current validator applies simple deterministic rules.

Candidate validation

If both amount and currency exist:

SUPPORTED

and confidence is increased by 0.2, bounded to the range 0.0–1.0.

If neither amount nor currency exists:

reinvoicing or cost → PARTIALLY_SUPPORTED
otherwise → AMBIGUOUS

If only partial pricing information exists:

PARTIALLY_SUPPORTED

and confidence is increased by 0.1.

Block validation

Block status is derived from candidate statuses.

Priority is:

any SUPPORTED candidate → block SUPPORTED
otherwise any PARTIALLY_SUPPORTED candidate → block PARTIALLY_SUPPORTED
otherwise any AMBIGUOUS candidate → block AMBIGUOUS
otherwise → UNSUPPORTED
Target limitation

This validator does not determine whether an interpretation is actually supported by sufficient evidence.

The target architecture needs evidence-aware validation rather than simply checking whether fields are populated.

10. OutputFormatter

File: src/output_formatter.py

OutputFormatter formats logical blocks and fee candidates into structured JSON.

It includes:

document analysis metadata
logical blocks
fee candidates
evidence sources
source coordinates
status
confidence

It removes None values from fee candidate output.

Current architectural inconsistency

The supplied DocumentProcessor has its own output-formatting method.

It therefore does not currently call OutputFormatter.

There are consequently two output-formatting paths in the prototype.

This should be resolved during implementation.

11. test_pipeline.py

File: src/test_pipeline.py

The current test harness creates mock PhysicalRow objects representing extracted PDF data.

It then passes them to DocumentProcessor and prints the resulting blocks and candidates.

It demonstrates:

research fee extraction
external research fee extraction
combined research fee constraint extraction
standard pricing cross-reference extraction

It does not perform actual PDF extraction.

It is therefore a demonstration/test harness rather than an end-to-end document-processing test.

Part III — Current Domain Model
12. PhysicalRow

PhysicalRow represents a physical observation extracted from a PDF.

Current fields:

page_number
coordinates
text
words

The target architecture should additionally provide a stable row_id.

A physical row is evidence, not a semantic fee entity.

13. EvidenceSource

EvidenceSource represents traceable source evidence.

Current fields:

source_type
page_number
coordinates
content
context

The target model should additionally support stable evidence identifiers and extensible metadata.

Possible evidence types include:

text
coordinate region
image
page

Evidence must remain traceable to the original document location.

14. LogicalDocumentBlock

LogicalDocumentBlock is the central semantic abstraction.

A block represents a coherent logical section of the document and may contain:

multiple physical rows
multiple fee candidates
descriptions
amounts
currencies
units
pricing rules
footnotes
constraints
cross-references

Current fields include:

block_id
type
page_number
coordinates
text_content
physical_rows
evidence_sources
fee_candidates
status
ambiguities
confidence_score
interpretation_notes

The target architecture should preserve all physical evidence supporting the block.

Possible semantic block types include:

fee section
description block
pricing rule
footnote block
cross-reference block
other semantic document unit

The agent, rather than the extraction tool, should determine the semantic classification.

15. FeeCandidate

FeeCandidate represents a hypothesis about a fee or pricing rule.

The current model includes:

description
amount
currency
unit
vat_status
pricing_type
references
constraints
source_page
source_coordinates
evidence_text
status
confidence_score

The target model should support additional concepts such as:

candidate_id
evidence IDs
footnotes
ambiguities
explicit provenance
relationships to other candidates
validation findings

Pricing must not be forced into a simple numeric amount.

Supported conceptual pricing types should include:

fixed
variable
reinvoicing
cost
reference
percentage
unknown
16. Status and Confidence

The prototype currently defines:

SUPPORTED
PARTIALLY_SUPPORTED
AMBIGUOUS
UNSUPPORTED

The target architecture should retain these concepts but make their meanings evidence-driven.

SUPPORTED

The interpretation is directly supported by sufficient evidence.

PARTIALLY_SUPPORTED

Some important aspects are supported, but one or more required details remain unresolved.

AMBIGUOUS

Multiple interpretations remain plausible or the available evidence is insufficient to choose one.

UNSUPPORTED

The proposed interpretation cannot be justified by available evidence.

Confidence should reflect the quality and completeness of evidence, not merely the presence of populated fields.

Part IV — Target Architecture
17. Target High-Level Flow

The target architecture is:

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

The DocumentAgent is the semantic orchestrator.

Deterministic tools provide observations.

The agent interprets those observations.

18. Core Design Principle — Deterministic Tools Are Observers

Deterministic tools are intentionally "dumb observers."

They may:

extract text
extract coordinates
extract words
identify physical rows
render PDF pages
inspect page regions
return page dimensions
retrieve source evidence
return raw OCR/extraction results
locate text occurrences
retrieve nearby rows
retrieve neighboring pages

They must not:

decide what constitutes a fee
assign semantic meaning
decide that two rows belong together
invent missing values
interpret legal constraints
resolve the meaning of a cross-reference
decide whether a pricing statement applies to a particular fee

Those decisions belong to the agent.

19. DocumentAgent

The target DocumentAgent is responsible for semantic reasoning and orchestration.

It should:

inspect available physical evidence
identify candidate logical regions
form logical block hypotheses
identify possible fee candidates
determine what evidence is sufficient
request additional evidence when necessary
interpret pricing
interpret footnotes
interpret constraints
identify cross-references
validate interpretations against evidence
revise hypotheses when evidence conflicts
preserve ambiguity when evidence is insufficient
produce final structured records with provenance

The agent should not directly perform low-level PDF extraction when a deterministic tool can provide the observation.

20. Hypothesis-Driven Processing

Semantic extraction should be treated as hypothesis generation followed by evidence validation.

A typical cycle is:

Observe
  ↓
Hypothesize
  ↓
Gather Evidence
  ↓
Validate
  ↓
Accept / Revise / Investigate

A candidate should not be considered final merely because an LLM produced a plausible interpretation.

21. Logical Block Hypotheses

The agent should determine which physical evidence belongs together.

A logical block may span:

several rows
multiple pages
a fee description and a separate pricing row
a fee and its footnote
a pricing statement and its legal limitation

The system must preserve the evidence used to justify the grouping.

22. Fee Candidate Hypotheses

A fee candidate is an interpretation of one or more pieces of evidence.

The candidate should identify:

what is being charged
pricing model
amount, if explicitly supported
currency, if explicitly supported
unit, if supported
VAT treatment
constraints
references
applicable footnotes
supporting evidence
unresolved ambiguity

The agent must not invent values simply to populate a schema.

Part V — Evidence Gathering
23. Evidence-Gathering Tools

The target system should provide deterministic tools that the agent can invoke when current evidence is insufficient.

Examples include:

Page evidence

Retrieve:

page text
page dimensions
all physical rows
page image
Region evidence

Retrieve:

text within a coordinate region
rows intersecting a region
rendered image of a region
Neighborhood evidence

Retrieve:

rows above and below a selected row
nearby blocks
adjacent pages
Search evidence

Find:

occurrences of a phrase
references to a tariff
repeated fee names
definitions elsewhere in the document

The tools return observations. The agent decides what those observations mean.

24. Evidence Sufficiency

The target architecture should explicitly distinguish:

evidence available
evidence interpreted
evidence sufficient
evidence conflicting
evidence missing

A candidate should be marked ambiguous when the available evidence does not justify a stronger conclusion.

This is preferable to guessing.

Part VI — Validation and Revision
25. Validation

Validation should answer questions such as:

Is the fee description supported?
Is the amount explicitly supported?
Is the currency supported?
Is the unit supported?
Is VAT treatment supported?
Is the pricing model supported?
Are constraints supported?
Are footnotes correctly associated?
Are cross-references resolved?
Does the candidate have sufficient provenance?
Does evidence conflict with the interpretation?

Validation should be evidence-based rather than field-population-based.

26. Revision / Investigation Loop

When validation identifies insufficient or conflicting evidence, the agent should investigate.

Conceptually:

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

The loop should terminate when:

the interpretation is sufficiently supported
the evidence remains ambiguous
a configured investigation limit is reached
no additional useful evidence can be obtained

The system should preserve the reason for ambiguity rather than silently failing.

Part VII — Provenance
27. Evidence Traceability

Every semantic conclusion should be traceable back to source evidence.

At minimum, final records should be able to identify:

source document
page
coordinates
evidence text
related physical rows
supporting evidence IDs

For example:

Research fee — EUR 75/hour + VAT

should be traceable to the exact source region containing that statement.

A constraint such as:

maximum 10% of assets, maximum EUR 25,000

should likewise retain its own source evidence.

28. No Unsupported Inference

The architecture explicitly prohibits unsupported semantic invention.

If the document says:

Cf standard pricing

the agent should not invent the standard price.

Instead it should produce a cross-reference and record that the referenced pricing remains unresolved unless evidence elsewhere in the document resolves it.

Part VIII — Target Component Structure

A future implementation should evolve toward components conceptually similar to:

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

This is a target organizational concept, not a requirement to create all files immediately.

The existing files should be refactored incrementally rather than discarded.

Part IX — Current-to-Target Gap
29. Major Gaps
Area	Current Prototype	Target v3
Orchestrator	DocumentProcessor	DocumentAgent
Block creation	One block per page	Agent-generated hypotheses
Semantic interpretation	Hard-coded rules	Agent reasoning
Fee extraction	String rules	Evidence-backed hypotheses
Evidence gathering	None	Tool-driven investigation
Validation	Field-based rules	Evidence-based validation
Revision	None	Iterative investigation/revision
Cross-references	Flagged only	Investigated and resolved when possible
Constraints	Hard-coded demonstration	Agent interpretation with provenance
Provenance	Partial	Explicit evidence graph/links
PDF extraction	External input/mock rows	Deterministic extraction tools
Output	Two formatting paths	Single canonical formatter
30. Architectural Direction

The existing prototype should be treated as the foundation rather than as production architecture.

The implementation strategy should be incremental:

preserve the current domain concepts
establish robust evidence and provenance
introduce deterministic PDF evidence tools
introduce the DocumentAgent
replace page-based block creation with agent hypotheses
replace hard-coded fee rules with agent reasoning
introduce evidence-gathering tools
introduce evidence-aware validation
introduce revision/investigation loops
consolidate output formatting
build end-to-end tests against real documents

The goal is not to make the deterministic extractor increasingly clever.

The goal is to give the agent reliable observations and make its semantic conclusions traceable.

Part X — Non-Goals and Guardrails
31. Guardrails

The target architecture must not:

hallucinate fees
invent amounts
invent currencies
silently resolve unknown references
treat every physical row as a fee
assume nearby text automatically belongs to a fee
hide ambiguity
discard source coordinates
discard source text
allow an LLM-generated conclusion to become authoritative without evidence
32. Architectural Principle

The central principle of Financial Document Agent v3 is:

Observe deterministically. Reason semantically. Preserve evidence. Validate conclusions. Investigate uncertainty.

This principle should guide future implementation decisions.

Appendix A — Supplied Prototype Files

The initial prototype consists of:

src/document_processor.py
src/evidence_manager.py
src/fee_candidate_extractor.py
src/logical_block_generator.py
src/models.py
src/output_formatter.py
src/validator.py
src/test_pipeline.py

The supplied test data includes:

documents/ing_luxembourg.pdf