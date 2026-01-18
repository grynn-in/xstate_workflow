"""
Comprehensive Purchase Order Workflow

This workflow demonstrates all advanced XState features:
- Auto-triggers (on_submit)
- Conditional routing (amount-based)
- Approval nodes (with resolver and SLA)
- Parallel states (Finance + Legal for high-value POs)
- Auto-actions (email, API call)
- Scheduled transitions (7-day escalation)
- History states (pause/resume)
- Entry/Exit actions (notifications, logging)
- Context flow (approval history, API responses)

Usage:
    bench --site xs.local execute xstate_workflow.fixtures.purchase_order_workflow.create_workflow
"""

import json
import frappe


def get_workflow_config():
    """Build the complete XState JSON configuration."""
    return {
        "id": "purchase_order_approval",
        "initial": "draft",
        "context": {
            "escalation_count": 0,
            "approval_history": [],
        },
        "states": {
            # ============================================================
            # DRAFT - Initial state
            # ============================================================
            "draft": {
                "meta": {
                    "label": "Draft",
                    "description": "Purchase Order is being prepared",
                },
                "on": {
                    # Auto-trigger on document submit
                    "SUBMIT_FOR_REVIEW": {
                        "target": "review",
                        "actions": ["log_submission"],
                    },
                },
            },
            # ============================================================
            # REVIEW - Procurement team verifies details
            # ============================================================
            "review": {
                "meta": {
                    "label": "Under Review",
                    "description": "Procurement team is reviewing the PO",
                },
                "entry": ["notify_procurement_team", "log_state_entry"],
                "exit": ["log_state_exit"],
                "on": {
                    # Conditional routing based on amount
                    "APPROVE": [
                        {
                            "target": "auto_approved",
                            "guard": "amount_under_10k",
                            "actions": ["log_auto_approval"],
                        },
                        {
                            "target": "manager_approval",
                            "guard": "amount_10k_to_100k",
                            "actions": ["notify_manager"],
                        },
                        {
                            "target": "parallel_approval",
                            "guard": "amount_over_100k",
                            "actions": ["notify_finance_and_legal"],
                        },
                    ],
                    "RETURN_TO_DRAFT": {
                        "target": "draft",
                        "actions": ["notify_requester_return"],
                    },
                    "REJECT": {
                        "target": "rejected",
                        "actions": ["notify_rejection"],
                    },
                    "PAUSE": {
                        "target": "paused",
                        "actions": ["log_pause"],
                    },
                },
            },
            # ============================================================
            # PAUSED - Workflow paused, with history state for resume
            # ============================================================
            "paused": {
                "meta": {
                    "label": "Paused",
                    "description": "Workflow is paused - can be resumed",
                },
                "on": {
                    "RESUME": {
                        "target": "review_history",
                        "actions": ["log_resume"],
                    },
                    "CANCEL": {
                        "target": "cancelled",
                        "actions": ["log_cancellation"],
                    },
                },
            },
            # ============================================================
            # REVIEW_HISTORY - History state to resume where left off
            # ============================================================
            "review_history": {
                "type": "history",
                "history": "shallow",
                "target": "review",  # Default if no history
            },
            # ============================================================
            # AUTO_APPROVED - Small orders auto-approved (< 10K)
            # ============================================================
            "auto_approved": {
                "meta": {
                    "label": "Auto Approved",
                    "description": "Automatically approved (under threshold)",
                    "domain_node": {
                        "type": "auto_action",
                        "action_type": "update_field",
                        "action_config": {
                            "field": "custom_approval_type",
                            "value": "Auto",
                        },
                    },
                },
                "entry": ["set_auto_approved", "log_state_entry"],
                # Always transition immediately to next state
                "always": [{"target": "approved"}],
            },
            # ============================================================
            # MANAGER_APPROVAL - Manager approval node (10K - 100K)
            # ============================================================
            "manager_approval": {
                "meta": {
                    "label": "Manager Approval",
                    "description": "Awaiting manager approval",
                    "domain_node": {
                        "type": "approval",
                        "resolver": {
                            "type": "role_resolver",
                            "role": "System Manager",
                        },
                        "available_actions": ["Approve", "Reject", "Request Info"],
                        "sla_hours": 24,
                        "priority": "Medium",
                        "fallback_user": "Administrator",
                        "escalation": {
                            "enabled": True,
                            "after_hours": 48,
                            "to_role": "System Manager",
                        },
                    },
                },
                "entry": ["create_manager_task", "start_sla_timer", "log_state_entry"],
                "exit": ["complete_approval_task", "stop_sla_timer", "log_state_exit"],
                "on": {
                    "APPROVE": {
                        "target": "approved",
                        "actions": ["record_approval", "notify_requester_approved"],
                    },
                    "REJECT": {
                        "target": "rejected",
                        "actions": ["record_rejection", "notify_rejection"],
                    },
                    "REQUEST_INFO": {
                        "target": "info_requested",
                        "actions": ["notify_info_request"],
                    },
                    "ESCALATE": {
                        "target": "escalated_approval",
                        "guard": "can_escalate",
                        "actions": ["increment_escalation", "notify_escalation"],
                    },
                },
                # Scheduled auto-escalation after 48 hours
                "after": {
                    "172800000": {
                        "target": "escalated_approval",
                        "guard": "can_escalate",
                        "actions": ["auto_escalate"],
                    },
                },
            },
            # ============================================================
            # INFO_REQUESTED - Waiting for additional information
            # ============================================================
            "info_requested": {
                "meta": {
                    "label": "Info Requested",
                    "description": "Additional information requested from requester",
                },
                "entry": ["log_state_entry"],
                "on": {
                    "PROVIDE_INFO": {
                        "target": "manager_approval",
                        "actions": ["log_info_provided"],
                    },
                    "CANCEL": {
                        "target": "cancelled",
                        "actions": ["log_cancellation"],
                    },
                },
            },
            # ============================================================
            # ESCALATED_APPROVAL - Escalated to higher authority
            # ============================================================
            "escalated_approval": {
                "meta": {
                    "label": "Escalated Approval",
                    "description": "Escalated to Senior Manager",
                    "domain_node": {
                        "type": "approval",
                        "resolver": {
                            "type": "role_resolver",
                            "role": "System Manager",
                        },
                        "available_actions": ["Approve", "Reject"],
                        "sla_hours": 12,
                        "priority": "High",
                    },
                },
                "entry": ["create_escalated_task", "log_state_entry"],
                "exit": ["complete_approval_task", "log_state_exit"],
                "on": {
                    "APPROVE": {
                        "target": "approved",
                        "actions": ["record_approval", "notify_requester_approved"],
                    },
                    "REJECT": {
                        "target": "rejected",
                        "actions": ["record_rejection", "notify_rejection"],
                    },
                },
            },
            # ============================================================
            # PARALLEL_APPROVAL - Finance AND Legal must both approve (> 100K)
            # ============================================================
            "parallel_approval": {
                "type": "parallel",
                "meta": {
                    "label": "Parallel Approval",
                    "description": "Requires both Finance and Legal approval",
                },
                "states": {
                    # Finance approval region
                    "finance_region": {
                        "initial": "finance_pending",
                        "states": {
                            "finance_pending": {
                                "meta": {
                                    "label": "Finance Review",
                                    "domain_node": {
                                        "type": "approval",
                                        "resolver": {
                                            "type": "role_resolver",
                                            "role": "System Manager",
                                        },
                                        "available_actions": ["Approve", "Reject"],
                                        "sla_hours": 24,
                                    },
                                },
                                "entry": ["create_finance_task"],
                                "on": {
                                    "APPROVE_FINANCE": "finance_approved",
                                    "REJECT_FINANCE": "finance_rejected",
                                },
                            },
                            "finance_approved": {
                                "type": "final",
                                "entry": ["record_finance_approval"],
                            },
                            "finance_rejected": {
                                "type": "final",
                                "entry": ["record_finance_rejection"],
                            },
                        },
                    },
                    # Legal approval region
                    "legal_region": {
                        "initial": "legal_pending",
                        "states": {
                            "legal_pending": {
                                "meta": {
                                    "label": "Legal Review",
                                    "domain_node": {
                                        "type": "approval",
                                        "resolver": {
                                            "type": "role_resolver",
                                            "role": "System Manager",
                                        },
                                        "available_actions": ["Approve", "Reject"],
                                        "sla_hours": 48,
                                    },
                                },
                                "entry": ["create_legal_task"],
                                "on": {
                                    "APPROVE_LEGAL": "legal_approved",
                                    "REJECT_LEGAL": "legal_rejected",
                                },
                            },
                            "legal_approved": {
                                "type": "final",
                                "entry": ["record_legal_approval"],
                            },
                            "legal_rejected": {
                                "type": "final",
                                "entry": ["record_legal_rejection"],
                            },
                        },
                    },
                },
                # When both regions complete, check if all approved
                "onDone": [
                    {
                        "target": "approved",
                        "guard": "all_parallel_approved",
                        "actions": ["notify_requester_approved"],
                    },
                    {
                        "target": "rejected",
                        "actions": ["notify_parallel_rejection"],
                    },
                ],
            },
            # ============================================================
            # APPROVED - PO approved, ready to send to supplier
            # ============================================================
            "approved": {
                "meta": {
                    "label": "Approved",
                    "description": "Purchase Order has been approved",
                },
                "entry": [
                    "set_approved_status",
                    "record_approval_timestamp",
                    "log_state_entry",
                ],
                "on": {
                    "SEND_TO_SUPPLIER": {
                        "target": "sent_to_supplier",
                        "actions": ["email_supplier", "call_supplier_api"],
                    },
                    "CANCEL": {
                        "target": "cancelled",
                        "guard": "can_cancel_approved",
                        "actions": ["log_cancellation"],
                    },
                },
            },
            # ============================================================
            # SENT_TO_SUPPLIER - PO sent, waiting for confirmation
            # ============================================================
            "sent_to_supplier": {
                "meta": {
                    "label": "Sent to Supplier",
                    "description": "PO sent to supplier, awaiting confirmation",
                },
                "entry": [
                    "set_sent_date",
                    "start_supplier_timer",
                    "log_state_entry",
                ],
                "on": {
                    "CONFIRM_RECEIPT": {
                        "target": "order_confirmed",
                        "actions": ["record_confirmation", "cancel_escalation_timer"],
                    },
                    "SUPPLIER_REJECTED": {
                        "target": "supplier_issue",
                        "actions": ["notify_supplier_issue"],
                    },
                },
                # Auto-escalate if no response in 7 days (604800000 ms)
                "after": {
                    "604800000": {
                        "target": "supplier_escalated",
                        "actions": ["notify_procurement_head", "flag_urgent"],
                    },
                },
            },
            # ============================================================
            # SUPPLIER_ESCALATED - Supplier didn't respond
            # ============================================================
            "supplier_escalated": {
                "meta": {
                    "label": "Supplier Escalated",
                    "description": "No supplier response - escalated to procurement head",
                },
                "entry": ["log_state_entry"],
                "on": {
                    "CONFIRM_RECEIPT": {
                        "target": "order_confirmed",
                        "actions": ["record_late_confirmation"],
                    },
                    "CANCEL": {
                        "target": "cancelled",
                        "actions": ["notify_supplier_cancelled"],
                    },
                    "RESEND": {
                        "target": "sent_to_supplier",
                        "actions": ["email_supplier", "log_resend"],
                    },
                },
            },
            # ============================================================
            # SUPPLIER_ISSUE - Supplier has an issue with the PO
            # ============================================================
            "supplier_issue": {
                "meta": {
                    "label": "Supplier Issue",
                    "description": "Supplier reported an issue with the PO",
                },
                "entry": ["notify_requester_issue", "log_state_entry"],
                "on": {
                    "RESOLVE_ISSUE": {
                        "target": "sent_to_supplier",
                        "actions": ["log_issue_resolved", "email_supplier"],
                    },
                    "CANCEL": {
                        "target": "cancelled",
                        "actions": ["log_cancellation"],
                    },
                },
            },
            # ============================================================
            # ORDER_CONFIRMED - Final successful state
            # ============================================================
            "order_confirmed": {
                "type": "final",
                "meta": {
                    "label": "Order Confirmed",
                    "description": "Supplier confirmed the order",
                    "domain_node": {
                        "type": "end",
                        "final_status": "Completed",
                    },
                },
                "entry": [
                    "set_confirmed_status",
                    "record_completion_time",
                    "notify_stakeholders_complete",
                    "log_state_entry",
                ],
            },
            # ============================================================
            # REJECTED - Final rejected state
            # ============================================================
            "rejected": {
                "type": "final",
                "meta": {
                    "label": "Rejected",
                    "description": "Purchase Order was rejected",
                    "domain_node": {
                        "type": "end",
                        "final_status": "Rejected",
                    },
                },
                "entry": ["set_rejected_status", "log_state_entry"],
            },
            # ============================================================
            # CANCELLED - Final cancelled state
            # ============================================================
            "cancelled": {
                "type": "final",
                "meta": {
                    "label": "Cancelled",
                    "description": "Purchase Order was cancelled",
                    "domain_node": {
                        "type": "end",
                        "final_status": "Cancelled",
                    },
                },
                "entry": ["set_cancelled_status", "cancel_all_tasks", "log_state_entry"],
            },
        },
    }


def get_guards():
    """Define all guard conditions."""
    return [
        # Amount-based routing
        {
            "guard_name": "amount_under_10k",
            "description": "Check if PO amount is under 10,000",
            "python_code": "doc.grand_total < 10000",
        },
        {
            "guard_name": "amount_10k_to_100k",
            "description": "Check if PO amount is between 10,000 and 100,000",
            "python_code": "doc.grand_total >= 10000 and doc.grand_total <= 100000",
        },
        {
            "guard_name": "amount_over_100k",
            "description": "Check if PO amount is over 100,000",
            "python_code": "doc.grand_total > 100000",
        },
        # Escalation controls
        {
            "guard_name": "can_escalate",
            "description": "Check if escalation is allowed (max 3 times)",
            "python_code": "context.get('escalation_count', 0) < 3",
        },
        # Parallel approval check
        {
            "guard_name": "all_parallel_approved",
            "description": "Check if both Finance and Legal approved",
            "python_code": """
context.get('finance_approved') == True and context.get('legal_approved') == True
""".strip(),
        },
        # Cancel permissions
        {
            "guard_name": "can_cancel_approved",
            "description": "Check if approved PO can be cancelled (no goods received)",
            "python_code": "doc.per_received == 0 and doc.per_billed == 0",
        },
        # Owner check
        {
            "guard_name": "is_owner",
            "description": "Check if current user is document owner",
            "python_code": "doc.owner == frappe.session.user",
        },
        # Urgent check
        {
            "guard_name": "is_urgent",
            "description": "Check if PO is marked urgent or overdue",
            "python_code": """
doc.get('is_urgent') or (frappe.utils.date_diff(frappe.utils.nowdate(), doc.schedule_date or doc.transaction_date) > 3)
""".strip(),
        },
    ]


def get_actions():
    """Define all workflow actions."""
    return [
        # ============================================================
        # Logging Actions
        # ============================================================
        {
            "action_name": "log_state_entry",
            "action_type": "entry",
            "description": "Log entry into a state",
            "python_code": """
import json
from frappe.utils import now_datetime

state = context.get('_current_state', 'unknown')
frappe.logger().info(f"PO Workflow: Entering state '{state}' for {doc.name}")

# Add to transition log
if 'transition_log' not in context:
    context['transition_log'] = []
context['transition_log'].append({
    'state': state,
    'action': 'entry',
    'user': frappe.session.user,
    'timestamp': str(now_datetime())
})
""",
        },
        {
            "action_name": "log_state_exit",
            "action_type": "exit",
            "description": "Log exit from a state",
            "python_code": """
state = context.get('_current_state', 'unknown')
frappe.logger().info(f"PO Workflow: Exiting state '{state}' for {doc.name}")
""",
        },
        {
            "action_name": "log_submission",
            "action_type": "transition",
            "description": "Log PO submission",
            "python_code": """
context['submitted_at'] = str(frappe.utils.now_datetime())
context['submitted_by'] = frappe.session.user
frappe.logger().info(f"PO {doc.name} submitted for review by {frappe.session.user}")
""",
        },
        {
            "action_name": "log_pause",
            "action_type": "transition",
            "description": "Log workflow pause",
            "python_code": """
context['paused_at'] = str(frappe.utils.now_datetime())
context['paused_by'] = frappe.session.user
context['paused_from_state'] = context.get('_current_state')
""",
        },
        {
            "action_name": "log_resume",
            "action_type": "transition",
            "description": "Log workflow resume",
            "python_code": """
context['resumed_at'] = str(frappe.utils.now_datetime())
context['resumed_by'] = frappe.session.user
""",
        },
        {
            "action_name": "log_cancellation",
            "action_type": "transition",
            "description": "Log workflow cancellation",
            "python_code": """
context['cancelled_at'] = str(frappe.utils.now_datetime())
context['cancelled_by'] = frappe.session.user
context['cancelled_from_state'] = context.get('_current_state')
frappe.logger().info(f"PO {doc.name} workflow cancelled by {frappe.session.user}")
""",
        },
        {
            "action_name": "log_auto_approval",
            "action_type": "transition",
            "description": "Log automatic approval",
            "python_code": """
context['auto_approved'] = True
context['auto_approved_at'] = str(frappe.utils.now_datetime())
context['auto_approved_reason'] = f'Amount {doc.grand_total} is under auto-approval threshold'
frappe.logger().info(f"PO {doc.name} auto-approved (amount: {doc.grand_total})")
""",
        },
        # ============================================================
        # Notification Actions
        # ============================================================
        {
            "action_name": "notify_procurement_team",
            "action_type": "entry",
            "description": "Notify procurement team of new PO for review",
            "python_code": """
# Get users with Purchase User role
recipients = frappe.get_all(
    'Has Role',
    filters={'role': 'Purchase User', 'parenttype': 'User'},
    pluck='parent'
)
if recipients:
    frappe.sendmail(
        recipients=recipients[:5],  # Limit to 5 recipients
        subject=f'New PO {doc.name} for Review',
        message=f'''
        <p>A new Purchase Order requires your review:</p>
        <ul>
            <li><b>PO Number:</b> {doc.name}</li>
            <li><b>Supplier:</b> {doc.supplier_name}</li>
            <li><b>Amount:</b> {frappe.format_value(doc.grand_total, {'fieldtype': 'Currency'})}</li>
            <li><b>Requested By:</b> {doc.owner}</li>
        </ul>
        <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">View Purchase Order</a></p>
        ''',
        reference_doctype='Purchase Order',
        reference_name=doc.name
    )
    context['procurement_notified'] = True
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_manager",
            "action_type": "transition",
            "description": "Notify manager for approval",
            "python_code": """
recipients = frappe.get_all(
    'Has Role',
    filters={'role': 'Purchase Manager', 'parenttype': 'User'},
    pluck='parent'
)
if recipients:
    frappe.sendmail(
        recipients=recipients[:3],
        subject=f'PO {doc.name} Requires Your Approval',
        message=f'''
        <p>A Purchase Order requires your approval:</p>
        <ul>
            <li><b>PO Number:</b> {doc.name}</li>
            <li><b>Supplier:</b> {doc.supplier_name}</li>
            <li><b>Amount:</b> {frappe.format_value(doc.grand_total, {'fieldtype': 'Currency'})}</li>
        </ul>
        <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">Review and Approve</a></p>
        ''',
        reference_doctype='Purchase Order',
        reference_name=doc.name
    )
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_finance_and_legal",
            "action_type": "transition",
            "description": "Notify both Finance and Legal for parallel approval",
            "python_code": """
# Notify Finance
finance_users = frappe.get_all(
    'Has Role',
    filters={'role': 'Accounts Manager', 'parenttype': 'User'},
    pluck='parent'
)
# Notify Legal
legal_users = frappe.get_all(
    'Has Role',
    filters={'role': 'Legal Manager', 'parenttype': 'User'},
    pluck='parent'
)

all_recipients = list(set(finance_users + legal_users))[:6]
if all_recipients:
    frappe.sendmail(
        recipients=all_recipients,
        subject=f'High Value PO {doc.name} Requires Approval',
        message=f'''
        <p>A high-value Purchase Order requires parallel approval from Finance AND Legal:</p>
        <ul>
            <li><b>PO Number:</b> {doc.name}</li>
            <li><b>Supplier:</b> {doc.supplier_name}</li>
            <li><b>Amount:</b> {frappe.format_value(doc.grand_total, {'fieldtype': 'Currency'})}</li>
        </ul>
        <p>Both Finance and Legal must approve before the PO can proceed.</p>
        <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">Review and Approve</a></p>
        ''',
        reference_doctype='Purchase Order',
        reference_name=doc.name
    )
context['parallel_approval_started'] = str(frappe.utils.now_datetime())
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_requester_return",
            "action_type": "transition",
            "description": "Notify requester that PO was returned",
            "python_code": """
frappe.sendmail(
    recipients=[doc.owner],
    subject=f'PO {doc.name} Returned for Corrections',
    message=f'''
    <p>Your Purchase Order has been returned for corrections:</p>
    <ul>
        <li><b>PO Number:</b> {doc.name}</li>
        <li><b>Returned By:</b> {frappe.session.user}</li>
        <li><b>Comments:</b> {event.get('comments', 'No comments provided')}</li>
    </ul>
    <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">View and Correct</a></p>
    ''',
    reference_doctype='Purchase Order',
    reference_name=doc.name
)
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_rejection",
            "action_type": "transition",
            "description": "Notify requester of rejection",
            "python_code": """
frappe.sendmail(
    recipients=[doc.owner],
    subject=f'PO {doc.name} Rejected',
    message=f'''
    <p>Your Purchase Order has been rejected:</p>
    <ul>
        <li><b>PO Number:</b> {doc.name}</li>
        <li><b>Rejected By:</b> {frappe.session.user}</li>
        <li><b>Reason:</b> {event.get('rejection_reason', 'No reason provided')}</li>
    </ul>
    <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">View Details</a></p>
    ''',
    reference_doctype='Purchase Order',
    reference_name=doc.name
)
context['rejection_reason'] = event.get('rejection_reason')
context['rejected_by'] = frappe.session.user
context['rejected_at'] = str(frappe.utils.now_datetime())
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_requester_approved",
            "action_type": "transition",
            "description": "Notify requester that PO was approved",
            "python_code": """
frappe.sendmail(
    recipients=[doc.owner],
    subject=f'PO {doc.name} Approved!',
    message=f'''
    <p>Great news! Your Purchase Order has been approved:</p>
    <ul>
        <li><b>PO Number:</b> {doc.name}</li>
        <li><b>Approved By:</b> {frappe.session.user}</li>
        <li><b>Amount:</b> {frappe.format_value(doc.grand_total, {'fieldtype': 'Currency'})}</li>
    </ul>
    <p>The PO is now ready to be sent to the supplier.</p>
    <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">View Details</a></p>
    ''',
    reference_doctype='Purchase Order',
    reference_name=doc.name
)
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_info_request",
            "action_type": "transition",
            "description": "Notify requester that more info is needed",
            "python_code": """
frappe.sendmail(
    recipients=[doc.owner],
    subject=f'Additional Info Required for PO {doc.name}',
    message=f'''
    <p>Additional information is required for your Purchase Order:</p>
    <ul>
        <li><b>PO Number:</b> {doc.name}</li>
        <li><b>Requested By:</b> {frappe.session.user}</li>
        <li><b>Details Needed:</b> {event.get('info_request', 'Please provide additional details')}</li>
    </ul>
    <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">Provide Information</a></p>
    ''',
    reference_doctype='Purchase Order',
    reference_name=doc.name
)
context['info_requested_at'] = str(frappe.utils.now_datetime())
context['info_requested_by'] = frappe.session.user
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_escalation",
            "action_type": "transition",
            "description": "Notify about escalation",
            "python_code": """
recipients = frappe.get_all(
    'Has Role',
    filters={'role': 'Accounts Manager', 'parenttype': 'User'},
    pluck='parent'
)
if recipients:
    frappe.sendmail(
        recipients=recipients[:3],
        subject=f'ESCALATED: PO {doc.name} Requires Urgent Approval',
        message=f'''
        <p><b>ESCALATED:</b> This Purchase Order has been escalated and requires urgent attention:</p>
        <ul>
            <li><b>PO Number:</b> {doc.name}</li>
            <li><b>Supplier:</b> {doc.supplier_name}</li>
            <li><b>Amount:</b> {frappe.format_value(doc.grand_total, {'fieldtype': 'Currency'})}</li>
            <li><b>Escalation Count:</b> {context.get('escalation_count', 0)}</li>
        </ul>
        <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">Review Immediately</a></p>
        ''',
        reference_doctype='Purchase Order',
        reference_name=doc.name
    )
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_procurement_head",
            "action_type": "transition",
            "description": "Notify procurement head about supplier non-response",
            "python_code": """
# Get procurement manager/head
recipients = frappe.get_all(
    'Has Role',
    filters={'role': 'Purchase Manager', 'parenttype': 'User'},
    pluck='parent'
)
if recipients:
    frappe.sendmail(
        recipients=recipients[:2],
        subject=f'URGENT: No Supplier Response for PO {doc.name}',
        message=f'''
        <p><b>URGENT:</b> The supplier has not responded to PO {doc.name} within 7 days:</p>
        <ul>
            <li><b>PO Number:</b> {doc.name}</li>
            <li><b>Supplier:</b> {doc.supplier_name}</li>
            <li><b>Amount:</b> {frappe.format_value(doc.grand_total, {'fieldtype': 'Currency'})}</li>
            <li><b>Sent On:</b> {context.get('sent_to_supplier_at', 'Unknown')}</li>
        </ul>
        <p>Please contact the supplier or take appropriate action.</p>
        <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">View Details</a></p>
        ''',
        reference_doctype='Purchase Order',
        reference_name=doc.name
    )
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_requester_issue",
            "action_type": "entry",
            "description": "Notify requester about supplier issue",
            "python_code": """
frappe.sendmail(
    recipients=[doc.owner],
    subject=f'Supplier Issue with PO {doc.name}',
    message=f'''
    <p>The supplier has reported an issue with your Purchase Order:</p>
    <ul>
        <li><b>PO Number:</b> {doc.name}</li>
        <li><b>Supplier:</b> {doc.supplier_name}</li>
        <li><b>Issue:</b> {event.get('supplier_issue', 'Issue details not provided')}</li>
    </ul>
    <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">View and Resolve</a></p>
    ''',
    reference_doctype='Purchase Order',
    reference_name=doc.name
)
context['supplier_issue'] = event.get('supplier_issue')
context['supplier_issue_at'] = str(frappe.utils.now_datetime())
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_stakeholders_complete",
            "action_type": "entry",
            "description": "Notify all stakeholders of completion",
            "python_code": """
recipients = [doc.owner]
# Add any approvers from history
for approval in context.get('approval_history', []):
    if approval.get('user') and approval['user'] not in recipients:
        recipients.append(approval['user'])

frappe.sendmail(
    recipients=recipients[:5],
    subject=f'PO {doc.name} Order Confirmed by Supplier',
    message=f'''
    <p>The supplier has confirmed the order:</p>
    <ul>
        <li><b>PO Number:</b> {doc.name}</li>
        <li><b>Supplier:</b> {doc.supplier_name}</li>
        <li><b>Amount:</b> {frappe.format_value(doc.grand_total, {'fieldtype': 'Currency'})}</li>
        <li><b>Confirmation:</b> {event.get('supplier_confirmation', 'Confirmed')}</li>
    </ul>
    <p>The workflow is now complete.</p>
    ''',
    reference_doctype='Purchase Order',
    reference_name=doc.name
)
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_parallel_rejection",
            "action_type": "transition",
            "description": "Notify about parallel approval rejection",
            "python_code": """
rejection_details = []
if not context.get('finance_approved'):
    rejection_details.append('Finance: Rejected or Pending')
if not context.get('legal_approved'):
    rejection_details.append('Legal: Rejected or Pending')

frappe.sendmail(
    recipients=[doc.owner],
    subject=f'PO {doc.name} Not Approved in Parallel Review',
    message=f'''
    <p>Your Purchase Order was not approved in the parallel review process:</p>
    <ul>
        <li><b>PO Number:</b> {doc.name}</li>
        <li><b>Details:</b> {', '.join(rejection_details)}</li>
    </ul>
    <p><a href="{frappe.utils.get_url_to_form('Purchase Order', doc.name)}">View Details</a></p>
    ''',
    reference_doctype='Purchase Order',
    reference_name=doc.name
)
""",
            "is_async": 0,
        },
        {
            "action_name": "notify_supplier_cancelled",
            "action_type": "transition",
            "description": "Notify supplier of cancellation",
            "python_code": """
supplier_email = doc.get('supplier_email') or frappe.db.get_value('Supplier', doc.supplier, 'email_id')
if supplier_email:
    frappe.sendmail(
        recipients=[supplier_email],
        subject=f'Purchase Order {doc.name} Cancelled',
        message=f'''
        <p>We regret to inform you that Purchase Order {doc.name} has been cancelled.</p>
        <p>Please disregard any previous communications about this order.</p>
        <p>If you have any questions, please contact us.</p>
        ''',
        reference_doctype='Purchase Order',
        reference_name=doc.name
    )
""",
            "is_async": 0,
        },
        # ============================================================
        # Approval Recording Actions
        # ============================================================
        {
            "action_name": "record_approval",
            "action_type": "transition",
            "description": "Record approval in context",
            "python_code": """
if 'approval_history' not in context:
    context['approval_history'] = []

context['approval_history'].append({
    'action': 'APPROVE',
    'user': frappe.session.user,
    'user_fullname': frappe.db.get_value('User', frappe.session.user, 'full_name'),
    'state': context.get('_current_state'),
    'comments': event.get('comments', ''),
    'timestamp': str(frappe.utils.now_datetime())
})
context['last_approved_by'] = frappe.session.user
context['last_approved_at'] = str(frappe.utils.now_datetime())
""",
        },
        {
            "action_name": "record_rejection",
            "action_type": "transition",
            "description": "Record rejection in context",
            "python_code": """
if 'approval_history' not in context:
    context['approval_history'] = []

context['approval_history'].append({
    'action': 'REJECT',
    'user': frappe.session.user,
    'user_fullname': frappe.db.get_value('User', frappe.session.user, 'full_name'),
    'state': context.get('_current_state'),
    'reason': event.get('rejection_reason', ''),
    'timestamp': str(frappe.utils.now_datetime())
})
""",
        },
        {
            "action_name": "record_finance_approval",
            "action_type": "entry",
            "description": "Record finance approval in parallel state",
            "python_code": """
context['finance_approved'] = True
context['finance_approved_by'] = frappe.session.user
context['finance_approved_at'] = str(frappe.utils.now_datetime())

if 'approval_history' not in context:
    context['approval_history'] = []
context['approval_history'].append({
    'action': 'APPROVE_FINANCE',
    'user': frappe.session.user,
    'timestamp': str(frappe.utils.now_datetime())
})
""",
        },
        {
            "action_name": "record_finance_rejection",
            "action_type": "entry",
            "description": "Record finance rejection in parallel state",
            "python_code": """
context['finance_approved'] = False
context['finance_rejected_by'] = frappe.session.user
context['finance_rejected_at'] = str(frappe.utils.now_datetime())
""",
        },
        {
            "action_name": "record_legal_approval",
            "action_type": "entry",
            "description": "Record legal approval in parallel state",
            "python_code": """
context['legal_approved'] = True
context['legal_approved_by'] = frappe.session.user
context['legal_approved_at'] = str(frappe.utils.now_datetime())

if 'approval_history' not in context:
    context['approval_history'] = []
context['approval_history'].append({
    'action': 'APPROVE_LEGAL',
    'user': frappe.session.user,
    'timestamp': str(frappe.utils.now_datetime())
})
""",
        },
        {
            "action_name": "record_legal_rejection",
            "action_type": "entry",
            "description": "Record legal rejection in parallel state",
            "python_code": """
context['legal_approved'] = False
context['legal_rejected_by'] = frappe.session.user
context['legal_rejected_at'] = str(frappe.utils.now_datetime())
""",
        },
        # ============================================================
        # Task Management Actions
        # ============================================================
        {
            "action_name": "create_manager_task",
            "action_type": "entry",
            "description": "Create approval task for manager",
            "python_code": """
# Check if Approval Task doctype exists
if frappe.db.exists('DocType', 'Approval Task'):
    task = frappe.get_doc({
        'doctype': 'Approval Task',
        'workflow_instance': context.get('_instance_name'),
        'node_id': 'manager_approval',
        'node_label': 'Manager Approval',
        'reference_doctype': 'Purchase Order',
        'reference_name': doc.name,
        'assigned_role': 'Purchase Manager',
        'status': 'Pending',
        'priority': 'Medium',
        'available_actions': json.dumps(['Approve', 'Reject', 'Request Info']),
        'sla_hours': 24
    })
    task.insert(ignore_permissions=True)
    context['_current_approval_task'] = task.name
else:
    # Fallback: just log
    frappe.logger().info(f"Manager approval task created for {doc.name}")
""",
        },
        {
            "action_name": "create_escalated_task",
            "action_type": "entry",
            "description": "Create escalated approval task",
            "python_code": """
if frappe.db.exists('DocType', 'Approval Task'):
    task = frappe.get_doc({
        'doctype': 'Approval Task',
        'workflow_instance': context.get('_instance_name'),
        'node_id': 'escalated_approval',
        'node_label': 'Escalated Approval',
        'reference_doctype': 'Purchase Order',
        'reference_name': doc.name,
        'assigned_role': 'Accounts Manager',
        'status': 'Pending',
        'priority': 'High',
        'available_actions': json.dumps(['Approve', 'Reject']),
        'sla_hours': 12
    })
    task.insert(ignore_permissions=True)
    context['_current_approval_task'] = task.name
""",
        },
        {
            "action_name": "create_finance_task",
            "action_type": "entry",
            "description": "Create finance approval task for parallel approval",
            "python_code": """
if frappe.db.exists('DocType', 'Approval Task'):
    task = frappe.get_doc({
        'doctype': 'Approval Task',
        'workflow_instance': context.get('_instance_name'),
        'node_id': 'parallel_approval.finance_region.finance_pending',
        'node_label': 'Finance Approval',
        'reference_doctype': 'Purchase Order',
        'reference_name': doc.name,
        'assigned_role': 'Accounts Manager',
        'status': 'Pending',
        'priority': 'High',
        'available_actions': json.dumps(['Approve', 'Reject']),
        'sla_hours': 24
    })
    task.insert(ignore_permissions=True)
    context['_finance_task'] = task.name
""",
        },
        {
            "action_name": "create_legal_task",
            "action_type": "entry",
            "description": "Create legal approval task for parallel approval",
            "python_code": """
if frappe.db.exists('DocType', 'Approval Task'):
    task = frappe.get_doc({
        'doctype': 'Approval Task',
        'workflow_instance': context.get('_instance_name'),
        'node_id': 'parallel_approval.legal_region.legal_pending',
        'node_label': 'Legal Approval',
        'reference_doctype': 'Purchase Order',
        'reference_name': doc.name,
        'assigned_role': 'Legal Manager',
        'status': 'Pending',
        'priority': 'High',
        'available_actions': json.dumps(['Approve', 'Reject']),
        'sla_hours': 48
    })
    task.insert(ignore_permissions=True)
    context['_legal_task'] = task.name
""",
        },
        {
            "action_name": "complete_approval_task",
            "action_type": "exit",
            "description": "Complete the current approval task",
            "python_code": """
task_name = context.get('_current_approval_task')
if task_name and frappe.db.exists('Approval Task', task_name):
    task = frappe.get_doc('Approval Task', task_name)
    task.status = 'Completed'
    task.completed_by = frappe.session.user
    task.completed_at = frappe.utils.now_datetime()
    task.save(ignore_permissions=True)
    context.pop('_current_approval_task', None)
""",
        },
        {
            "action_name": "cancel_all_tasks",
            "action_type": "entry",
            "description": "Cancel all pending approval tasks",
            "python_code": """
if frappe.db.exists('DocType', 'Approval Task'):
    pending_tasks = frappe.get_all(
        'Approval Task',
        filters={
            'reference_doctype': 'Purchase Order',
            'reference_name': doc.name,
            'status': 'Pending'
        },
        pluck='name'
    )
    for task_name in pending_tasks:
        task = frappe.get_doc('Approval Task', task_name)
        task.status = 'Cancelled'
        task.save(ignore_permissions=True)
    context['tasks_cancelled'] = len(pending_tasks)
""",
        },
        # ============================================================
        # Timer Actions
        # ============================================================
        {
            "action_name": "start_sla_timer",
            "action_type": "entry",
            "description": "Start SLA timer for approval",
            "python_code": """
context['sla_started_at'] = str(frappe.utils.now_datetime())
context['sla_hours'] = 24
""",
        },
        {
            "action_name": "stop_sla_timer",
            "action_type": "exit",
            "description": "Stop SLA timer",
            "python_code": """
if context.get('sla_started_at'):
    from frappe.utils import now_datetime, get_datetime, time_diff_in_hours
    elapsed = time_diff_in_hours(now_datetime(), get_datetime(context['sla_started_at']))
    context['sla_elapsed_hours'] = round(elapsed, 2)
    context.pop('sla_started_at', None)
""",
        },
        {
            "action_name": "start_supplier_timer",
            "action_type": "entry",
            "description": "Start supplier response timer",
            "python_code": """
context['supplier_timer_started'] = str(frappe.utils.now_datetime())
""",
        },
        {
            "action_name": "cancel_escalation_timer",
            "action_type": "transition",
            "description": "Cancel the escalation timer",
            "python_code": """
context['escalation_timer_cancelled'] = True
context.pop('supplier_timer_started', None)
""",
        },
        # ============================================================
        # Escalation Actions
        # ============================================================
        {
            "action_name": "increment_escalation",
            "action_type": "transition",
            "description": "Increment escalation counter",
            "python_code": """
context['escalation_count'] = context.get('escalation_count', 0) + 1
context['last_escalated_at'] = str(frappe.utils.now_datetime())
context['last_escalated_by'] = frappe.session.user
""",
        },
        {
            "action_name": "auto_escalate",
            "action_type": "transition",
            "description": "Auto-escalate due to timeout",
            "python_code": """
context['escalation_count'] = context.get('escalation_count', 0) + 1
context['auto_escalated'] = True
context['auto_escalated_at'] = str(frappe.utils.now_datetime())
context['auto_escalation_reason'] = 'No response within SLA'
frappe.logger().warning(f"PO {doc.name} auto-escalated due to SLA breach")
""",
        },
        {
            "action_name": "flag_urgent",
            "action_type": "transition",
            "description": "Flag the PO as urgent",
            "python_code": """
context['is_urgent'] = True
context['flagged_urgent_at'] = str(frappe.utils.now_datetime())
# Update custom field if exists
if frappe.get_meta('Purchase Order').has_field('custom_is_urgent'):
    frappe.db.set_value('Purchase Order', doc.name, 'custom_is_urgent', 1)
""",
        },
        # ============================================================
        # Status Update Actions
        # ============================================================
        {
            "action_name": "set_auto_approved",
            "action_type": "entry",
            "description": "Set auto-approved status",
            "python_code": """
context['approval_type'] = 'Auto'
context['approved_at'] = str(frappe.utils.now_datetime())
""",
        },
        {
            "action_name": "set_approved_status",
            "action_type": "entry",
            "description": "Set document approved status",
            "python_code": """
context['workflow_status'] = 'Approved'
# Update custom field if exists
if frappe.get_meta('Purchase Order').has_field('custom_workflow_status'):
    frappe.db.set_value('Purchase Order', doc.name, 'custom_workflow_status', 'Approved')
""",
        },
        {
            "action_name": "record_approval_timestamp",
            "action_type": "entry",
            "description": "Record approval timestamp",
            "python_code": """
context['final_approved_at'] = str(frappe.utils.now_datetime())
# Calculate total approval time
if context.get('submitted_at'):
    from frappe.utils import now_datetime, get_datetime, time_diff_in_hours
    elapsed = time_diff_in_hours(now_datetime(), get_datetime(context['submitted_at']))
    context['total_approval_hours'] = round(elapsed, 2)
""",
        },
        {
            "action_name": "set_rejected_status",
            "action_type": "entry",
            "description": "Set document rejected status",
            "python_code": """
context['workflow_status'] = 'Rejected'
if frappe.get_meta('Purchase Order').has_field('custom_workflow_status'):
    frappe.db.set_value('Purchase Order', doc.name, 'custom_workflow_status', 'Rejected')
""",
        },
        {
            "action_name": "set_cancelled_status",
            "action_type": "entry",
            "description": "Set document cancelled status",
            "python_code": """
context['workflow_status'] = 'Cancelled'
if frappe.get_meta('Purchase Order').has_field('custom_workflow_status'):
    frappe.db.set_value('Purchase Order', doc.name, 'custom_workflow_status', 'Cancelled')
""",
        },
        {
            "action_name": "set_sent_date",
            "action_type": "entry",
            "description": "Record when PO was sent to supplier",
            "python_code": """
context['sent_to_supplier_at'] = str(frappe.utils.now_datetime())
context['sent_to_supplier_by'] = frappe.session.user
""",
        },
        {
            "action_name": "set_confirmed_status",
            "action_type": "entry",
            "description": "Set order confirmed status",
            "python_code": """
context['workflow_status'] = 'Completed'
context['confirmed_at'] = str(frappe.utils.now_datetime())
if frappe.get_meta('Purchase Order').has_field('custom_workflow_status'):
    frappe.db.set_value('Purchase Order', doc.name, 'custom_workflow_status', 'Completed')
""",
        },
        {
            "action_name": "record_completion_time",
            "action_type": "entry",
            "description": "Record total workflow completion time",
            "python_code": """
if context.get('submitted_at'):
    from frappe.utils import now_datetime, get_datetime, time_diff_in_hours
    elapsed = time_diff_in_hours(now_datetime(), get_datetime(context['submitted_at']))
    context['total_workflow_hours'] = round(elapsed, 2)
    frappe.logger().info(f"PO {doc.name} workflow completed in {context['total_workflow_hours']} hours")
""",
        },
        {
            "action_name": "record_confirmation",
            "action_type": "transition",
            "description": "Record supplier confirmation",
            "python_code": """
context['supplier_confirmed'] = True
context['supplier_confirmed_at'] = str(frappe.utils.now_datetime())
context['supplier_confirmation_ref'] = event.get('confirmation_reference', '')
""",
        },
        {
            "action_name": "record_late_confirmation",
            "action_type": "transition",
            "description": "Record late supplier confirmation",
            "python_code": """
context['supplier_confirmed'] = True
context['supplier_confirmed_at'] = str(frappe.utils.now_datetime())
context['late_confirmation'] = True
""",
        },
        # ============================================================
        # Supplier Communication Actions
        # ============================================================
        {
            "action_name": "email_supplier",
            "action_type": "transition",
            "description": "Email PO to supplier",
            "python_code": """
supplier_email = doc.get('supplier_email') or frappe.db.get_value('Supplier', doc.supplier, 'email_id')
if supplier_email:
    # Get PDF attachment
    attachments = []
    try:
        pdf = frappe.attach_print('Purchase Order', doc.name, print_format='Standard')
        attachments.append(pdf)
    except Exception:
        pass  # Skip attachment if print fails

    frappe.sendmail(
        recipients=[supplier_email],
        subject=f'Purchase Order {doc.name}',
        message=f'''
        <p>Dear {doc.supplier_name},</p>
        <p>Please find attached Purchase Order {doc.name}.</p>
        <ul>
            <li><b>PO Number:</b> {doc.name}</li>
            <li><b>Amount:</b> {frappe.format_value(doc.grand_total, {'fieldtype': 'Currency', 'options': doc.currency})}</li>
            <li><b>Required By:</b> {doc.schedule_date or 'As soon as possible'}</li>
        </ul>
        <p>Please confirm receipt of this order.</p>
        <p>Thank you for your business.</p>
        ''',
        attachments=attachments,
        reference_doctype='Purchase Order',
        reference_name=doc.name
    )
    context['supplier_email_sent'] = True
    context['supplier_email_sent_at'] = str(frappe.utils.now_datetime())
else:
    context['supplier_email_sent'] = False
    context['supplier_email_error'] = 'No supplier email found'
""",
            "is_async": 0,
        },
        {
            "action_name": "call_supplier_api",
            "action_type": "transition",
            "description": "Call supplier API to submit order",
            "python_code": """
# Example: Call external supplier API
# In a real scenario, you would configure the API endpoint
import requests

api_config = frappe.get_single('Buying Settings')
supplier_api_url = getattr(api_config, 'custom_supplier_api_url', None)

if supplier_api_url:
    try:
        payload = {
            'po_number': doc.name,
            'supplier': doc.supplier,
            'items': [{'item_code': i.item_code, 'qty': i.qty, 'rate': i.rate}
                      for i in doc.items],
            'total': doc.grand_total,
            'currency': doc.currency
        }
        response = requests.post(
            supplier_api_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        context['_api_response'] = {
            'status_code': response.status_code,
            'body': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
        context['supplier_api_success'] = response.status_code == 200
    except Exception as e:
        context['supplier_api_success'] = False
        context['supplier_api_error'] = str(e)
else:
    # API not configured, just log
    frappe.logger().info(f"Supplier API not configured, skipping API call for {doc.name}")
    context['supplier_api_success'] = None
""",
            "is_async": 0,
        },
        # ============================================================
        # Misc Actions
        # ============================================================
        {
            "action_name": "log_info_provided",
            "action_type": "transition",
            "description": "Log that additional info was provided",
            "python_code": """
context['info_provided_at'] = str(frappe.utils.now_datetime())
context['info_provided_by'] = frappe.session.user
context['additional_info'] = event.get('additional_info', '')
""",
        },
        {
            "action_name": "log_issue_resolved",
            "action_type": "transition",
            "description": "Log supplier issue resolution",
            "python_code": """
context['issue_resolved_at'] = str(frappe.utils.now_datetime())
context['issue_resolved_by'] = frappe.session.user
context['resolution_notes'] = event.get('resolution_notes', '')
""",
        },
        {
            "action_name": "log_resend",
            "action_type": "transition",
            "description": "Log PO resend to supplier",
            "python_code": """
context['resend_count'] = context.get('resend_count', 0) + 1
context['last_resent_at'] = str(frappe.utils.now_datetime())
""",
        },
    ]


def create_workflow(force=False):
    """
    Create the Purchase Order Workflow State Machine.

    Args:
        force: If True, delete existing workflow and recreate
    """
    machine_id = "purchase_order_approval"

    # Check if already exists
    if frappe.db.exists("State Machine", {"machine_id": machine_id}):
        if force:
            frappe.delete_doc("State Machine", machine_id, force=True)
            frappe.db.commit()
            print(f"Deleted existing workflow: {machine_id}")
        else:
            print(f"Workflow '{machine_id}' already exists. Use force=True to recreate.")
            return frappe.get_doc("State Machine", machine_id)

    # Build the configuration
    config = get_workflow_config()
    guards = get_guards()
    actions = get_actions()

    # Create the State Machine document
    machine = frappe.get_doc({
        "doctype": "State Machine",
        "machine_id": machine_id,
        "title": "Purchase Order Approval Workflow",
        "description": """Comprehensive Purchase Order workflow demonstrating:
- Auto-triggers (on document submit)
- Conditional routing based on amount thresholds
- Manager approval for mid-range orders (10K-100K)
- Parallel Finance + Legal approval for high-value orders (>100K)
- Auto-approval for small orders (<10K)
- Scheduled escalation after SLA breach
- History states for pause/resume functionality
- Supplier communication and confirmation tracking
""",
        "json_config": json.dumps(config, indent=2),
        "attached_doctype": "Purchase Order",
        "is_active": 1,
        "auto_start_on_create": 0,  # Manual start since PO uses Submit
        "xstate_version": "v5",
        "guards_table": guards,
        "actions_table": actions,
    })

    machine.insert(ignore_permissions=True)
    frappe.db.commit()

    print(f"✅ Created workflow: {machine.title}")
    print(f"   Machine ID: {machine.machine_id}")
    print(f"   Attached to: {machine.attached_doctype}")
    print(f"   Guards: {len(guards)}")
    print(f"   Actions: {len(actions)}")
    print(f"   States: {len(config['states'])}")

    return machine


def delete_workflow():
    """Delete the Purchase Order workflow."""
    machine_id = "purchase_order_approval"
    if frappe.db.exists("State Machine", {"machine_id": machine_id}):
        frappe.delete_doc("State Machine", machine_id, force=True)
        frappe.db.commit()
        print(f"✅ Deleted workflow: {machine_id}")
    else:
        print(f"Workflow '{machine_id}' does not exist.")


if __name__ == "__main__":
    create_workflow()
