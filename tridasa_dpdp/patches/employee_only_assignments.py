import frappe


def execute():
	"""Training is mapped to Employees only. Assignments made earlier for logins without an
	Employee record are moved onto the person's Employee when one can be matched (linked
	User ID, or company/preferred/personal email); otherwise they are cancelled."""
	from tridasa_dpdp.services.enrolment import _link_employee_by_email, adopt_user_assignments

	moved = cancelled = 0
	for r in frappe.get_all(
		"Training Assignment", filters={"employee": ("is", "not set")}, fields=["name", "user", "status"]
	):
		employee = None
		if r.user:
			employee = frappe.db.get_value("Employee", {"user_id": r.user, "status": "Active"})
			if not employee:
				linked = _link_employee_by_email(r.user)
				employee = linked[0] if linked else None
		if employee:
			moved += adopt_user_assignments(employee, r.user)
			continue
		if r.status != "Cancelled":
			frappe.db.set_value(
				"Training Assignment",
				r.name,
				{
					"status": "Cancelled",
					"overdue": 0,
					"cancel_reason": "Training is for employees only: this login has no Employee record.",
				},
			)
			cancelled += 1
	print(f"Tridasa DPDP: {moved} assignment(s) moved to Employees, {cancelled} cancelled (no Employee)")
