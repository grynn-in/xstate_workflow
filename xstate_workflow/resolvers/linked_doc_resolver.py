# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Linked document field resolver.

Read user from a field on a linked document.
Generic resolver that works with any DocType.
"""

import frappe
from frappe import _

from . import register_resolver
from .base import (
    AssignmentResolver,
    ResolverConfigError,
    NoAssigneeFoundError,
    get_field_value,
    get_linked_doc_user,
)


@register_resolver
class LinkedDocFieldResolver(AssignmentResolver):
    """
    Read user from a linked document's field.

    Generic resolver that works with any DocType structure.
    For example:
    - Get manager from Cost Center: link_field="cost_center", user_field="custom_manager"
    - Get head from Department: link_field="department", user_field="custom_head"
    """

    resolver_type = "linked_doc_field"

    def validate_config(self) -> None:
        if not self.config.get("link_field"):
            raise ResolverConfigError("LinkedDocFieldResolver requires 'link_field' in config")

        if not self.config.get("user_field"):
            raise ResolverConfigError("LinkedDocFieldResolver requires 'user_field' in config")

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "link_field": {
                    "type": "string",
                    "description": "Field on the document that links to another DocType (e.g., 'cost_center', 'department')"
                },
                "user_field": {
                    "type": "string",
                    "description": "Field on the linked DocType that contains the User (e.g., 'custom_manager', 'owner')"
                },
                "linked_doctype": {
                    "type": "string",
                    "description": "Optional - DocType of the linked document (auto-detected if not provided)",
                    "x-frappe-link": "DocType"
                },
                "fallback_field": {
                    "type": "string",
                    "description": "Optional fallback user field on the linked doc"
                },
                "fallback_resolver": {
                    "type": "object",
                    "description": "Optional fallback resolver config if linked doc field is empty"
                }
            },
            "required": ["link_field", "user_field"]
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        link_field = self.config["link_field"]
        user_field = self.config["user_field"]
        linked_doctype = self.config.get("linked_doctype")
        fallback_field = self.config.get("fallback_field")
        fallback_resolver = self.config.get("fallback_resolver")

        # Get the linked doc name
        linked_name = get_field_value(doc, link_field)
        if not linked_name:
            return self._handle_fallback(doc, context, f"Field '{link_field}' is empty")

        # Determine linked DocType if not provided
        if not linked_doctype:
            meta = frappe.get_meta(doc.doctype)
            field_meta = meta.get_field(link_field)
            if not field_meta:
                raise ResolverConfigError(f"Field '{link_field}' does not exist on {doc.doctype}")
            if field_meta.fieldtype != "Link":
                raise ResolverConfigError(f"Field '{link_field}' is not a Link field")
            linked_doctype = field_meta.options

        # Get user from linked doc
        user = frappe.db.get_value(linked_doctype, linked_name, user_field)

        # Try fallback field if primary is empty
        if not user and fallback_field:
            user = frappe.db.get_value(linked_doctype, linked_name, fallback_field)

        if not user:
            return self._handle_fallback(
                doc, context,
                f"No user found in {linked_doctype}.{user_field} for {linked_name}"
            )

        # Validate user is enabled
        if not frappe.db.get_value("User", user, "enabled"):
            return self._handle_fallback(
                doc, context,
                f"User '{user}' from {linked_doctype}.{user_field} is disabled"
            )

        return [user]

    def _handle_fallback(self, doc, context: dict, error_msg: str) -> list[str]:
        """Handle fallback when primary resolution fails."""
        fallback_resolver = self.config.get("fallback_resolver")

        if fallback_resolver:
            from . import resolve_assignment
            return resolve_assignment(doc, fallback_resolver, context)

        raise NoAssigneeFoundError(error_msg)


# Convenience presets for common patterns

@register_resolver
class CostCenterManagerResolver(AssignmentResolver):
    """
    Get manager from the document's cost center.

    Shorthand for linked_doc_field with cost_center -> custom_manager.
    """

    resolver_type = "cost_center_manager"

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cost_center_field": {
                    "type": "string",
                    "default": "cost_center",
                    "description": "Field on document that contains Cost Center"
                },
                "manager_field": {
                    "type": "string",
                    "default": "custom_manager",
                    "description": "Field on Cost Center that contains the manager User"
                },
                "fallback_resolver": {
                    "type": "object",
                    "description": "Optional fallback resolver if cost center has no manager"
                }
            }
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        # Delegate to LinkedDocFieldResolver
        config = {
            "link_field": self.config.get("cost_center_field", "cost_center"),
            "user_field": self.config.get("manager_field", "custom_manager"),
            "linked_doctype": "Cost Center",
            "fallback_resolver": self.config.get("fallback_resolver")
        }

        resolver = LinkedDocFieldResolver(config)
        return resolver.resolve(doc, context)


@register_resolver
class DepartmentHeadResolver(AssignmentResolver):
    """
    Get head from the document's department.

    Shorthand for linked_doc_field with department -> custom_head.
    """

    resolver_type = "department_head"

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "department_field": {
                    "type": "string",
                    "default": "department",
                    "description": "Field on document that contains Department"
                },
                "head_field": {
                    "type": "string",
                    "default": "custom_head",
                    "description": "Field on Department that contains the head User"
                },
                "fallback_resolver": {
                    "type": "object",
                    "description": "Optional fallback resolver if department has no head"
                }
            }
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        # Delegate to LinkedDocFieldResolver
        config = {
            "link_field": self.config.get("department_field", "department"),
            "user_field": self.config.get("head_field", "custom_head"),
            "linked_doctype": "Department",
            "fallback_resolver": self.config.get("fallback_resolver")
        }

        resolver = LinkedDocFieldResolver(config)
        return resolver.resolve(doc, context)
