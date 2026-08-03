# ODA Marketing — Architecture & Operational Workflow

This document explains the current system architecture, data model, user roles, security scoping, and step-by-step operational workflow for the **ODA Marketing** application.

---

## 1. Overview & Core Architecture

The ODA Marketing platform manages the end-to-end lifecycle of enterprise marketing deliverables (Blogs, Polls, Flowcharts, Carousels). It provides structured planning, mandatory content brief gates, attachment requirement rules, multi-stage sequential reviews, mandatory feedback tracking, strict role permission controls, default publisher settings, and automated SLA email alerts.

```mermaid
graph TD
    A[Content Calendar] -->|Master Setup| B[Content Item]
    B -->|Linked Creative Blueprint| C[Content Brief]
    D[Marketing Settings] -->|Controls Email Templates & Default Publisher| E[Automated Email Engine]
    B -->|Triggers Notifications| E
```

---

## 2. DocType Data Model Summary

### 1. `Content Calendar` (Master Setup)
- **Purpose**: Defines active marketing operational periods (e.g. *"2026 Global Marketing Calendar"*, Jan 1 – Dec 31). Modeled after Frappe HR's Holiday List.
- **Key Fields**: `calendar_name`, `from_date`, `to_date`, `status` (*Active / Inactive*), `description`.

### 2. `Content Item` (Core Deliverable)
- **Purpose**: The central tracking document for every blog, poll, flowchart, or carousel asset.
- **Key Fields**:
  - `title`, `content_type`, `topic`, `practice_area` (*HCLS, Pharma, Fintech, AgTech, Cross-domain*).
  - `content_calendar`, `planned_publish_date`, `sla_due_date`, `risk_flag` (*On track, At risk, Late*).
  - `assigned_to` (Writer), `reviewer_technical` (SME), `reviewer_business` (Marketing Manager).
  - `status` / `workflow_state` (*Planned, Briefed, In Progress, In Review - Technical, In Review - Business, In Revision, Approved, Published*).
  - **Attachment Slots**:
    - `content_file_1` (Attach - **Primary Content File (Mandatory for Review)**).
    - `content_file_2` (Attach - Supporting Asset 1 (Optional)).
    - `content_file_3` (Attach - Supporting Asset 2 (Optional)).
  - `revision_feedback_notes` (Mandatory notes required when requesting changes).

### 3. `Content Brief` (Creative Blueprint)
- **Purpose**: Creative instructions and SEO guidelines created by the Marketing Lead for the writer.
- **Mandatory Gate**: A linked `Content Brief` **must** exist before an item can be moved to state **`Briefed`**.
- **Key Fields**: `content_item` (Link), `outline` (Rich text editor), `target_audience`, `primary_keyword`, `word_target`, `accepted_by_writer` (Check), `accepted_on` (Datetime).

### 4. `Marketing Settings` (Central Configuration)
- **Purpose**: Single DocType accessible under **Setup** in the workspace sidebar to configure global defaults, default publisher, and email templates.
- **Key Fields**:
  - `enable_email_notifications` (Checkbox master switch).
  - `default_publisher` (Link: User - Default Publisher / Marketing Lead).
  - `writer_email_template` (Link: Email Template for assignments & revisions).
  - `reviewer_email_template` (Link: Email Template for technical & business reviews).
  - `publisher_email_template` (Link: Email Template for final approval & publishing).
  - `overdue_sla_email_template` (Link: Email Template for late SLA alerts).

---

## 3. Strict Role Permissions & Access Control Matrix

Access permissions are enforced dynamically in `permissions.py` (record level), `content_item.py` (server validation), and `content_item.js` (client form control):

| Role | Creation & Deletion Rights | Field-Level Edit Permissions | File Attachment Access |
| :--- | :--- | :--- | :--- |
| **Marketing Lead** | Full (`create: 1, delete: 1`) | Full edit access to all metadata, calendar, and publishing fields. | Full View, Download & Replace. |
| **Default Publisher** | Full (`create: 1, delete: 1`) | Can view all deliverables and edit publishing details. | Full View & Download. |
| **Content Writer** | **Blocked** (`create: 0, delete: 0`) | Core metadata fields are **read-only**. Can ONLY upload attachments (`content_file_1`, `content_file_2`, `content_file_3`), add notes, check `accepted_by_writer` on brief, and transition state to `In Review`. | View, Download & Upload. |
| **Technical Reviewer** | **Blocked** (`create: 0, delete: 0`) | Core metadata & attachments are **read-only**. Can ONLY edit `revision_feedback_notes` when requesting changes and transition states (`Approve Technical`, `Request Changes`). | Full View & Download (Cannot Replace). |
| **Business Reviewer** | **Blocked** (`create: 0, delete: 0`) | Core metadata & attachments are **read-only**. Can ONLY edit `revision_feedback_notes` when requesting changes and transition states (`Approve Business`, `Request Changes`). | Full View & Download (Cannot Replace). |

---

## 4. End-to-End Operational Workflow

The following state machine governs every deliverable from planning to publishing:

```mermaid
stateDiagram-v2
    [*] --> Planned: Lead schedules Content Item
    Planned --> Briefed: Lead issues Content Brief (Mandatory Brief Check)
    Briefed --> InProgress: Writer reviews & checks 'Accepted By Writer'
    InProgress --> InReviewTechnical: Writer uploads primary file & submits (Mandatory File Check)
    InReviewTechnical --> InRevision: Technical Reviewer requests changes (mandatory notes)
    InReviewTechnical --> InReviewBusiness: Technical Reviewer approves technical
    InReviewBusiness --> InRevision: Business Reviewer requests changes (mandatory notes)
    InReviewBusiness --> Approved: Business Reviewer approves business
    InRevision --> InReviewTechnical: Writer updates draft file & resubmits
    Approved --> Published: Publisher / Lead publishes asset
    Published --> [*]
```

### Detailed Step-by-Step Flow:

1. **Scheduling (`Planned`)**:
   - The Marketing Lead creates a `Content Item` on the calendar grid, assigning a Writer, Technical Reviewer, and Business Reviewer.

2. **Briefing (`Planned` → `Briefed`)**:
   - The Lead creates a linked `Content Brief` (outline, keywords, target audience) and clicks **`Issue Brief`**.
   - **Validation Gate**: If no `Content Brief` is linked, the system blocks the transition.
   - **Email**: Triggers email notification to the assigned **Content Writer**.

3. **Acceptance (`Briefed` → `In Progress`)**:
   - The assigned Writer opens the `Content Brief`, reviews the guidelines, and checks **`Accepted By Writer`**. This automatically advances the item to **`In Progress`**.

4. **Technical Review Submission (`In Progress` → `In Review - Technical`)**:
   - The Writer completes the draft, attaches `content_file_1` (Primary Content File - Mandatory), and clicks **`Submit for Technical Review`**.
   - **Validation Gate**: If `content_file_1` is empty, the system blocks submission.
   - **Email**: Triggers email notification to `reviewer_technical` with full human names and clean HTML hyperlinks for attached files.

5. **Technical Review Signoff or Revision**:
   - **If Revision Needed**: Technical Reviewer enters notes into `revision_feedback_notes` and clicks **`Request Changes`** → State becomes **`In Revision`** (Triggers email to Writer with feedback notes).
   - **If Technical Approved**: Technical Reviewer clicks **`Approve Technical`** → State becomes **`In Review - Business`** (Triggers email to Business Reviewer). If Technical and Business reviewers are the same person, recipient lists deduplicate automatically.

6. **Business Review Signoff**:
   - Business Reviewer reviews the deliverable and clicks **`Approve Business`** → State becomes **`Approved`**.
   - **Email**: Triggers email notification to the **Default Publisher** and Writer.

7. **Publishing (`Approved` → `Published`)**:
   - The Publisher / Marketing Lead enters `published_url` and clicks **`Publish`**. State becomes **`Published`**.

---

## 5. Automated SLA & Overdue Alert Engine

- Every `Content Item` calculates an `sla_due_date` based on `content_type` (e.g. 30 days before publish date for Blogs, 14 days for Flowcharts/Carousels, 7 days for Polls).
- A daily automated job evaluates items past `sla_due_date`:
  - Sets `risk_flag = "Late"`.
  - Dispatches an urgent email alert to involved users using `overdue_sla_email_template`.

---

## 6. Workspace Sidebar Navigation Structure

```text
ODA Marketing
│
├── Content Execution
│   ├── Content Item (Calendar & List Views)
│   └── Content Brief
│
└── Setup
    ├── Content Calendar (Master Calendar Setup)
    └── Marketing Settings (Email, Publisher & Template Configuration)
```
