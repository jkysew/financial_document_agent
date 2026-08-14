# AGENTS.md

## Project

Financial Document Agent v3

A Python-based financial-document processing pipeline that converts PDF evidence into structured semantic information while preserving traceability back to the original document.

The pipeline separates deterministic document processing from LLM-assisted interpretation.

---

## Primary Objective

Build a reliable, evidence-first financial document processing system.

The system must:

- Preserve the original PDF evidence.
- Maintain deterministic physical-row extraction.
- Preserve coordinates and source locations.
- Build logical document blocks from physical evidence.
- Extract and normalize financial information such as fees.
- Maintain traceability from interpreted data back to source evidence.
- Prefer deterministic processing where possible.
- Use LLMs only where interpretation or ambiguity requires them.

Accuracy and evidence preservation are more important than aggressive inference.

---

## Environment

### Operating System

Windows 11

### Project Location

```text
D:\John\financial_document_agent_v3

### Test Command

Always run the test suite from the project root using:

```powershell
python -m pytest -q

## Agent Operating Rules

You are working directly in the repository workspace.

### Tool usage

When you need to inspect a file, use the available file-reading tool.

When you need to modify a file, use the available file-editing tool.
Do not merely describe the edit and do not output pseudo-tool syntax such as:

TOOL_NAME: edit_existing_file
BEGIN_ARG: filepath(string):The path of the file to edit, relative to the root of the workspace.

When you need to run a command, use the available terminal tool.
Do not write a simulated tool call as text.

Never invent tool names. Use only tools actually provided by the agent environment.

### Repository safety

Before modifying code:
1. Inspect the relevant existing implementation.
2. Make the smallest change necessary.
3. Preserve existing behavior unless the task explicitly requires changing it.

After modifying code, run the relevant tests using the actual terminal tool.

For this repository, prefer:

python -m pytest -q

Do not substitute `pytest` unless there is a specific reason.

### Important

Do not stop after explaining what you intend to do.

When the task requires a code change:
1. inspect
2. edit
3. test
4. report the result

Do not ask the user to perform these steps unless you are genuinely unable to execute the required tool.