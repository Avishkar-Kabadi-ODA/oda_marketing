# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	return [
		{
			"module_name": "ODA Marketing",
			"category": "Modules",
			"label": _("ODA Marketing"),
			"color": "#5E5CE6",
			"icon": "octicon octicon-megaphone",
			"type": "module",
			"description": "Agentic Marketing Operations Platform for ODA"
		}
	]
