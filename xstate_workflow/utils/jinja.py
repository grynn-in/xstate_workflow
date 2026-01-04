# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Jinja template helpers for XState Workflow.
These functions are available in Jinja templates via jinja_methods in hooks.py.
"""

import frappe


def get_workflow_state(doctype: str, docname: str) -> str | None:
    """
    Get the current workflow state for a document.

    Usage in Jinja:
        {{ get_workflow_state("Sales Order", "SO-00001") }}

    Args:
        doctype: The DocType name
        docname: The document name

    Returns:
        Current state string or None if no workflow instance exists
    """
    instance = frappe.db.get_value(
        "Machine Instance",
        {"ref_doctype": doctype, "ref_docname": docname},
        "current_state"
    )
    return instance


def get_workflow_buttons(doctype: str, docname: str) -> list[dict]:
    """
    Get available workflow action buttons for a document.

    Usage in Jinja:
        {% for btn in get_workflow_buttons("Sales Order", "SO-00001") %}
            <button data-event="{{ btn.event }}">{{ btn.label }}</button>
        {% endfor %}

    Args:
        doctype: The DocType name
        docname: The document name

    Returns:
        List of button dicts with keys: event, label, description
    """
    # Get the machine instance
    instance = frappe.db.get_value(
        "Machine Instance",
        {"ref_doctype": doctype, "ref_docname": docname},
        ["name", "state_machine", "current_state"],
        as_dict=True
    )

    if not instance:
        return []

    # Get the machine config
    machine = frappe.get_doc("State Machine", instance.state_machine)
    config = machine.get_config()

    if not config:
        return []

    # Find available transitions from current state
    buttons = []
    current_state = instance.current_state
    states = config.get("states", {})

    if current_state in states:
        state_config = states[current_state]
        transitions = state_config.get("on", {})

        for event, transition in transitions.items():
            # Handle both simple and complex transition formats
            if isinstance(transition, str):
                target = transition
                description = ""
            elif isinstance(transition, dict):
                target = transition.get("target", "")
                description = transition.get("description", "")
            elif isinstance(transition, list) and transition:
                target = transition[0].get("target", "") if isinstance(transition[0], dict) else transition[0]
                description = transition[0].get("description", "") if isinstance(transition[0], dict) else ""
            else:
                continue

            buttons.append({
                "event": event,
                "label": event.replace("_", " ").replace(".", " ").title(),
                "target": target,
                "description": description
            })

    return buttons


def get_workflow_history(doctype: str, docname: str, limit: int = 10) -> list[dict]:
    """
    Get workflow transition history for a document.

    Usage in Jinja:
        {% for entry in get_workflow_history("Sales Order", "SO-00001") %}
            {{ entry.timestamp }}: {{ entry.from_state }} -> {{ entry.to_state }}
        {% endfor %}

    Args:
        doctype: The DocType name
        docname: The document name
        limit: Maximum number of history entries to return

    Returns:
        List of history dicts with keys: timestamp, from_state, to_state, event, user
    """
    import json

    instance = frappe.db.get_value(
        "Machine Instance",
        {"ref_doctype": doctype, "ref_docname": docname},
        "history"
    )

    if not instance:
        return []

    try:
        history = json.loads(instance) if instance else []
        # Return most recent entries first, limited
        return list(reversed(history[-limit:]))
    except (json.JSONDecodeError, TypeError):
        return []


def has_workflow(doctype: str) -> bool:
    """
    Check if a DocType has an active workflow attached.

    Usage in Jinja:
        {% if has_workflow("Sales Order") %}
            <!-- Show workflow UI -->
        {% endif %}

    Args:
        doctype: The DocType name

    Returns:
        True if an active workflow exists for this DocType
    """
    return bool(frappe.db.exists(
        "State Machine",
        {"attached_doctype": doctype, "is_active": 1}
    ))
