# ODA Marketing

**Enterprise Marketing Operations & Content Governance Engine for Frappe Framework v15/v16.**

Built for **Optimum Data Analytics (ODA)** to govern deliverable lifecycles, enforce multi-stage technical reviews, provide autonomous 2-stage AI Copilot evaluations, and automate publisher notifications and SLA reminders.

---

## Key Capabilities

* **7-Stage Governance Workflow:** `Planned → Briefed → In Progress → In Review → In Revision → Approved → Published`
* **Single Custom App Role Paradigm:** Eliminates redundant database roles by defining a single custom role (**`Marketing Lead`**). Content Writers and Technical Reviewers are standard Frappe **`Desk User`**s resolved dynamically at runtime per deliverable.
* **Autonomous 2-Stage AI Copilot:**
  - **Stage 1 (Prompt Generator Subagent):** Generates domain-tailored System Prompts based on deliverable metadata and reviewer instructions.
  - **Stage 2 (Primary Evaluator Agent):** Evaluates draft copy and attachments, returning JSON scores, strengths, and actionable feedback.
  - **Interoperable Dual Headers:** Full support for NVIDIA NIM, OpenAI, Anthropic, Azure APIM, and custom gateways.
  - **Non-Blocking & Informational:** AI reviews never halt or auto-route workflow transitions.
* **Planned-State Privacy:** Deliverables in `Planned` state are hidden from non-leads until officially briefed.
* **Automated Background Reminders & SLA Escalation:** Daily scheduler tracks approaching due dates and automatically flags overdue deliverables as `Late`.
* **Visual Kanban Board & Executive Dashboard:** Real-time visibility into the content pipeline across all 7 workflow stages.

---

## Deliverable Lifecycle & State Transitions

See [`FLOW_DIAGRAM.txt`](FLOW_DIAGRAM.txt) for the full ASCII flow diagram.

```
Marketing Lead                 Content Writer (Desk User)       Technical Reviewer (Desk User)
──────────────                 ──────────────────────────       ──────────────────────────────
Create Deliverable (Planned)
  │ (Issue Brief)
  ▼
Briefed ─────────────────────► Start Work (In Progress)
                               Attach Draft & Notes
                               (Optional Writer AI Copilot)
                               Submit for Review ─────────────► In Review
                                                                (Optional Reviewer AI Copilot)
                                                                Approve ────────────► Approved
                                                                Request Changes ────► In Revision
                               Resubmit Draft ◄─────────────────────────────────────────┘
                               (Moves to In Progress)
Live Publication ◄───────────── (Approved)
(Mandatory live URL)
```

| State | Action | Next State | Action Performed By | Key Validations & Side Effects |
| :--- | :--- | :--- | :--- | :--- |
| **`Planned`** | `Issue Brief` | `Briefed` | Marketing Lead / System Mgr | Privacy locked. Sends notification to Assigned Writer. |
| **`Briefed`** | `Start Work` | `In Progress` | Assigned Writer | Unlocks attachments; stamps `brief_accepted_on`. |
| **`In Progress`** | `Submit for Review` | `In Review` | Assigned Writer | Requires `content_file_1` (Primary Draft). Alerts Reviewer. |
| **`In Review`** | `Approve` | `Approved` | Assigned Reviewer / Lead | Confirms technical & brand quality. Alerts Publisher. |
| **`In Review`** | `Request Changes` | `In Revision` | Assigned Reviewer / Lead | Requires `revision_feedback_notes`. Alerts Writer. |
| **`In Revision`** | `Resubmit Draft` | `In Progress` | Assigned Writer | Resubmits updated draft back to drafting state. |
| **`Approved`** | `Publish` | `Published` | Marketing Lead / Publisher | Requires `published_url`. Terminal live asset state. |

---

## Role & Permission Matrix

| Permission Area | Marketing Lead | Assigned Content Writer (`Desk User`) | Assigned Reviewer (`Desk User`) | Other Users |
| :--- | :---: | :---: | :---: | :---: |
| **Create / Delete Deliverables** | ✅ | ❌ | ❌ | ❌ |
| **View Planned Items** | ✅ | ❌ (Hidden until Briefed) | ❌ (Hidden until Briefed) | ❌ |
| **View Briefed / Active Items** | ✅ | ✅ | ✅ | ❌ |
| **Edit Deliverable Metadata** | ✅ | ❌ | ❌ | ❌ |
| **Edit Due Date** | ✅ | ✅ (In Progress / Revision) | ❌ | ❌ |
| **Edit Draft Attachments & Notes** | ✅ | ✅ (In Progress / Revision) | ❌ | ❌ |
| **Run Writer AI Copilot Review** | ✅ | ✅ (Up to quota) | ❌ | ❌ |
| **Run Reviewer AI Copilot Audit** | ✅ | ❌ | ✅ (Up to quota) | ❌ |
| **Approve / Request Changes** | ✅ | ❌ (Anti-self-review) | ✅ | ❌ |
| **Publish Live** | ✅ | ❌ | ❌ | ❌ |

---

## Quick Installation & Setup

```bash
# 1. Fetch the app into your bench
bench get-app https://github.com/OptimumDataAnalytics/oda_marketing.git --branch main

# 2. Install on target site
bench --site marketing.localhost install-app oda_marketing

# 3. Run migrations and setup fixtures
bench --site marketing.localhost migrate

# 4. Build assets and restart
bench build && bench restart
```

---

## Configuration & Environment Variables

1. Open **Marketing Settings** (`/app/marketing-settings`) in Frappe Desk:
   - Configure **Default Publisher** and Email Notification Switches.
   - Configure **AI Copilot** (Provider: `APIM Gateway`, `OpenAI`, `Anthropic`, `Azure OpenAI`).
   - For **NVIDIA NIM** or OpenAI compatible endpoints:
     - Provider: `OpenAI` or `APIM Gateway`
     - Base URL: `https://integrate.api.nvidia.com/v1`
     - API Key: `nvapi-...`
2. Configure **Marketing Env Variables** (`/app/marketing-env-variable`) for AES-encrypted secrets.

---

## Running Automated Test Suites

The app includes **24 automated unit tests** covering end-to-end multi-stage workflows, role scoping, Planned-state privacy, attachment locking, dual-header LLM connectivity, prompt subagent generation, and SLA overdue tracking:

```bash
# Run all app unit tests
bench --site marketing.localhost run-tests --app oda_marketing
```

---

## System Documentation & Developer Memory

Persistent architecture and maintenance guides are maintained in the repository:

* [`FLOW_DIAGRAM.txt`](FLOW_DIAGRAM.txt) — Comprehensive ASCII state machine and AI execution diagram.
* [`memory/PROJECT_OVERVIEW.md`](memory/PROJECT_OVERVIEW.md) — DocType schemas and single-role paradigm.
* [`memory/WORKFLOW_AND_PERMISSIONS.md`](memory/WORKFLOW_AND_PERMISSIONS.md) — State machine and permission rules.
* [`memory/AI_COPILOT_ENGINE.md`](memory/AI_COPILOT_ENGINE.md) — 2-stage subagent pipeline and LLM integration.
* [`memory/TESTING_AND_TROUBLESHOOTING.md`](memory/TESTING_AND_TROUBLESHOOTING.md) — Test suites, gotchas, and resolutions.
* [`memory/MAINTENANCE_INSTRUCTIONS.md`](memory/MAINTENANCE_INSTRUCTIONS.md) — Agent memory update guidelines.

---

## License

Proprietary — Optimum Data Analytics Private Limited © 2026. All rights reserved.