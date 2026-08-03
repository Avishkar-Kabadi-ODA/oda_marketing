// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.ui.form.on("Marketing Settings", {
	refresh(frm) {
		frm.trigger("toggle_mandatory_templates");
	},
	enable_email_notifications(frm) {
		frm.trigger("toggle_mandatory_templates");
	},
	toggle_mandatory_templates(frm) {
		const enabled = frm.doc.enable_email_notifications ? 1 : 0;
		frm.set_df_property("default_publisher", "reqd", enabled);
		frm.set_df_property("writer_email_template", "reqd", enabled);
		frm.set_df_property("reviewer_email_template", "reqd", enabled);
		frm.set_df_property("publisher_email_template", "reqd", enabled);
		frm.set_df_property("overdue_sla_email_template", "reqd", enabled);
	}
});
