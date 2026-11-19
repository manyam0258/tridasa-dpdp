// Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
// For license information, please see license.txt

const TA_COLORS = {
	Invited: "gray",
	"In Progress": "blue",
	"Course Completed": "purple",
	"Assessment Failed": "orange",
	Certified: "green",
	Expired: "red",
	Cancelled: "darkgrey",
};

frappe.listview_settings["Training Assignment"] = {
	add_fields: ["status", "overdue"],
	hide_name_column: true,
	get_indicator(doc) {
		if (doc.overdue && doc.status !== "Certified") return [__("Overdue"), "red", "overdue,=,1"];
		return [__(doc.status), TA_COLORS[doc.status] || "gray", `status,=,${doc.status}`];
	},
};
