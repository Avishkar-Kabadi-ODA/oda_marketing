# ODA Marketing - Coding Standards & Architectural Invariants

## 1. Single App Role Paradigm
* The app strictly defines **one custom role**: **`Marketing Lead`** (`desk_access: 1`).
* Do **not** create or reference database roles like `Content Writer` or `Technical Reviewer`.
* Document-level writer and reviewer roles are derived dynamically at runtime from `doc.assigned_to` and `doc.reviewer_technical`.
* All regular writers and reviewers hold the standard Frappe **`Desk User`** role.

## 2. Dynamic Document Permissions & Invariants
* **Planned-State Privacy:** Non-leads (`assigned_to` and `reviewer_technical`) cannot view deliverables in `Planned` state. Items only become visible once moved to `Briefed` or `In Progress`.
* **Anti-Self-Review Rule:** `assigned_to` and `reviewer_technical` cannot be the same user. If a `Marketing Lead` is listed as `assigned_to`, their lead authority on that document is revoked—they act strictly as a Writer and cannot approve their own item.
* **Attachment & Note Locking:** Writers cannot modify attachments (`content_file_1`, `content_file_2`, `content_file_3`) or `notes` in `Planned` or `Briefed` states. They unlock upon clicking `Start Work` (`In Progress`).
* **Due Date Modification:** Content Writers are allowed to adjust `due_date` in `In Progress` and `In Revision` states to manage schedules.

## 3. Frappe Workflow Invariants
* **Concrete Role Bindings:** When defining workflow states (`allow_edit`) and transitions (`allowed`), always use concrete database roles (`Desk User`, `Marketing Lead`, `System Manager`). Never use the pseudo-role `"All"`.
* **Custom DocPerm Gotcha:** Frappe ignores `content_item.json` permissions if any `Custom DocPerm` exists for that DocType. `setup_fixtures.run_setup()` automatically removes stale `Custom DocPerm` records during setup and migrations.

## 4. AI Copilot Standards
* **Dual Header Interoperability:** All external LLM requests must include both `Authorization: Bearer <key>` and `api-key: <key>` to support NVIDIA NIM, OpenAI, Azure APIM, Anthropic, and custom gateways.
* **Informational & Non-Blocking:** AI reviews are strictly optional and must never block or auto-transition workflow states.
* **Fallback Heuristics:** Always maintain deterministic fallback heuristics to handle socket timeouts and external network disconnects gracefully.

## 5. Agent Memory Maintenance
* Any AI agent making schema, functional, or architectural changes **must** update the memory files in `memory/` and the root `FLOW_DIAGRAM.txt`.
