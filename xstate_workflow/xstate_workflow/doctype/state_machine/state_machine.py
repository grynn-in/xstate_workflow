# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.model.document import Document


class StateMachine(Document):
    def validate(self):
        self.validate_json_config()
        self.validate_logic_module()
        self.modified_by = frappe.session.user

    def validate_json_config(self):
        """Validate that json_config is valid XState machine config"""
        try:
            config = json.loads(self.json_config)

            # Basic XState structure validation
            if not isinstance(config, dict):
                frappe.throw(_("JSON config must be an object"))

            if "id" not in config:
                frappe.throw(_("XState config must have an 'id' field"))

            if "initial" not in config and "type" not in config:
                frappe.throw(_("XState config must have an 'initial' state or be a parallel/final state"))

            if "states" not in config and config.get("type") not in ["final", "history"]:
                frappe.throw(_("XState config must have 'states' defined"))

        except json.JSONDecodeError as e:
            frappe.throw(_("Invalid JSON in config: {0}").format(str(e)))

    def validate_logic_module(self):
        """Validate that logic module exists if specified"""
        if self.logic_module:
            try:
                __import__(self.logic_module, fromlist=[""])
            except ImportError:
                frappe.msgprint(
                    _("Warning: Logic module '{0}' could not be imported. "
                      "Make sure it exists before using this machine.").format(self.logic_module),
                    indicator="orange"
                )

    def before_save(self):
        # Auto-increment version on config change
        if self.has_value_changed("json_config") and not self.is_new():
            self.version = (self.version or 0) + 1

    def get_xstate_config(self):
        """Return parsed XState config with guards and actions resolved"""
        return json.loads(self.json_config)

    def get_react_flow_config(self):
        """Return parsed React Flow config"""
        if self.react_flow_config:
            return json.loads(self.react_flow_config)
        return None

    @frappe.whitelist()
    def duplicate(self):
        """Create a copy of this state machine"""
        new_doc = frappe.copy_doc(self)
        new_doc.machine_id = f"{self.machine_id}_copy"
        new_doc.title = f"{self.title} (Copy)"
        new_doc.version = 1
        new_doc.is_active = 0
        new_doc.insert()
        return new_doc.name

    @frappe.whitelist()
    def export_config(self):
        """Export machine config as downloadable JSON"""
        self.last_exported_at = frappe.utils.now()
        self.save()

        return {
            "machine_id": self.machine_id,
            "title": self.title,
            "version": self.version,
            "xstate_config": json.loads(self.json_config),
            "react_flow_config": json.loads(self.react_flow_config) if self.react_flow_config else None,
            "guards": [{"name": g.guard_name, "description": g.description} for g in self.guards_table],
            "actions": [{"name": a.action_name, "description": a.description} for a in self.actions_table]
        }
