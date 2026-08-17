# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	return {
		"fieldname": "content_item",
		"non_standard_fieldnames": {
			"Content Item AI Review": "parent"
		},
		"transactions": [
			{
				"label": _("Deliverable Reviews & History"),
				"items": ["Content Item AI Review"]
			}
		]
	}
