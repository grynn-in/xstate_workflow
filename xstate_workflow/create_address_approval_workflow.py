#!/usr/bin/env python
"""Create Address approval workflow with role-based assignments."""
import frappe
import json


def create_address_approval_workflow():
    """Create a 3-level approval workflow for Address using roles."""

    if frappe.db.exists("State Machine", "address_approval_workflow"):
        print("Workflow 'address_approval_workflow' already exists. Deleting and recreating...")
        frappe.delete_doc("State Machine", "address_approval_workflow", force=True)

    xstate_config = {
        "id": "address_approval_workflow",
        "version": "1",
        "initial": "pending_sales_user_approval",
        "context": {},
        "states": {
            "pending_sales_user_approval": {
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "Sales User Approval",
                        "resolver": {
                            "type": "role",
                            "role": "Sales User",
                            "strategy": "all"
                        },
                        "available_actions": ["Approve", "Reject"],
                        "priority": "Medium"
                    }
                },
                "on": {
                    "APPROVE": "pending_sales_manager_approval",
                    "REJECT": "rejected"
                }
            },
            "pending_sales_manager_approval": {
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "Sales Manager Approval",
                        "resolver": {
                            "type": "role",
                            "role": "Sales Manager",
                            "strategy": "all"
                        },
                        "available_actions": ["Approve", "Reject", "Send Back"],
                        "priority": "High"
                    }
                },
                "on": {
                    "APPROVE": "pending_admin_approval",
                    "REJECT": "rejected",
                    "SEND_BACK": "pending_sales_user_approval"
                }
            },
            "pending_admin_approval": {
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "Administrator Final Approval",
                        "resolver": {
                            "type": "static_user",
                            "user": "Administrator"
                        },
                        "available_actions": ["Approve", "Reject"],
                        "priority": "Urgent"
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
        "id": "address_approval_workflow",
        "name": "Address Approval Workflow",
        "version": 1,
        "nodes": [
            {
                "id": "node_1",
                "type": "approval",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Sales User Approval",
                    "xstateType": "atomic",
                    "domainType": "approval",
                    "isInitial": True,
                    "resolver": {
                        "type": "role",
                        "role": "Sales User",
                        "strategy": "all"
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
                    "label": "Sales Manager Approval",
                    "xstateType": "atomic",
                    "domainType": "approval",
                    "resolver": {
                        "type": "role",
                        "role": "Sales Manager",
                        "strategy": "all"
                    },
                    "availableActions": ["Approve", "Reject", "Send Back"],
                    "priority": "High"
                }
            },
            {
                "id": "node_3",
                "type": "approval",
                "position": {"x": 100, "y": 400},
                "data": {
                    "label": "Administrator Final Approval",
                    "xstateType": "atomic",
                    "domainType": "approval",
                    "resolver": {
                        "type": "static_user",
                        "user": "Administrator"
                    },
                    "availableActions": ["Approve", "Reject"],
                    "priority": "Urgent"
                }
            },
            {
                "id": "node_4",
                "type": "end",
                "position": {"x": 100, "y": 550},
                "data": {
                    "label": "Approved",
                    "xstateType": "final",
                    "domainType": "end",
                    "finalStatus": "Approved"
                }
            },
            {
                "id": "node_5",
                "type": "end",
                "position": {"x": 350, "y": 250},
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
                "target": "node_5",
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
                "target": "node_5",
                "type": "transition",
                "data": {"event": "REJECT", "transitionType": "event"}
            },
            {
                "id": "edge_5",
                "source": "node_2",
                "target": "node_1",
                "type": "transition",
                "data": {"event": "SEND_BACK", "transitionType": "event"}
            },
            {
                "id": "edge_6",
                "source": "node_3",
                "target": "node_4",
                "type": "transition",
                "data": {"event": "APPROVE", "transitionType": "event"}
            },
            {
                "id": "edge_7",
                "source": "node_3",
                "target": "node_5",
                "type": "transition",
                "data": {"event": "REJECT", "transitionType": "event"}
            }
        ]
    }

    doc = frappe.get_doc({
        "doctype": "State Machine",
        "machine_id": "address_approval_workflow",
        "title": "Address Approval Workflow",
        "description": "3-level approval: Sales User -> Sales Manager -> Administrator",
        "is_active": 1,
        "version": 1,
        "attached_doctype": "Address",
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
    create_address_approval_workflow()
