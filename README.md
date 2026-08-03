### ODA Marketing

Agentic marketing operations platform for ODA built on Frappe Framework v15.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench --site marketing.localhost install-app oda_marketing
bench --site marketing.localhost execute oda_marketing.setup_fixtures.run_setup
```

### Documentation

- [System Architecture & Operational Flow](file:///home/user/frappe-bench/apps/oda_marketing/app-architecture-and-flow.md): Detailed explanation of DocTypes, workflow state machine, user involvement security, and automated email engine.
- [Development & Customization Guide](file:///home/user/frappe-bench/apps/oda_marketing/development-guide.md): Developer guide for creating fields, DocTypes, linking fields, and running migrations.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/oda_marketing
pre-commit install
```

### License

MIT
