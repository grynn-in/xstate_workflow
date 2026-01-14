# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Web Page controller for Workflow Instance Viewer
"""

import json
import frappe
from frappe import _


def get_context(context):
    """
    Context for workflow-viewer page.
    Displays the current runtime state of a document's workflow.
    All data is loaded server-side to avoid CSRF/API issues.
    """
    # Initialize ALL context variables FIRST before any code that could fail
    context.no_cache = 1
    context.no_breadcrumbs = 1
    context.full_width = 1
    context.title = _("Workflow Viewer")
    context.workflow_state = {"has_workflow": False}
    context.machine_config = {}
    context.transition_history = []
    context.all_states = []
    context.error = None
    context.machine_id = ""
    context.doctype = ""
    context.docname = ""
    context.mermaid_definition = ""
    context.tooltip_data = {}

    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to access the Workflow Viewer"), frappe.PermissionError)

    # Parse URL params - machine_id comes from path, others from query string
    # URL format: /xstate-viewer/<machine_id>?doctype=X&docname=Y
    path_parts = frappe.request.path.split("/")
    context.machine_id = path_parts[-1] if len(path_parts) > 2 else ""
    context.doctype = frappe.form_dict.get("doctype") or ""
    context.docname = frappe.form_dict.get("docname") or ""

    try:
        # Load workflow state if we have doctype and docname
        if context.doctype and context.docname:
            from xstate_workflow.workflow_engine import get_machine_state_with_history
            context.workflow_state = get_machine_state_with_history(context.doctype, context.docname)

            # Extract transition history and all states from the response
            if context.workflow_state.get("has_workflow"):
                context.transition_history = context.workflow_state.get("transition_history", [])
                context.all_states = context.workflow_state.get("all_states", [])

        # Load machine config if we have machine_id
        if context.machine_id:
            from xstate_workflow.workflow_engine import get_machine
            try:
                context.machine_config = get_machine(context.machine_id)
                # Parse states from JSON config for diagram
                if context.machine_config.get("json_config"):
                    config = json.loads(context.machine_config["json_config"])
                    context.all_states = list(config.get("states", {}).keys())
            except Exception:
                pass  # Machine might not exist

        # Generate Mermaid diagram definition (server-side for performance)
        if context.workflow_state.get("has_workflow") and context.machine_config.get("json_config"):
            from xstate_workflow.mermaid_generator import (
                generate_mermaid_diagram,
                generate_tooltip_data,
            )
            try:
                config = json.loads(context.machine_config["json_config"])
                context.mermaid_definition = generate_mermaid_diagram(
                    config=config,
                    current_state=context.workflow_state.get("current_state"),
                    transition_log=context.transition_history,
                    all_states=context.all_states,
                )
                context.tooltip_data = generate_tooltip_data(context.transition_history)
            except Exception as e:
                frappe.log_error(f"Mermaid diagram generation error: {e}")

    except frappe.PermissionError as e:
        context.error = str(e)
    except Exception as e:
        context.error = _("Error loading workflow: {0}").format(str(e))
