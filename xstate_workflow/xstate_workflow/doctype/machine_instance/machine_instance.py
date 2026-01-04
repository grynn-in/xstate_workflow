# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.model.document import Document


class MachineInstance(Document):
    def before_insert(self):
        """Initialize instance with machine's initial state"""
        if not self.current_state:
            machine = frappe.get_doc("State Machine", self.machine)
            config = json.loads(machine.json_config)
            self.current_state = config.get("initial", "")
            self.status = "idle"
            self.context = json.dumps(config.get("context", {}))
            self.transition_log = json.dumps([])

    def validate(self):
        # Ensure reference exists
        if self.reference_doctype and self.reference_name:
            if not frappe.db.exists(self.reference_doctype, self.reference_name):
                frappe.throw(_("Reference document {0} {1} does not exist").format(
                    self.reference_doctype, self.reference_name
                ))

    def log_transition(self, event, from_state, to_state, success=True, error=None):
        """Add entry to transition log"""
        log = json.loads(self.transition_log or "[]")
        log.append({
            "timestamp": str(frappe.utils.now()),
            "event": event,
            "from_state": from_state,
            "to_state": to_state,
            "success": success,
            "error": error,
            "user": frappe.session.user
        })
        # Keep last 100 entries
        self.transition_log = json.dumps(log[-100:])
        self.transition_count = (self.transition_count or 0) + 1
        if not success:
            self.error_count = (self.error_count or 0) + 1

    def get_context_dict(self):
        """Return context as Python dict"""
        return json.loads(self.context or "{}")

    def set_context(self, context_dict):
        """Set context from Python dict"""
        self.context = json.dumps(context_dict)

    def update_context(self, updates):
        """Merge updates into existing context"""
        ctx = self.get_context_dict()
        ctx.update(updates)
        self.set_context(ctx)

    @frappe.whitelist()
    def get_available_events(self):
        """Get list of valid events for current state"""
        from xstate_workflow.workflow_engine import get_next_events
        return get_next_events(self.machine, self.current_state, self.get_context_dict())

    @frappe.whitelist()
    def send_event(self, event, data=None):
        """Send event to this instance"""
        from xstate_workflow.workflow_engine import trigger_event_sync
        return trigger_event_sync(
            self.reference_doctype,
            self.reference_name,
            event,
            data or {}
        )

    @frappe.whitelist()
    def reset(self):
        """Reset instance to initial state"""
        machine = frappe.get_doc("State Machine", self.machine)
        config = json.loads(machine.json_config)

        self.current_state = config.get("initial", "")
        self.status = "idle"
        self.context = json.dumps(config.get("context", {}))
        self.snapshot = None
        self.last_event = None
        self.transition_count = 0
        self.error_count = 0
        self.transition_log = json.dumps([{
            "timestamp": str(frappe.utils.now()),
            "event": "RESET",
            "from_state": None,
            "to_state": self.current_state,
            "success": True,
            "user": frappe.session.user
        }])
        self.save()
        return {"success": True, "state": self.current_state}
