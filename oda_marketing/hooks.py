app_name = "oda_marketing"
app_title = "ODA Marketing"
app_publisher = "Optimum Data Analytics"
app_description = "Agentic marketing operations platform for Optimum Data Analytics"
app_email = "info@optimumdataanalytics.com"
app_license = "mit"

# App Icon & Branding (standard Desk App Switcher layout)
app_icon = "octicon octicon-megaphone"
app_color = "#5E5CE6"
app_logo_url = "/assets/oda_marketing/images/oda_logo.svg"
app_home = "/app/oda-marketing"

# Desk & Apps Screen Registration
add_to_apps_screen = [
	{
		"name": "oda_marketing",
		"logo": "/assets/oda_marketing/images/oda_logo.svg",
		"title": "ODA Marketing",
		"route": "/app/oda-marketing",
		"has_permission": "oda_marketing.permissions.has_app_permission"
	}
]

# Permission Hooks (Strict User Involvement Scoping)
permission_query_conditions = {
	"Content Item": "oda_marketing.permissions.get_content_item_permission_query_conditions",
}

has_permission = {
	"Content Item": "oda_marketing.permissions.has_content_item_permission",
}

# Scheduled Events (Overdue SLA Engine)
scheduler_events = {
	"daily": [
		"oda_marketing.oda_marketing.doctype.content_item.content_item.send_overdue_sla_notifications"
	]
}

# Installation & Migration Hooks
after_install = "oda_marketing.setup_fixtures.run_setup"
after_migrate = "oda_marketing.setup_fixtures.run_setup"

# Home Pages
home_page = "login"
