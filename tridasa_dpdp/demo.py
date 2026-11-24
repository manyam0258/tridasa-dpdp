"""Sample data for trying the invite → slides → assessment → certificate flow.

    bench --site <site> execute tridasa_dpdp.demo.make_demo
"""

import frappe

COMPANY = "Tridasa Realty Ventures Pvt. Ltd."
ABBR = "TRV"
DEPARTMENTS = ["Sales", "Marketing", "CRM & Customer Relations", "Finance & Accounts", "Human Resources", "IT"]

# (first, last, gender, department, email, create desk login)
EMPLOYEES = [
	("Ananya", "Rao", "Female", "Human Resources", "ananya.rao@tridasa.test", True),
	("Vikram", "Reddy", "Male", "Sales", "vikram.reddy@tridasa.test", False),
	("Meera", "Iyer", "Female", "Sales", "meera.iyer@tridasa.test", False),
	("Arjun", "Nair", "Male", "Marketing", "arjun.nair@tridasa.test", False),
	("Kavya", "Sharma", "Female", "CRM & Customer Relations", "kavya.sharma@tridasa.test", False),
	("Rohit", "Varma", "Male", "Finance & Accounts", "rohit.varma@tridasa.test", True),
	("Sneha", "Kulkarni", "Female", "IT", "sneha.kulkarni@tridasa.test", False),
	("Farhan", "Ali", "Male", "Sales", None, False),  # no email: shows up in the invite summary
]


def make_demo():
	complete_setup()
	frappe.set_user("Administrator")
	for d in DEPARTMENTS:
		if not frappe.db.exists("Department", f"{d} - {ABBR}"):
			frappe.get_doc({"doctype": "Department", "department_name": d, "company": COMPANY}).insert()

	hr_head = None
	for first, last, gender, dept, email, desk in EMPLOYEES:
		if frappe.db.exists("Employee", {"first_name": first, "last_name": last}):
			continue
		user = None
		if desk:
			user = frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": first, "last_name": last, "send_welcome_email": 0,
				 "roles": [{"role": "Employee"}]}
			).insert().name
		emp = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first,
				"last_name": last,
				"gender": gender,
				"date_of_birth": "1992-04-12",
				"date_of_joining": "2024-06-01",
				"status": "Active",
				"company": COMPANY,
				"department": f"{dept} - {ABBR}",
				"company_email": email if not desk else None,
				"prefered_contact_email": "Company Email" if (email and not desk) else "",
				"user_id": user,
				"reports_to": hr_head,
			}
		)
		emp.flags.ignore_mandatory = True
		emp.insert()
		if first == "Ananya":
			hr_head = emp.name
			frappe.get_doc("User", user).add_roles("Training Manager")
	frappe.db.commit()
	print(frappe.get_all("Employee", fields=["name", "employee_name", "department", "user_id", "company_email"]))


def complete_setup():
	if frappe.is_setup_complete():
		return
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	setup_complete(
		{
			"language": "English",
			"country": "India",
			"timezone": "Asia/Kolkata",
			"currency": "INR",
			"company_name": COMPANY,
			"company_abbr": ABBR,
			"chart_of_accounts": "Standard",
			"fy_start_date": "2026-04-01",
			"fy_end_date": "2027-03-31",
			"setup_demo": 0,
		}
	)
