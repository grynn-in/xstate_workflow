# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
User-based assignment resolvers.

Direct user assignment and document field-based user lookup.
"""

import frappe
from frappe import _

from . import register_resolver
from .base import (
    AssignmentResolver,
    ResolverConfigError,
    NoAssigneeFoundError,
    get_field_value,
)


@register_resolver
class StaticUserResolver(AssignmentResolver):
    """
    Assign to a specific user directly.

    Useful for fixed assignments or testing.
    """

    resolver_type = "static_user"

    def validate_config(self) -> None:
        # Accept both 'user' and 'user_id' for backward compatibility with frontend
        if not self.config.get("user") and not self.config.get("user_id"):
            raise ResolverConfigError("StaticUserResolver requires 'user' or 'user_id' in config")

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user": {
                    "type": "string",
                    "description": "The user ID (email) to assign to",
                    "x-frappe-link": "User"
                }
            },
            "required": ["user"]
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        # Accept both 'user' and 'user_id' for backward compatibility
        user = self.config.get("user") or self.config.get("user_id")

        # Validate user exists and is enabled
        user_doc = frappe.db.get_value(
            "User",
            user,
            ["name", "enabled"],
            as_dict=True
        )

        if not user_doc:
            raise NoAssigneeFoundError(f"User '{user}' does not exist")

        if not user_doc.enabled:
            raise NoAssigneeFoundError(f"User '{user}' is disabled")

        return [user]


@register_resolver
class DocumentFieldResolver(AssignmentResolver):
    """
    Read user from a field on the document.

    Supports dot notation for accessing fields on linked documents.
    """

    resolver_type = "document_field"

    def validate_config(self) -> None:
        # Accept both 'field' and 'field_name' for backward compatibility with frontend
        if not self.config.get("field") and not self.config.get("field_name"):
            raise ResolverConfigError("DocumentFieldResolver requires 'field' or 'field_name' in config")

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "Field name or dot-notation path (e.g., 'owner', 'custom_approver', 'customer.owner')"
                },
                "fallback_field": {
                    "type": "string",
                    "description": "Optional fallback field if primary field is empty"
                },
                "fallback_user": {
                    "type": "string",
                    "description": "Optional fallback user if both fields are empty",
                    "x-frappe-link": "User"
                }
            },
            "required": ["field"]
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        # Accept both 'field' and 'field_name' for backward compatibility
        field = self.config.get("field") or self.config.get("field_name")
        fallback_field = self.config.get("fallback_field")
        fallback_user = self.config.get("fallback_user")

        # Try primary field
        user = get_field_value(doc, field)

        # Try fallback field if primary is empty
        if not user and fallback_field:
            user = get_field_value(doc, fallback_field)

        # Try fallback user if still empty
        if not user and fallback_user:
            user = fallback_user

        if not user:
            raise NoAssigneeFoundError(
                f"No user found in field '{field}'"
                + (f" or '{fallback_field}'" if fallback_field else "")
            )

        # Handle case where field value might be a list
        if isinstance(user, list):
            users = user
        else:
            users = [user]

        # Validate all users exist and are enabled
        valid_users = []
        for u in users:
            if frappe.db.get_value("User", u, "enabled"):
                valid_users.append(u)

        if not valid_users:
            raise NoAssigneeFoundError(f"No enabled users found from field '{field}'")

        return valid_users


@register_resolver
class OwnerResolver(AssignmentResolver):
    """
    Assign to the document owner.

    Convenience resolver equivalent to document_field with field="owner".
    """

    resolver_type = "owner"

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fallback_user": {
                    "type": "string",
                    "description": "Optional fallback user if owner is disabled",
                    "x-frappe-link": "User"
                }
            }
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        owner = doc.owner if hasattr(doc, "owner") else None
        fallback_user = self.config.get("fallback_user")

        if not owner:
            if fallback_user:
                return [fallback_user]
            raise NoAssigneeFoundError("Document has no owner")

        # Check if owner is enabled
        if frappe.db.get_value("User", owner, "enabled"):
            return [owner]

        if fallback_user:
            return [fallback_user]

        raise NoAssigneeFoundError(f"Document owner '{owner}' is disabled")
