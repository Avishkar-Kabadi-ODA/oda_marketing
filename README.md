# ODA Marketing

Enterprise marketing operations and content governance for **Frappe Framework 16**.

The app manages deliverables from planning through publication using one custom role,
**Marketing Lead**. Writers and reviewers are regular Desk users assigned on each
Content Item; their document-level responsibilities are derived from `assigned_to`
and `reviewer_technical`, not separate database roles.

## Core behavior

- Seven workflow states: `Planned`, `Briefed`, `In Progress`, `In Review`,
  `In Revision`, `Approved`, and `Published`.
- Non-leads cannot see `Planned` items. Assigned writers and reviewers can access
  their items after briefing; format publishers receive access only to their
  `Approved`/`Published` items.
- Writers draft and resubmit; reviewers approve or request changes. A writer cannot
  review or publish their own item. Marketing Leads and System Managers administer
  the workflow. Publishing requires `published_url`.
- `due_date` cannot be later than `planned_publish_date`; changing workflow state
  keeps `status` synchronized with `workflow_state`.
- The hourly scheduler recalculates overdue flags and sends deduplicated due-date
  reminders and overdue emails during configured business hours.
- The AI Copilot runs asynchronously through prompt generation and evaluation.
  `Not Started`, `Queued`, `In Progress`, `Completed`, and `Failed` are informational
  review statuses; a score never blocks or changes workflow state.
- Attachments are resolved through Frappe File records under site file storage and
  are size-limited. Import accepts CSV/XLSX File records.
- Dashboard metrics use database aggregations and support calendar, date, format,
  domain, and risk filters.

## AI provider configuration

Configure the provider, endpoint, model, and API-key/endpoint variable names in
**Marketing Settings**. Store secrets in **Env Variable**; secret reads require
DocType read permission. Supported live clients are OpenAI-compatible endpoints
(including configured APIM/NVIDIA NIM endpoints) and Anthropic. Both send
`Authorization: Bearer <key>` and `api-key: <key>`. Unsupported providers fail
explicitly; prompt generation has a deterministic fallback for network/provider
errors.

## Install and migrate

```bash
bench get-app https://github.com/OptimumDataAnalytics/oda_marketing.git --branch main
bench --site marketing.localhost install-app oda_marketing
bench --site marketing.localhost migrate
bench build
bench restart
```

Migrations add fields and apply the forward patch in `patches.txt`. Fixture setup is
additive: it creates missing defaults and does not replace existing workflows,
templates, prompts, boards, dashboards, or sidebar customizations.

## Tests

Run the app suite:

```bash
bench --site marketing.localhost run-tests --app oda_marketing
```

Focused modules:

```bash
bench --site marketing.localhost run-tests --module oda_marketing.tests.test_demo_script
bench --site marketing.localhost run-tests --module oda_marketing.oda_marketing.tests.test_permissions_and_features
bench --site marketing.localhost run-tests --module oda_marketing.oda_marketing.tests.test_ai_agent
bench --site marketing.localhost run-tests --module oda_marketing.oda_marketing.tests.test_content_item_sla
```

Database tests use Frappe test transactions and generated identities. Do not add
site-wide deletes or explicit commits to test setup.

## Documentation

- [Architecture and operational workflow](./app-architecture-and-flow.md)
- [State and AI flow diagram](./FLOW_DIAGRAM.txt)
- [Dashboard guide](./MARKETING_DASHBOARD_GUIDE.md)
- [Development guide](./development-guide.md)
- [Project overview memory](./memory/PROJECT_OVERVIEW.md)
- [Workflow and permissions memory](./memory/WORKFLOW_AND_PERMISSIONS.md)
- [AI Copilot memory](./memory/AI_COPILOT_ENGINE.md)
- [Testing and troubleshooting memory](./memory/TESTING_AND_TROUBLESHOOTING.md)
- [Maintenance instructions](./memory/MAINTENANCE_INSTRUCTIONS.md)

## License

Proprietary — Optimum Data Analytics Private Limited © 2026. All rights reserved.
