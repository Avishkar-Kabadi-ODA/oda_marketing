// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.ui.form.on("Marketing Settings", {
	refresh(frm) {
		frm.trigger("toggle_ai_copilot_fields");
	},
	enable_ai_copilot(frm) {
		frm.trigger("toggle_ai_copilot_fields");
	},
	toggle_ai_copilot_fields(frm) {
		const enabled = Boolean(frm.doc.enable_ai_copilot);
		const ai_fields = [
			"ai_copilot_passing_score",
			"max_writer_copilot_reviews_per_item",
			"max_reviewer_copilot_reviews_per_item",
			"ai_provider",
			"ai_api_key_var",
			"ai_endpoint_var",
			"ai_model_name",
			"subagent_meta_prompt",
			"evaluator_default_prompt"
		];
		ai_fields.forEach(field => {
			frm.set_df_property(field, "hidden", enabled ? 0 : 1);
			frm.set_df_property(field, "reqd", enabled ? 1 : 0);
		});
	}
});
