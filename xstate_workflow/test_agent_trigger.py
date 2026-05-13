#!/usr/bin/env python3
"""Test script to debug agentic node triggering"""
import frappe
import json

def test():
    frappe.init(site='xs.local')
    frappe.connect()

    try:
        # Get the workflow config
        machine = frappe.get_doc("State Machine", "content-post-workflow")
        config = json.loads(machine.json_config)

        print("=== Workflow States ===")
        for state_name, state_config in config.get("states", {}).items():
            meta = state_config.get("meta", {})
            domain_node = meta.get("domain_node", {})
            node_type = domain_node.get("type") if domain_node else None
            entry = state_config.get("entry", [])
            print(f"  {state_name}: type={node_type}, entry={entry}")

        print("\n=== Research Topic Config ===")
        research_config = config.get("states", {}).get("Research Topic", {})
        print(json.dumps(research_config, indent=2)[:2000])

        # Get a Content Post instance
        docs = frappe.get_all("Machine Instance",
            filters={"state_machine": "content-post-workflow"},
            fields=["name", "current_state", "status"],
            order_by="creation desc",
            limit=1
        )

        if docs:
            print(f"\n=== Machine Instance ===")
            inst = frappe.get_doc("Machine Instance", docs[0].name)
            print(f"Name: {inst.name}")
            print(f"Current State: {inst.current_state}")
            print(f"Status: {inst.status}")
            print(f"State Machine: {inst.state_machine}")

            # Get the ref doc
            ref_doctype = inst.doctype_link if hasattr(inst, 'doctype_link') else None
            ref_docname = inst.docname_link if hasattr(inst, 'docname_link') else None
            print(f"Ref: {ref_doctype} / {ref_docname}")

            # Try to manually call handle_domain_node_entry
            print("\n=== Testing handle_domain_node_entry ===")
            from xstate_workflow.workflow_engine import handle_domain_node_entry

            state_config = config.get("states", {}).get(inst.current_state, {})
            if state_config:
                # Get ref_doc
                all_fields = [f.fieldname for f in frappe.get_meta("Machine Instance").fields]
                print(f"Instance fields: {all_fields[:10]}...")
        else:
            print("No machine instances found")

    finally:
        frappe.destroy()

if __name__ == "__main__":
    test()
