# ODA Marketing

Enterprise content delivery pipeline with AI-powered quality reviews, built on **Frappe Framework v16**.

---

## What It Does

- **7-Stage Workflow**: `Planned → Briefed → In Progress → In Review → In Revision → Approved → Published`
- **AI Copilot Reviews**: Optional on-demand LLM-based quality scoring (non-blocking, informational only)
- **Role-Based Access**: Marketing Lead, Content Writer, Technical Reviewer, System Manager
- **Email & Bell Notifications**: Targeted alerts on workflow transitions, overdue items, and due date reminders
- **Kanban Board**: Visual pipeline view across all workflow states

---

## Content Pipeline

```
Marketing Lead          Content Writer           Technical Reviewer
─────────────          ──────────────           ──────────────────
Create Item ──────────► Accept Brief ──────────► Review Draft
Assign Writer           Attach Draft             Approve / Request Changes
Assign Reviewer         (Optional AI Review)     (Optional AI Review)
Issue Brief             Submit for Review
Publish Final
```

| State | Action | Next State | Who |
|-------|--------|------------|-----|
| Planned | Issue Brief | Briefed | Marketing Lead |
| Briefed | Start Work | In Progress | Content Writer |
| In Progress | Submit for Review | In Review | Content Writer |
| In Review | Approve | Approved | Technical Reviewer |
| In Review | Request Changes | In Revision | Technical Reviewer |
| In Revision | Resubmit Draft | In Progress | Content Writer |
| Approved | Publish | Published | Marketing Lead |

---

## Installation

```bash
# 1. Get the app
cd /path/to/frappe-bench
bench get-app https://github.com/your-org/oda_marketing.git --branch main

# 2. Install on site
bench --site your-site.local install-app oda_marketing

# 3. Run setup (creates roles, workflow, kanban, email templates, settings)
bench --site your-site.local execute oda_marketing.setup_fixtures.run_setup

# 4. Build and restart
bench build && bench restart
```

### Post-Install Configuration

1. Go to **Marketing Settings** (`/app/marketing-settings`)
2. Set **Default Publisher** and **Email Templates**
3. Enable **Email Notifications** and/or **AI Copilot**
4. For AI Copilot: configure provider, model, and API keys via **Env Variables**
5. Assign roles to users: `Marketing Lead`, `Content Writer`, `Technical Reviewer`

---

## Key DocTypes

| DocType | Purpose |
|---------|---------|
| **Content Item** | Core deliverable with workflow, attachments, AI reviews |
| **Content Calendar** | Date-bounded calendar for planning |
| **Content Item Option** | Dynamic dropdown values for Format and Industry Domain |
| **Content Item AI Review** | Child table recording AI review history |
| **Marketing Settings** | Single DocType for all configuration |
| **Env Variable** | Encrypted storage for API keys and secrets |

---

## AI Copilot Engine

The AI Copilot is an optional, non-blocking quality review system:

1. **Prompt Subagent** generates a dynamic evaluation prompt from deliverable metadata
2. **Evaluator Agent** scores the content via LLM (supports APIM Gateway, OpenAI, Google Gemini)
3. **Score & feedback** are recorded on the form and in the review history table
4. AI score is **purely informational** — it does not block workflow transitions

**Supported Providers**: APIM Gateway, OpenAI, Google Gemini, Anthropic (fallback: heuristic mock evaluator)

---

## Email & Reminder System

- **Workflow Emails**: Sent on state transitions (Briefed, In Review, In Revision, Approved, Published)
- **Overdue Alerts**: Sent daily at Business Hours Start (default 9 AM) for items past due date
- **Due Date Reminders**: Up to 3 reminder offsets (1 global default + 2 per-item) — each sends exactly 1 email on the target day
- **Business Hours**: Configurable start/end hours in Marketing Settings (default 9 AM – 7 PM)

---

## Permissions

| Action | Marketing Lead | Content Writer | Technical Reviewer |
|--------|:-:|:-:|:-:|
| Create / Delete | ✅ | ❌ | ❌ |
| Edit Metadata | ✅ | ❌ | ❌ |
| Edit Due Date | ✅ | ✅ | ❌ |
| Edit Attachments | ✅ | ✅ (after Briefed) | ❌ |
| Edit Revision Feedback | ✅ | ❌ | ✅ |
| Run Writer AI Copilot | ✅ | ✅ | ❌ |
| Run Reviewer AI Copilot | ✅ | ❌ | ✅ |
| Approve / Request Changes | ✅ | ❌ | ✅ |
| Publish | ✅ | ❌ | ❌ |

---

## Project Structure

```
oda_marketing/
├── hooks.py                    # Frappe hooks, scheduler, permissions
├── permissions.py              # Role-based access control
├── setup_fixtures.py           # One-time setup (roles, workflow, kanban, templates)
├── oda_marketing/
│   ├── doctype/
│   │   ├── content_item/       # Core deliverable DocType
│   │   ├── content_calendar/   # Calendar DocType
│   │   ├── content_item_option/# Dynamic Format/Industry Domain options
│   │   ├── content_item_ai_review/ # AI review history (child table)
│   │   ├── marketing_settings/ # Single DocType configuration
│   │   └── env_variable/       # Encrypted secrets storage
│   └── ai_engine/
│       ├── runner.py           # AI review orchestrator
│       ├── evaluator_agent.py  # LLM evaluator + heuristic fallback
│       ├── prompt_subagent.py  # Dynamic prompt generator
│       ├── file_extractor.py   # Attachment text extraction (.txt, .pdf, .docx, .pptx)
│       └── key_manager.py      # Secure credential resolution
├── tests/
│   └── test_ai_agent.py        # 7 unit tests
└── patches/                    # Migration patches
```

---

## Running Tests

```bash
bench run-tests --app oda_marketing --module oda_marketing.oda_marketing.tests.test_ai_agent
```

---

## License

Proprietary — Optimum Data Analytics Private Limited © 2026. All rights reserved.