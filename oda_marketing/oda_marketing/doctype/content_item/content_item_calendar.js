frappe.views.calendar["Content Item"] = {
	field_map: {
		start: "planned_publish_date",
		end: "planned_publish_date",
		id: "name",
		title: "title",
		allDay: "allDay",
		status: "workflow_state"
	},
	style_map: {
		"Planned": "info",
		"Briefed": "info",
		"In Progress": "warning",
		"In Review - Technical": "warning",
		"In Review - Business": "purple",
		"In Revision": "danger",
		"Approved": "success",
		"Published": "success"
	},
	filters: [
		{
			fieldname: "content_calendar",
			fieldtype: "Link",
			options: "Content Calendar",
			label: __("Content Calendar")
		},
		{
			fieldname: "content_type",
			fieldtype: "Select",
			options: "\nBlog\nPoll\nFlowchart\nCarousel",
			label: __("Content Type")
		},
		{
			fieldname: "assigned_to",
			fieldtype: "Link",
			options: "User",
			label: __("Assigned To")
		}
	],
	get_events_method: "frappe.desk.calendar.get_events"
};
