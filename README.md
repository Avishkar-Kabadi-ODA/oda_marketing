# ODA Marketing

**ODA Marketing Operations Platform** is an enterprise-grade agentic marketing workflow and AI evaluation system built on **Frappe Framework v16**.

---

## Key Features

- **Content Delivery Pipeline**: Lifecycle management for Blogs, Polls, Flowcharts, and Carousels.
- **Workflow State Machine**: Streamlined status transitions (`Planned` → `Briefed` → `In Progress` → `Marketing Copilot Review` / `In Review - Technical` → `In Revision` → `Approved` → `Published`).
- **Configurable SLA Engine**: Single master **Default SLA Lead Time (Days)** setting (`default_sla_lead_days`, default: `14` days) dynamically computing `sla_due_date = planned_publish_date - default_sla_lead_days`.
- **AI Copilot Gatekeeper & Subagent**:
  - Configurable AI Copilot Review with dynamic prompt generator subagent.
  - Gatekeeper score thresholding (e.g., `80%`) enforcing quality sign-off before technical review.
  - Conditionally enabled/disabled under **Marketing Settings**. When disabled, items advance directly to Technical Review.
- **Role-Based Access Control & Safeguards**:
  - Strict permissions for `Marketing Lead`, `Content Writer`, `Technical Reviewer`, and `System Manager`.
  - Mandatory validation safeguards for primary draft attachment, assigned technical reviewer, revision feedback notes, and live published URL.
- **Targeted Notification Engine**:
  - HTML email notifications with direct Desk action buttons ("View Content Item in Desk").
  - Frappe In-App Bell 🔔 notifications sent directly to assigned users.
- **Frappe Desk & Docker Integration**: Standard `desktop.py` module registration and `frappe_docker` compatibility.

---

## Installation Guide

### 1. Install App on Bench

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/Avishkar-Kabadi-ODA/oda_marketing.git --branch main
bench --site your.site.name install-app oda_marketing
```

### 2. Run Production Setup

Run the setup fixture to initialize roles, email templates, workflow state machine, kanban pipeline, and desktop icons:

```bash
bench --site your.site.name execute oda_marketing.setup_fixtures.run_setup
```

*(Note: Production setup initializes all master switches to `0` (disabled) and creates zero dummy content items.)*

---

## Configuration & Operational Defaults

### Marketing Settings

Navigate to **Desk → ODA Marketing → Marketing Settings**:

1. **Master Switches & Operational Defaults**:
   - **Enable Email Notifications**: Master toggle for email delivery (default: `0`).
   - **Enable Automatic Overdue Risk Flagging**: Toggles automatic SLA due date tracking (default: `0`).
   - **Default SLA Lead Time (Days)**: Master SLA lead time setting in days (default: `14`, mandatory).
   - **Default Publisher**: Default Marketing Lead / Publisher user.

2. **AI Copilot Configuration** *(visible & mandatory when Enable AI Copilot is checked)*:
   - **Enable AI Copilot Automated Review & Gatekeeper**: Enables the AI evaluation engine and quality gatekeeper (default: `0`).
   - **Minimum Passing Score (%)**: Quality threshold required to advance to Technical Review (default: `80`).
   - **AI LLM Provider / Architecture**: Provider architecture (e.g. `APIM Gateway`, `OpenAI`, `Google Gemini`).
   - **API Key / Subscription Key (Env Variable)**: Select stored key from **Env Variable** DocType.
   - **APIM / Endpoint URL (Env Variable)**: Select stored endpoint from **Env Variable** DocType.
   - **Model Name**: Target model (e.g. `gpt-4o`, `gemini-1.5-pro`).
   - **Prompt Templates**: Customizable Jinja2 subagent meta-prompt and evaluator rubric templates.

---

## Workflow & State Machine

```
                              Planned
                                 ↓ (Issue Brief)
                              Briefed
                                 ↓ (Accept Brief)
                            In Progress
                                 │
           ┌─────────────────────┴─────────────────────┐
           ▼ (AI Copilot Enabled)                      ▼ (AI Copilot Disabled)
Submit for Copilot Review                   Submit for Technical Review
           │                                           │
Marketing Copilot Review                               │
   ├── Score ≥ 80% (Pass) ──┐                          │
   └── Score < 80% (Fail) ─┐│                          │
                           ││                          │
                           │└──────────────────────────┼──────────────┐
                           │                           │              │
                           │                           ▼              │
                           │                 In Review - Technical    │
                           │                           │              │
                           │                 (Approve Technical)      │
                           │                           │              │
                           ▼                           ▼              │
                      In Revision                   Approved          │
                           │                           │              │
                    (Resubmit Draft)               (Publish)          │
                           │                           │              │
                           └───────────────────────────┼──────────────┘
                                                       ▼
                                                   Published
```

---

## Running Unit Tests

Run the automated test suite on your bench site:

```bash
bench --site marketing.localhost run-tests --app oda_marketing
```

---

## Architecture & Documentation

- [System Architecture & Operational Flow](file:///home/user/frappe-bench/apps/oda_marketing/app-architecture-and-flow.md)
- [Development Guide](file:///home/user/frappe-bench/apps/oda_marketing/development-guide.md)

---

## License

MIT License - Optimum Data Analytics (ODA)
