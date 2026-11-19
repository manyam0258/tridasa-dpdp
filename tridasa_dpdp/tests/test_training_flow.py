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
