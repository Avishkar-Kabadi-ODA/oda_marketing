app_name = "oda_marketing"
app_title = "ODA Marketing Copilot"
app_publisher = "Optimum Data Analytics"
app_description = "Agentic marketing operations platform for Optimum Data Analytics"
app_email = "info@optimumdataanalytics.com"
app_license = "mit"

# App Icon & Branding (matching standard HRMS / Builder layout)
app_icon = "octicon octicon-megaphone"
app_color = "#5E5CE6"
app_logo_url = "/assets/oda_marketing/images/oda_logo.svg"
app_home = "/app/oda-marketing"

# Apps Screen Registration (automatically displays icon in Desk app launcher)
add_to_apps_screen = [
	{
		"name": "oda_marketing",
		"logo": "/assets/oda_marketing/images/oda_logo.svg",
		"title": "ODA Marketing Copilot",
		"route": "/app/oda-marketing",
		"has_permission": "oda_marketing.permissions.has_app_permission"
	}
]

# Installation & Migration Hooks
# ------------------------------
after_install = "oda_marketing.setup_fixtures.run_setup"
after_migrate = "oda_marketing.setup_fixtures.run_setup"

# Home Pages
# ----------
home_page = "login"
