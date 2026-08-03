# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	return [
		{
			"label": _("Campaign Planning"),
			"icon": "octicon octicon-calendar",
			"items": [
				{
					"type": "doctype",
					"name": "Content Calendar",
					"label": _("Content Calendar"),
					"description": _("Plan and approve content campaigns."),
				},
			],
		},
		{
			"label": _("Content Execution"),
			"icon": "octicon octicon-checklist",
			"items": [
				{
					"type": "doctype",
					"name": "Content Item",
					"label": _("Content Item"),
					"description": _("Track items through the 8-state workflow."),
				},
			],
		},
	]
