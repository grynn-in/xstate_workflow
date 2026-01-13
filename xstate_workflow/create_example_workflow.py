#!/usr/bin/env python
"""Create example Contact approval workflow."""
import frappe
import json

def create_contact_approval_workflow():
    """Create a two-level approval workflow for Contact: John → Administrator"""

    # Check if it already exists
    if frappe.db.exists("State Machine", "contact_approval_workflow"):
        print("Workflow 'contact_approval_workflow' already exists. Deleting and recreating...")
        frappe.delete_doc("State Machine", "contact_approval_workflow", force=True)

    # XState JSON configuration
    xstate_config = {
        "id": "contact_approval_workflow",
        "version": "1",
        "initial": "pending_john_approval",
        "context": {},
        "states": {
            "pending_john_approval": {
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "John Approval",
                        "resolver": {
                            "type": "static_user",
                            "user": "john@example.com"
                        },
                        "available_actions": ["Approve", "Reject"],
                        "priority": "Medium"
                    }
                },
                "on": {
                    "APPROVE": "pending_admin_approval",
                    "REJECT": "rejected"
                }
            },
            "pending_admin_approval": {
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "Administrator Approval",
                        "resolver": {
                            "type": "static_user",
                            "user": "Administrator"
                        },
                        "available_actions": ["Approve", "Reject"],
                        "priority": "High"
                    }
                },
                "on": {
                    "APPROVE": "approved",
                    "REJECT": "rejected"
                }
            },
            "approved": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "label": "Approved",
                        "final_status": "Approved"
                    }
                }
            },
            "rejected": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "label": "Rejected",
                        "final_status": "Rejected"
                    }
                }
            }
        }
    }

    # Workflow builder config (for visual editor)
    builder_config = {
        "id": "contact_approval_workflow",
        "name": "Contact Approval Workflow",
        "version": 1,
        "nodes": [
            {
                "id": "node_1",
                "type": "approval",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "John Approval",
                    "xstateType": "atomic",
                    "domainType": "approval",
                    "isInitial": True,
                    "resolver": {
                        "type": "static_user",
                        "user": "john@example.com"
                    },
                    "availableActions": ["Approve", "Reject"],
                    "priority": "Medium"
                }
            },
            {
                "id": "node_2",
                "type": "approval",
                "position": {"x": 100, "y": 250},
                "data": {
                    "label": "Administrator Approval",
                    "xstateType": "atomic",
                    "domainType": "approval",
                    "resolver": {
                        "type": "static_user",
                        "user": "Administrator"
                    },
                    "availableActions": ["Approve", "Reject"],
                    "priority": "High"
                }
            },
            {
                "id": "node_3",
                "type": "end",
                "position": {"x": 100, "y": 400},
                "data": {
                    "label": "Approved",
                    "xstateType": "final",
                    "domainType": "end",
                    "finalStatus": "Approved"
                }
            },
            {
                "id": "node_4",
                "type": "end",
                "position": {"x": 300, "y": 250},
                "data": {
                    "label": "Rejected",
                    "xstateType": "final",
                    "domainType": "end",
                    "finalStatus": "Rejected"
                }
            }
        ],
        "edges": [
            {
                "id": "edge_1",
                "source": "node_1",
                "target": "node_2",
                "type": "transition",
                "data": {"event": "APPROVE", "transitionType": "event"}
            },
            {
                "id": "edge_2",
                "source": "node_1",
                "target": "node_4",
                "type": "transition",
                "data": {"event": "REJECT", "transitionType": "event"}
            },
            {
                "id": "edge_3",
                "source": "node_2",
                "target": "node_3",
                "type": "transition",
                "data": {"event": "APPROVE", "transitionType": "event"}
            },
            {
                "id": "edge_4",
                "source": "node_2",
                "target": "node_4",
                "type": "transition",
                "data": {"event": "REJECT", "transitionType": "event"}
            }
        ]
    }

    # Create the State Machine document
    doc = frappe.get_doc({
        "doctype": "State Machine",
        "machine_id": "contact_approval_workflow",
        "title": "Contact Approval Workflow",
        "description": "Two-level approval workflow for new Contacts: John → Administrator",
        "is_active": 1,
        "version": 1,
        "attached_doctype": "Contact",
        "json_config": json.dumps(xstate_config, indent=2),
        "workflow_builder_config": json.dumps(builder_config, indent=2)
    })

    doc.insert()
    frappe.db.commit()

    print(f"Created workflow: {doc.name}")
    print(f"Attached to: {doc.attached_doctype}")
    print(f"View at: /app/state-machine/{doc.name}")
    print(f"Edit in builder: /xstate-builder/{doc.name}")

    return doc.name

if __name__ == "__main__":
    create_contact_approval_workflow()
