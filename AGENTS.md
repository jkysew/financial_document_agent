# AGENTS.md

## Project

Financial Document Agent v4

A Python-based financial-document processing pipeline that converts PDF evidence into structured semantic information while preserving traceability back to the original document.

The pipeline separates deterministic document processing from LLM-assisted interpretation.

---

## Primary Objective

Build a reliable, evidence-first financial document processing system.

The system must:

* Preserve the original PDF evidence.
* Maintain deterministic physical-row extraction.
* Preserve coordinates and source locations.
* Build logical document blocks from physical evidence.
* Extract and normalize financial information such as fees.
* Maintain traceability from interpreted data back to source evidence.
* Prefer deterministic processing where possible.
* Use LLMs only where interpretation or ambiguity requires them.

Accuracy and evidence preservation are more important than aggressive inference.

---

## Environment

### Operating System

Windows 11

### Project Location

```text
D:\John\financial_document_agent_v4
```

---

## Agent Operating Rules

You are working directly in the repository workspace.

### Tool usage

When you need to inspect a file, use the available file-reading tool.

When you need to modify a file, use the available file-editing tool.

Do not merely describe the edit and do not output pseudo-tool syntax such as:

```text
TOOL_NAME: edit_existing_file
BEGIN_ARG: filepath(string):The path of the file to edit, relative to the root of the workspace.
```

When you need to run a command, use the available terminal tool.

Do not write a simulated tool call as text.

Never invent tool names. Use only tools actually provided by the agent environment.

---

## Repository Safety

Before modifying code:

1. Inspect the relevant existing implementation.
2. Make the smallest change necessary.
3. Preserve existing behavior unless the task explicitly requires changing it.

After modifying code, run the relevant tests using the actual terminal tool.

For this repository, use:

```powershell
python -m pytest -q
```

Do not substitute `pytest` unless there is a specific reason.

---

## Important

Do not stop after explaining what you intend to do.

When the task requires a code change:

1. Inspect.
2. Edit.
3. Re-read the changed file.
4. Run the relevant tests.
5. Run `git diff -- <changed-file>` to verify the intended change.
6. Report the actual result.

Do not ask the user to perform these steps unless you are genuinely unable to execute the required tool.

---

## Editing and Verification Rules

### Apply Changes

When asked to modify a file, actually apply the change using the file-editing tool.

Do not merely display a code block describing the proposed change.

Do not claim that a file was modified unless the actual filesystem confirms that it was modified.

### Verify the Actual File

After editing a file:

1. Re-read the relevant portion of the actual file.
2. Confirm the intended change is present.
3. Confirm surrounding code was not unintentionally changed.

### Diff Validation

After editing a tracked file, run:

```powershell
git diff -- <changed-file>
```

Use the diff to verify that:

* The intended change is present.
* No unrelated changes were introduced.
* No indentation or formatting corruption occurred.
* Existing code was not accidentally deleted or rewritten.

### No False Successes

Never claim an edit succeeded unless the actual file and, where applicable, `git diff` confirm the change.

If the edit tool reports success but the filesystem does not contain the change, treat the edit as unsuccessful.

### Minimize Impact

Make the smallest change necessary.

Do not rewrite an entire file when a localized edit is sufficient.

Do not introduce unrelated formatting changes.

Do not rename variables, reorganize functions, or refactor code unless explicitly required by the task.

### Testing Standards

For Python changes, use:

```powershell
python -m pytest -q
```

rather than:

```powershell
pytest -q
```

Run the tests after the edit, not merely before the edit.

### Error Handling

If an editing or terminal tool reports a permission error or other failure:

1. Stop the current edit operation.
2. Inspect the actual filesystem state.
3. Determine whether the requested change was partially applied.
4. Do not blindly retry the same multi-line edit.
5. Restore the file if necessary before attempting another approach.

### Integrity First

If an edit tool cannot reliably apply a multi-line change, stop rather than repeatedly corrupting the file.

Do not attempt increasingly large or complex replacement operations when previous edits have failed.

If necessary, make smaller, independently verifiable edits.

## Windows UTF-8 Rule

All project JSON and text files are UTF-8.

When reading JSON/text files, always specify:
`encoding="utf-8"`

When writing JSON/text files, always specify:
`encoding="utf-8"`

For scripts that print PDF-derived text on Windows, initialize stdout with:
```python
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

### Completion Requirement

A code-change task is not complete until:

1. The actual file has been modified.
2. The modified file has been re-read.
3. The relevant tests have been run.
4. The resulting `git diff` has been inspected.
5. The final response accurately reports what actually happened.
