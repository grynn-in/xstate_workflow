# xstate_workflow/xstate_workflow/hooks.py
"""
Frappe Hooks Configuration for XState Workflow App

This configures:
- JS/CSS includes for React Flow editor
- Scheduler events for delayed transitions and cleanup
- Document events for auto-triggering workflows
"""

app_name = "xstate_workflow"
app_title = "XState Workflow"
app_publisher = "Grynn GmbH"
app_description = "XState-powered workflow engine with React Flow visual builder"
app_email = "deepak.pai@grynn.ch"
app_license = "MIT"
app_icon = "octicon octicon-git-branch"
app_color = "#6366f1"

# ============================================================================
# INCLUDES
# ============================================================================

# Include JS/CSS in desk (for form integration)
app_include_css = [
    "/assets/xstate_workflow/css/workflow.css",  # Base workflow styles
    "/assets/xstate_workflow/js/workflow_builder.desk.css"  # React component styles
]
app_include_js = [
    "/assets/xstate_workflow/js/workflow_builder.desk.iife.js",  # React components for desk
    "/assets/xstate_workflow/js/workflow_client.js"  # Vanilla JS form integration
]

# Include in website/web pages (for workflow builder standalone page)
web_include_css = [
    "/assets/xstate_workflow/css/workflow.css",
    "/assets/xstate_workflow/js/workflow_builder.css"  # Built from standalone app
]
web_include_js = [
    "/assets/xstate_workflow/js/workflow_builder.standalone.iife.js"  # Standalone React app
]

# ============================================================================
# WEBSITE
# ============================================================================

# Website context
website_context = {
    "favicon": "/assets/xstate_workflow/images/favicon.ico",
    "splash_image": "/assets/xstate_workflow/images/splash.png"
}

# Website route rules
website_route_rules = [
    {"from_route": "/xstate-builder", "to_route": "xstate-builder"},
    {"from_route": "/xstate-builder/<machine_id>", "to_route": "xstate-builder"},
    {"from_route": "/my-approvals", "to_route": "my-approvals"},
]

# ============================================================================
# DOCTYPES
# ============================================================================

# Fixtures for export
fixtures = [
    {
        "doctype": "Role",
        "filters": [["name", "in", ["Workflow Manager"]]]
    }
]

# DocType overrides
# override_doctype_class = {
#     "Contact": "xstate_workflow.overrides.contact.CustomContact"
# }

# ============================================================================
# DOCUMENT EVENTS
# ============================================================================

# Auto-trigger workflow events on document changes
doc_events = {
    "*": {
        "on_update": "xstate_workflow.workflow_engine.check_and_trigger",
        "after_insert": "xstate_workflow.workflow_engine.check_and_trigger"
    }
}

# ============================================================================
# SCHEDULER EVENTS
# ============================================================================

scheduler_events = {
    # Process delayed transitions every minute
    "cron": {
        "* * * * *": [
            "xstate_workflow.workflow_engine.process_delayed_transitions"
        ],
        # Check for overdue approval tasks every 15 minutes
        "*/15 * * * *": [
            "xstate_workflow.approval.task_manager.check_overdue_tasks"
        ]
    },
    # Daily cleanup of old instances
    "daily": [
        "xstate_workflow.workflow_engine.cleanup_old_snapshots"
    ]
}

# ============================================================================
# JINJA
# ============================================================================

# Custom Jinja methods for templates
jinja = {
    "methods": [
        "xstate_workflow.utils.jinja.get_workflow_state",
        "xstate_workflow.utils.jinja.get_workflow_buttons"
    ]
}

# ============================================================================
# PERMISSIONS
# ============================================================================

# Permission query conditions
permission_query_conditions = {
    "Machine Instance": "xstate_workflow.permissions.get_permission_query_conditions"
}

has_permission = {
    "Machine Instance": "xstate_workflow.permissions.has_permission"
}

# ============================================================================
# INSTALLATION
# ============================================================================

before_install = "xstate_workflow.install.before_install"
after_install = "xstate_workflow.install.after_install"

# ============================================================================
# BOOT SESSION
# ============================================================================

# Add workflow state info to boot
boot_session = "xstate_workflow.boot.boot_session"

# ============================================================================
# OVERRIDE WHITELISTED METHODS
# ============================================================================

# Override for custom workflow integration
# override_whitelisted_methods = {
#     "frappe.client.save": "xstate_workflow.overrides.save_with_workflow"
# }

# ============================================================================
# API ENDPOINTS
# ============================================================================

# Define API namespace
# api = {
#     "v1": {
#         "workflow": "xstate_workflow.api.v1.workflow"
#     }
# }
