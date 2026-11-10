import json
import os

import frappe

ROLES = (("Training Manager", 1), ("Training Learner", 0))


def before_install():
	for role, desk in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": desk}).insert(ignore_permissions=True)


def after_install():
	create_dpdp_course()


def create_dpdp_course(publish: bool = True) -> str:
	"""Seed the Tridasa DPDP playbook as a course with its 40-question bank."""
	path = os.path.join(frappe.get_app_path("tridasa_lms"), "setup_data", "dpdp_course.json")
	with open(path, encoding="utf-8") as f:
		data = json.load(f)

	code = data["course_code"]
	if frappe.db.exists("Training Course", code):
		return code

	intro = (
		f'<span class="eyebrow">{data["eyebrow"]}</span>'
		f'<p class="lede">{data["introduction"]}</p>{data["timeline"]}'
	)
	course = frappe.get_doc(
		{
			"doctype": "Training Course",
			"course_name": data["course_name"],
			"course_code": code,
			"version": data["version"],
			"tagline": "Protecting the people behind every booking",
			"introduction": intro,
			"status": "Draft",
			"chapters": [
				{"chapter_title": c["title"], "content": c["content"], "estimated_minutes": 2} for c in data["chapters"]
			],
		}
	).insert(ignore_permissions=True)

	for q in data["questions"]:
		frappe.get_doc(
			{
				"doctype": "Training Question",
				"course": course.name,
				"question_code": q["code"],
				"topic": q["topic"],
				"question": q["question"],
				"explanation": q["explanation"],
				"options": [{"option_text": o, "is_correct": int(i == q["correct"])} for i, o in enumerate(q["options"])],
			}
		).insert(ignore_permissions=True)

	if publish:
		course.reload()
		course.status = "Published"
		course.save(ignore_permissions=True)
	return course.name
