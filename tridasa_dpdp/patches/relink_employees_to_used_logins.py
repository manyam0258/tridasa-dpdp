import frappe


def execute():
	"""Training had been attached to logins nobody signs in with (created from an Employee's
	preferred email when the Employee wasn't linked to the person's real login). Link each
	Employee to the login they use and move their training there."""
	from tridasa_dpdp.services.enrolment import relink_employee_logins

	fixed = relink_employee_logins()
	print(f"Tridasa DPDP: re-linked {fixed} employee(s) to the login they use")
