# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class CalendarSlot(Document):
	def before_save(self):
		if self.planned_publish_date:
			dt = getdate(self.planned_publish_date)
			month_name = dt.strftime("%B")  # e.g., "August"
			self.month = month_name
