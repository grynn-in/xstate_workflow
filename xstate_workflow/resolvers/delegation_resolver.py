# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Delegation Authority resolver.

Query Delegation Authority DocType to find users with authority
to approve based on amount, cost center, department, etc.
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
class DelegationMatrixResolver(AssignmentResolver):
    """
    Query Delegation Authority to find users with authority.

    Looks up users in the Delegation Authority DocType who have
    the authority to approve based on amount, cost center,
    department, or custom criteria.
    """

    resolver_type = "delegation_matrix"

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "amount_field": {
                    "type": "string",
                    "default": "grand_total",
                    "description": "Document field containing the amount to check"
                },
                "cost_center_field": {
                    "type": "string",
                    "description": "Document field containing cost center (optional filter)"
                },
                "department_field": {
                    "type": "string",
                    "description": "Document field containing department (optional filter)"
                },
                "doctype_specific": {
                    "type": "boolean",
                    "default": True,
                    "description": "Only match authority records for this DocType"
                },
                "strategy": {
                    "type": "string",
                    "enum": ["lowest_authority", "highest_authority", "all", "first"],
                    "default": "lowest_authority",
                    "description": "Selection strategy when multiple users have authority"
                },
                "fallback_resolver": {
                    "type": "object",
                    "description": "Fallback resolver if no authority found"
                }
            }
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        amount_field = self.config.get("amount_field", "grand_total")
        cost_center_field = self.config.get("cost_center_field")
        department_field = self.config.get("department_field")
        doctype_specific = self.config.get("doctype_specific", True)
        strategy = self.config.get("strategy", "lowest_authority")

        # Get document values
        amount = get_field_value(doc, amount_field) or 0
        cost_center = get_field_value(doc, cost_center_field) if cost_center_field else None
        department = get_field_value(doc, department_field) if department_field else None

        # Build filters for Delegation Authority query
        filters = {
            "is_active": 1,
            "max_amount": [">=", amount]
        }

        # Filter by min_amount if set
        # We want authorities where min_amount <= amount <= max_amount
        or_filters = [
            {"min_amount": ["<=", amount]},
            {"min_amount": ["is", "not set"]},
            {"min_amount": 0}
        ]

        # Optional: DocType specific
        if doctype_specific:
            filters["doctype"] = ["in", [doc.doctype, None, ""]]

        # Optional: Cost center filter
        if cost_center:
            filters["cost_center"] = ["in", [cost_center, None, ""]]

        # Optional: Department filter
        if department:
            filters["department"] = ["in", [department, None, ""]]

        # Query delegation authorities
        authorities = frappe.get_all(
            "Delegation Authority",
            filters=filters,
            or_filters=or_filters,
            fields=["user", "role", "max_amount", "min_amount"],
            order_by="max_amount asc"  # For lowest_authority strategy
        )

        if not authorities:
            return self._handle_fallback(
                doc, context,
                f"No delegation authority found for amount {amount}"
            )

        # Collect users from authorities
        users = []
        for auth in authorities:
            if auth.user:
                # Check user is enabled
                if frappe.db.get_value("User", auth.user, "enabled"):
                    users.append({
                        "user": auth.user,
                        "max_amount": auth.max_amount or 0
                    })
            elif auth.role:
                # Get all users with this role
                from .base import get_users_with_role
                role_users = get_users_with_role(auth.role)
                for u in role_users:
                    if u not in [x["user"] for x in users]:
                        users.append({
                            "user": u,
                            "max_amount": auth.max_amount or 0
                        })

        if not users:
            return self._handle_fallback(
                doc, context,
                f"No enabled users found with delegation authority for amount {amount}"
            )

        # Apply selection strategy
        if strategy == "lowest_authority":
            # User with lowest max_amount that still covers the document amount
            users.sort(key=lambda x: x["max_amount"])
            return [users[0]["user"]]

        elif strategy == "highest_authority":
            # User with highest authority
            users.sort(key=lambda x: x["max_amount"], reverse=True)
            return [users[0]["user"]]

        elif strategy == "all":
            return [u["user"] for u in users]

        elif strategy == "first":
            return [users[0]["user"]]

        else:
            return [users[0]["user"]]

    def _handle_fallback(self, doc, context: dict, error_msg: str) -> list[str]:
        """Handle fallback when no authority found."""
        fallback_resolver = self.config.get("fallback_resolver")

        if fallback_resolver:
            from . import resolve_assignment
            return resolve_assignment(doc, fallback_resolver, context)

        raise NoAssigneeFoundError(error_msg)


@register_resolver
class AuthorityCheckResolver(AssignmentResolver):
    """
    Check if a specific user has authority for this document.

    Unlike DelegationMatrixResolver which finds users, this resolver
    checks if a given user (from another resolver) has sufficient authority.

    Useful for validation or conditional logic.
    """

    resolver_type = "authority_check"

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_resolver": {
                    "type": "object",
                    "description": "Resolver to get the user to check"
                },
                "amount_field": {
                    "type": "string",
                    "default": "grand_total",
                    "description": "Document field containing the amount"
                },
                "fallback_resolver": {
                    "type": "object",
                    "description": "Fallback resolver if user doesn't have authority"
                }
            },
            "required": ["user_resolver"]
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        user_resolver = self.config.get("user_resolver")
        amount_field = self.config.get("amount_field", "grand_total")
        fallback_resolver = self.config.get("fallback_resolver")

        # Get user from sub-resolver
        from . import resolve_assignment
        users = resolve_assignment(doc, user_resolver, context, apply_delegation=False)

        if not users:
            if fallback_resolver:
                return resolve_assignment(doc, fallback_resolver, context)
            raise NoAssigneeFoundError("User resolver returned no users")

        user = users[0]
        amount = get_field_value(doc, amount_field) or 0

        # Check if user has authority
        authority = frappe.db.get_value(
            "Delegation Authority",
            {
                "user": user,
                "is_active": 1,
                "max_amount": [">=", amount],
                "doctype": ["in", [doc.doctype, None, ""]]
            },
            "max_amount"
        )

        if authority:
            return [user]

        # User doesn't have authority, try fallback
        if fallback_resolver:
            return resolve_assignment(doc, fallback_resolver, context)

        raise NoAssigneeFoundError(
            f"User '{user}' does not have authority for amount {amount}"
        )
