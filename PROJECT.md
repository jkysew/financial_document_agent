# Financial Document Agent v3

## 1. Project Purpose

Financial Document Agent v3 is a document-processing pipeline for
extracting structured fee information from financial tariff documents
while preserving a traceable chain back to the original PDF evidence.

The design separates deterministic document processing from later
semantic interpretation. The current implementation deliberately avoids
LLM/AI logic in the physical-evidence and logical-block stages.

The current pipeline is:

``` text
PDF
  ↓
Physical Evidence Extraction
  ↓
PhysicalRow evidence
  ↓
Deterministic Logical Block Grouping
  ↓
LogicalDocumentBlock
  ↓
Fee Candidate Extraction
  ↓
Validation
  ↓
Formatted Output
```

The project is currently being developed around the ING Luxembourg
tariff brochure as the primary real-document test case.

------------------------------------------------------------------------

## 2. Design Principles

### Evidence first

The original document evidence is preserved as physical rows containing:

-   page number
-   coordinates
-   text
-   word-level information
-   row identity

The physical evidence is the foundation for all downstream processing.

### Deterministic before semantic

The current logical-block stage uses spatial relationships between
physical rows. It does not attempt to understand the meaning of the
text.

This is intentional. Semantic interpretation should occur only after
reliable physical evidence and document structure have been established.

### Traceability

Every downstream object should be traceable back to the evidence from
which it was derived.

The intended evidence chain is:

``` text
PDF
 ↓
PhysicalRow
 ↓
LogicalDocumentBlock
 ↓
FeeCandidate
 ↓
Validation
```

### Preserve existing pipeline components

The v3 implementation builds on the existing components rather than
replacing the pipeline with a new architecture.

------------------------------------------------------------------------

## 3. Current Source Components

### `src/models.py`

Defines the core data structures used throughout the pipeline.

Important models include:

-   `PhysicalRow`
-   `LogicalDocumentBlock`
-   `EvidenceSource`
-   `FeeCandidate`
-   `Status`

`PhysicalRow` represents physical evidence extracted from a PDF.

`LogicalDocumentBlock` represents a deterministic grouping of related
physical rows.

`FeeCandidate` represents a possible fee extracted from a logical block.

------------------------------------------------------------------------

### `src/evidence_tools.py`

Provides PDF evidence retrieval functionality.

The evidence tools can:

-   retrieve evidence from pages
-   retrieve physical rows from pages
-   search document text
-   retrieve evidence from coordinate regions
-   create evidence sources from physical rows
-   create evidence sources from coordinate regions
-   retrieve all pages

The current implementation successfully processes the ING Luxembourg PDF
into physical-row evidence.

------------------------------------------------------------------------

### `src/evidence_manager.py`

Maintains the physical evidence used by the document processor.

The `EvidenceManager` stores `PhysicalRow` objects and provides access
to rows associated with pages.

It forms the bridge between PDF evidence retrieval and the logical-block
generation stage.

------------------------------------------------------------------------

### `src/logical_block_generator.py`

Creates logical document blocks from physical rows.

The current implementation contains two related capabilities:

#### `create_logical_block()`

Creates a `LogicalDocumentBlock` from a supplied collection of physical
rows and associated metadata.

#### `create_blocks_from_rows()`

This is the current deterministic grouping algorithm used by
`DocumentProcessor`.

It:

1.  accepts physical rows
2.  orders/processes them spatially
3.  groups rows according to their spatial relationships
4.  calculates block coordinates
5.  combines row text into block text
6.  creates `LogicalDocumentBlock` objects

The grouping is based on document layout, including vertical spacing
between rows.

It does **not** use:

-   an LLM
-   semantic classification
-   AI interpretation
-   fee meaning
-   business rules about what the text means

The current real-document test produced:

``` text
572 physical rows
20 pages
48 logical blocks
```

This confirms that the deterministic grouping is producing multiple
blocks rather than simply creating one block per page.

------------------------------------------------------------------------

### `src/document_processor.py`

The `DocumentProcessor` is the main orchestration component for the v3
pipeline.

Its current flow is:

#### Step 1 --- Store physical evidence

Each `PhysicalRow` is added to the `EvidenceManager`.

#### Step 2 --- Create logical blocks

The processor calls:

``` python
self.block_generator.create_blocks_from_rows(
    self.evidence_manager.physical_rows
)
```

This replaced the earlier demonstration implementation that created one
logical block per page.

#### Step 3 --- Extract fee candidates

The resulting logical blocks are passed to `FeeCandidateExtractor`.

#### Step 4 --- Validate

The blocks are passed to `Validator`.

#### Step 5 --- Format output

The validated blocks are converted into the current output dictionary
structure.

The processor therefore remains an orchestrator rather than containing
the grouping algorithm itself.

------------------------------------------------------------------------

### `src/fee_candidate_extractor.py`

Extracts fee candidates from logical document blocks.

This component operates after physical evidence and logical structure
have been established.

The intended responsibility is to identify possible fee information from
the contents of logical blocks.

It is downstream of deterministic document structuring.

------------------------------------------------------------------------

### `src/validator.py`

Validates the generated logical blocks and their extracted information.

Validation is a separate pipeline stage so that extraction and
validation remain independently testable.

------------------------------------------------------------------------

### `src/output_formatter.py`

Provides output-formatting functionality for pipeline results.

The project should continue to use a dedicated formatting layer rather
than mixing presentation concerns into the evidence or grouping
components.

------------------------------------------------------------------------

### `src/inspection_tool.py`

Provides inspection/export functionality for examining the physical
evidence.

The current inspection tests confirm that evidence can be exported and
that the resulting structure is valid.

------------------------------------------------------------------------

### `src/inspect_evidence.py`

Utility entry point for inspecting extracted evidence.

------------------------------------------------------------------------

### `src/run_inspection_test.py`

Utility/test runner associated with the evidence inspection workflow.

------------------------------------------------------------------------

## 4. Current Evidence Artifacts

The current real-document evidence is stored under:

``` text
data/evidence/
```

The primary artifact is:

``` text
data/evidence/ing_luxembourg_evidence_output.json
```

It contains the physical evidence extracted from the 20-page ING
Luxembourg tariff document.

The current evidence contains:

``` text
20 pages
572 physical rows
```

A typical physical row contains information such as:

``` json
{
  "row_id": "...",
  "page_number": 1,
  "coordinates": {
    "x1": 79.82,
    "y1": 45.46,
    "x2": 392.13,
    "y2": 80.44
  },
  "text": "Tariff brochure's extract",
  "words": [...]
}
```

The physical evidence JSON is considered the lower-level evidence layer
and should not be confused with logical document structure.

------------------------------------------------------------------------

## 5. Logical Block Evidence

The current implementation creates logical blocks in memory.

A logical block contains information such as:

-   block ID
-   block type
-   page number
-   bounding coordinates
-   combined text content
-   associated physical rows
-   status
-   confidence information
-   fee candidates after downstream extraction

The current integration test demonstrated that the real document
produces:

``` text
572 physical rows
    ↓
48 logical blocks
```

A future step is to persist these logical blocks as a separate derived
evidence artifact, for example:

``` text
data/evidence/ing_luxembourg_logical_blocks.json
```

The logical-block artifact should preserve traceability to the physical
evidence, preferably through physical-row identifiers rather than
unnecessarily duplicating the entire physical evidence dataset.

------------------------------------------------------------------------

## 6. Fee Candidate Stage

After logical blocks have been created, the `FeeCandidateExtractor`
processes the blocks.

The resulting candidates can contain fields including:

-   description
-   amount
-   currency
-   unit
-   VAT status
-   pricing type
-   references
-   constraints
-   source page
-   source coordinates
-   evidence text
-   status
-   confidence score

The fee candidate stage should remain downstream from deterministic
document structuring.

------------------------------------------------------------------------

## 7. Validation Stage

The `Validator` receives the generated logical blocks after fee
candidate extraction.

Its responsibility is to validate the resulting structures and candidate
information rather than to determine the physical document layout.

This separation allows:

``` text
Evidence retrieval
        ↓
Layout grouping
        ↓
Candidate extraction
        ↓
Validation
```

to be tested independently.

------------------------------------------------------------------------

## 8. Tests

The project currently contains tests for the principal components.

### Evidence tests

`src/test_evidence_tools.py`

Tests PDF evidence retrieval functionality, including:

-   page retrieval
-   physical-row retrieval
-   coordinate-based evidence retrieval
-   evidence-source creation
-   text search
-   initialization

### Inspection tests

`src/test_inspection.py`

Tests evidence inspection/export functionality.

### Model tests

`src/test_models.py`

Tests creation of the core data models.

### Pipeline tests

`src/test_pipeline.py`

Contains existing pipeline-level tests.

### Simple tests

`src/test_simple.py`

Contains additional lightweight tests.

### Logical block integration test

`src/test_logical_block_integration.py`

This is the current real-data integration test for deterministic
logical-block grouping.

It:

1.  loads the real evidence JSON
2.  handles the actual nested JSON structure
3.  converts physical evidence into `PhysicalRow` objects
4.  invokes `DocumentProcessor.process_document()`
5.  verifies processing completes
6.  verifies logical blocks are produced
7.  reports diagnostic block information
8.  verifies block structure
9.  verifies page consistency
10. verifies coordinates and text are present

The current result is:

``` text
Loaded 572 physical rows
Data spans 20 pages
Successfully created 48 logical blocks
OK
```

------------------------------------------------------------------------

## 9. Current Test Status

The existing unit test suite currently passes:

``` text
Ran 15 tests
OK
```

The real-evidence logical-block integration test also passes:

``` text
Loaded 572 physical rows
Data spans 20 pages
Successfully created 48 logical blocks
OK
```

These tests establish a safe baseline for continuing development.

------------------------------------------------------------------------

## 10. Current Architecture

The current implementation can be viewed as four major layers.

### Layer 1 --- Evidence

``` text
PDF
 ↓
evidence_tools.py
 ↓
PhysicalRow
 ↓
EvidenceManager
```

This layer answers:

> What physically exists in the source document?

### Layer 2 --- Document Structure

``` text
PhysicalRow
 ↓
LogicalBlockGenerator
 ↓
LogicalDocumentBlock
```

This layer answers:

> Which physical rows belong together spatially?

The current implementation uses deterministic spatial grouping.

### Layer 3 --- Business Information Extraction

``` text
LogicalDocumentBlock
 ↓
FeeCandidateExtractor
 ↓
FeeCandidate
```

This layer answers:

> What possible fee information is contained in the structured document
> block?

### Layer 4 --- Validation and Output

``` text
FeeCandidate / LogicalDocumentBlock
 ↓
Validator
 ↓
Output formatting
```

This layer answers:

> Is the resulting information structurally and logically acceptable,
> and how should it be returned?

------------------------------------------------------------------------

## 11. Current Repository Structure

The important current structure is:

``` text
financial_document_agent_v3/
│
├── data/
│   └── evidence/
│       └── ing_luxembourg_evidence_output.json
│
├── src/
│   ├── document_processor.py
│   ├── evidence_manager.py
│   ├── evidence_tools.py
│   ├── fee_candidate_extractor.py
│   ├── inspection_tool.py
│   ├── inspect_evidence.py
│   ├── logical_block_generator.py
│   ├── models.py
│   ├── output_formatter.py
│   ├── validator.py
│   │
│   ├── test_evidence_tools.py
│   ├── test_inspection.py
│   ├── test_logical_block_integration.py
│   ├── test_models.py
│   ├── test_pipeline.py
│   └── test_simple.py
│
└── PROJECT.md
```

------------------------------------------------------------------------

## 12. Important Current Design Decision

The transition from the earlier one-block-per-page demonstration to
deterministic spatial grouping is a significant architectural
improvement.

Previously:

``` text
Physical rows
    ↓
one block per page
```

Current implementation:

``` text
Physical rows
    ↓
deterministic spatial grouping
    ↓
multiple logical blocks per page where appropriate
```

For the current ING Luxembourg document:

``` text
20 pages
572 physical rows
48 logical blocks
```

This gives downstream fee extraction a more useful document structure
without introducing semantic assumptions.

------------------------------------------------------------------------

## 13. Planned / Future Work

The following items are logical next steps but are **not yet part of the
current implementation**.

### Persist logical blocks

Create a derived logical-block evidence JSON artifact:

``` text
data/evidence/ing_luxembourg_logical_blocks.json
```

It should maintain traceability to physical evidence.

### Improve logical-block inspection

Provide inspection capabilities for:

-   block boundaries
-   physical rows contained in each block
-   block-to-row relationships
-   block text
-   block coordinates

### Strengthen integration tests

Add assertions around:

-   expected block counts/ranges
-   page-level grouping
-   physical-row traceability
-   deterministic repeatability

### Continue fee candidate extraction

Improve fee extraction only after the physical and logical evidence
layers are stable.

### Maintain deterministic boundaries

Semantic/LLM processing should not be introduced into the physical
evidence or deterministic grouping stages unless there is a specific
architectural reason to do so.

------------------------------------------------------------------------

## 14. Development Rule

When modifying the pipeline:

1.  Preserve the physical evidence layer.
2.  Keep deterministic document structure separate from semantic
    interpretation.
3.  Maintain traceability from every derived object to its source
    evidence.
4.  Add or update tests before making large architectural changes.
5.  Run the existing test suite after changes.
6.  Run the real-evidence integration test when changing document
    grouping.
7.  Commit stable checkpoints to Git before beginning the next
    architectural change.

The current passing state should be treated as a baseline for future
development.
