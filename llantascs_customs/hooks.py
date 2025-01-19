app_name = "llantascs_customs"
app_title = "Llantascs Customs"
app_publisher = "Consultoria en Negocios y Aplicaciones"
app_description = "Customizaciones ERPNEXT Llantas CS"
app_email = "it@buzola.mx"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "llantascs_customs",
# 		"logo": "/assets/llantascs_customs/logo.png",
# 		"title": "Llantascs Customs",
# 		"route": "/llantascs_customs",
# 		"has_permission": "llantascs_customs.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/llantascs_customs/css/llantascs_customs.css"
# app_include_js = "/assets/llantascs_customs/js/llantascs_customs.js"

# include js, css files in header of web template
# web_include_css = "/assets/llantascs_customs/css/llantascs_customs.css"
# web_include_js = "/assets/llantascs_customs/js/llantascs_customs.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "llantascs_customs/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Sales Invoice" : "llantascs_customs/core_doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "llantascs_customs/public/icons.svg"

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
# 	"methods": "llantascs_customs.utils.jinja_methods",
# 	"filters": "llantascs_customs.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "llantascs_customs.install.before_install"
# after_install = "llantascs_customs.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "llantascs_customs.uninstall.before_uninstall"
# after_uninstall = "llantascs_customs.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "llantascs_customs.utils.before_app_install"
# after_app_install = "llantascs_customs.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "llantascs_customs.utils.before_app_uninstall"
# after_app_uninstall = "llantascs_customs.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "llantascs_customs.notifications.get_notification_config"

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
# 		"llantascs_customs.tasks.all"
# 	],
# 	"daily": [
# 		"llantascs_customs.tasks.daily"
# 	],
# 	"hourly": [
# 		"llantascs_customs.tasks.hourly"
# 	],
# 	"weekly": [
# 		"llantascs_customs.tasks.weekly"
# 	],
# 	"monthly": [
# 		"llantascs_customs.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "llantascs_customs.install.before_tests"

# Overriding Methods
# ------------------------------

override_whitelisted_methods = {
	"erpnext.controllers.item_variant.create_variant": "llantascs_customs.controllers.override.custom_create_variant"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "llantascs_customs.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["llantascs_customs.utils.before_request"]
# after_request = ["llantascs_customs.utils.after_request"]

# Job Events
# ----------
# before_job = ["llantascs_customs.utils.before_job"]
# after_job = ["llantascs_customs.utils.after_job"]

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
# 	"llantascs_customs.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# fixtures = ["Role"]

fixtures = ["Custom Field"]

