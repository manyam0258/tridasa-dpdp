import frappe


def execute():
	"""Assignments, attempts and certificates (and Employee.user_id) were sometimes saved with
	the login's email lowercased instead of its real User ID. The database still matched them,
	but the learner was refused access ('You don't have access to this training'). Restore
	the exact User ID."""
	for table, field in (
		("Training Assignment", "user"),
		("Training Assessment Attempt", "user"),
		("Training Certificate", "user"),
		("Employee", "user_id"),
	):
		frappe.db.sql(
			f"""UPDATE `tab{table}` t JOIN `tabUser` u ON t.`{field}` = u.name
			SET t.`{field}` = u.name
			WHERE BINARY t.`{field}` != BINARY u.name"""
		)
