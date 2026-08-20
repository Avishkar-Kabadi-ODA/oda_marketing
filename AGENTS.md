# ODA Marketing Agent Rules & Coding Standards

## 1. Single App Role Rule
- The app only defines **one custom role**: `Marketing Lead`.
- Do **not** create or reference database roles like `Content Writer` or `Technical Reviewer`.
- Document-level writer and reviewer roles are derived dynamically at runtime from `doc.assigned_to` and `doc.reviewer_technical`.

## 2. Permission and Workflow Invariants
- When modifying workflow transitions, ensure all allowed actions bind to real roles (`Desk User`, `Marketing Lead`, `System Manager`), never pseudo-role `"All"`.
- When updating permissions, maintain Planned-state privacy: non-leads cannot see items in `Planned` state.
- Always ensure `Desk User` has read/write permissions in `content_item.json`.

## 3. AI Copilot Standards
- All LLM HTTP requests must include dual headers: `Authorization: Bearer <key>` and `api-key: <key>`.
- Copilot evaluations must remain strictly informational and must never block or auto-transition workflow states.
- Always maintain fallback heuristics to gracefully handle timeouts or external network failures.

## 4. Memory Maintenance
- Any agent making architectural, schema, or functional changes **must** update the files in `memory/` and the root `FLOW_DIAGRAM.txt`.
