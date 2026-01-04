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
    instance = get_instance_for_doc(doctype, docname)

    if not instance:
        return {
            "has_workflow": False,
            "message": _("No workflow attached to this document")
        }

    available_events = get_next_events(
        instance.machine,
        instance.current_state,
        json.loads(instance.context or "{}")
    )

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
        "transition_count": instance.transition_count
    }


@frappe.whitelist()
def save_machine(machine_id: str, json_config: str, title: str = "",
                 react_flow_config: str = None, attached_doctype: str = None) -> dict:
    """
    Save or update a state machine configuration.

    Args:
        machine_id: Unique identifier for the machine
        json_config: XState JSON configuration
        title: Human-readable title
        react_flow_config: React Flow nodes/edges JSON
        attached_doctype: DocType to attach this workflow to

    Returns:
        dict with saved machine name
    """
    existing = frappe.db.exists("State Machine", machine_id)

    if existing:
        machine = frappe.get_doc("State Machine", machine_id)
        machine.json_config = json_config
        if react_flow_config:
            machine.react_flow_config = react_flow_config
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
            "react_flow_config": react_flow_config,
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

    machine = frappe.get_doc("State Machine", machine_id)

    return {
        "machine_id": machine.machine_id,
        "title": machine.title,
        "version": machine.version,
        "is_active": machine.is_active,
        "attached_doctype": machine.attached_doctype,
        "json_config": machine.json_config,
        "react_flow_config": machine.react_flow_config,
        "logic_module": machine.logic_module,
        "guards": [{"name": g.guard_name, "code": g.python_code}
                   for g in machine.guards_table],
        "actions": [{"name": a.action_name, "type": a.action_type, "code": a.python_code}
                    for a in machine.actions_table]
    }


@frappe.whitelist()
def list_machines(attached_to: str = None) -> list:
    """
    List all state machines, optionally filtered by attached DocType.

    Args:
        attached_to: Filter by attached DocType

    Returns:
        list of machine summaries
    """
    filters = {"is_active": 1}
    if attached_to:
        filters["attached_doctype"] = attached_to

    machines = frappe.get_all(
        "State Machine",
        filters=filters,
        fields=["machine_id", "title", "version", "attached_doctype", "modified"]
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
            # Multiple possible transitions (conditional)
            for t in transition:
                if isinstance(t, dict):
                    event_info["target"] = t.get("target")
                    if t.get("guard"):
                        event_info["guards"].append(t["guard"])

        # Check if guards pass
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
    instance = get_instance_for_doc(doctype, docname)

    if not instance:
        frappe.throw(_("No workflow instance found for {0} {1}").format(doctype, docname))

    instance_doc = frappe.get_doc("Machine Instance", instance.name)
    return instance_doc.reset()


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

    # Create new instance
    instance = frappe.get_doc({
        "doctype": "Machine Instance",
        "reference_doctype": doctype,
        "reference_name": docname,
        "machine": state_machine
    }).insert(ignore_permissions=True)

    frappe.db.commit()

    return instance.name


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

        # Get reference document
        ref_doc = frappe.get_doc(instance.reference_doctype, instance.reference_name)

        # Load config
        config = json.loads(machine_doc.json_config)

        # Get current state and context
        current_state = instance.current_state
        context = json.loads(instance.context or "{}")

        # Build guards and actions from machine definition
        guards = build_guards(machine_doc, ref_doc)
        actions = build_actions(machine_doc, ref_doc, instance)

        # Find the target state for this event
        state_config = find_state_config(config, current_state)

        if not state_config:
            return {
                "success": False,
                "error": _("State '{0}' not found in machine config").format(current_state)
            }

        transition = state_config.get("on", {}).get(event)

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

        # Execute exit actions for current state
        if state_config.get("exit"):
            execute_actions(state_config["exit"], actions, context, input_data)

        # Execute transition actions
        if transition_actions:
            context = execute_actions(transition_actions, actions, context, input_data)

        # Find target state config and execute entry actions
        target_state_config = find_state_config(config, target_state)
        if target_state_config and target_state_config.get("entry"):
            context = execute_actions(target_state_config["entry"], actions, context, input_data)

        # Check if final state
        is_final = target_state_config and target_state_config.get("type") == "final"

        # Update instance
        old_state = instance.current_state
        instance.current_state = target_state
        instance.context = json.dumps(context)
        instance.last_event = event
        instance.last_transition_at = frappe.utils.now()
        instance.status = "final" if is_final else "active"

        # Log transition
        instance.log_transition(event, old_state, target_state, success=True)

        instance.save(ignore_permissions=True)

        # Post-transition hooks
        post_transition_actions(instance, event, old_state, target_state, ref_doc)

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

    # Add default guards
    guards["always"] = lambda ctx, evt: True
    guards["never"] = lambda ctx, evt: False

    return guards


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


def evaluate_guard(machine_doc, guard_name: str, context: dict, event: dict) -> bool:
    """
    Evaluate a single guard by name.

    Args:
        machine_doc: State Machine document
        guard_name: Guard name
        context: Current context
        event: Event data

    Returns:
        Guard result (True/False)
    """
    guards = build_guards(machine_doc, None)
    guard_fn = guards.get(guard_name)

    if guard_fn:
        return guard_fn(context, event)

    return True


# ============================================================================
# HOOKS AND SCHEDULED TASKS
# ============================================================================

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

    # Get instance
    instance = get_instance_for_doc(doc.doctype, doc.name)

    if not instance:
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
                trigger_event(doc.doctype, doc.name, event, json.dumps({"field": field, "value": new_value}))


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
    """
    # Find instances with pending delayed transitions
    instances = frappe.get_all(
        "Machine Instance",
        filters={
            "status": "active"
        },
        fields=["name", "machine", "current_state", "context"]
    )

    for inst in instances:
        machine = frappe.get_doc("State Machine", inst.machine)
        config = json.loads(machine.json_config)
        state_config = find_state_config(config, inst.current_state)

        if not state_config:
            continue

        # Check for "after" transitions
        after_transitions = state_config.get("after", {})
        context = json.loads(inst.context or "{}")

        for delay_ms, transition in after_transitions.items():
            delay_field = f"_delay_{delay_ms}_started"
            if context.get(delay_field):
                started_at = context[delay_field]
                elapsed = (frappe.utils.now_datetime() -
                          frappe.utils.get_datetime(started_at)).total_seconds() * 1000

                if elapsed >= int(delay_ms):
                    # Trigger delayed transition
                    trigger_event_sync(
                        frappe.db.get_value("Machine Instance", inst.name, "reference_doctype"),
                        frappe.db.get_value("Machine Instance", inst.name, "reference_name"),
                        f"xstate.after.{delay_ms}",
                        {}
                    )


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
