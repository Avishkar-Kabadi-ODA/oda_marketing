// Copyright (c) 2026, Optimum Data Analytics and contributors
// For license information, please see license.txt

frappe.pages["marketing-dashboard"].on_page_load = function(wrapper) {
	const is_lead = frappe.user.has_role("Marketing Lead") || frappe.user.has_role("System Manager") || frappe.session.user === "Administrator";

	if (!is_lead) {
		frappe.show_not_permitted(__("Access Restricted: The Marketing Operations Dashboard is only accessible by Marketing Leads and System Managers."));
		frappe.set_route("List", "Content Item");
		return;
	}

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Marketing Operations Dashboard"),
		single_column: true
	});

	page.dashboard = new MarketingOperationsDashboard(page);
};

class MarketingOperationsDashboard {
	constructor(page) {
		this.page = page;
		this.wrapper = $(page.body);
		this.charts = {};
		this.options_loaded = false;
		this.last_data = null;

		this.setup_header_actions();
		this.render_layout();
		this.bind_filter_events();
		this.fetch_data();

		$(window).off("resize.marketing_dashboard").on("resize.marketing_dashboard", frappe.utils.debounce(() => {
			if (this.last_data) {
				this.render_charts(this.last_data);
			}
		}, 200));
	}


	setup_header_actions() {
		this.page.set_secondary_action(__("Refresh"), () => {
			this.fetch_data();
		}, "octicon octicon-sync");

		this.page.set_primary_action(__("View Content Items"), () => {
			frappe.set_route("List", "Content Item");
		}, "octicon octicon-checklist");
	}

	render_layout() {
		const current_year = new Date().getFullYear();

		const months = [
			{ label: __("Full Year"), val: "0" },
			{ label: __("January (M01)"), val: "1" },
			{ label: __("February (M02)"), val: "2" },
			{ label: __("March (M03)"), val: "3" },
			{ label: __("April (M04)"), val: "4" },
			{ label: __("May (M05)"), val: "5" },
			{ label: __("June (M06)"), val: "6" },
			{ label: __("July (M07)"), val: "7" },
			{ label: __("August (M08)"), val: "8" },
			{ label: __("September (M09)"), val: "9" },
			{ label: __("October (M10)"), val: "10" },
			{ label: __("November (M11)"), val: "11" },
			{ label: __("December (M12)"), val: "12" }
		];

		const month_options_html = months.map(m => `<option value="${m.val}">${m.label}</option>`).join("");
		const year_options_html = `
			<option value="${current_year}">${current_year}</option>
			<option value="${current_year - 1}">${current_year - 1}</option>
			<option value="${current_year + 1}">${current_year + 1}</option>
			<option value="All">All Years</option>
		`;

		this.wrapper.html(`
			<div class="marketing-dashboard-wrapper">
				<!-- Dedicated Responsive Filter Toolbar Card -->
				<div class="dashboard-filter-card">
					<div class="dashboard-filter-header">
						<div style="display: flex; align-items: center; gap: 8px;">
							<span style="font-weight: 700; color: #1E293B; font-size: 14px;">
								<i class="octicon octicon-filter" style="color: #4F46E5; margin-right: 4px;"></i> Analytics Filter Controls
							</span>
							<span class="badge badge-light" id="active-filter-summary" style="font-size: 11px; color: #64748B;">All Records</span>
						</div>
						<div>
							<button class="btn btn-xs btn-default" id="btn-reset-filters" style="font-weight: 600;">
								<i class="octicon octicon-x"></i> Reset Filters
							</button>
						</div>
					</div>

					<div class="filter-grid">
						<!-- 1. Content Calendar Filter -->
						<div class="filter-item">
							<label class="filter-label">
								<i class="octicon octicon-calendar"></i> Content Calendar
							</label>
							<select class="filter-select" id="filter-calendar">
								<option value="All">All Calendars</option>
							</select>
						</div>

						<!-- 2. Year Filter -->
						<div class="filter-item">
							<label class="filter-label">
								<i class="octicon octicon-clock"></i> Year
							</label>
							<select class="filter-select" id="filter-year">
								${year_options_html}
							</select>
						</div>

						<!-- 3. Month / Period Filter -->
						<div class="filter-item">
							<label class="filter-label">
								<i class="octicon octicon-milestone"></i> Month / Period
							</label>
							<select class="filter-select" id="filter-month">
								${month_options_html}
							</select>
						</div>

						<!-- 4. Format Filter -->
						<div class="filter-item">
							<label class="filter-label">
								<i class="octicon octicon-tag"></i> Format
							</label>
							<select class="filter-select" id="filter-format">
								<option value="All">All Formats</option>
							</select>
						</div>

						<!-- 5. Industry Domain Filter -->
						<div class="filter-item">
							<label class="filter-label">
								<i class="octicon octicon-globe"></i> Domain
							</label>
							<select class="filter-select" id="filter-domain">
								<option value="All">All Domains</option>
							</select>
						</div>

						<!-- 6. Risk Status Filter -->
						<div class="filter-item">
							<label class="filter-label">
								<i class="octicon octicon-alert"></i> Risk Status
							</label>
							<select class="filter-select" id="filter-risk">
								<option value="All">All Risk Levels</option>
								<option value="On track">On track</option>
								<option value="At risk">At risk</option>
								<option value="Late">Late</option>
							</select>
						</div>
					</div>
				</div>

				<!-- Responsive KPI Cards Grid -->
				<div class="kpi-grid">
					<div class="kpi-box" data-state="">
						<div class="kpi-title" style="color: #4F46E5;">Total Deliverables</div>
						<div class="kpi-value" id="kpi-total">0</div>
						<div class="kpi-subtitle">In current scope</div>
					</div>
					<div class="kpi-box" data-state="Planned">
						<div class="kpi-title" style="color: #64748B;">Planned</div>
						<div class="kpi-value" id="kpi-planned" style="color: #475569;">0</div>
						<div class="kpi-subtitle">Not yet briefed</div>
					</div>
					<div class="kpi-box" data-state="Briefed">
						<div class="kpi-title" style="color: #2563EB;">Briefed</div>
						<div class="kpi-value" id="kpi-briefed" style="color: #1D4ED8;">0</div>
						<div class="kpi-subtitle">Ready to start</div>
					</div>
					<div class="kpi-box" data-state="In Progress">
						<div class="kpi-title" style="color: #EA580C;">In Progress</div>
						<div class="kpi-value" id="kpi-in-progress" style="color: #C2410C;">0</div>
						<div class="kpi-subtitle">Active drafting</div>
					</div>
					<div class="kpi-box" data-state="In Review">
						<div class="kpi-title" style="color: #CA8A04;">In Review</div>
						<div class="kpi-value" id="kpi-in-review" style="color: #A16207;">0</div>
						<div class="kpi-subtitle">Pending approval</div>
					</div>
					<div class="kpi-box" data-state="In Revision">
						<div class="kpi-title" style="color: #DC2626;">In Revision</div>
						<div class="kpi-value" id="kpi-in-revision" style="color: #B91C1C;">0</div>
						<div class="kpi-subtitle">Changes requested</div>
					</div>
					<div class="kpi-box" data-state="Approved">
						<div class="kpi-title" style="color: #0891B2;">Approved</div>
						<div class="kpi-value" id="kpi-approved" style="color: #0E7490;">0</div>
						<div class="kpi-subtitle">Ready to publish</div>
					</div>
					<div class="kpi-box" data-state="Published">
						<div class="kpi-title" style="color: #059669;">Published</div>
						<div class="kpi-value" id="kpi-published" style="color: #047857;">0</div>
						<div class="kpi-subtitle">Live on channels</div>
					</div>
					<div class="kpi-box" data-risk="Late">
						<div class="kpi-title" style="color: #BE123C;">Late Risk</div>
						<div class="kpi-value" id="kpi-late" style="color: #BE123C;">0</div>
						<div class="kpi-subtitle">Past SLA due date</div>
					</div>
					<div class="kpi-box">
						<div class="kpi-title" style="color: #7E22CE;">AI Quality Score</div>
						<div class="kpi-value" id="kpi-ai-score" style="color: #7E22CE;">--</div>
						<div class="kpi-subtitle">Average score</div>
					</div>
				</div>

				<!-- Responsive Visual Charts Grid -->
				<div class="charts-grid">
					<div class="chart-card">
						<div class="chart-card-title">
							<i class="octicon octicon-pulse" style="color: #4F46E5;"></i> Workflow Pipeline Funnel
						</div>
						<div id="chart-status-funnel" class="chart-container"></div>
						<div id="funnel-custom-legend" class="dashboard-custom-legend"></div>
					</div>

					<div class="chart-card">
						<div class="chart-card-title">
							<i class="octicon octicon-graph" style="color: #6366F1;"></i> Monthly Publication Cadence
						</div>
						<div id="chart-monthly-cadence" class="chart-container"></div>
					</div>

					<div class="chart-card">
						<div class="chart-card-title">
							<i class="octicon octicon-tag" style="color: #8B5CF6;"></i> Content Format Distribution
						</div>
						<div id="chart-format-mix" class="chart-container"></div>
					</div>

					<div class="chart-card">
						<div class="chart-card-title">
							<i class="octicon octicon-globe" style="color: #0EA5E9;"></i> Industry Domain Breakdown
						</div>
						<div id="chart-domain-breakdown" class="chart-container"></div>
					</div>
				</div>
			</div>
		`);

		// KPI Card Click Navigation
		this.wrapper.find(".kpi-box").on("click", function() {
			const state = $(this).data("state");
			const risk = $(this).data("risk");
			if (state) {
				frappe.set_route("List", "Content Item", { workflow_state: state });
			} else if (risk) {
				frappe.set_route("List", "Content Item", { risk_flag: risk });
			} else {
				frappe.set_route("List", "Content Item");
			}
		});
	}

	bind_filter_events() {
		const me = this;

		// Listen to changes on any filter select
		this.wrapper.find(".filter-select").on("change", function() {
			me.fetch_data();
		});

		// Reset filters button
		this.wrapper.find("#btn-reset-filters").on("click", function() {
			const current_year = new Date().getFullYear();
			me.wrapper.find("#filter-calendar").val("All");
			me.wrapper.find("#filter-year").val(String(current_year));
			me.wrapper.find("#filter-month").val("0");
			me.wrapper.find("#filter-format").val("All");
			me.wrapper.find("#filter-domain").val("All");
			me.wrapper.find("#filter-risk").val("All");
			me.fetch_data();
		});
	}

	fetch_data() {
		const me = this;
		const cal = this.wrapper.find("#filter-calendar").val() || "All";
		const year = this.wrapper.find("#filter-year").val() || String(new Date().getFullYear());
		const month = this.wrapper.find("#filter-month").val() || "0";
		const format = this.wrapper.find("#filter-format").val() || "All";
		const domain = this.wrapper.find("#filter-domain").val() || "All";
		const risk = this.wrapper.find("#filter-risk").val() || "All";

		frappe.call({
			method: "oda_marketing.oda_marketing.doctype.content_item.content_item.get_dashboard_metrics",
			args: {
				calendar: cal,
				year: year,
				month: month,
				format: format,
				domain: domain,
				risk: risk
			},
			callback(res) {
				if (res && res.message) {
					const data = res.message;
					me.last_data = data;
					if (!me.options_loaded) {
						me.populate_dynamic_options(data);
						me.options_loaded = true;
					}
					me.render_kpis(data.kpis || {});
					me.render_charts(data);
					me.update_summary_label(cal, year, month, format, domain, risk);
				}
			}
		});
	}

	populate_dynamic_options(data) {
		// Populate Calendars
		if (data.calendars && data.calendars.length > 0) {
			const $cal = this.wrapper.find("#filter-calendar");
			const cur_val = $cal.val();
			$cal.empty().append(`<option value="All">All Calendars</option>`);
			data.calendars.forEach(c => {
				$cal.append(`<option value="${c.name}">${c.name}</option>`);
			});
			if (cur_val) $cal.val(cur_val);
		}

		// Populate Formats
		if (data.formats && data.formats.length > 0) {
			const $fmt = this.wrapper.find("#filter-format");
			const cur_val = $fmt.val();
			$fmt.empty().append(`<option value="All">All Formats</option>`);
			data.formats.forEach(f => {
				$fmt.append(`<option value="${f}">${f}</option>`);
			});
			if (cur_val) $fmt.val(cur_val);
		}

		// Populate Domains
		if (data.domains && data.domains.length > 0) {
			const $dom = this.wrapper.find("#filter-domain");
			const cur_val = $dom.val();
			$dom.empty().append(`<option value="All">All Domains</option>`);
			data.domains.forEach(d => {
				$dom.append(`<option value="${d}">${d}</option>`);
			});
			if (cur_val) $dom.val(cur_val);
		}
	}

	update_summary_label(cal, year, month, format, domain, risk) {
		let parts = [];
		if (cal !== "All") parts.push(cal);
		if (year !== "All") parts.push(year);
		if (month !== "0" && month !== "All") {
			const month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
			parts.push(month_names[parseInt(month)] || `M${month}`);
		}
		if (format !== "All") parts.push(format);
		if (domain !== "All") parts.push(domain);
		if (risk !== "All") parts.push(risk);

		const summary_text = parts.length > 0 ? parts.join(" • ") : "All Records";
		this.wrapper.find("#active-filter-summary").text(summary_text);
	}

	render_kpis(kpis) {
		this.wrapper.find("#kpi-total").text(kpis.total || 0);
		this.wrapper.find("#kpi-planned").text(kpis.planned || 0);
		this.wrapper.find("#kpi-briefed").text(kpis.briefed || 0);
		this.wrapper.find("#kpi-in-progress").text(kpis.in_progress || 0);
		this.wrapper.find("#kpi-in-review").text(kpis.in_review || 0);
		this.wrapper.find("#kpi-in-revision").text(kpis.in_revision || 0);
		this.wrapper.find("#kpi-approved").text(kpis.approved || 0);
		this.wrapper.find("#kpi-published").text(kpis.published || 0);
		this.wrapper.find("#kpi-late").text(kpis.late_risk || 0);

		if (kpis.avg_ai_score && kpis.avg_ai_score > 0) {
			this.wrapper.find("#kpi-ai-score").text(`${kpis.avg_ai_score}%`);
		} else {
			this.wrapper.find("#kpi-ai-score").text("--");
		}
	}

	render_charts(data) {
		// 1. Status Funnel Donut Chart
		const status_color_map = {
			"Planned": "#64748B",
			"Briefed": "#2563EB",
			"In Progress": "#EA580C",
			"In Review": "#CA8A04",
			"In Revision": "#DC2626",
			"Approved": "#0891B2",
			"Published": "#059669"
		};

		const status_labels = Object.keys(data.status_distribution || {});
		const status_values = Object.values(data.status_distribution || {});
		const status_colors = status_labels.map(lbl => status_color_map[lbl] || "#6366F1");

		$("#chart-status-funnel").empty();
		this.charts.status_funnel = new frappe.Chart("#chart-status-funnel", {
			title: "",
			data: {
				labels: status_labels.length ? status_labels : ["None"],
				datasets: [{ name: __("Deliverables"), values: status_values.length ? status_values : [0] }]
			},
			type: "donut",
			height: 290,
			colors: status_colors,
			maxSlices: 8,
			truncateLegends: 0
		});

		// Responsive custom status pills below the donut chart
		const $legendContainer = $("#funnel-custom-legend");
		$legendContainer.empty();
		if (status_labels.length > 0) {
			const total_items = status_values.reduce((a, b) => a + b, 0);
			status_labels.forEach((label, idx) => {
				const val = status_values[idx] || 0;
				const color = status_colors[idx] || "#64748B";
				const pct = total_items > 0 ? Math.round((val / total_items) * 100) : 0;
				$legendContainer.append(`
					<div class="legend-pill" data-state="${label}" title="${label}: ${val} (${pct}%) • Click to filter">
						<span class="legend-dot" style="background-color: ${color};"></span>
						<span class="legend-name">${label}</span>
						<span class="legend-count">${val}</span>
					</div>
				`);
			});

			$legendContainer.find(".legend-pill").on("click", function() {
				const st = $(this).data("state");
				if (st) {
					frappe.set_route("List", "Content Item", { workflow_state: st });
				}
			});
		}

		// 2. Monthly Cadence Bar Chart
		const monthly_data = data.monthly_trend || [];
		const month_labels = monthly_data.map(m => m.month);
		const month_values = monthly_data.map(m => m.count);

		$("#chart-monthly-cadence").empty();
		this.charts.monthly_cadence = new frappe.Chart("#chart-monthly-cadence", {
			title: "",
			data: {
				labels: month_labels,
				datasets: [{ name: __("Deliverables"), values: month_values }]
			},
			type: "bar",
			height: 240,
			colors: ["#6366F1"]
		});

		// 3. Format Mix Bar Chart
		const format_labels = Object.keys(data.format_distribution || {});
		const format_values = Object.values(data.format_distribution || {});

		$("#chart-format-mix").empty();
		this.charts.format_mix = new frappe.Chart("#chart-format-mix", {
			title: "",
			data: {
				labels: format_labels.length ? format_labels : ["None"],
				datasets: [{ name: __("Deliverables"), values: format_values.length ? format_values : [0] }]
			},
			type: "bar",
			height: 240,
			colors: ["#8B5CF6"]
		});

		// 4. Industry Domain Breakdown Bar Chart
		const domain_labels = Object.keys(data.domain_distribution || {});
		const domain_values = Object.values(data.domain_distribution || {});

		$("#chart-domain-breakdown").empty();
		this.charts.domain_breakdown = new frappe.Chart("#chart-domain-breakdown", {
			title: "",
			data: {
				labels: domain_labels.length ? domain_labels : ["None"],
				datasets: [{ name: __("Deliverables"), values: domain_values.length ? domain_values : [0] }]
			},
			type: "bar",
			height: 240,
			colors: ["#0EA5E9"]
		});
	}
}
