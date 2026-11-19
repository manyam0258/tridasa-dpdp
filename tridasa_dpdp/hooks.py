app_name = "tridasa_dpdp"
app_title = "Tridasa DPDP"
app_publisher = "Tridasa Realty Ventures Pvt. Ltd."
app_description = "DPDP Act awareness playbook, assessment and certification for employees"
app_email = "kjvaditya@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "tridasa_dpdp",
# 		"logo": "/assets/tridasa_dpdp/logo.png",
# 		"title": "Tridasa DPDP",
# 		"route": "/tridasa_dpdp",
# 		"has_permission": "tridasa_dpdp.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/tridasa_dpdp/css/tridasa_dpdp.css"
# app_include_js = "/assets/tridasa_dpdp/js/tridasa_dpdp.js"

# include js, css files in header of web template
# web_include_css = "/assets/tridasa_dpdp/css/tridasa_dpdp.css"
# web_include_js = "/assets/tridasa_dpdp/js/tridasa_dpdp.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "tridasa_dpdp/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "tridasa_dpdp/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "tridasa_dpdp.utils.jinja_methods",
# 	"filters": "tridasa_dpdp.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "tridasa_dpdp.install.before_install"
# after_install = "tridasa_dpdp.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "tridasa_dpdp.uninstall.before_uninstall"
# after_uninstall = "tridasa_dpdp.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "tridasa_dpdp.utils.before_app_install"
# after_app_install = "tridasa_dpdp.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "tridasa_dpdp.utils.before_app_uninstall"
# after_app_uninstall = "tridasa_dpdp.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "tridasa_dpdp.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"tridasa_dpdp.tasks.all"
# 	],
# 	"daily": [
# 		"tridasa_dpdp.tasks.daily"
# 	],
# 	"hourly": [
# 		"tridasa_dpdp.tasks.hourly"
# 	],
# 	"weekly": [
# 		"tridasa_dpdp.tasks.weekly"
# 	],
# 	"monthly": [
# 		"tridasa_dpdp.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "tridasa_dpdp.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "tridasa_dpdp.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "tridasa_dpdp.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["tridasa_dpdp.utils.before_request"]
# after_request = ["tridasa_dpdp.utils.after_request"]

# Job Events
# ----------
# before_job = ["tridasa_dpdp.utils.before_job"]
# after_job = ["tridasa_dpdp.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"tridasa_dpdp.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# ---------------------------------------------------------------- Tridasa DPDP

required_apps = ["frappe", "erpnext", "hrms"]

before_install = "tridasa_dpdp.install.before_install"
after_install = "tridasa_dpdp.install.after_install"

app_include_js = "/assets/tridasa_dpdp/js/desk_training_banner.js"

# Employees who only have a portal login land on their trainings
role_home_page = {"Training Learner": "training"}

standard_portal_menu_items = [
	{"title": "My Trainings", "route": "/training", "role": "Training Learner"},
]

has_website_permission = {
	"Training Certificate": "tridasa_dpdp.permissions.certificate_website_permission",
}

doc_events = {
	"Employee": {
		"after_insert": "tridasa_dpdp.overrides.employee.enroll_new_joiner",
		"on_update": "tridasa_dpdp.overrides.employee.on_status_change",
	},
}

scheduler_events = {
	"daily": ["tridasa_dpdp.tasks.daily"],
	"hourly": ["tridasa_dpdp.tasks.hourly"],
}

jinja = {
	"methods": ["tridasa_dpdp.utils.logo_data_uri"],
}
