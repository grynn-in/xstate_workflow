# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Installation hooks for XState Workflow app.
"""

import frappe


def before_install():
    """Pre-installation checks."""
    pass


def after_install():
    """Post-installation setup."""
    create_workflow_manager_role()
    register_workflow_queue()


def after_migrate():
    """Ensure workflow queue is registered after every migrate."""
    register_workflow_queue()


def create_workflow_manager_role():
    """Create Workflow Manager role if not exists."""
    if not frappe.db.exists("Role", "Workflow Manager"):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": "Workflow Manager",
            "desk_access": 1,
            "is_custom": 1
        }).insert(ignore_permissions=True)
        frappe.db.commit()


def register_workflow_queue():
    """Register the 'workflow' queue for state transition background jobs."""
    from frappe.installer import update_site_config

    site_config = frappe.get_conf()
    workers = site_config.get("workers") or {}

    if "workflow" not in workers:
        workers["workflow"] = {"timeout": 300}
        update_site_config("workers", workers)
