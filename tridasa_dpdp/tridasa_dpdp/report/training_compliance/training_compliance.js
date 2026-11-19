// Copyright (c) 2026, Tridasa Realty Ventures Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Training Compliance"] = {
	filters: [
		{ fieldname: "course", label: __("Course"), fieldtype: "Link", options: "Training Course" },
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: "Department\nBranch\nDesignation\nCompany",
			default: "Department",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (column.fieldname === "overdue" && data.overdue) return `<span style="color:var(--red-600);font-weight:600">${value}</span>`;
		if (column.fieldname === "certified" && data.certified) return `<span style="color:var(--green-600);font-weight:600">${value}</span>`;
		return value;
	},
};
