# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ContentItemOption(Document):
	def validate(self):
		if not (self.option_label or "").strip():
			frappe.throw(_("Option Label cannot be empty."))
