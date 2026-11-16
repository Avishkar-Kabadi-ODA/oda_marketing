# ODA Marketing — Architecture and Operations

This app targets Frappe Framework 16. The DocType JSON and Python validation are the
source of truth; client scripts improve usability but are not the authorization
boundary.

## Data model

| DocType | Purpose and key data |
|---|---|
| **Content Item** | Deliverable, format, description, industry domain, calendar, planned publish date, due date, assigned writer, technical reviewer, files/notes, workflow state, risk status, AI status/results, and audit history. |
| **Content Calendar** | Named date range with `Active` or `Inactive` status. |
| **Content Item Option** | Active `Format` or `Industry Domain` choices; a Format may name a default publisher. |
| **Content Item AI Review** | Child history row containing review type, timestamp, score, outcome, feedback, and generated prompt. |
| **Marketing Settings** | Single DocType for email templates, publisher, SLA/business-hours settings, provider configuration, passing threshold, and per-role review limits. |
| **Env Variable** | AES-encrypted provider secret/endpoint values. Reads are permission-checked; arbitrary process environment variables are not returned. |

`Content Item` maintains both `workflow_state` and `status`; validation synchronizes
them. The `risk_flag` choices are `On track`, `At risk`, and `Late`. The AI status
choices are `Not Started`, `Queued`, `In Progress`, `Completed`, and `Failed`.

## Roles and permissions

The only custom app role is **Marketing Lead**. Do not create Writer or Reviewer
database roles. The app resolves a user's document-level role from
`assigned_to` and `reviewer_technical`.

| Actor | Access |
|---|---|
| Administrator, System Manager, Marketing Lead | Manage all Content Items and configuration; perform lead workflow actions. An assigned Lead is treated as the writer on that item for self-review/publishing checks. |
| Assigned writer (`Desk User`) | Read/write the assigned item after it leaves `Planned`; edit draft files and notes while drafting; cannot edit core metadata/due date, review the same item, or publish it. |
| Assigned reviewer (`Desk User`) | Read/write the assigned item after it leaves `Planned`; maintain review feedback and reviewer Copilot instructions; cannot edit writer drafts or review metadata. |
| Format publisher | Read/write items of the configured format only in `Approved` or `Published`; may publish an approved item unless they are its assigned writer. |
| Other users | No document access. `Planned` items are private to leads. |

DocType permissions provide the baseline; permission-query and document-permission
hooks enforce assignment and Planned-state privacy. Workflow transitions use real
roles (`Marketing Lead`, `System Manager`, and `Desk User`); server validation
narrows Desk User actions to the assigned participant or configured publisher.

## Workflow

```text
Planned --Issue Brief--> Briefed --Start Work--> In Progress
  In Progress --Submit for Review--> In Review
  In Review --Request Changes--> In Revision --Resubmit Draft--> In Progress
  In Review --Approve--> Approved --Publish--> Published
```

- A Lead issues the brief; the assigned writer starts work and uploads the draft.
- Submission requires a primary draft. The reviewer approves or supplies revision
  feedback; the writer resubmits to `In Progress`.
- Publishing requires a live URL. Workflow validation also rejects writer self-review
  and writer self-publication.
- Due date must be on or before the planned publish date. `brief_accepted_on` is
  stamped when work starts.
- Workflow email templates and Frappe Notification Logs are triggered when the
  state changes. Recipients are the assigned writer, reviewer, or selected publisher
  appropriate to that state.

## SLA and scheduled work

`hooks.py` registers an hourly SLA job and stale-Copilot recovery job.

- Overdue detection uses the site's configured date/time. Open items with `due_date`
  before today are marked `Late` when automatic flagging is enabled. Resolved or no
  longer overdue items have a stale `Late` flag cleared.
- Due-date reminders use configured/default and item-level offsets. Reminders and
  overdue email are sent only during the configured business-hours window
  (`start <= hour < end`) and are deduplicated by date.
- Overdue and reminder emails are sent to the assigned writer and reviewer.
- An AI job still `Queued` or `In Progress` after 30 minutes is marked `Failed`,
  its job token is invalidated, and the requester is notified so the user can retry.

## AI Copilot

The writer trigger is available in `Briefed`, `In Progress`, or `In Revision`; the
reviewer trigger is available only in `In Review`. Both server endpoints check
document read permission, assignment/lead identity, Markdown attachment, feature
enablement, and the role-specific review limit.

```text
Client action -> validate and enqueue after commit -> Queued
  -> In Progress -> prompt-generation subagent -> evaluator
  -> save score/feedback/history -> realtime completion -> form reload
```

The runner uses the `long` queue with a 600-second job timeout. Provider requests
use bounded retries/timeouts and both `Authorization: Bearer <key>` and `api-key`
headers. Prompt-generation errors can fall back to a deterministic prompt;
evaluation failures are explicitly marked `Failed`. Successful results are stored
in the role-scoped feedback/history. Scores use the configured passing threshold
but are informational only: they never approve, reject, or transition a workflow.

## Dashboard, imports, and migrations

- `/app/marketing-dashboard` is lead-only and filters on calendar, year/month,
  format, domain, and risk. Metrics use SQL aggregates rather than loading every
  Content Item into Python.
- CSV/XLSX imports create `Planned` Content Items. Uploads must resolve to a Frappe
  File under site storage and stay within the configured size limit.
- The app provides a custom dashboard and Kanban board; no custom report module is
  required for the pipeline metrics.
- `patches.txt` contains forward-only data migrations. Fixture setup creates
  missing defaults and preserves existing custom workflows, templates, prompts,
  dashboards, boards, and sidebars.

Operational testing and deployment notes are in the [development guide](./development-guide.md)
and [testing memory](./memory/TESTING_AND_TROUBLESHOOTING.md).
