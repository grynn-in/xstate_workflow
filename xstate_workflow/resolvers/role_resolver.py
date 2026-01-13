# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Role-based assignment resolver.

Assigns tasks to users who have a specific role, with various
selection strategies when multiple users qualify.
"""

import frappe
from frappe import _

from . import register_resolver
from .base import (
    AssignmentResolver,
    ResolverConfigError,
    NoAssigneeFoundError,
    get_users_with_role,
)


@register_resolver
class RoleResolver(AssignmentResolver):
    """
    Assign to users with a specific role.

    Supports multiple selection strategies when multiple users have the role.
    """

    resolver_type = "role"

    def validate_config(self) -> None:
        if not self.config.get("role"):
            raise ResolverConfigError("RoleResolver requires 'role' in config")

        # Validate role exists
        role = self.config["role"]
        if not frappe.db.exists("Role", role):
            raise ResolverConfigError(f"Role '{role}' does not exist")

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "The role name to match",
                    "x-frappe-link": "Role"
                },
                "strategy": {
                    "type": "string",
                    "enum": ["all", "round_robin", "least_loaded", "random", "first"],
                    "default": "all",
                    "description": "Selection strategy when multiple users have the role"
                },
                "tenant": {
                    "type": "string",
                    "description": "Optional tenant/company to filter users",
                    "x-frappe-link": "Company"
                }
            },
            "required": ["role"]
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        role = self.config["role"]
        strategy = self.config.get("strategy", "all")
        tenant = self.config.get("tenant") or self._get_tenant_from_context(doc, context)

        # Get all users with the role
        users = get_users_with_role(role, tenant)

        if not users:
            raise NoAssigneeFoundError(f"No users found with role '{role}'")

        # Apply selection strategy
        if strategy == "all":
            return users
        elif strategy == "round_robin":
            return [self._get_round_robin_user(users, role, tenant)]
        elif strategy == "least_loaded":
            return [self._get_least_loaded_user(users)]
        elif strategy == "random":
            import random
            return [random.choice(users)]
        elif strategy == "first":
            return [users[0]]
        else:
            return users

    def _get_tenant_from_context(self, doc, context: dict = None) -> str | None:
        """Extract tenant from document or context."""
        if context and context.get("tenant"):
            return context["tenant"]

        if hasattr(doc, "company") and doc.company:
            return doc.company

        return None

    def _get_round_robin_user(self, users: list[str], role: str, tenant: str = None) -> str:
        """
        Get next user in round-robin order.

        Uses a simple counter stored in cache to track last assigned user.
        """
        cache_key = f"resolver_rr_{role}_{tenant or 'global'}"

        # Get current index from cache
        current_index = frappe.cache().get_value(cache_key) or 0

        # Get next user
        next_index = current_index % len(users)
        selected_user = users[next_index]

        # Update cache
        frappe.cache().set_value(cache_key, next_index + 1)

        return selected_user

    def _get_least_loaded_user(self, users: list[str]) -> str:
        """
        Get user with fewest pending approval tasks.
        """
        # Count pending tasks for each user
        task_counts = {}

        for user in users:
            count = frappe.db.count(
                "Approval Task",
                filters={
                    "assigned_to": user,
                    "status": "Pending"
                }
            )
            task_counts[user] = count

        # Return user with minimum tasks
        return min(users, key=lambda u: task_counts.get(u, 0))
