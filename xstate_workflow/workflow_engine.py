# xstate_workflow/xstate_workflow/workflow_engine.py
"""
XState Workflow Engine for Frappe
Handles state machine execution, persistence, and integration with Frappe documents.

Uses xstate-statemachine library for Python XState interpreter.
"""

import json
import traceback
from typing import Any

import frappe
from frappe import _
from frappe.utils.background_jobs import enqueue


# ============================================================================
# WHITELISTED API METHODS
# ============================================================================

@frappe.whitelist()
def trigger_event(doctype: str, docname: str, event: str, data: str | None = None) -> dict:
    """
    Whitelisted API to send XState event from forms/API.
    Enqueues transition for background processing.

    Args:
        doctype: Reference DocType name
        docname: Reference document name
        event: XState event to trigger
        data: Optional JSON string with event data

    Returns:
        dict with job_id for tracking
    """
    # Permission check - user must have write access to the document
    if not frappe.has_permission(doctype, "write", docname):
        frappe.throw(_("No permission to modify {0} {1}").format(doctype, docname), frappe.PermissionError)

    input_data = json.loads(data) if data else {}

    instance_name = get_or_create_instance(doctype, docname)

    job = enqueue(
        execute_transition,
        queue="default",
        timeout=300,
        instance_name=instance_name,
        event=event,
        input_data=input_data
    )

    return {
        "success": True,
        "message": _("Event '{0}' queued for processing").format(event),
        "job_id": job.id if job else None,
        "instance": instance_name
    }


@frappe.whitelist()
def trigger_event_sync(doctype: str, docname: str, event: str, data: str | None = None) -> dict:
    """
    Synchronous event trigger - use for immediate feedback.
    Not recommended for long-running actions.

    Args:
        doctype: Reference DocType name
        docname: Reference document name
        event: XState event to trigger
        data: Optional JSON string or dict with event data

    Returns:
        dict with transition result
    """
    # Permission check - user must have write access to the document
    if not frappe.has_permission(doctype, "write", docname):
        frappe.throw(_("No permission to modify {0} {1}").format(doctype, docname), frappe.PermissionError)

    if isinstance(data, str):
        input_data = json.loads(data) if data else {}
    else:
        input_data = data or {}

    instance_name = get_or_create_instance(doctype, docname)

    return execute_transition(instance_name, event, input_data)


def _trigger_event_internal(doctype: str, docname: str, event: str, data: str | None = None) -> dict:
    """
    Internal event trigger - used by hooks where permission is already validated.
    Enqueues transition for background processing WITHOUT permission check.

    Args:
        doctype: Reference DocType name
        docname: Reference document name
        event: XState event to trigger
        data: Optional JSON string with event data

    Returns:
        dict with job_id for tracking
    """
    input_data = json.loads(data) if data else {}

    instance_name = get_or_create_instance(doctype, docname)

    job = enqueue(
        execute_transition,
        queue="default",
        timeout=300,
        instance_name=instance_name,
        event=event,
        input_data=input_data
    )

    return {
        "success": True,
        "message": _("Event '{0}' queued for processing").format(event),
        "job_id": job.id if job else None,
        "instance": instance_name
    }


def _trigger_event_sync_internal(doctype: str, docname: str, event: str, data: str | None = None) -> dict:
    """
    Internal synchronous event trigger - used by hooks where permission is already validated.
    Does NOT perform permission check.

    Args:
        doctype: Reference DocType name
        docname: Reference document name
        event: XState event to trigger
        data: Optional JSON string or dict with event data

    Returns:
        dict with transition result
    """
    if isinstance(data, str):
        input_data = json.loads(data) if data else {}
    else:
        input_data = data or {}

    instance_name = get_or_create_instance(doctype, docname)

    return execute_transition(instance_name, event, input_data)


@frappe.whitelist()
def get_machine_state(doctype: str, docname: str) -> dict:
    """
    Get current state of a document's workflow instance.

    Args:
        doctype: Reference DocType name
        docname: Reference document name

    Returns:
        dict with current state, context, and available events
    """
    # Permission check - user must have read access to the document
    if not frappe.has_permission(doctype, "read", docname):
        frappe.throw(_("No permission to access {0} {1}").format(doctype, docname), frappe.PermissionError)

    instance = get_instance_for_doc(doctype, docname)

    # Check if a workflow is attached to this doctype (even if no instance exists yet)
    machine_info = frappe.db.get_value(
        "State Machine",
        {"attached_doctype": doctype, "is_active": 1},
        ["name", "auto_start_on_create", "edit_restriction_mode"],
        as_dict=True
    )

    if not instance:
        # No instance, but check if workflow is configured for this doctype
        if machine_info:
            return {
                "has_workflow": False,
                "workflow_attached": True,
                "auto_start": machine_info.auto_start_on_create,
                "machine": machine_info.name,
                "message": _("Workflow configured but not started for this document")
            }
        return {
            "has_workflow": False,
            "workflow_attached": False,
            "message": _("No workflow attached to this document")
        }

    # Build context with doctype/docname for guard evaluation
    context = json.loads(instance.context or "{}")
    context["doctype"] = doctype
    context["docname"] = docname

    available_events = get_next_events(
        instance.machine,
        instance.current_state,
        context
    )

    # Get edit permission info
    edit_restriction_mode = machine_info.get("edit_restriction_mode", "None") if machine_info else "None"
    edit_permission_info = _get_edit_permission_info(
        instance,
        edit_restriction_mode,
        frappe.session.user
    )

    return {
        "has_workflow": True,
        "workflow_attached": True,
        "auto_start": machine_info.auto_start_on_create if machine_info else True,
        "instance_name": instance.name,
        "machine": instance.machine,
        "current_state": instance.current_state,
        "status": instance.status,
        "context": json.loads(instance.context or "{}"),
        "last_event": instance.last_event,
        "last_transition_at": str(instance.last_transition_at) if instance.last_transition_at else None,
        "available_events": available_events,
        "transition_count": instance.transition_count,
        "edit_restriction_mode": edit_restriction_mode,
        "can_user_edit": edit_permission_info["can_edit"],
        "current_task": edit_permission_info.get("current_task")
    }


def _get_edit_permission_info(instance, edit_restriction_mode: str, user: str) -> dict:
    """
    Get edit permission info for a workflow instance.

    Args:
        instance: Machine Instance document or None
        edit_restriction_mode: The edit restriction mode from State Machine
        user: The user to check permissions for

    Returns:
        dict with can_edit boolean and current_task info
    """
    result = {"can_edit": True, "current_task": None}

    # No restrictions if mode is None or no instance
    if edit_restriction_mode == "None" or not instance:
        return result

    # No restrictions for idle or final workflows
    if instance.status in ("idle", "final"):
        return result

    # Get current pending approval task
    task = frappe.db.get_value(
        "Approval Task",
        {
            "workflow_instance": instance.name,
            "status": "Pending"
        },
        ["name", "assigned_to", "assigned_role"],
        as_dict=True
    )

    if not task:
        return result  # No pending task, no restrictions

    result["current_task"] = {
        "name": task.name,
        "assigned_to": task.assigned_to,
        "assigned_role": task.assigned_role
    }

    # Check permissions
    allowed = False

    # Check if user is directly assigned
    if edit_restriction_mode in ("Assigned Only", "Assigned or Role"):
        if task.assigned_to and task.assigned_to == user:
            allowed = True

    # Check if user has the assigned role
    if edit_restriction_mode in ("Role Only", "Assigned or Role"):
        if task.assigned_role and task.assigned_role in frappe.get_roles(user):
            allowed = True

    # System Manager always allowed
    if "System Manager" in frappe.get_roles(user):
        allowed = True

    result["can_edit"] = allowed
    return result


@frappe.whitelist()
def get_machine_state_with_history(doctype: str, docname: str) -> dict:
    """
    Get current state of a document's workflow instance with full transition history.
    Used by the workflow instance viewer for runtime state visualization.

    Args:
        doctype: Reference DocType name
        docname: Reference document name

    Returns:
        dict with current state, context, available events, and transition history
    """
    # Permission check - user must have read access to the document
    if not frappe.has_permission(doctype, "read", docname):
        frappe.throw(_("No permission to access {0} {1}").format(doctype, docname), frappe.PermissionError)

    instance = get_instance_for_doc(doctype, docname)

    if not instance:
        return {
            "has_workflow": False,
            "message": _("No workflow attached to this document")
        }

    # Build context with doctype/docname for guard evaluation
    context = json.loads(instance.context or "{}")
    context["doctype"] = doctype
    context["docname"] = docname

    available_events = get_next_events(
        instance.machine,
        instance.current_state,
        context
    )

    # Parse transition log
    transition_log = json.loads(instance.transition_log or "[]")

    # Get all state names from machine config for visualization
    all_states = []
    try:
        machine_doc = frappe.get_doc("State Machine", instance.machine)
        config = json.loads(machine_doc.json_config)
        all_states = list(config.get("states", {}).keys())
    except Exception:
        pass

    return {
        "has_workflow": True,
        "instance_name": instance.name,
        "machine": instance.machine,
        "current_state": instance.current_state,
        "status": instance.status,
        "context": json.loads(instance.context or "{}"),
        "last_event": instance.last_event,
        "last_transition_at": str(instance.last_transition_at) if instance.last_transition_at else None,
        "available_events": available_events,
        "transition_count": instance.transition_count,
        "transition_log": transition_log,
        "all_states": all_states
    }


@frappe.whitelist()
def save_machine(machine_id: str, json_config: str, title: str = "",
                 workflow_builder_config: str = None, attached_doctype: str = None) -> dict:
    """
    Save or update a state machine configuration.

    Args:
        machine_id: Unique identifier for the machine
        json_config: XState JSON configuration
        title: Human-readable title
        workflow_builder_config: Visual workflow builder configuration JSON
        attached_doctype: DocType to attach this workflow to

    Returns:
        dict with saved machine name
    """
    # Permission check - user must have permission to create/edit State Machine
    existing = frappe.db.exists("State Machine", machine_id)
    if existing:
        if not frappe.has_permission("State Machine", "write", machine_id):
            frappe.throw(_("No permission to modify State Machine"), frappe.PermissionError)
    else:
        if not frappe.has_permission("State Machine", "create"):
            frappe.throw(_("No permission to create State Machine"), frappe.PermissionError)

    existing = frappe.db.exists("State Machine", machine_id)

    if existing:
        machine = frappe.get_doc("State Machine", machine_id)
        machine.json_config = json_config
        if workflow_builder_config:
            machine.workflow_builder_config = workflow_builder_config
        if title:
            machine.title = title
        if attached_doctype:
            machine.attached_doctype = attached_doctype
        machine.save()
    else:
        machine = frappe.get_doc({
            "doctype": "State Machine",
            "machine_id": machine_id,
            "title": title or machine_id,
            "json_config": json_config,
            "workflow_builder_config": workflow_builder_config,
            "attached_doctype": attached_doctype,
            "is_active": 1
        }).insert()

    frappe.db.commit()

    return {
        "success": True,
        "name": machine.name,
        "version": machine.version
    }


@frappe.whitelist()
def get_machine(machine_id: str) -> dict:
    """
    Retrieve a state machine configuration.

    Args:
        machine_id: Machine identifier

    Returns:
        dict with machine configuration
    """
    if not frappe.db.exists("State Machine", machine_id):
        frappe.throw(_("State Machine '{0}' not found").format(machine_id))

    # Permission check - user must have read access to State Machine
    if not frappe.has_permission("State Machine", "read", machine_id):
        frappe.throw(_("No permission to access State Machine"), frappe.PermissionError)

    machine = frappe.get_doc("State Machine", machine_id)

    return {
        "machine_id": machine.machine_id,
        "title": machine.title,
        "version": machine.version,
        "is_active": machine.is_active,
        "attached_doctype": machine.attached_doctype,
        "json_config": machine.json_config,
        "workflow_builder_config": machine.workflow_builder_config,
        "logic_module": machine.logic_module,
        "guards": [{"name": g.guard_name, "code": g.python_code}
                   for g in machine.guards_table],
        "actions": [{"name": a.action_name, "type": a.action_type, "code": a.python_code}
                    for a in machine.actions_table]
    }


@frappe.whitelist()
def list_machines(attached_to: str = None, include_inactive: bool = False) -> list:
    """
    List all state machines, optionally filtered by attached DocType.

    Args:
        attached_to: Filter by attached DocType
        include_inactive: If True, include inactive workflows (default: False)

    Returns:
        list of machine summaries
    """
    # Permission check - user must have read access to State Machine doctype
    if not frappe.has_permission("State Machine", "read"):
        frappe.throw(_("No permission to access State Machines"), frappe.PermissionError)

    # Handle string "true"/"false" from frontend
    if isinstance(include_inactive, str):
        include_inactive = include_inactive.lower() == "true"

    filters = {}
    if not include_inactive:
        filters["is_active"] = 1
    if attached_to:
        filters["attached_doctype"] = attached_to

    machines = frappe.get_all(
        "State Machine",
        filters=filters,
        fields=["machine_id", "title", "version", "attached_doctype", "is_active", "modified"],
        order_by="modified desc"
    )

    return machines


@frappe.whitelist()
def get_next_events(machine_name: str, current_state: str, context: dict = None) -> list:
    """
    Get list of valid events for a given state.

    Args:
        machine_name: State Machine name
        current_state: Current state value
        context: Current context dict

    Returns:
        list of available event names with metadata
    """
    context = context or {}

    if not frappe.db.exists("State Machine", machine_name):
        return []

    machine = frappe.get_doc("State Machine", machine_name)
    config = json.loads(machine.json_config)

    events = []
    state_config = find_state_config(config, current_state)

    if not state_config:
        return []

    # Extract transitions from "on" property
    on_transitions = state_config.get("on", {})
    for event_name, transition in on_transitions.items():
        event_info = {
            "event": event_name,
            "target": None,
            "guards": [],
            "actions": []
        }

        # Handle different transition formats
        if isinstance(transition, str):
            event_info["target"] = transition
        elif isinstance(transition, dict):
            event_info["target"] = transition.get("target")
            if transition.get("guard"):
                event_info["guards"].append(transition["guard"])
            if transition.get("actions"):
                event_info["actions"] = transition["actions"] if isinstance(
                    transition["actions"], list) else [transition["actions"]]
        elif isinstance(transition, list):
            # Multiple possible transitions (conditional) - at least ONE guard must pass
            event_info["is_conditional"] = True
            for t in transition:
                if isinstance(t, dict):
                    if not event_info["target"]:  # Use first target as default
                        event_info["target"] = t.get("target")
                    if t.get("guard"):
                        event_info["guards"].append(t["guard"])

        # Check if guards pass
        if event_info.get("is_conditional") and event_info["guards"]:
            # For conditional transitions, at least ONE guard must pass
            guards_pass = False
            for guard_name in event_info["guards"]:
                if evaluate_guard(machine, guard_name, context, {"type": event_name}):
                    guards_pass = True
                    break
        else:
            # For regular transitions, ALL guards must pass
            guards_pass = True
            for guard_name in event_info["guards"]:
                if not evaluate_guard(machine, guard_name, context, {"type": event_name}):
                    guards_pass = False
                    break

        event_info["enabled"] = guards_pass
        events.append(event_info)

    return events


@frappe.whitelist()
def reset_instance(doctype: str, docname: str) -> dict:
    """
    Reset a workflow instance to initial state.

    Args:
        doctype: Reference DocType
        docname: Reference document name

    Returns:
        dict with reset result
    """
    # Permission check - user must have write access to the document
    if not frappe.has_permission(doctype, "write", docname):
        frappe.throw(_("No permission to modify {0} {1}").format(doctype, docname), frappe.PermissionError)

    instance = get_instance_for_doc(doctype, docname)

    if not instance:
        frappe.throw(_("No workflow instance found for {0} {1}").format(doctype, docname))

    instance_doc = frappe.get_doc("Machine Instance", instance.name)
    return instance_doc.reset()


# ============================================================================
# PARALLEL STATE EXECUTION
# ============================================================================

def execute_parallel_states(instance, parallel_config: dict, context: dict,
                            event: dict, actions: dict, ref_doc) -> dict:
    """
    Execute all parallel regions concurrently and merge contexts.

    In XState, parallel states have multiple child regions that are all active
    simultaneously. This function executes entry actions for all regions and
    tracks their individual states.

    Args:
        instance: Machine Instance document
        parallel_config: The parallel state configuration with 'states' containing regions
        context: Current context
        event: Event that triggered this
        actions: Dict of action functions
        ref_doc: Reference document

    Returns:
        Updated context after executing all region entries
    """
    regions = parallel_config.get("states", {})
    parallel_states = {}

    # Get the parent state path
    parent_path = instance.current_state

    for region_name, region_config in regions.items():
        region_path = f"{parent_path}.{region_name}"

        # Find initial state for this region
        initial_state = region_config.get("initial")
        if not initial_state and region_config.get("states"):
            initial_state = list(region_config["states"].keys())[0]

        if initial_state:
            # Set the initial state for this region
            parallel_states[region_path] = initial_state

            # Execute entry actions for the initial state
            initial_config = region_config.get("states", {}).get(initial_state, {})
            if initial_config.get("entry"):
                context = execute_actions(initial_config["entry"], actions, context, event)

            # Schedule any delayed transitions for this region
            schedule_delayed_transitions(
                instance, initial_config,
                f"{region_path}.{initial_state}", context
            )

    # Update instance with parallel states
    instance.set_parallel_states(parallel_states)

    return context


def execute_parallel_transition(instance, event: str, input_data: dict,
                                 actions: dict, guards: dict, ref_doc) -> tuple[bool, dict]:
    """
    Execute a transition within a parallel state.

    When in a parallel state, events may affect one or more regions.
    This function checks each region for valid transitions.

    Args:
        instance: Machine Instance document
        event: Event name
        input_data: Event payload
        actions: Dict of action functions
        guards: Dict of guard functions
        ref_doc: Reference document

    Returns:
        Tuple of (transition_occurred, updated_context)
    """
    machine_doc = frappe.get_doc("State Machine", instance.machine)
    config = json.loads(machine_doc.json_config)
    context = json.loads(instance.context or "{}")
    parallel_states = instance.get_parallel_states()

    transition_occurred = False
    parent_path = instance.current_state

    # Get the parent parallel state config
    parent_config = find_state_config(config, parent_path)
    if not parent_config or parent_config.get("type") != "parallel":
        return False, context

    regions = parent_config.get("states", {})

    for region_name, region_config in regions.items():
        region_path = f"{parent_path}.{region_name}"
        current_region_state = parallel_states.get(region_path)

        if not current_region_state:
            continue

        # Find the current state config within this region
        state_config = region_config.get("states", {}).get(current_region_state, {})
        transition = state_config.get("on", {}).get(event)

        if not transition:
            continue

        # Resolve the transition
        target_state, transition_actions = resolve_transition(
            transition, context, input_data, guards
        )

        if target_state:
            transition_occurred = True

            # Execute exit actions
            if state_config.get("exit"):
                context = execute_actions(state_config["exit"], actions, context, input_data)

            # Execute transition actions
            if transition_actions:
                context = execute_actions(transition_actions, actions, context, input_data)

            # Update region state
            parallel_states[region_path] = target_state

            # Execute entry actions for new state
            new_state_config = region_config.get("states", {}).get(target_state, {})
            if new_state_config.get("entry"):
                context = execute_actions(new_state_config["entry"], actions, context, input_data)

            # Schedule delayed transitions
            schedule_delayed_transitions(
                instance, new_state_config,
                f"{region_path}.{target_state}", context
            )

    instance.set_parallel_states(parallel_states)
    return transition_occurred, context


def check_parallel_completion(instance, parallel_config: dict) -> bool:
    """
    Check if all parallel regions have reached final states.

    In XState, a parallel state completes when all regions are in final states.

    Args:
        instance: Machine Instance document
        parallel_config: The parallel state configuration

    Returns:
        True if all regions are complete
    """
    parallel_states = instance.get_parallel_states()
    parent_path = instance.current_state
    regions = parallel_config.get("states", {})

    for region_name, region_config in regions.items():
        region_path = f"{parent_path}.{region_name}"
        current_state = parallel_states.get(region_path)

        if not current_state:
            return False

        state_config = region_config.get("states", {}).get(current_state, {})
        if state_config.get("type") != "final":
            return False

    return True


# ============================================================================
# HISTORY STATE HANDLING
# ============================================================================

def handle_history_state(instance, history_config: dict, parent_path: str,
                         context: dict, actions: dict, event: dict) -> tuple[str, dict]:
    """
    Resolve a history state to the actual target state.

    XState history states remember the last active child state. When transitioning
    to a history state, we restore the previous state (or use the default).

    Args:
        instance: Machine Instance document
        history_config: The history state configuration
        parent_path: Path to the parent compound state
        context: Current context
        actions: Dict of action functions
        event: Event data

    Returns:
        Tuple of (resolved_target_state, updated_context)
    """
    # Determine if this is deep or shallow history
    history_type = history_config.get("history", "shallow")
    is_deep = history_type == "deep"

    # Get the recorded history
    recorded_state = instance.get_history(parent_path, deep=is_deep)

    if recorded_state:
        target = recorded_state
    else:
        # Use default target if no history recorded
        target = history_config.get("target")

    if not target:
        # If no target and no history, use parent's initial state
        machine_doc = frappe.get_doc("State Machine", instance.machine)
        config = json.loads(machine_doc.json_config)
        parent_config = find_state_config(config, parent_path)
        if parent_config:
            target = parent_config.get("initial")

    return target, context


def record_state_history(instance, from_state: str, to_state: str, config: dict):
    """
    Record history when leaving a compound state.

    Called during transitions to track which child state was active.

    Args:
        instance: Machine Instance document
        from_state: State being left
        to_state: State being entered
        config: Full machine config
    """
    # Check if from_state is a child of a compound state
    if "." in from_state:
        parts = from_state.rsplit(".", 1)
        parent_path = parts[0]
        child_state = parts[1]

        # Record shallow history (just the immediate child)
        instance.record_history(parent_path, child_state, deep=False)

        # Record deep history (full nested path relative to parent)
        parallel_states = instance.get_parallel_states()
        if parallel_states:
            # Include parallel state info for deep history
            deep_state = {
                "state": child_state,
                "parallel": {k: v for k, v in parallel_states.items()
                            if k.startswith(from_state)}
            }
            instance.record_history(parent_path, json.dumps(deep_state), deep=True)
        else:
            instance.record_history(parent_path, from_state, deep=True)


# ============================================================================
# INVOKE SERVICE EXECUTION
# ============================================================================

def invoke_service(instance, invoke_config: dict | list, context: dict,
                   event: dict, ref_doc) -> dict:
    """
    Execute invoke services (Python functions, HTTP calls, background jobs).

    XState invoke allows spawning services that can send events back to the machine.
    Supports onDone and onError callbacks.

    Args:
        instance: Machine Instance document
        invoke_config: Invoke configuration (can be a list of invokes)
        context: Current context
        event: Event that triggered the invoke
        ref_doc: Reference document

    Returns:
        Updated context
    """
    if isinstance(invoke_config, dict):
        invoke_config = [invoke_config]

    for invoke in invoke_config:
        service_id = invoke.get("id", f"service_{frappe.generate_hash()[:8]}")
        src = invoke.get("src")

        if not src:
            continue

        # Track the service
        instance.add_active_service(service_id, {
            "src": src,
            "onDone": invoke.get("onDone"),
            "onError": invoke.get("onError"),
            "input": invoke.get("input")
        })

        # Execute based on service type
        try:
            if src.startswith("http://") or src.startswith("https://"):
                # HTTP service - execute in background
                enqueue(
                    _execute_http_service,
                    queue="default",
                    timeout=300,
                    instance_name=instance.name,
                    service_id=service_id,
                    url=src,
                    method=invoke.get("method", "POST"),
                    headers=invoke.get("headers", {}),
                    body=invoke.get("input") or context
                )
            else:
                # Python function service
                service_doc = frappe.db.get_value(
                    "XSM Service",
                    {"service_name": src},
                    ["python_path", "is_async"],
                    as_dict=True
                )

                if service_doc:
                    if service_doc.is_async:
                        enqueue(
                            _execute_python_service,
                            queue="default",
                            timeout=300,
                            instance_name=instance.name,
                            service_id=service_id,
                            python_path=service_doc.python_path,
                            context=context,
                            event=event,
                            ref_doctype=ref_doc.doctype,
                            ref_name=ref_doc.name
                        )
                    else:
                        result = _execute_python_service_sync(
                            service_doc.python_path, context, event, ref_doc
                        )
                        _handle_service_completion(
                            instance.name, service_id, result, success=True
                        )

        except Exception as e:
            frappe.log_error(f"Invoke service error: {e}", "XState Invoke Error")
            _handle_service_completion(
                instance.name, service_id, {"error": str(e)}, success=False
            )

    return context


def _execute_http_service(instance_name: str, service_id: str, url: str,
                          method: str, headers: dict, body: dict):
    """Background job to execute HTTP service"""
    import requests

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=body,
            timeout=60
        )
        response.raise_for_status()
        result = response.json() if response.text else {}
        _handle_service_completion(instance_name, service_id, result, success=True)
    except Exception as e:
        _handle_service_completion(instance_name, service_id, {"error": str(e)}, success=False)


def _execute_python_service(instance_name: str, service_id: str, python_path: str,
                            context: dict, event: dict, ref_doctype: str, ref_name: str):
    """Background job to execute Python service"""
    try:
        ref_doc = frappe.get_doc(ref_doctype, ref_name)
        result = _execute_python_service_sync(python_path, context, event, ref_doc)
        _handle_service_completion(instance_name, service_id, result, success=True)
    except Exception as e:
        _handle_service_completion(instance_name, service_id, {"error": str(e)}, success=False)


def _execute_python_service_sync(python_path: str, context: dict,
                                  event: dict, ref_doc) -> dict:
    """Execute a Python service synchronously"""
    module_path, func_name = python_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[func_name])
    func = getattr(module, func_name)
    return func(context=context, event=event, doc=ref_doc) or {}


def _handle_service_completion(instance_name: str, service_id: str,
                                result: dict, success: bool):
    """Handle service completion - trigger onDone or onError"""
    instance = frappe.get_doc("Machine Instance", instance_name)
    services = instance.get_active_services()
    service_config = next((s for s in services if s.get("id") == service_id), None)

    if not service_config:
        return

    # Remove from active services
    instance.remove_active_service(service_id)
    instance.save(ignore_permissions=True)

    # Get callback config
    config = service_config.get("config", {})
    callback = config.get("onDone") if success else config.get("onError")

    if callback:
        # Trigger callback event
        event_type = callback if isinstance(callback, str) else callback.get("target")
        if event_type:
            from xstate_workflow.workflow_engine import trigger_event_sync
            trigger_event_sync(
                instance.reference_doctype,
                instance.reference_name,
                f"xstate.done.invoke.{service_id}" if success else f"xstate.error.invoke.{service_id}",
                {"output": result}
            )

    frappe.db.commit()


# ============================================================================
# DELAYED TRANSITION SCHEDULING
# ============================================================================

def schedule_delayed_transitions(instance, state_config: dict,
                                  state_path: str, context: dict):
    """
    Schedule delayed transitions defined in state's "after" property.

    XState "after" defines delayed transitions that fire after a timeout.

    Args:
        instance: Machine Instance document
        state_config: State configuration with "after" property
        state_path: Full path to the state
        context: Current context
    """
    after_config = state_config.get("after")
    if not after_config:
        return

    now = frappe.utils.now_datetime()

    for delay_spec, transition in after_config.items():
        # Parse delay (can be number or string with unit)
        delay_ms = parse_delay(delay_spec, context)

        if delay_ms <= 0:
            continue

        # Calculate fire time
        fire_at = now + frappe.utils.datetime.timedelta(milliseconds=delay_ms)

        # Get target from transition
        target = transition if isinstance(transition, str) else transition.get("target")

        if target:
            delay_key = f"{state_path}:{delay_spec}"
            instance.add_delayed_transition(
                delay_key=delay_key,
                target_state=target,
                fire_at=fire_at,
                event_data={
                    "delay": delay_ms,
                    "transition": transition if isinstance(transition, dict) else {"target": transition}
                }
            )


def parse_delay(delay_spec: str | int, context: dict) -> int:
    """
    Parse a delay specification to milliseconds.

    Supports:
    - Integer (milliseconds): 5000
    - String with units: "5s", "2m", "1h", "1d"
    - Context reference: "delays.approval" (looks up in context)

    Args:
        delay_spec: Delay specification
        context: Context for variable resolution

    Returns:
        Delay in milliseconds
    """
    if isinstance(delay_spec, int):
        return delay_spec

    delay_str = str(delay_spec)

    # Check if it's a context reference
    if delay_str.startswith("delays."):
        key = delay_str[7:]  # Remove "delays." prefix
        delays = context.get("delays", {})
        return delays.get(key, 0)

    # Parse string with units
    import re
    match = re.match(r"^(\d+)(ms|s|m|h|d)?$", delay_str)
    if match:
        value = int(match.group(1))
        unit = match.group(2) or "ms"

        multipliers = {
            "ms": 1,
            "s": 1000,
            "m": 60000,
            "h": 3600000,
            "d": 86400000
        }
        return value * multipliers.get(unit, 1)

    # Try parsing as plain integer
    try:
        return int(delay_spec)
    except (ValueError, TypeError):
        return 0


def cancel_state_delayed_transitions(instance, state_path: str):
    """
    Cancel all delayed transitions for a state when leaving it.

    Args:
        instance: Machine Instance document
        state_path: Path to the state being exited
    """
    instance.clear_delayed_transitions(state_path)


# ============================================================================
# CORE ENGINE FUNCTIONS
# ============================================================================

def get_or_create_instance(doctype: str, docname: str) -> str:
    """
    Find or create Machine Instance for a document.

    Args:
        doctype: Reference DocType
        docname: Reference document name

    Returns:
        Instance name
    """
    existing = frappe.db.get_value(
        "Machine Instance",
        {"reference_doctype": doctype, "reference_name": docname},
        "name"
    )

    if existing:
        return existing

    # Find active state machine for this doctype
    state_machine = frappe.db.get_value(
        "State Machine",
        {"attached_doctype": doctype, "is_active": 1},
        "name"
    )

    if not state_machine:
        frappe.throw(_("No active State Machine attached to {0}").format(doctype))

    # Get tenant from reference document
    tenant = None
    try:
        from xstate_workflow.tenant import get_tenant_from_doc
        ref_doc = frappe.get_doc(doctype, docname)
        tenant = get_tenant_from_doc(ref_doc)
    except Exception:
        pass

    # Create new instance
    instance = frappe.get_doc({
        "doctype": "Machine Instance",
        "reference_doctype": doctype,
        "reference_name": docname,
        "machine": state_machine,
        "tenant": tenant
    }).insert(ignore_permissions=True)

    frappe.db.commit()

    # Execute entry actions for initial state
    try:
        machine_doc = frappe.get_doc("State Machine", state_machine)
        config = json.loads(machine_doc.json_config)
        initial_state = config.get("initial", "")

        if initial_state:
            state_config = find_state_config(config, initial_state)
            if state_config:
                ref_doc = frappe.get_doc(doctype, docname)
                # Execute entry actions
                entry_actions = state_config.get("entry", [])
                if isinstance(entry_actions, str):
                    entry_actions = [entry_actions]

                actions = build_actions(machine_doc, ref_doc, instance)
                for action_name in entry_actions:
                    if action_name in actions:
                        try:
                            actions[action_name]({"instance": instance, "doc": ref_doc, "state": initial_state})
                        except Exception as e:
                            frappe.log_error(f"Entry action {action_name} failed: {e}")

                # Also handle domain node entry (create approval tasks etc)
                handle_domain_node_entry(instance, initial_state, state_config, ref_doc)
    except Exception as e:
        frappe.log_error(f"Failed to execute initial state entry actions: {e}")

    return instance.name


def handle_domain_node_entry(instance, state_name: str, state_config: dict, ref_doc):
    """Handle entry into a domain node state (create approval tasks, etc)."""
    meta = state_config.get("meta", {})
    domain_node = meta.get("domain_node", {})

    if not domain_node:
        return

    node_type = domain_node.get("type")

    # Handle "submit" node type - auto-submit document when workflow reaches this state
    if node_type == "submit":
        if ref_doc.meta.is_submittable and ref_doc.docstatus == 0:
            try:
                # Set flag to bypass our own validation hook
                ref_doc.flags.ignore_workflow_submit_check = True
                ref_doc.submit()
                frappe.msgprint(
                    _("Document submitted by workflow approval"),
                    indicator="green",
                    alert=True
                )
            except Exception as e:
                frappe.log_error(f"Workflow auto-submit failed for {ref_doc.doctype} {ref_doc.name}: {e}")
                frappe.throw(
                    _("Failed to submit document: {0}").format(str(e)),
                    title=_("Auto-Submit Failed")
                )

    # NOTE: Legacy auto-submit on "end" node with final_status="Approved" has been removed.
    # Use node_type="submit" for auto-submit behavior.
    # With node_type="end" and approved state, manual submit is allowed via validate_workflow_state_for_submit.

    if node_type == "approval":
        # Create approval task
        try:
            from xstate_workflow.approval.task_manager import create_approval_task
            from xstate_workflow.resolvers import resolve_assignment

            # Get resolver config and resolve assignees
            resolver_config = domain_node.get("resolver", {})
            assignees = resolve_assignment(ref_doc, resolver_config)

            if not assignees:
                frappe.log_error(f"No assignees resolved for approval node {state_name}")
                return

            # Get other config from domain_node
            node_label = domain_node.get("label", state_name)
            available_actions = domain_node.get("available_actions", ["Approve", "Reject"])
            sla_hours = domain_node.get("sla_hours")
            priority = domain_node.get("priority", "Medium")

            # Get tenant from instance
            tenant = instance.tenant if hasattr(instance, "tenant") else None

            # Get assigned_role for role-based assignments
            assigned_role = None
            if resolver_config.get("type") == "role":
                assigned_role = resolver_config.get("role")

            create_approval_task(
                workflow_instance=instance.name,
                node_id=state_name,
                node_label=node_label,
                assignees=assignees,
                available_actions=available_actions,
                sla_hours=sla_hours,
                priority=priority,
                tenant=tenant,
                assigned_role=assigned_role
            )

            # Show appropriate message based on assignment type
            if assigned_role:
                frappe.msgprint(
                    _("Approval task created and assigned to role: {0}").format(assigned_role),
                    indicator="blue",
                    alert=True
                )
            else:
                frappe.msgprint(
                    _("Approval task created and assigned to {0}").format(assignees[0]),
                    indicator="blue",
                    alert=True
                )
        except ImportError as e:
            frappe.log_error(f"Import error creating approval task: {e}")
        except Exception as e:
            frappe.log_error(f"Failed to create approval task: {e}")


def get_instance_for_doc(doctype: str, docname: str):
    """
    Get Machine Instance for a document if it exists.

    Args:
        doctype: Reference DocType
        docname: Reference document name

    Returns:
        Machine Instance doc or None
    """
    instance_name = frappe.db.get_value(
        "Machine Instance",
        {"reference_doctype": doctype, "reference_name": docname},
        "name"
    )

    if instance_name:
        return frappe.get_doc("Machine Instance", instance_name)

    return None


def execute_transition(instance_name: str, event: str, input_data: dict = None) -> dict:
    """
    Core transition execution with XState interpreter.

    Handles:
    - Simple atomic state transitions
    - Parallel state transitions (within regions)
    - History state resolution
    - Invoke service execution
    - Delayed transition scheduling

    Args:
        instance_name: Machine Instance name
        event: Event to send
        input_data: Event payload data

    Returns:
        dict with transition result
    """
    input_data = input_data or {}

    try:
        instance = frappe.get_doc("Machine Instance", instance_name)
        machine_doc = frappe.get_doc("State Machine", instance.machine)

        # Get reference document - use ignore_permissions since authorization
        # is handled at the API layer via approval task assignment
        ref_doc = frappe.get_doc(instance.reference_doctype, instance.reference_name, ignore_permissions=True)

        # Load config
        config = json.loads(machine_doc.json_config)

        # Get current state and context
        current_state = instance.current_state
        context = json.loads(instance.context or "{}")

        # Build guards and actions from machine definition
        guards = build_guards(machine_doc, ref_doc)
        actions = build_actions(machine_doc, ref_doc, instance)

        # Find the current state config
        state_config = find_state_config(config, current_state)

        if not state_config:
            return {
                "success": False,
                "error": _("State '{0}' not found in machine config").format(current_state)
            }

        # Check if current state is a parallel state
        if state_config.get("type") == "parallel":
            # Try to execute transition within parallel regions
            transition_occurred, context = execute_parallel_transition(
                instance, event, input_data, actions, guards, ref_doc
            )

            if transition_occurred:
                instance.context = json.dumps(context)
                instance.last_event = event
                instance.last_transition_at = frappe.utils.now()

                # Check if all regions are complete
                if check_parallel_completion(instance, state_config):
                    # Handle onDone for parallel state
                    if state_config.get("onDone"):
                        on_done = state_config["onDone"]
                        done_target = on_done if isinstance(on_done, str) else on_done.get("target")
                        if done_target:
                            # Transition out of parallel state
                            return execute_transition(instance_name, "xstate.done.state", input_data)

                instance.save(ignore_permissions=True)
                frappe.db.commit()

                return {
                    "success": True,
                    "previous_state": current_state,
                    "new_state": current_state,
                    "context": context,
                    "is_final": False,
                    "parallel_transition": True
                }

        # Regular transition handling
        transition = state_config.get("on", {}).get(event)

        # Check for "always" transitions if no event-based transition
        if not transition and event == "xstate.always":
            always_transitions = state_config.get("always", [])
            if always_transitions:
                transition = always_transitions

        if not transition:
            return {
                "success": False,
                "error": _("Event '{0}' not valid in state '{1}'").format(event, current_state)
            }

        # Resolve transition (handle guards, conditional transitions)
        target_state, transition_actions = resolve_transition(
            transition, context, input_data, guards
        )

        if not target_state:
            return {
                "success": False,
                "error": _("Transition blocked by guard")
            }

        # Check if target is a history state
        target_state_config = find_state_config(config, target_state)
        if target_state_config and target_state_config.get("type") == "history":
            # Resolve history to actual target
            parent_path = target_state.rsplit(".", 1)[0] if "." in target_state else ""
            target_state, context = handle_history_state(
                instance, target_state_config, parent_path, context, actions, input_data
            )
            target_state_config = find_state_config(config, target_state)

        # Record history before leaving current state
        record_state_history(instance, current_state, target_state, config)

        # Cancel any delayed transitions from current state
        cancel_state_delayed_transitions(instance, current_state)

        # Clear active services when leaving state
        instance.clear_active_services()

        # Execute exit actions for current state
        if state_config.get("exit"):
            context = execute_actions(state_config["exit"], actions, context, input_data)

        # Execute transition actions
        if transition_actions:
            context = execute_actions(transition_actions, actions, context, input_data)

        # Execute entry actions for target state
        if target_state_config and target_state_config.get("entry"):
            context = execute_actions(target_state_config["entry"], actions, context, input_data)

        # Check if target is a parallel state - initialize regions
        if target_state_config and target_state_config.get("type") == "parallel":
            old_state = instance.current_state
            instance.current_state = target_state
            context = execute_parallel_states(
                instance, target_state_config, context, input_data, actions, ref_doc
            )
        else:
            old_state = instance.current_state
            instance.current_state = target_state

            # Clear parallel states when entering non-parallel state
            instance.clear_parallel_states()

        # Schedule delayed transitions for new state
        if target_state_config:
            schedule_delayed_transitions(instance, target_state_config, target_state, context)

        # Execute invoke services
        if target_state_config and target_state_config.get("invoke"):
            context = invoke_service(
                instance, target_state_config["invoke"], context, input_data, ref_doc
            )

        # Handle domain node entry (create approval tasks, etc)
        if target_state_config:
            handle_domain_node_entry(instance, target_state, target_state_config, ref_doc)

        # Check if final state
        is_final = target_state_config and target_state_config.get("type") == "final"

        # Update instance
        instance.context = json.dumps(context)
        instance.last_event = event
        instance.last_transition_at = frappe.utils.now()
        instance.status = "final" if is_final else "active"

        # Reload to get latest version before save to avoid conflicts
        instance.reload()
        instance.current_state = target_state
        instance.context = json.dumps(context)
        instance.last_event = event
        instance.last_transition_at = frappe.utils.now()
        instance.status = "final" if is_final else "active"

        # Log transition AFTER reload so it's not cleared
        instance.log_transition(event, old_state, target_state, success=True)
        instance.save(ignore_permissions=True)

        # Post-transition hooks
        post_transition_actions(instance, event, old_state, target_state, ref_doc)

        # Check for "always" transitions (eventless auto-transitions)
        if target_state_config and target_state_config.get("always"):
            frappe.db.commit()
            # Execute always transition after saving
            return execute_transition(instance_name, "xstate.always", input_data)

        frappe.db.commit()

        return {
            "success": True,
            "previous_state": old_state,
            "new_state": target_state,
            "context": context,
            "is_final": is_final
        }

    except Exception as e:
        frappe.log_error(traceback.format_exc(), "XState Transition Error")

        # Update error count
        try:
            instance = frappe.get_doc("Machine Instance", instance_name)
            instance.log_transition(event, instance.current_state, None, success=False, error=str(e))
            instance.status = "error"
            instance.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            pass

        return {
            "success": False,
            "error": str(e)
        }


def find_state_config(config: dict, state_path: str) -> dict | None:
    """
    Find state configuration, supporting nested/hierarchical states.

    Args:
        config: Full machine config
        state_path: State path (e.g., "idle" or "active.pending")

    Returns:
        State configuration dict or None
    """
    parts = state_path.split(".")
    current = config

    for part in parts:
        states = current.get("states", {})
        if part in states:
            current = states[part]
        else:
            return None

    return current


def resolve_transition(transition: Any, context: dict, event_data: dict,
                       guards: dict) -> tuple[str | None, list]:
    """
    Resolve a transition definition to target state and actions.

    Args:
        transition: Transition config (string, dict, or list)
        context: Current context
        event_data: Event payload
        guards: Guard functions dict

    Returns:
        Tuple of (target_state, actions_list)
    """
    # Simple string target
    if isinstance(transition, str):
        return transition, []

    # Single transition object
    if isinstance(transition, dict):
        guard_name = transition.get("guard") or transition.get("cond")
        if guard_name:
            guard_fn = guards.get(guard_name)
            if guard_fn and not guard_fn(context, event_data):
                return None, []

        target = transition.get("target")
        actions = transition.get("actions", [])
        if isinstance(actions, str):
            actions = [actions]

        return target, actions

    # Conditional transitions (list)
    if isinstance(transition, list):
        for t in transition:
            if isinstance(t, dict):
                guard_name = t.get("guard") or t.get("cond")
                if guard_name:
                    guard_fn = guards.get(guard_name)
                    if not guard_fn or not guard_fn(context, event_data):
                        continue

                target = t.get("target")
                actions = t.get("actions", [])
                if isinstance(actions, str):
                    actions = [actions]

                return target, actions
            elif isinstance(t, str):
                return t, []

    return None, []


def build_guards(machine_doc, ref_doc) -> dict:
    """
    Build guard functions from machine definition.

    Supports three types of guards:
    1. Logic module guards (Python functions)
    2. Guards table (inline Python code)
    3. Visual guards from workflow_builder_config (no code required!)

    Args:
        machine_doc: State Machine document
        ref_doc: Reference document

    Returns:
        Dict of guard_name -> function
    """
    guards = {}

    # Load from logic module
    if machine_doc.logic_module:
        try:
            module = __import__(machine_doc.logic_module, fromlist=["guards"])
            if hasattr(module, "guards"):
                guards.update(module.guards)
        except ImportError:
            frappe.log_error(f"Could not import logic module: {machine_doc.logic_module}")

    # Load from guards_table (inline Python code)
    for guard in machine_doc.guards_table:
        if guard.python_code:
            guards[guard.guard_name] = create_guard_function(guard.python_code, ref_doc)

    # Load visual guards from workflow_builder_config (NO CODE REQUIRED!)
    if machine_doc.workflow_builder_config:
        try:
            builder_config = json.loads(machine_doc.workflow_builder_config)
            visual_guards = extract_visual_guards(builder_config, ref_doc)
            # Visual guards take precedence over code guards for same name
            guards.update(visual_guards)
        except (json.JSONDecodeError, Exception) as e:
            frappe.log_error(f"Could not parse workflow_builder_config: {e}")

    # Add default guards
    guards["always"] = lambda ctx, evt: True
    guards["never"] = lambda ctx, evt: False

    return guards


def extract_visual_guards(builder_config: dict, ref_doc) -> dict:
    """
    Extract guard functions from visual builder configuration.

    This enables NO-CODE guard creation via the visual editor!
    Supports:
    - Simple guards: field operator value (e.g., grand_total > 100000)
    - Compound guards: AND/OR combinations of simple guards
    - Role guards: check if user has specific roles

    Args:
        builder_config: Visual builder configuration (nodes, edges, etc.)
        ref_doc: Reference document

    Returns:
        Dict of guard_name -> function
    """
    guards = {}
    edges = builder_config.get("edges", [])

    for edge in edges:
        edge_data = edge.get("data", {})
        guard_config = edge_data.get("guard")

        if not guard_config:
            continue

        guard_type = guard_config.get("type")
        guard_name = guard_config.get("name")

        if guard_type == "simple":
            # Simple field comparison: field operator value
            guards[guard_name or f"guard_{edge['id']}"] = create_simple_guard(guard_config, ref_doc)

        elif guard_type == "compound":
            # Compound guard: AND/OR of multiple conditions
            guards[guard_name or f"guard_{edge['id']}"] = create_compound_guard(guard_config, ref_doc)

        elif guard_type == "role":
            # Role-based guard: check user roles
            guards[guard_name or f"guard_{edge['id']}"] = create_role_guard(guard_config)

        # Note: "python" type guards are handled by the logic module

    return guards


def create_simple_guard(guard_config: dict, ref_doc):
    """
    Create a guard function from a simple visual guard config.

    Config format:
    {
        "type": "simple",
        "field": "grand_total",
        "operator": ">",
        "value": 100000
    }

    Supported operators:
    - Comparison: ==, !=, >, <, >=, <=
    - String: contains, not_contains, starts_with, ends_with
    - List: in, not_in
    - Null: is_set, is_not_set

    Args:
        guard_config: Guard configuration from visual builder
        ref_doc: Reference document

    Returns:
        Guard function
    """
    field = guard_config.get("field", "")
    operator = guard_config.get("operator", "==")
    value = guard_config.get("value")

    def guard_fn(context: dict, event: dict) -> bool:
        # Get field value from context or document
        field_value = get_field_value(field, context, ref_doc)

        try:
            return evaluate_operator(field_value, operator, value)
        except Exception as e:
            frappe.log_error(f"Simple guard error: {field} {operator} {value}: {e}")
            return False

    return guard_fn


def create_compound_guard(guard_config: dict, ref_doc):
    """
    Create a guard function from a compound visual guard config.

    Config format:
    {
        "type": "compound",
        "operator": "and",  // or "or"
        "conditions": [
            {"field": "grand_total", "operator": ">", "value": 100000},
            {"field": "status", "operator": "==", "value": "Draft"}
        ]
    }

    Args:
        guard_config: Guard configuration from visual builder
        ref_doc: Reference document

    Returns:
        Guard function
    """
    logic_operator = guard_config.get("operator", "and").lower()
    conditions = guard_config.get("conditions", [])

    # Create guard functions for each condition
    condition_guards = []
    for cond in conditions:
        if cond.get("type") == "compound":
            condition_guards.append(create_compound_guard(cond, ref_doc))
        else:
            condition_guards.append(create_simple_guard(cond, ref_doc))

    def guard_fn(context: dict, event: dict) -> bool:
        if logic_operator == "and":
            return all(g(context, event) for g in condition_guards)
        elif logic_operator == "or":
            return any(g(context, event) for g in condition_guards)
        else:
            return False

    return guard_fn


def create_role_guard(guard_config: dict):
    """
    Create a role-based guard function.

    Config format:
    {
        "type": "role",
        "roles": ["Sales Manager", "System Manager"],
        "require_all": false  // true = AND, false = OR
    }

    Args:
        guard_config: Guard configuration from visual builder

    Returns:
        Guard function
    """
    required_roles = guard_config.get("roles", [])
    require_all = guard_config.get("require_all", False)

    def guard_fn(context: dict, event: dict) -> bool:
        user = frappe.session.user
        user_roles = set(frappe.get_roles(user))

        if require_all:
            return all(role in user_roles for role in required_roles)
        else:
            return any(role in user_roles for role in required_roles)

    return guard_fn


def get_field_value(field_path: str, context: dict, ref_doc):
    """
    Get a field value from context or document.

    Supports:
    - Simple fields: "grand_total"
    - Nested fields: "customer.territory"
    - Context fields: "context.workflow_status"

    Args:
        field_path: Field path (dot notation for nested)
        context: Current context
        ref_doc: Reference document

    Returns:
        Field value
    """
    parts = field_path.split(".")

    # Try context first
    if parts[0] == "context" or parts[0] in context:
        value = context
        start_idx = 1 if parts[0] == "context" else 0
        for part in parts[start_idx:]:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
        return value

    # Try document
    if ref_doc:
        value = ref_doc
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    # Try context directly
    return context.get(field_path)


def evaluate_operator(field_value, operator: str, compare_value) -> bool:
    """
    Evaluate a comparison operator.

    Args:
        field_value: Value from field
        operator: Comparison operator
        compare_value: Value to compare against

    Returns:
        Comparison result
    """
    # Handle None/null checks first
    if operator == "is_set":
        return field_value is not None and field_value != ""
    if operator == "is_not_set":
        return field_value is None or field_value == ""

    # Type coercion for numeric comparisons
    if operator in (">", "<", ">=", "<="):
        try:
            field_value = float(field_value) if field_value else 0
            compare_value = float(compare_value) if compare_value else 0
        except (ValueError, TypeError):
            pass

    # Comparison operators
    if operator == "==" or operator == "equals":
        return field_value == compare_value
    if operator == "!=" or operator == "not_equals":
        return field_value != compare_value
    if operator == ">":
        return field_value > compare_value
    if operator == "<":
        return field_value < compare_value
    if operator == ">=":
        return field_value >= compare_value
    if operator == "<=":
        return field_value <= compare_value

    # String operators
    str_field = str(field_value) if field_value else ""
    str_compare = str(compare_value) if compare_value else ""

    if operator == "contains":
        return str_compare.lower() in str_field.lower()
    if operator == "not_contains":
        return str_compare.lower() not in str_field.lower()
    if operator == "starts_with":
        return str_field.lower().startswith(str_compare.lower())
    if operator == "ends_with":
        return str_field.lower().endswith(str_compare.lower())

    # List operators
    if operator == "in":
        if isinstance(compare_value, list):
            return field_value in compare_value
        return str(field_value) in str(compare_value).split(",")
    if operator == "not_in":
        if isinstance(compare_value, list):
            return field_value not in compare_value
        return str(field_value) not in str(compare_value).split(",")

    return False


def create_guard_function(code: str, ref_doc):
    """
    Create a guard function from Python code string.

    Args:
        code: Python code that returns True/False
        ref_doc: Reference document

    Returns:
        Callable guard function
    """
    def guard_fn(context: dict, event: dict) -> bool:
        local_vars = {
            "context": context,
            "event": event,
            "doc": ref_doc,
            "frappe": frappe,
            "True": True,
            "False": False
        }
        try:
            # Execute as expression or statements
            if "\n" not in code and not code.strip().startswith("return"):
                return eval(code, {"__builtins__": {}}, local_vars)
            else:
                exec(code, {"__builtins__": {"frappe": frappe}}, local_vars)
                return local_vars.get("result", False)
        except Exception as e:
            frappe.log_error(f"Guard execution error: {e}\nCode: {code}")
            return False

    return guard_fn


def build_actions(machine_doc, ref_doc, instance) -> dict:
    """
    Build action functions from machine definition.

    Args:
        machine_doc: State Machine document
        ref_doc: Reference document
        instance: Machine Instance

    Returns:
        Dict of action_name -> function
    """
    actions = {}

    # Load from logic module
    if machine_doc.logic_module:
        try:
            module = __import__(machine_doc.logic_module, fromlist=["actions"])
            if hasattr(module, "actions"):
                actions.update(module.actions)
        except ImportError:
            pass

    # Load from actions_table
    for action in machine_doc.actions_table:
        if action.python_code:
            actions[action.action_name] = create_action_function(
                action.python_code, ref_doc, instance, action.is_async
            )

    # Add domain node actions (approval, auto-action, etc.)
    try:
        from xstate_workflow.domain_nodes import get_domain_node_actions
        actions.update(get_domain_node_actions(machine_doc, ref_doc, instance))
    except ImportError:
        pass

    # Add default actions
    actions["log"] = lambda ctx, evt: frappe.log_error(
        f"XState Log: {evt}", "XState Action"
    )

    return actions


def create_action_function(code: str, ref_doc, instance, is_async: bool = False):
    """
    Create an action function from Python code string.

    Args:
        code: Python code
        ref_doc: Reference document
        instance: Machine Instance
        is_async: Whether to run in background

    Returns:
        Callable action function
    """
    def action_fn(context: dict, event: dict) -> dict:
        local_vars = {
            "context": context.copy(),
            "event": event,
            "doc": ref_doc,
            "instance": instance,
            "frappe": frappe
        }

        try:
            exec(code, {"__builtins__": {"frappe": frappe, "json": json}}, local_vars)
            return local_vars.get("context", context)
        except Exception as e:
            frappe.log_error(f"Action execution error: {e}\nCode: {code}")
            return context

    if is_async:
        def async_action(context: dict, event: dict) -> dict:
            enqueue(action_fn, context=context, event=event)
            return context
        return async_action

    return action_fn


def execute_actions(action_names: list | str, actions: dict,
                    context: dict, event_data: dict) -> dict:
    """
    Execute a list of actions.

    Args:
        action_names: Action name(s) to execute
        actions: Dict of action functions
        context: Current context
        event_data: Event payload

    Returns:
        Updated context
    """
    if isinstance(action_names, str):
        action_names = [action_names]

    for name in action_names:
        if name in actions:
            result = actions[name](context, event_data)
            if isinstance(result, dict):
                context = result

    return context


def evaluate_guard(machine_doc, guard_name: str, context: dict, event: dict, ref_doc=None) -> bool:
    """
    Evaluate a single guard by name.

    Args:
        machine_doc: State Machine document
        guard_name: Guard name
        context: Current context
        event: Event data
        ref_doc: Reference document (optional, will be loaded from context if not provided)

    Returns:
        Guard result (True/False)
    """
    # Load ref_doc if not provided but context has doctype/docname
    if ref_doc is None:
        doctype = context.get("doctype") or (machine_doc.attached_doctype if machine_doc else None)
        docname = context.get("docname") or context.get("name")
        if doctype and docname:
            try:
                ref_doc = frappe.get_doc(doctype, docname)
            except Exception:
                pass  # Document might not exist

    guards = build_guards(machine_doc, ref_doc)
    guard_fn = guards.get(guard_name)

    if guard_fn:
        return guard_fn(context, event)

    return True


# ============================================================================
# HOOKS AND SCHEDULED TASKS
# ============================================================================

def validate_workflow_state_for_submit(doc, method=None):
    """
    Hook: Validate workflow state before document submission.

    Hybrid logic:
    - If workflow has "submit" node → auto-submit happens there (this hook bypassed via flag)
    - If no "submit" node but workflow is approved → allow manual submit
    - If workflow is pending or rejected → block manual submit

    Called from doc_events before_submit for all DocTypes.

    Args:
        doc: Frappe document
        method: Hook method name
    """
    # Allow if flagged by workflow auto-submit (bypasses this check)
    if getattr(doc.flags, "ignore_workflow_submit_check", False):
        return

    # Skip during installation/migration
    try:
        if not frappe.db.table_exists("State Machine"):
            return
        if not frappe.db.table_exists("Machine Instance"):
            return
    except Exception:
        return

    # Check if this doctype has a workflow attached
    workflow = frappe.db.get_value(
        "State Machine",
        {"attached_doctype": doc.doctype, "is_active": 1},
        "name"
    )

    if not workflow:
        return  # No workflow for this doctype, allow submission

    # Check if there's a machine instance for this document
    instance = frappe.db.get_value(
        "Machine Instance",
        {
            "reference_doctype": doc.doctype,
            "reference_name": doc.name
        },
        ["current_state", "status"],
        as_dict=True
    )

    if not instance:
        # No workflow instance yet - block submission, workflow should be triggered first
        frappe.throw(
            _("Cannot submit {0}: Workflow approval required. Please start the approval process first.").format(
                doc.doctype
            ),
            title=_("Workflow Required")
        )

    current_state = instance.get("current_state", "").lower()
    status = instance.get("status", "")

    # Define states that allow manual submission (when no submit node)
    approved_states = ["approved", "completed", "done", "accepted"]

    # Allow if workflow is final AND in approved state
    if status == "final" and current_state in approved_states:
        return  # Allow manual submit

    # Block if workflow ended in non-approved state (rejected, etc.)
    if status == "final":
        frappe.throw(
            _("Cannot submit {0} {1}: Workflow ended in '{2}' state.").format(
                doc.doctype, doc.name, instance.get("current_state")
            ),
            title=_("Workflow Rejected")
        )

    # Block if workflow is still pending (idle or active)
    frappe.throw(
        _("Cannot submit {0} {1}: Workflow approval pending. Current state: '{2}'").format(
            doc.doctype, doc.name, instance.get("current_state")
        ),
        title=_("Approval Required")
    )

    # If status is final but not in allowed states, block
    if status == "final" and current_state not in allowed_states:
        frappe.throw(
            _("Cannot submit {0} {1}: Workflow ended in state '{2}' which does not allow submission.").format(
                doc.doctype, doc.name, instance.get("current_state")
            ),
            title=_("Workflow State Invalid")
        )


def validate_workflow_state_for_save(doc, method=None):
    """
    Hook: Validate edit permissions based on workflow state and task assignment.

    Controls who can edit documents when workflow is active:
    - None: No restrictions (current behavior)
    - Assigned Only: Only assigned user can edit
    - Role Only: Only users with assigned role can edit
    - Assigned or Role: Either assigned user or users with role can edit

    Called from doc_events before_save for all DocTypes.

    Args:
        doc: Frappe document
        method: Hook method name
    """
    # Allow if flagged to skip check (e.g., system operations)
    if getattr(doc.flags, "ignore_workflow_edit_check", False):
        return

    # Skip for new documents
    if doc.get("__islocal"):
        return

    # Skip during installation/migration
    try:
        if not frappe.db.table_exists("State Machine"):
            return
        if not frappe.db.table_exists("Machine Instance"):
            return
    except Exception:
        return

    # Skip for system doctypes
    skip_doctypes = ["DocType", "Module Def", "Workspace", "Custom Field", "Property Setter"]
    if doc.doctype in skip_doctypes:
        return

    # Check if this doctype has a workflow attached
    machine = frappe.db.get_value(
        "State Machine",
        {"attached_doctype": doc.doctype, "is_active": 1},
        ["name", "edit_restriction_mode"],
        as_dict=True
    )

    if not machine:
        return  # No workflow for this doctype

    edit_mode = machine.get("edit_restriction_mode") or "None"

    # No restrictions if mode is None
    if edit_mode == "None":
        return

    # Check if there's a machine instance for this document
    instance = frappe.db.get_value(
        "Machine Instance",
        {
            "reference_doctype": doc.doctype,
            "reference_name": doc.name
        },
        ["name", "status"],
        as_dict=True
    )

    if not instance:
        return  # No workflow instance, no restrictions

    status = instance.get("status", "")

    # No restrictions for idle or final workflows
    if status in ("idle", "final"):
        return

    # Get current pending approval task
    task = frappe.db.get_value(
        "Approval Task",
        {
            "workflow_instance": instance.name,
            "status": "Pending"
        },
        ["assigned_to", "assigned_role"],
        as_dict=True
    )

    if not task:
        return  # No pending task, no restrictions

    user = frappe.session.user
    allowed = False

    # Check if user is directly assigned
    if edit_mode in ("Assigned Only", "Assigned or Role"):
        if task.assigned_to and task.assigned_to == user:
            allowed = True

    # Check if user has the assigned role
    if edit_mode in ("Role Only", "Assigned or Role"):
        if task.assigned_role and task.assigned_role in frappe.get_roles(user):
            allowed = True

    # System Manager always allowed
    if "System Manager" in frappe.get_roles(user):
        allowed = True

    if not allowed:
        frappe.throw(
            _("You are not authorized to edit this document while workflow is active. Only the assigned approver can edit."),
            frappe.ValidationError,
            title=_("Edit Restricted")
        )


def check_and_trigger(doc, method=None):
    """
    Hook: Auto-trigger workflow events on document updates.
    Called from doc_events for all DocTypes.

    Args:
        doc: Frappe document
        method: Hook method name
    """
    if doc.get("__islocal"):
        return

    # Skip during installation/migration when tables don't exist yet
    try:
        if not frappe.db.table_exists("State Machine"):
            return
    except Exception:
        return

    # Skip for system doctypes that are synced during migration
    skip_doctypes = ["DocType", "Module Def", "Workspace", "Custom Field", "Property Setter"]
    if doc.doctype in skip_doctypes:
        return

    # Check if there's an active workflow for this doctype
    try:
        machine = frappe.db.get_value(
            "State Machine",
            {"attached_doctype": doc.doctype, "is_active": 1},
            "name"
        )
    except Exception:
        # Table might not exist during migration
        return

    if not machine:
        return

    # Check if auto-start is enabled for this machine
    auto_start = frappe.db.get_value("State Machine", machine, "auto_start_on_create")

    # Get or create instance
    instance = get_instance_for_doc(doc.doctype, doc.name)

    if not instance:
        # Create new instance for documents with active workflow
        # This triggers the workflow to start in its initial state
        if method == "after_insert":
            # Skip auto-creation if auto_start_on_create is disabled
            if not auto_start:
                return
            try:
                instance_name = get_or_create_instance(doc.doctype, doc.name)
                instance = frappe.get_doc("Machine Instance", instance_name)
                frappe.msgprint(
                    _("Workflow '{0}' started for this document").format(machine),
                    indicator="blue",
                    alert=True
                )

                # Auto-trigger initial event if configured
                machine_doc = frappe.get_cached_doc("State Machine", machine)
                config = json.loads(machine_doc.json_config)
                initial_event = config.get("meta", {}).get("auto_trigger_initial_event")

                if initial_event:
                    # Trigger the configured initial event to kick off the workflow
                    frappe.db.commit()  # Commit instance creation first
                    try:
                        # Use internal version to avoid permission check during hook execution
                        result = _trigger_event_sync_internal(doc.doctype, doc.name, initial_event, "{}")
                        if result.get("success"):
                            frappe.msgprint(
                                _("Workflow transitioned to: {0}").format(result.get("new_state")),
                                indicator="green",
                                alert=True
                            )
                    except Exception as trigger_err:
                        frappe.log_error(f"Failed to auto-trigger initial event: {trigger_err}")

            except Exception as e:
                frappe.log_error(f"Failed to create workflow instance: {e}")
                return
        else:
            return

    # Auto-trigger based on field changes
    machine_doc = frappe.get_doc("State Machine", machine)
    config = json.loads(machine_doc.json_config)

    # Check for auto-trigger events defined in machine
    auto_triggers = config.get("meta", {}).get("auto_triggers", {})

    for field, event_mapping in auto_triggers.items():
        if hasattr(doc, field) and doc.has_value_changed(field):
            new_value = doc.get(field)
            if new_value in event_mapping:
                event = event_mapping[new_value]
                # Use internal version to avoid permission check during hook execution
                _trigger_event_internal(doc.doctype, doc.name, event, json.dumps({"field": field, "value": new_value}))


def post_transition_actions(instance, event: str, from_state: str, to_state: str, ref_doc):
    """
    Execute post-transition hooks (notifications, webhooks, etc.)

    Args:
        instance: Machine Instance
        event: Triggered event
        from_state: Previous state
        to_state: New state
        ref_doc: Reference document
    """
    machine = frappe.get_doc("State Machine", instance.machine)
    config = json.loads(machine.json_config)

    # Check for notification config
    notifications = config.get("meta", {}).get("notifications", {})

    state_notifications = notifications.get(to_state, [])
    for notification in state_notifications:
        if notification.get("type") == "email":
            send_workflow_email(
                instance, ref_doc,
                notification.get("recipients", []),
                notification.get("subject", f"Workflow: {to_state}"),
                notification.get("message", "")
            )

    # Publish realtime event
    frappe.publish_realtime(
        "workflow_transition",
        {
            "doctype": instance.reference_doctype,
            "docname": instance.reference_name,
            "event": event,
            "from_state": from_state,
            "to_state": to_state
        },
        doctype=instance.reference_doctype,
        docname=instance.reference_name
    )


def send_workflow_email(instance, ref_doc, recipients: list, subject: str, message: str):
    """
    Send workflow notification email.
    """
    try:
        frappe.sendmail(
            recipients=recipients,
            subject=f"[{instance.reference_doctype}] {subject}",
            message=f"""
            <p>{message}</p>
            <p>
                Document: {instance.reference_doctype} - {instance.reference_name}<br>
                Current State: {instance.current_state}
            </p>
            """
        )
    except Exception as e:
        frappe.log_error(f"Workflow email failed: {e}")


def cleanup_old_snapshots():
    """
    Scheduled task: Clean up old/stale instances.
    """
    # Delete final instances older than 30 days
    frappe.db.sql("""
        DELETE FROM `tabMachine Instance`
        WHERE status = 'final'
        AND last_transition_at < DATE_SUB(NOW(), INTERVAL 30 DAY)
    """)

    # Archive error instances
    frappe.db.sql("""
        UPDATE `tabMachine Instance`
        SET status = 'archived'
        WHERE status = 'error'
        AND last_transition_at < DATE_SUB(NOW(), INTERVAL 7 DAY)
    """)

    frappe.db.commit()


def process_delayed_transitions():
    """
    Scheduled task: Process delayed transitions (after/delay in XState).
    Run every minute.

    Uses the new delayed_transitions field on Machine Instance which stores
    scheduled transitions with their fire times.
    """
    # Find active instances with pending delayed transitions
    instances = frappe.get_all(
        "Machine Instance",
        filters={
            "status": "active",
            "delayed_transitions": ["!=", "[]"]
        },
        fields=["name", "reference_doctype", "reference_name", "delayed_transitions"]
    )

    now = frappe.utils.now_datetime()

    for inst in instances:
        try:
            delayed = json.loads(inst.delayed_transitions or "[]")

            for delay in delayed:
                fire_at = frappe.utils.get_datetime(delay.get("fire_at"))

                if fire_at <= now:
                    # Get transition config
                    event_data = delay.get("event_data", {})
                    transition_config = event_data.get("transition", {})

                    # Determine the event to fire
                    delay_key = delay.get("key", "")
                    delay_ms = delay_key.split(":")[-1] if ":" in delay_key else "0"

                    # Trigger the delayed transition
                    trigger_event_sync(
                        inst.reference_doctype,
                        inst.reference_name,
                        f"xstate.after.{delay_ms}",
                        event_data
                    )

                    # Remove this delay from the instance
                    instance_doc = frappe.get_doc("Machine Instance", inst.name)
                    instance_doc.remove_delayed_transition(delay_key)
                    instance_doc.save(ignore_permissions=True)
                    frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Error processing delayed transition for {inst.name}: {e}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

@frappe.whitelist()
def convert_react_flow_to_xstate(react_flow_json: str) -> str:
    """
    Convert React Flow nodes/edges to XState machine config.

    Args:
        react_flow_json: JSON string with {nodes: [...], edges: [...]}

    Returns:
        XState JSON config string
    """
    data = json.loads(react_flow_json)
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    # Find initial node
    initial_node = next(
        (n for n in nodes if n.get("data", {}).get("stateType") == "initial"),
        nodes[0] if nodes else None
    )

    # Build states
    states = {}
    for node in nodes:
        node_id = node["id"]
        node_data = node.get("data", {})
        state_type = node_data.get("stateType", "atomic")

        state_config = {}

        if state_type == "final":
            state_config["type"] = "final"
        elif state_type == "parallel":
            state_config["type"] = "parallel"

        # Add entry/exit actions
        if node_data.get("entryActions"):
            state_config["entry"] = node_data["entryActions"]
        if node_data.get("exitActions"):
            state_config["exit"] = node_data["exitActions"]

        # Build transitions from edges
        on = {}
        for edge in edges:
            if edge["source"] == node_id:
                event_name = edge.get("data", {}).get("event", edge.get("label", ""))
                if not event_name:
                    event_name = f"TO_{edge['target'].upper()}"

                transition = {"target": edge["target"]}

                # Add guard if specified
                if edge.get("data", {}).get("guard"):
                    transition["guard"] = edge["data"]["guard"]

                # Add actions if specified
                if edge.get("data", {}).get("actions"):
                    transition["actions"] = edge["data"]["actions"]

                # Simplify if just target
                if len(transition) == 1:
                    on[event_name] = edge["target"]
                else:
                    on[event_name] = transition

        if on:
            state_config["on"] = on

        states[node_id] = state_config if state_config else {}

    # Build final config
    machine_config = {
        "id": data.get("machineId", "workflow"),
        "initial": initial_node["id"] if initial_node else list(states.keys())[0],
        "context": data.get("context", {}),
        "states": states
    }

    return json.dumps(machine_config, indent=2)


@frappe.whitelist()
def convert_xstate_to_react_flow(xstate_json: str) -> str:
    """
    Convert XState machine config to React Flow nodes/edges.

    Args:
        xstate_json: XState JSON config string

    Returns:
        React Flow JSON with nodes and edges
    """
    config = json.loads(xstate_json)

    nodes = []
    edges = []

    states = config.get("states", {})
    initial_state = config.get("initial", "")

    # Layout constants
    x_spacing = 250
    y_spacing = 150
    x_pos = 50
    y_pos = 50

    # Create nodes
    for i, (state_name, state_config) in enumerate(states.items()):
        # Determine state type
        state_type = state_config.get("type", "atomic")
        if state_name == initial_state:
            state_type = "initial"
        elif state_type == "final":
            state_type = "final"
        elif "states" in state_config:
            state_type = "compound"

        node = {
            "id": state_name,
            "type": "stateNode",
            "position": {
                "x": x_pos + (i % 4) * x_spacing,
                "y": y_pos + (i // 4) * y_spacing
            },
            "data": {
                "label": state_name,
                "stateType": state_type,
                "entryActions": state_config.get("entry", []),
                "exitActions": state_config.get("exit", [])
            }
        }
        nodes.append(node)

        # Create edges from transitions
        on_transitions = state_config.get("on", {})
        for event_name, transition in on_transitions.items():
            target = None
            guard = None
            actions = []

            if isinstance(transition, str):
                target = transition
            elif isinstance(transition, dict):
                target = transition.get("target")
                guard = transition.get("guard")
                actions = transition.get("actions", [])
            elif isinstance(transition, list) and transition:
                # Take first transition for simplicity
                first = transition[0]
                if isinstance(first, str):
                    target = first
                elif isinstance(first, dict):
                    target = first.get("target")
                    guard = first.get("guard")

            if target:
                edge = {
                    "id": f"{state_name}-{event_name}-{target}",
                    "source": state_name,
                    "target": target,
                    "type": "transitionEdge",
                    "label": event_name,
                    "data": {
                        "event": event_name,
                        "guard": guard,
                        "actions": actions
                    }
                }
                edges.append(edge)

    return json.dumps({
        "machineId": config.get("id", "workflow"),
        "nodes": nodes,
        "edges": edges,
        "context": config.get("context", {})
    }, indent=2)
