import json

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests import IntegrationTestCase

from tridasa_dpdp import api
from tridasa_dpdp.install import create_dpdp_course


class TestTrainingFlow(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.course = create_dpdp_course()

	def setUp(self):
		frappe.set_user("Administrator")
		self.emp = make_employee("lms.learner@example.com", company=frappe.db.get_value("Company", {}, "name"))
		res = api.invite_employees(course=self.course, employees=json.dumps([self.emp]))
		self.assertEqual(res["matched"], 1)
		self.assignment = frappe.db.get_value("Training Assignment", {"employee": self.emp}, "name")
		frappe.set_user("lms.learner@example.com")

	def tearDown(self):
		frappe.set_user("Administrator")

	def read_all_slides(self):
		for c in api.get_course_player(self.assignment)["chapters"]:
			api.mark_chapter_read(self.assignment, c["idx"])

	def answer(self, paper, correct=True):
		attempt = frappe.get_doc("Training Assessment Attempt", paper["attempt"])
		return {r.idx: r.correct_option if correct else (r.correct_option + 1) % 4 for r in attempt.questions}

	def test_slides_in_order_and_assessment_locked(self):
		self.assertRaises(frappe.ValidationError, api.start_attempt, self.assignment)
		self.assertRaises(frappe.ValidationError, api.mark_chapter_read, self.assignment, 2)

	def test_paper_hides_answers_and_covers_topics(self):
		self.read_all_slides()
		paper = api.start_attempt(self.assignment)
		self.assertNotIn("correct", json.dumps(paper))
		self.assertEqual(len({q["topic"] for q in paper["questions"]}), 10)

	def test_pass_issues_certificate(self):
		self.read_all_slides()
		paper = api.start_attempt(self.assignment)
		res = api.submit_attempt(paper["attempt"], json.dumps(self.answer(paper)))
		self.assertEqual(res["result"], "Passed")
		self.assertTrue(res["certificate"])
		self.assertEqual(frappe.db.get_value("Training Assignment", self.assignment, "status"), "Certified")
		frappe.set_user("Guest")
		self.assertEqual(api.verify_certificate(res["certificate"])["status"], "Active")

	def test_attempt_limit(self):
		self.read_all_slides()
		for _ in range(3):
			paper = api.start_attempt(self.assignment)
			res = api.submit_attempt(paper["attempt"], json.dumps(self.answer(paper, correct=False)))
		self.assertEqual(res["attempts_left"], 0)
		self.assertRaises(frappe.ValidationError, api.start_attempt, self.assignment)

	def test_other_users_cannot_access(self):
		frappe.set_user("Guest")
		self.assertRaises(frappe.PermissionError, api.get_course_player, self.assignment)


class TestAssignAllAndLoginRedirect(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.course = create_dpdp_course()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_assign_all_active_enrols_unassigned_employees(self):
		from tridasa_dpdp.services.enrolment import assign_all_active

		emp = make_employee("lms.everyone@example.com", company=frappe.db.get_value("Company", {}, "name"))
		frappe.db.delete("Training Assignment", {"employee": emp})
		emails_before = frappe.db.count("Email Queue")
		assign_all_active(self.course)
		name = frappe.db.get_value("Training Assignment", {"course": self.course, "employee": emp})
		self.assertTrue(name)
		# Silent: no email queued, not marked as invited
		self.assertEqual(frappe.db.count("Email Queue"), emails_before)
		self.assertFalse(frappe.db.get_value("Training Assignment", name, "invitation_emailed_on"))

	def test_uninvited_assignments_get_no_reminders(self):
		from tridasa_dpdp.services.enrolment import assign_all_active, send_due_reminders

		emp = make_employee("lms.quiet@example.com", company=frappe.db.get_value("Company", {}, "name"))
		assign_all_active(self.course)
		name = frappe.db.get_value("Training Assignment", {"course": self.course, "employee": emp})
		send_due_reminders(course=self.course, force=True)
		self.assertEqual(frappe.db.get_value("Training Assignment", name, "reminders_sent"), 0)

	def test_cancelled_assignment_is_not_reopened(self):
		from tridasa_dpdp.services.enrolment import assign_all_active

		emp = make_employee("lms.exempt@example.com", company=frappe.db.get_value("Company", {}, "name"))
		assign_all_active(self.course)
		name = frappe.db.get_value("Training Assignment", {"course": self.course, "employee": emp})
		frappe.db.set_value("Training Assignment", name, "status", "Cancelled")
		assign_all_active(self.course)
		self.assertEqual(frappe.db.get_value("Training Assignment", name, "status"), "Cancelled")

	def test_login_redirects_to_pending_training(self):
		from tridasa_dpdp.overrides.login import redirect_to_pending_training
		from tridasa_dpdp.services.enrolment import assign_all_active

		user = "lms.redirect@example.com"
		emp = make_employee(user, company=frappe.db.get_value("Company", {}, "name"))
		assign_all_active(self.course)
		name = frappe.db.get_value("Training Assignment", {"course": self.course, "employee": emp})

		frappe.local.form_dict = frappe._dict()
		frappe.cache.hdel("redirect_after_login", user)
		redirect_to_pending_training(frappe._dict(user=user))
		self.assertEqual(frappe.cache.hget("redirect_after_login", user), f"/training/course?a={name}")

		frappe.cache.hdel("redirect_after_login", user)
		frappe.local.form_dict = frappe._dict(redirect_to="/app/todo")
		redirect_to_pending_training(frappe._dict(user=user))
		self.assertIsNone(frappe.cache.hget("redirect_after_login", user))
