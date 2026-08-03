# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate


class ContentItem(Document):
	def validate(self):
		self.sync_status_with_workflow()
		self.validate_publish_date_with_calendar()
		self.calculate_sla_due_date()
		self.check_overdue_sla()
		self.validate_revision_notes()

	def before_insert(self):
		if self.assigned_to:
			self.owner = self.assigned_to
		self.sync_status_with_workflow()

	def sync_status_with_workflow(self):
		wf_state = getattr(self, "workflow_state", None)
		if wf_state:
			self.status = wf_state
		elif not getattr(self, "status", None):
			self.status = "Planned"

	def validate_publish_date_with_calendar(self):
		if self.content_calendar and self.planned_publish_date:
			cal = frappe.get_doc("Content Calendar", self.content_calendar)
			pub_date = getdate(self.planned_publish_date)
			if cal.from_date and pub_date < getdate(cal.from_date):
				frappe.throw(_("Planned Publish Date ({0}) cannot be before Content Calendar start date ({1}).").format(self.planned_publish_date, cal.from_date))
			if cal.to_date and pub_date > getdate(cal.to_date):
				frappe.throw(_("Planned Publish Date ({0}) cannot be after Content Calendar end date ({1}).").format(self.planned_publish_date, cal.to_date))

	def calculate_sla_due_date(self):
		if not self.planned_publish_date:
			return

		dt = getdate(self.planned_publish_date)
		offsets = {
			"Blog": -30,
			"Poll": -7,
			"Flowchart": -14,
			"Carousel": -14
		}
		offset = offsets.get(self.content_type, -14)
		self.sla_due_date = add_days(dt, offset)

	def check_overdue_sla(self):
		if self.sla_due_date and getattr(self, "workflow_state", None) not in ["Approved", "Published"]:
			if getdate(nowdate()) > getdate(self.sla_due_date):
				self.risk_flag = "Late"

	def validate_revision_notes(self):
		if getattr(self, "workflow_state", None) == "In Revision" and not (self.revision_feedback_notes and self.revision_feedback_notes.strip()):
			frappe.throw(_("Revision Feedback / Notes are mandatory when requesting changes or sending an item to 'In Revision'."))

	def on_update(self):
		self.trigger_workflow_notifications()

	def trigger_workflow_notifications(self):
		settings = frappe.get_single("Marketing Settings")
		if not settings.enable_email_notifications:
			return

		previous_state = self.get_doc_before_save().workflow_state if self.get_doc_before_save() else None
		current_state = self.workflow_state

		if previous_state == current_state or not current_state:
			return

		recipients = []
		cc = []
		template_name = None

		if current_state == "In Review - Technical":
			if self.reviewer_technical:
				recipients.append(self.reviewer_technical)
			if self.reviewer_business:
				cc.append(self.reviewer_business)
			template_name = settings.reviewer_email_template

		elif current_state == "In Review - Business":
			if self.reviewer_business:
				recipients.append(self.reviewer_business)
			template_name = settings.reviewer_email_template

		elif current_state == "In Revision":
			if self.assigned_to:
				recipients.append(self.assigned_to)
			template_name = settings.writer_email_template

		elif current_state == "Approved":
			if self.assigned_to:
				recipients.append(self.assigned_to)
			lead = frappe.db.get_value("Has Role", {"role": "Marketing Lead"}, "parent")
			if lead:
				cc.append(lead)
			template_name = settings.publisher_email_template

		elif current_state == "Published":
			if self.assigned_to:
				recipients.append(self.assigned_to)
			template_name = settings.publisher_email_template

		if recipients and template_name and frappe.db.exists("Email Template", template_name):
			try:
				tmpl = frappe.get_doc("Email Template", template_name)
				subject = frappe.render_template(tmpl.subject, {"doc": self})
				message = frappe.render_template(tmpl.response, {"doc": self})

				frappe.sendmail(
					recipients=recipients,
					cc=cc,
					subject=subject,
					message=message,
					now=True
				)
			except Exception as e:
				frappe.log_error(f"Failed to send workflow email for Content Item {self.name}: {str(e)}")


def send_overdue_sla_notifications():
	"""Scheduled job / function to alert involved parties for late items using Marketing Settings template."""
	settings = frappe.get_single("Marketing Settings")
	if not settings.enable_email_notifications:
		return

	template_name = settings.overdue_sla_email_template
	if not (template_name and frappe.db.exists("Email Template", template_name)):
		return

	tmpl = frappe.get_doc("Email Template", template_name)

	overdue_items = frappe.get_all(
		"Content Item",
		filters={
			"risk_flag": "Late",
			"workflow_state": ["not in", ["Approved", "Published"]]
		},
		fields=["name", "title", "assigned_to", "reviewer_technical", "reviewer_business", "sla_due_date", "planned_publish_date"]
	)

	for item_data in overdue_items:
		item = frappe.get_doc("Content Item", item_data.name)
		recipients = set()
		if item.assigned_to:
			recipients.add(item.assigned_to)
		if item.reviewer_technical:
			recipients.add(item.reviewer_technical)
		if item.reviewer_business:
			recipients.add(item.reviewer_business)

		if recipients:
			try:
				subject = frappe.render_template(tmpl.subject, {"doc": item})
				message = frappe.render_template(tmpl.response, {"doc": item})

				frappe.sendmail(
					recipients=list(recipients),
					subject=subject,
					message=message,
					now=True
				)
			except Exception as e:
				frappe.log_error(f"Failed to send overdue email for {item.name}: {str(e)}")
