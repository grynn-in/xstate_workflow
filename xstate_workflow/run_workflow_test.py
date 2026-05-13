"""Run a test of the Content Post workflow"""
import frappe
from xstate_workflow.workflow_engine import trigger_event_sync, get_machine_state

def run():
    """Run and advance the workflow, triggering whatever event is available"""
    # Debug: Check instance directly
    from xstate_workflow.workflow_engine import get_instance_for_doc, get_next_events, find_state_config
    import json

    instance = get_instance_for_doc("Content Post", "CP-0007")
    print(f"[DEBUG] Instance exists: {instance is not None}")
    if instance:
        print(f"[DEBUG] Instance.machine: {instance.machine}")
        print(f"[DEBUG] Instance.current_state: {instance.current_state}")

        # Check if state is found
        machine = frappe.get_doc("State Machine", instance.machine)
        config = json.loads(machine.json_config)
        print(f"[DEBUG] Config states: {list(config.get('states', {}).keys())}")

        state_config = find_state_config(config, instance.current_state)
        print(f"[DEBUG] State config found: {state_config is not None}")
        if state_config:
            print(f"[DEBUG] State 'on' transitions: {state_config.get('on', {})}")
            print(f"[DEBUG] State 'always' transitions: {state_config.get('always', [])}")

    # Get current state of CP-0007
    state = get_machine_state("Content Post", "CP-0007")
    print(f"Current state: {state.get('current_state')}")
    print(f"Available events: {state.get('available_events')}")

    # Check for always transition and execute it
    if instance and state_config and state_config.get('always'):
        print(f"\n[DEBUG] Triggering 'always' transition...")
        result = trigger_event_sync("Content Post", "CP-0007", "xstate.always")
        print(f"[DEBUG] Always result: {result}")

        # Check new state
        new_state = get_machine_state("Content Post", "CP-0007")
        print(f"New state: {new_state.get('current_state')}")
        print(f"New events: {new_state.get('available_events')}")
        return result

    # Get the first available event
    available = state.get('available_events', [])
    if not available:
        print("No available events!")
        return {"success": False, "error": "No available events"}

    event_name = available[0].get('event')
    print(f"\nTriggering event: {event_name}")

    # Trigger the event
    result = trigger_event_sync("Content Post", "CP-0007", event_name)
    print(f"Trigger result: {result}")

    # Check new state
    new_state = get_machine_state("Content Post", "CP-0007")
    print(f"New state: {new_state.get('current_state')}")

    return result


def reset():
    """Reset the workflow back to start state"""
    instances = frappe.get_all("Machine Instance", filters={
        "reference_doctype": "Content Post",
        "reference_name": "CP-0007"
    }, pluck="name")

    if not instances:
        print("No instance found for CP-0007")
        return {"success": False}

    instance = frappe.get_doc("Machine Instance", instances[0])
    print(f"Instance: {instance.name}")
    print(f"Current state: {instance.current_state}")

    instance.current_state = "start"
    instance.save(ignore_permissions=True)
    frappe.db.commit()

    print(f"Reset to: {instance.current_state}")

    # Show new state
    state = get_machine_state("Content Post", "CP-0007")
    print(f"Available events: {state.get('available_events')}")
    return {"success": True}


def check_jobs():
    """Check background jobs in the queue"""
    import redis
    from frappe.utils.background_jobs import get_redis_conn

    conn = get_redis_conn()

    # Check various queues
    queues = ["default", "long", "workflow"]
    for queue in queues:
        key = f"rq:queue:{queue}"
        count = conn.llen(key)
        print(f"Queue '{queue}': {count} jobs")

        if count > 0:
            # Show first few jobs
            jobs = conn.lrange(key, 0, 2)
            for job in jobs:
                print(f"  Job: {job[:100]}...")

    return {"success": True}


def debug():
    """Debug the machine instance and state machine link"""
    instances = frappe.get_all("Machine Instance", filters={
        "reference_doctype": "Content Post",
        "reference_name": "CP-0007"
    }, fields=["name", "machine", "current_state"])

    if not instances:
        print("No instance found for CP-0007")
        return {"success": False}

    inst = instances[0]
    print(f"Instance: {inst.name}")
    print(f"Machine: {inst.machine}")
    print(f"Current state: {inst.current_state}")

    # Check if the machine exists
    if frappe.db.exists("State Machine", inst.machine):
        print(f"Machine exists: Yes")
        machine = frappe.get_doc("State Machine", inst.machine)
        print(f"Machine title: {machine.title}")
        print(f"Machine is_active: {machine.is_active}")
    else:
        print(f"Machine exists: No - needs to be re-linked!")
        # Find the right machine
        machines = frappe.get_all("State Machine", filters={
            "attached_doctype": "Content Post"
        }, fields=["name", "title"])
        print(f"Available machines for Content Post: {machines}")

    return {"success": True}


def show_config():
    """Show the actual State Machine config including domain_node settings"""
    import json
    machine = frappe.get_doc("State Machine", "content-post-workflow")
    config = json.loads(machine.json_config)
    print("Initial:", config.get("initial"))
    print("\nStates:")
    for name, state_config in config.get("states", {}).items():
        on_transitions = state_config.get("on", {})
        domain_node = state_config.get("meta", {}).get("domain_node", {})
        dn_type = domain_node.get("type", "-")
        frappe_access = domain_node.get("frappe_access", "-")
        print(f"  '{name}':")
        print(f"    type: {dn_type}")
        print(f"    frappe_access: {frappe_access}")
        print(f"    on: {list(on_transitions.keys())}")
    return config


def trigger(event_name="RESEARCH_COMPLETE"):
    """Manually trigger an event on the workflow"""
    result = trigger_event_sync("Content Post", "CP-0007", event_name)
    print(f"Trigger result: {result}")

    state = get_machine_state("Content Post", "CP-0007")
    print(f"New state: {state.get('current_state')}")
    print(f"Available events: {state.get('available_events')}")
    return result


def trends_complete():
    """Trigger TRENDS_COMPLETE event"""
    return trigger("TRENDS_COMPLETE")


def content_generated():
    """Trigger CONTENT_GENERATED event"""
    return trigger("CONTENT_GENERATED")


def approve():
    """Trigger APPROVE event"""
    return trigger("APPROVE")


def check(docname="CP-0007"):
    """Check state of any Content Post document"""
    state = get_machine_state("Content Post", docname)
    print(f"{docname} state: {state.get('current_state')}")
    print(f"Available events: {state.get('available_events')}")
    return state


def check8():
    """Check CP-0008"""
    return check("CP-0008")


def advance8(event_name):
    """Trigger event on CP-0008"""
    result = trigger_event_sync("Content Post", "CP-0008", event_name)
    print(f"Result: {result}")
    return check("CP-0008")


def push8_to_review():
    """Push CP-0008 through all states to Review Content"""
    events = ["RESEARCH_COMPLETE", "TRENDS_COMPLETE", "CONTENT_GENERATED"]
    for event in events:
        state = get_machine_state("Content Post", "CP-0008")
        current = state.get("current_state")
        available = [e.get("event") for e in state.get("available_events", [])]
        print(f"Current: {current}, Available: {available}")

        if event in available:
            print(f"Triggering {event}...")
            result = trigger_event_sync("Content Post", "CP-0008", event)
            print(f"Result: {result.get('success')}, New state: {result.get('new_state')}")
        else:
            print(f"Event {event} not available, skipping")

    return check("CP-0008")


def approve8():
    """Approve CP-0008"""
    result = trigger_event_sync("Content Post", "CP-0008", "APPROVE")
    print(f"Result: {result}")
    return check("CP-0008")


def check_twitter_config():
    """Check if Twitter credentials are configured"""
    keys = ["twitter_consumer_key", "twitter_consumer_secret", "twitter_access_token", "twitter_access_token_secret"]
    for key in keys:
        value = frappe.conf.get(key)
        print(f"{key}: {'✓ configured' if value else '✗ missing'}")
    return {"success": True}


def test_twitter_auth():
    """Test Twitter authentication by fetching user info (read-only)"""
    import requests
    from requests_oauthlib import OAuth1

    consumer_key = frappe.conf.get("twitter_consumer_key")
    consumer_secret = frappe.conf.get("twitter_consumer_secret")
    access_token = frappe.conf.get("twitter_access_token")
    access_token_secret = frappe.conf.get("twitter_access_token_secret")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("Missing credentials!")
        return {"success": False}

    auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)

    # Test with GET /2/users/me endpoint (read-only)
    print("Testing read access (GET /2/users/me)...")
    response = requests.get(
        "https://api.twitter.com/2/users/me",
        auth=auth,
        timeout=30,
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")

    if response.ok:
        data = response.json()
        username = data.get("data", {}).get("username")
        print(f"\n✓ Authenticated as: @{username}")

        # Now test write access with a dry-run
        print("\nTo post to Twitter, your app needs 'Read and Write' permissions.")
        print("If posting fails, go to developer.twitter.com:")
        print("1. Select your app → User authentication settings")
        print("2. Enable 'Read and write' permissions")
        print("3. Regenerate Access Token and Secret")
        print("4. Update site_config.json with new tokens")
    else:
        try:
            error = response.json()
            print(f"\n✗ Auth failed: {error}")
        except:
            print(f"\n✗ Auth failed: {response.text}")

    return {"success": response.ok}


def test_publish():
    """Test direct publishing action (no LLM)"""
    from xstate_workflow.domain_nodes.handlers import _publish_content_action

    doc = frappe.get_doc("Content Post", "CP-0007")
    print(f"Twitter content: {doc.twitter_version[:100] if doc.twitter_version else 'None'}...")

    # Simulate the event config
    event_config = {
        "platforms": ["twitter"],
        "field_mapping": {"twitter": "twitter_version"},
        "on_success_event": "PUBLISHED",
        "on_failure_event": "PUBLISH_FAILED",
    }

    context = {}
    result = _publish_content_action(context, event_config, doc, None)

    print(f"\nPublish results: {result.get('_publish_results')}")
    if result.get("_publish_errors"):
        print(f"Errors: {result.get('_publish_errors')}")

    return result


def show_doc():
    """Show the Content Post document"""
    doc = frappe.get_doc("Content Post", "CP-0007")
    print("Content Post CP-0007:")
    print(f"  prompt: {doc.prompt}")
    print(f"  industry_focus: {doc.industry_focus}")
    print(f"  title: {doc.title}")
    print(f"  topic: {doc.topic}")
    print(f"  twitter_version: {doc.twitter_version}")
    print(f"  linkedin_version: {(doc.linkedin_version or '')[:200]}...")

    # Check instance context
    import json
    instances = frappe.get_all("Machine Instance", filters={
        "reference_doctype": "Content Post",
        "reference_name": "CP-0007"
    }, pluck="name")

    if instances:
        instance = frappe.get_doc("Machine Instance", instances[0])
        context = json.loads(instance.context or "{}")
        print("\nInstance context:")
        for k, v in context.items():
            print(f"  {k}: {str(v)[:100]}...")

    return {"success": True}


def relink():
    """Relink instance to the correct State Machine and match state names"""
    import json

    instances = frappe.get_all("Machine Instance", filters={
        "reference_doctype": "Content Post",
        "reference_name": "CP-0007"
    }, pluck="name")

    if not instances:
        print("No instance found for CP-0007")
        return {"success": False}

    instance = frappe.get_doc("Machine Instance", instances[0])
    print(f"Instance: {instance.name}")
    print(f"Old machine: {instance.machine}")
    print(f"Old state: {instance.current_state}")

    # Find the correct machine
    machines = frappe.get_all("State Machine", filters={
        "attached_doctype": "Content Post"
    }, pluck="name")

    if not machines:
        print("No machine found for Content Post!")
        return {"success": False}

    instance.machine = machines[0]

    # Get the correct initial state from the config
    machine = frappe.get_doc("State Machine", instance.machine)
    config = json.loads(machine.json_config)
    initial_state = config.get("initial", "start")

    instance.current_state = initial_state
    instance.save(ignore_permissions=True)
    frappe.db.commit()

    print(f"New machine: {instance.machine}")
    print(f"Reset to: {instance.current_state}")

    # Show new state
    state = get_machine_state("Content Post", "CP-0007")
    print(f"Available events: {state.get('available_events')}")
    return {"success": True}
