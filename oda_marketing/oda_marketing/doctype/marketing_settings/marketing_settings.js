// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.ui.form.on("Marketing Settings", {
	refresh(frm) {
		frm.trigger("toggle_template_requirements");
	},

	enable_email_notifications(frm) {
		frm.trigger("toggle_template_requirements");
	},

	toggle_template_requirements(frm) {
		const reqd = frm.doc.enable_email_notifications ? 1 : 0;
		const fields = [
			"default_publisher",
			"writer_email_template",
			"reviewer_email_template",
			"publisher_email_template",
			"published_email_template",
			"overdue_sla_email_template"
		];
		fields.forEach(field => frm.set_df_property(field, "reqd", reqd));
	}
});
