// Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Training Course", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Question Bank"), () =>
			frappe.set_route("List", "Training Question", { course: frm.doc.name })
		);
		frm.add_custom_button(__("Compliance Report"), () =>
			frappe.set_route("query-report", "Training Compliance", { course: frm.doc.name })
		, __("View"));
		frm.add_custom_button(__("Assignments"), () =>
			frappe.set_route("List", "Training Assignment", { course: frm.doc.name })
		, __("View"));
		frm.add_custom_button(__("Preview a Paper"), () => preview_paper(frm), __("View"));

		if (frm.doc.status === "Published") {
			frm.add_custom_button(__("Assign to All Active Employees"), () => assign_all(frm), __("Actions"));
			frm.add_custom_button(__("Email Invitations…"), () => email_invitations_dialog(frm), __("Actions"));
			frm.add_custom_button(__("Invite Employees"), () => invite_dialog(frm), __("Actions"));
			frm.add_custom_button(__("Send Reminders Now"), () =>
				frappe.confirm(__("Email a reminder to everyone who was sent an invitation and hasn't finished yet?"), () =>
					frappe
						.call("tridasa_dpdp.api.send_reminders_now", { course: frm.doc.name })
						.then(({ message }) => frappe.show_alert({ message: __("{0} reminders sent", [message.sent]), indicator: "green" }))
				)
			, __("Actions"));
			frm.page.set_inner_btn_group_as_primary(__("Actions"));
		}
		render_funnel(frm);
		frappe.realtime.off("tridasa_dpdp_emails_done");
		frappe.realtime.on("tridasa_dpdp_emails_done", (data) => {
			if (data.course !== frm.doc.name) return;
			show_email_summary(data);
			render_funnel(frm);
		});
		frappe.realtime.off("tridasa_dpdp_invites_done");
		frappe.realtime.on("tridasa_dpdp_invites_done", (data) => {
			if (data.course !== frm.doc.name) return;
			show_invite_summary(data);
			render_funnel(frm);
		});
	},
});

function render_funnel(frm) {
	frappe.call("tridasa_dpdp.api.get_course_dashboard", { course: frm.doc.name }).then(({ message: s }) => {
		if (!s) return;
		const cell = (label, value, color, filters) =>
			`<a class="col" style="text-decoration:none" href="/app/training-assignment?course=${encodeURIComponent(frm.doc.name)}${filters || ""}">
				<div style="font-size:22px;font-weight:600;color:var(--${color}-600, var(--text-color))">${value}</div>
				<div class="text-muted small">${label}</div></a>`;
		const html = `<div class="row text-center" style="padding:6px 0">
			${cell(__("Invited"), s.invited, "gray")}
			${cell(__("Not started"), s.not_started, "gray", "&status=Invited")}
			${cell(__("Reading"), s.reading, "blue", "&status=In%20Progress")}
			${cell(__("Slides done"), s.slides_done, "blue")}
			${cell(__("Attempted"), s.attempted, "orange", "&attempts_used=%5B%22%3E%22%2C0%5D")}
			${cell(__("Certified"), s.certified, "green", "&status=Certified")}
			${cell(__("Overdue"), s.overdue, "red", "&overdue=1")}
			${cell(__("Completion"), s.completion + "%", "green")}
		</div>${s.avg_best_score !== null ? `<div class="text-muted small text-center">${__("Average best score")}: ${s.avg_best_score}%</div>` : ""}`;
		frm.dashboard.reset();
		frm.dashboard.add_section(html, __("Training progress"));
		frm.dashboard.show();
	});
}

function invite_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Invite Employees to {0}", [frm.doc.course_name]),
		fields: [
			{ fieldtype: "HTML", options: `<p class="text-muted">${__("Active employees matching the filters are enrolled. If 'Send invitation email' is ticked they are also emailed a link, and employees without a login get one with a set-password link. Anyone already enrolled is skipped.")}</p>` },
			{ fieldname: "company", fieldtype: "Link", options: "Company", label: __("Company"), default: frm.doc.company },
			{ fieldname: "department", fieldtype: "Link", options: "Department", label: __("Department") },
			{ fieldtype: "Column Break" },
			{ fieldname: "branch", fieldtype: "Link", options: "Branch", label: __("Branch") },
			{ fieldname: "designation", fieldtype: "Link", options: "Designation", label: __("Designation") },
			{ fieldtype: "Section Break" },
			{ fieldname: "employee_list", fieldtype: "MultiSelectList", label: __("Only these employees (optional)"),
				get_data: (txt) => frappe.db.get_link_options("Employee", txt, { status: "Active" }) },
			{ fieldname: "due_in_days", fieldtype: "Int", label: __("Complete within (days)"), default: frm.doc.due_in_days },
			{ fieldname: "send_email", fieldtype: "Check", label: __("Send invitation email now"), default: 1,
				description: __("Untick to assign quietly; email them later with Actions → Email Invitations.") },
			{ fieldname: "preview", fieldtype: "HTML" },
		],
		primary_action_label: __("Send Invitations"),
		primary_action(values) {
			d.disable_primary_action();
			frappe
				.call({
					method: "tridasa_dpdp.api.invite_employees",
					args: {
						course: frm.doc.name,
						company: values.company,
						department: values.department,
						branch: values.branch,
						designation: values.designation,
						employees: values.employee_list && values.employee_list.length ? values.employee_list : null,
						due_in_days: values.due_in_days,
						send_email: values.send_email ? 1 : 0,
					},
					freeze: true,
					freeze_message: __("Sending invitations…"),
				})
				.then(({ message }) => {
					d.hide();
					if (!message.matched) return frappe.msgprint(__("No active employees match these filters."));
					if (message.queued) {
						return frappe.msgprint(__("Inviting {0} employees in the background. You'll see a summary here when it's done.", [message.matched]));
					}
					show_invite_summary(message);
					frm.reload_doc();
				})
				.always(() => d.enable_primary_action());
		},
	});
	const refresh_count = frappe.utils.debounce(() => {
		const v = d.get_values(true);
		const filters = { status: "Active" };
		["company", "department", "branch", "designation"].forEach((k) => v[k] && (filters[k] = v[k]));
		if (v.employee_list && v.employee_list.length) filters.name = ["in", v.employee_list];
		frappe.db.count("Employee", { filters }).then((n) =>
			d.fields_dict.preview..html(`<p><b>${n}</b> ${__("active employees match.")}</p>`)
		);
	}, 300);
	["company", "department", "branch", "designation", "employee_list"].forEach((f) => (d.fields_dict[f].df.onchange = refresh_count));
	d.show();
	refresh_count();
}

function show_invite_summary(s) {
	const rows = [
		[s.notified === false ? __("Newly assigned (no email sent)") : __("Newly invited"), s.invited],
		[__("Re-invited (expired / cancelled)"), s.reinvited],
		[__("Already enrolled, skipped"), s.already_enrolled],
		[__("Logins created"), s.users_created],
	];
	let html = `<table class="table table-bordered">${rows.map(([l, v]) => `<tr><td>${l}</td><td><b>${v || 0}</b></td></tr>`).join("")}</table>`;
	if (s.emails_failed) {
		html += `<p class="text-warning">${__("{0} invitation email(s) could not be sent because no outgoing Email Account is configured. The employees are enrolled; set up the email account, then use Send Reminders Now.", [s.emails_failed])}</p>`;
	}
	if (s.no_email && s.no_email.length) {
		html += `<p class="text-danger">${__("No email address on these employees, so they could not be invited. Add a company or personal email and invite again:")}</p><p>${s.no_email
			.map((e) => `<a href="/app/employee/${encodeURIComponent(e)}">${frappe.utils.escape_html(e)}</a>`)
			.join(", ")}</p>`;
	}
	frappe.msgprint({ title: __("Invitations sent"), message: html, indicator: "green" });
}

function preview_paper(frm) {
	frappe.call("tridasa_dpdp.api.preview_paper", { course: frm.doc.name }).then(({ message }) => {
		const html = message
			.map((q, i) => `<div style="margin-bottom:14px"><div class="text-muted small">${frappe.utils.escape_html(q.topic)}</div>
				<b>Q${i + 1}. ${frappe.utils.escape_html(q.question)}</b>
				<ol type="A" style="margin:6px 0 0">${q.options.map((o, k) => `<li style="${k === q.correct ? "color:var(--green-600);font-weight:600" : ""}">${frappe.utils.escape_html(o)}${k === q.correct ? " ✓" : ""}</li>`).join("")}</ol></div>`)
			.join("");
		frappe.msgprint({ title: __("Sample paper with answer key"), message: html, wide: true });
	});
}

function assign_all(frm) {
	frappe.confirm(
		__("Assign this course to every active employee who isn't enrolled yet? No emails are sent; they'll see it on their trainings page and when they log in. Use Email Invitations when you want to email them."),
		() =>
			frappe.call("tridasa_dpdp.api.assign_all_now", { course: frm.doc.name }).then(({ message }) => {
				if (!message.pending) return frappe.msgprint(__("Every active employee is already enrolled."));
				frappe.msgprint(
					__("Assigning {0} employees in the background (no emails). You'll see a summary here when it's done.", [message.pending])
				);
			})
	);
}

function email_invitations_dialog(frm) {
	frappe.call("tridasa_dpdp.api.get_invitation_counts", { course: frm.doc.name }).then(({ message: c }) => {
		const d = new frappe.ui.Dialog({
			title: __("Email Invitations"),
			fields: [
				{
					fieldtype: "HTML",
					options: `<p class="text-muted">${__("Sends the course link to employees who haven't finished it. Employees without a login get one, with a set-password link. Runs in the background.")}</p>`,
				},
				{
					fieldname: "scope",
					fieldtype: "Select",
					label: __("Send to"),
					reqd: 1,
					default: "not_emailed",
					options: [
						{ value: "not_emailed", label: __("Not emailed yet ({0})", [c.not_emailed]) },
						{ value: "open", label: __("Everyone who hasn't finished ({0})", [c.open]) },
					],
				},
				{ fieldname: "department", fieldtype: "Link", options: "Department", label: __("Only this department (optional)") },
			],
			primary_action_label: __("Send Emails"),
			primary_action(values) {
				const n = values.scope === "open" ? c.open : c.not_emailed;
				frappe.confirm(__("Email up to {0} employees now?", [n]), () => {
					d.hide();
					frappe
						.call("tridasa_dpdp.api.email_invitations", { course: frm.doc.name, scope: values.scope, department: values.department })
						.then(() => frappe.show_alert({ message: __("Sending emails in the background…"), indicator: "blue" }));
				});
			},
		});
		d.show();
	});
}

function show_email_summary(s) {
	const rows = [
		[__("Emails sent"), s.emailed],
		[__("Logins created"), s.users_created],
		[__("Could not send"), s.emails_failed],
	];
	let html = `<table class="table table-bordered">${rows.map(([l, v]) => `<tr><td>${l}</td><td><b>${v || 0}</b></td></tr>`).join("")}</table>`;
	if (s.emails_failed) {
		html += `<p class="text-warning">${__("Some emails could not be sent. Check that a default outgoing Email Account is set up, then send again.")}</p>`;
	}
	if (s.no_email && s.no_email.length) {
		html += `<p class="text-danger">${__("No email address on these employees:")} ${s.no_email
			.map((e) => `<a href="/app/employee/${encodeURIComponent(e)}">${frappe.utils.escape_html(e)}</a>`)
			.join(", ")}</p>`;
	}
	frappe.msgprint({ title: __("Invitation emails"), message: html, indicator: s.emails_failed ? "orange" : "green" });
}
