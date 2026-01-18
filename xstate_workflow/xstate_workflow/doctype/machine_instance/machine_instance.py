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
            self.parallel_states = json.dumps({})
            self.history_states = json.dumps({})
            self.active_services = json.dumps([])
            self.delayed_transitions = json.dumps([])

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

    # ==================== PARALLEL STATE METHODS ====================

    def get_parallel_states(self):
        """Get parallel states as dict: {region_path: current_state}"""
        return json.loads(self.parallel_states or "{}")

    def set_parallel_states(self, states_dict):
        """Set parallel states from dict"""
        self.parallel_states = json.dumps(states_dict)

    def update_parallel_state(self, region_path, state):
        """Update a single parallel region's state"""
        states = self.get_parallel_states()
        states[region_path] = state
        self.set_parallel_states(states)

    def clear_parallel_states(self, parent_path=None):
        """Clear parallel states, optionally only under a parent path"""
        if parent_path is None:
            self.parallel_states = json.dumps({})
        else:
            states = self.get_parallel_states()
            states = {k: v for k, v in states.items() if not k.startswith(parent_path)}
            self.set_parallel_states(states)

    # ==================== HISTORY STATE METHODS ====================

    def get_history_states(self):
        """Get history states as dict: {state_path: last_active_state}"""
        return json.loads(self.history_states or "{}")

    def set_history_states(self, history_dict):
        """Set history states from dict"""
        self.history_states = json.dumps(history_dict)

    def record_history(self, parent_path, child_state, deep=False):
        """Record history when leaving a state

        Args:
            parent_path: Path to the parent compound state
            child_state: The child state that was active
            deep: If True, record full nested state (deep history)
        """
        history = self.get_history_states()
        key = f"{parent_path}.$history" if not deep else f"{parent_path}.$history.deep"
        history[key] = child_state
        self.set_history_states(history)

    def get_history(self, parent_path, deep=False):
        """Get recorded history for a parent state

        Returns the last active child state, or None if no history
        """
        history = self.get_history_states()
        key = f"{parent_path}.$history.deep" if deep else f"{parent_path}.$history"
        return history.get(key)

    def clear_history(self, parent_path=None):
        """Clear history states, optionally only under a parent path"""
        if parent_path is None:
            self.history_states = json.dumps({})
        else:
            history = self.get_history_states()
            history = {k: v for k, v in history.items() if not k.startswith(parent_path)}
            self.set_history_states(history)

    # ==================== SERVICE METHODS ====================

    def get_active_services(self):
        """Get list of active invoke services"""
        return json.loads(self.active_services or "[]")

    def add_active_service(self, service_id, service_config):
        """Add a service to active services list"""
        services = self.get_active_services()
        services.append({
            "id": service_id,
            "config": service_config,
            "started_at": str(frappe.utils.now())
        })
        self.active_services = json.dumps(services)

    def remove_active_service(self, service_id):
        """Remove a service from active services list"""
        services = self.get_active_services()
        services = [s for s in services if s.get("id") != service_id]
        self.active_services = json.dumps(services)

    def clear_active_services(self):
        """Clear all active services"""
        self.active_services = json.dumps([])

    # ==================== DELAYED TRANSITION METHODS ====================

    def get_delayed_transitions(self):
        """Get list of pending delayed transitions"""
        return json.loads(self.delayed_transitions or "[]")

    def add_delayed_transition(self, delay_key, target_state, fire_at, event_data=None):
        """Schedule a delayed transition

        Args:
            delay_key: Unique identifier for this delay (e.g., state_path + delay_ms)
            target_state: State to transition to
            fire_at: Datetime when transition should fire
            event_data: Optional event data to pass
        """
        delays = self.get_delayed_transitions()
        delays.append({
            "key": delay_key,
            "target": target_state,
            "fire_at": str(fire_at),
            "event_data": event_data or {},
            "created_at": str(frappe.utils.now())
        })
        self.delayed_transitions = json.dumps(delays)

    def remove_delayed_transition(self, delay_key):
        """Cancel a delayed transition"""
        delays = self.get_delayed_transitions()
        delays = [d for d in delays if d.get("key") != delay_key]
        self.delayed_transitions = json.dumps(delays)

    def clear_delayed_transitions(self, state_path=None):
        """Clear delayed transitions, optionally only for a specific state"""
        if state_path is None:
            self.delayed_transitions = json.dumps([])
        else:
            delays = self.get_delayed_transitions()
            delays = [d for d in delays if not d.get("key", "").startswith(state_path)]
            self.delayed_transitions = json.dumps(delays)

    def get_pending_delays(self):
        """Get delayed transitions that are ready to fire"""
        now = frappe.utils.now_datetime()
        delays = self.get_delayed_transitions()
        return [d for d in delays if frappe.utils.get_datetime(d.get("fire_at")) <= now]

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
        self.parallel_states = json.dumps({})
        self.history_states = json.dumps({})
        self.active_services = json.dumps([])
        self.delayed_transitions = json.dumps([])
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

    @frappe.whitelist()
    def cancel(self, reason: str = None):
        """
        Cancel this workflow instance.

        Cancels all pending approval tasks and marks the workflow as cancelled.
        After cancellation, the workflow can be restarted using start_workflow().

        Args:
            reason: Optional reason for cancellation

        Returns:
            Dict with success status and number of tasks cancelled
        """
        from xstate_workflow.approval import cancel_pending_tasks

        # Cancel all pending approval tasks
        cancelled_tasks = cancel_pending_tasks(self.name)

        # Update status
        old_state = self.current_state
        self.status = "cancelled"

        # Log the cancellation
        log = json.loads(self.transition_log or "[]")
        log.append({
            "timestamp": str(frappe.utils.now()),
            "event": "CANCEL",
            "from_state": old_state,
            "to_state": None,
            "success": True,
            "user": frappe.session.user,
            "reason": reason,
            "tasks_cancelled": cancelled_tasks
        })
        self.transition_log = json.dumps(log[-100:])
        self.save()

        return {"success": True, "tasks_cancelled": cancelled_tasks}
