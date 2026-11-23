import frappe


def execute():
	"""Existing courses: switch on 'Assign to All Active Employees' and 'Open Training Right
	After Login'. The after_migrate hook then enrols every active employee."""
	frappe.db.sql(
		"UPDATE `tabTraining Course` SET assign_to_all_active = 1, redirect_on_login = 1"
	)
