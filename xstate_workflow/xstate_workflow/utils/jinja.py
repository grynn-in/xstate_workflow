# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Jinja template methods for XState Workflow.
Use these in Frappe templates to display workflow state and buttons.
"""

import frappe


def get_workflow_state(doctype: str, docname: str) -> dict:
    """
    Get workflow state for use in Jinja templates.

    Usage in template:
        {% set wf = get_workflow_state(doc.doctype, doc.name) %}
        {% if wf.has_workflow %}
            <span class="badge">{{ wf.current_state }}</span>
        {% endif %}

    Args:
        doctype: DocType name
        docname: Document name

    Returns:
        dict with workflow state info
    """
    from xstate_workflow.workflow_engine import get_machine_state
    return get_machine_state(doctype, docname)


def get_workflow_buttons(doctype: str, docname: str) -> str:
    """
    Generate HTML buttons for available workflow events.

    Usage in template:
        {{ get_workflow_buttons(doc.doctype, doc.name) | safe }}

    Args:
        doctype: DocType name
        docname: Document name

    Returns:
        HTML string with workflow action buttons
    """
    from xstate_workflow.workflow_engine import get_machine_state

    state = get_machine_state(doctype, docname)

    if not state.get("has_workflow"):
        return ""

    buttons = []
    for event in state.get("available_events", []):
        if event.get("enabled", True):
            btn_class = "btn-primary" if event["event"] in ["APPROVE", "SUBMIT"] else "btn-secondary"
            buttons.append(f'''
                <button class="btn {btn_class} btn-sm workflow-action-btn"
                        data-doctype="{doctype}"
                        data-docname="{docname}"
                        data-event="{event['event']}">
                    {event['event'].replace('_', ' ').title()}
                </button>
            ''')

    return f'''
        <div class="workflow-actions" data-state="{state['current_state']}">
            <span class="workflow-state-badge badge">{state['current_state']}</span>
            {''.join(buttons)}
        </div>
    '''
