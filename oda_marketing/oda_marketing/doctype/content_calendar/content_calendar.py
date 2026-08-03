# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class ContentCalendar(Document):
	def validate(self):
		if self.from_date and self.to_date:
			if getdate(self.to_date) < getdate(self.from_date):
				frappe.throw("End Date cannot be before Start Date.")
