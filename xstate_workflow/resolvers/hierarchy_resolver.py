# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Generic hierarchy walk resolver.

Walk up any hierarchical DocType structure to find approvers.
Works with Employee, custom Approver hierarchies, or any DocType
with a parent-child relationship.
"""

import frappe
from frappe import _

from . import register_resolver
from .base import (
    AssignmentResolver,
    ResolverConfigError,
    NoAssigneeFoundError,
    get_field_value,
    get_hierarchy_user,
    walk_hierarchy_until,
    validate_hierarchy_config,
)


@register_resolver
class HierarchyWalkResolver(AssignmentResolver):
    """
    Walk up any hierarchical DocType to find approvers.

    Supports:
    - Fixed level walking (go up N levels)
    - Conditional walking (until authority, role, or custom condition)
    - Collecting all users up to a level

    This is a generic resolver that works with ANY DocType that has
    a hierarchical structure (parent-child relationship).
    """

    resolver_type = "hierarchy_walk"

    def validate_config(self) -> None:
        hierarchy_doctype = self.config.get("hierarchy_doctype")
        parent_field = self.config.get("parent_field")
        user_field = self.config.get("user_field")

        if not hierarchy_doctype:
            raise ResolverConfigError("hierarchy_walk requires 'hierarchy_doctype'")
        if not parent_field:
            raise ResolverConfigError("hierarchy_walk requires 'parent_field'")
        if not user_field:
            raise ResolverConfigError("hierarchy_walk requires 'user_field'")

        # Validate the hierarchy configuration
        is_valid, error = validate_hierarchy_config(hierarchy_doctype, parent_field, user_field)
        if not is_valid:
            raise ResolverConfigError(error)

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "hierarchy_doctype": {
                    "type": "string",
                    "description": "DocType with hierarchical structure (e.g., 'Employee', 'Approver')",
                    "x-frappe-link": "DocType"
                },
                "parent_field": {
                    "type": "string",
                    "description": "Field linking to parent record (e.g., 'reports_to', 'parent_approver')"
                },
                "user_field": {
                    "type": "string",
                    "description": "Field containing the User link (e.g., 'user_id', 'user')"
                },
                "start_from": {
                    "type": "string",
                    "enum": ["owner", "document_field", "linked_doc", "context"],
                    "default": "owner",
                    "description": "How to determine the starting record"
                },
                "start_field": {
                    "type": "string",
                    "description": "Field name when start_from is 'document_field' or 'linked_doc'"
                },
                "link_to_hierarchy": {
                    "type": "string",
                    "description": "When start_from='linked_doc', field on linked doc that points to hierarchy"
                },
                "level_mode": {
                    "type": "string",
                    "enum": ["fixed", "until_condition", "all_up_to"],
                    "default": "fixed",
                    "description": "How to determine where to stop walking"
                },
                "levels_up": {
                    "type": "integer",
                    "default": 1,
                    "description": "Number of levels to walk up (for 'fixed' mode)"
                },
                "max_levels": {
                    "type": "integer",
                    "description": "Maximum levels to collect (for 'all_up_to' mode)"
                },
                "skip_levels": {
                    "type": "integer",
                    "default": 0,
                    "description": "Number of initial levels to skip"
                },
                "until_condition": {
                    "type": "object",
                    "description": "Condition to check when level_mode='until_condition'",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "authority_covers_amount",
                                "has_role",
                                "field_equals",
                                "has_permission",
                                "is_root"
                            ]
                        },
                        "amount_field": {"type": "string"},
                        "role": {"type": "string"},
                        "field": {"type": "string"},
                        "value": {},
                        "doctype": {"type": "string"},
                        "perm": {"type": "string"}
                    }
                },
                "include_start": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include starting user in results"
                },
                "max_depth": {
                    "type": "integer",
                    "default": 10,
                    "description": "Safety limit for hierarchy depth"
                },
                "fallback_resolver": {
                    "type": "object",
                    "description": "Fallback resolver if hierarchy walk fails"
                }
            },
            "required": ["hierarchy_doctype", "parent_field", "user_field"]
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        hierarchy_doctype = self.config["hierarchy_doctype"]
        parent_field = self.config["parent_field"]
        user_field = self.config["user_field"]
        level_mode = self.config.get("level_mode", "fixed")
        max_depth = self.config.get("max_depth", 10)
        skip_levels = self.config.get("skip_levels", 0)
        include_start = self.config.get("include_start", False)

        # Determine starting record in the hierarchy
        start_record = self._get_start_record(doc, context, hierarchy_doctype)

        if not start_record:
            return self._handle_fallback(doc, context, "Could not determine starting record for hierarchy walk")

        # Skip levels if configured
        if skip_levels > 0:
            start_record = self._skip_levels(
                start_record, hierarchy_doctype, parent_field, skip_levels, max_depth
            )
            if not start_record:
                return self._handle_fallback(doc, context, f"Reached end of hierarchy while skipping {skip_levels} levels")

        # Execute based on level mode
        if level_mode == "fixed":
            return self._resolve_fixed(
                start_record, hierarchy_doctype, parent_field, user_field,
                doc, context, include_start
            )

        elif level_mode == "until_condition":
            return self._resolve_until_condition(
                start_record, hierarchy_doctype, parent_field, user_field,
                doc, context, include_start
            )

        elif level_mode == "all_up_to":
            return self._resolve_all_up_to(
                start_record, hierarchy_doctype, parent_field, user_field,
                doc, context, include_start
            )

        else:
            raise ResolverConfigError(f"Unknown level_mode: {level_mode}")

    def _get_start_record(self, doc, context: dict, hierarchy_doctype: str) -> str | None:
        """Determine the starting record in the hierarchy."""
        start_from = self.config.get("start_from", "owner")
        start_field = self.config.get("start_field")
        link_to_hierarchy = self.config.get("link_to_hierarchy")

        if start_from == "owner":
            # Find hierarchy record for document owner
            owner = doc.owner if hasattr(doc, "owner") else None
            if not owner:
                return None
            return frappe.db.get_value(
                hierarchy_doctype,
                {self.config["user_field"]: owner},
                "name"
            )

        elif start_from == "document_field":
            # Read hierarchy record directly from document field
            if not start_field:
                raise ResolverConfigError("start_from='document_field' requires 'start_field'")
            return get_field_value(doc, start_field)

        elif start_from == "linked_doc":
            # Read from linked doc, then follow to hierarchy
            if not start_field:
                raise ResolverConfigError("start_from='linked_doc' requires 'start_field'")

            linked_value = get_field_value(doc, start_field)
            if not linked_value:
                return None

            if link_to_hierarchy:
                # Get the linked doc, then read hierarchy field from it
                meta = frappe.get_meta(doc.doctype)
                field_meta = meta.get_field(start_field)
                if field_meta and field_meta.fieldtype == "Link":
                    linked_doctype = field_meta.options
                    return frappe.db.get_value(linked_doctype, linked_value, link_to_hierarchy)

            return linked_value

        elif start_from == "context":
            # Read from workflow context
            if not start_field:
                raise ResolverConfigError("start_from='context' requires 'start_field'")
            return context.get(start_field) if context else None

        return None

    def _skip_levels(
        self,
        start_record: str,
        hierarchy_doctype: str,
        parent_field: str,
        skip_levels: int,
        max_depth: int
    ) -> str | None:
        """Skip N levels up the hierarchy."""
        current = start_record
        for _ in range(min(skip_levels, max_depth)):
            parent = frappe.db.get_value(hierarchy_doctype, current, parent_field)
            if not parent:
                return None
            current = parent
        return current

    def _resolve_fixed(
        self,
        start_record: str,
        hierarchy_doctype: str,
        parent_field: str,
        user_field: str,
        doc,
        context: dict,
        include_start: bool
    ) -> list[str]:
        """Walk exactly N levels up."""
        levels_up = self.config.get("levels_up", 1)
        max_depth = self.config.get("max_depth", 10)

        users = []

        # Optionally include starting user
        if include_start:
            start_user = frappe.db.get_value(hierarchy_doctype, start_record, user_field)
            if start_user:
                users.append(start_user)

        # Walk up N levels
        user = get_hierarchy_user(
            start_record, hierarchy_doctype, parent_field, user_field,
            levels_up=levels_up, max_depth=max_depth
        )

        if user:
            if user not in users:
                users.append(user)
            return users

        if users:
            return users

        return self._handle_fallback(
            doc, context,
            f"Could not walk {levels_up} levels up {hierarchy_doctype} from {start_record}"
        )

    def _resolve_until_condition(
        self,
        start_record: str,
        hierarchy_doctype: str,
        parent_field: str,
        user_field: str,
        doc,
        context: dict,
        include_start: bool
    ) -> list[str]:
        """Walk until a condition is met."""
        until_condition = self.config.get("until_condition", {})
        condition_type = until_condition.get("type", "is_root")
        max_depth = self.config.get("max_depth", 10)

        # Build condition function
        condition_fn = self._build_condition_fn(condition_type, until_condition, doc, context)

        user = walk_hierarchy_until(
            start_record, hierarchy_doctype, parent_field, user_field,
            condition_fn=condition_fn,
            max_depth=max_depth,
            include_start=include_start,
            collect_all=False
        )

        if user:
            return [user] if isinstance(user, str) else user

        return self._handle_fallback(
            doc, context,
            f"Could not find user matching condition '{condition_type}' in {hierarchy_doctype}"
        )

    def _resolve_all_up_to(
        self,
        start_record: str,
        hierarchy_doctype: str,
        parent_field: str,
        user_field: str,
        doc,
        context: dict,
        include_start: bool
    ) -> list[str]:
        """Collect all users up to N levels."""
        max_levels = self.config.get("max_levels", 3)
        max_depth = self.config.get("max_depth", 10)

        # Build a condition that's never true (to collect all)
        level_counter = {"count": 0}

        def level_limit_condition(record, user):
            level_counter["count"] += 1
            return level_counter["count"] >= max_levels

        users = walk_hierarchy_until(
            start_record, hierarchy_doctype, parent_field, user_field,
            condition_fn=level_limit_condition,
            max_depth=max_depth,
            include_start=include_start,
            collect_all=True
        )

        if users:
            return users

        return self._handle_fallback(doc, context, f"No users found in {hierarchy_doctype} hierarchy")

    def _build_condition_fn(self, condition_type: str, config: dict, doc, context: dict):
        """Build a condition function for walk_hierarchy_until."""

        if condition_type == "authority_covers_amount":
            amount_field = config.get("amount_field", "grand_total")
            amount = get_field_value(doc, amount_field) or 0

            def check_authority(record, user):
                authority = frappe.db.get_value(
                    "Delegation Authority",
                    {"user": user, "is_active": 1},
                    "max_amount"
                )
                return authority and float(authority) >= float(amount)

            return check_authority

        elif condition_type == "has_role":
            role = config.get("role")

            def check_role(record, user):
                return role in frappe.get_roles(user)

            return check_role

        elif condition_type == "field_equals":
            field = config.get("field")
            value = config.get("value")
            hierarchy_doctype = self.config["hierarchy_doctype"]

            def check_field(record, user):
                record_value = frappe.db.get_value(hierarchy_doctype, record, field)
                return record_value == value

            return check_field

        elif condition_type == "has_permission":
            doctype = config.get("doctype", doc.doctype)
            perm = config.get("perm", "submit")

            def check_permission(record, user):
                return frappe.has_permission(doctype, perm, user=user)

            return check_permission

        elif condition_type == "is_root":
            hierarchy_doctype = self.config["hierarchy_doctype"]
            parent_field = self.config["parent_field"]

            def check_root(record, user):
                parent = frappe.db.get_value(hierarchy_doctype, record, parent_field)
                return not parent

            return check_root

        else:
            # Default: always stop (effectively single level)
            return lambda record, user: True

    def _handle_fallback(self, doc, context: dict, error_msg: str) -> list[str]:
        """Handle fallback when hierarchy walk fails."""
        fallback_resolver = self.config.get("fallback_resolver")

        if fallback_resolver:
            from . import resolve_assignment
            return resolve_assignment(doc, fallback_resolver, context)

        raise NoAssigneeFoundError(error_msg)


# Convenience preset for Employee hierarchy (if HR module exists)

@register_resolver
class ReportingManagerResolver(AssignmentResolver):
    """
    Get reporting manager from Employee hierarchy.

    Shorthand for hierarchy_walk with Employee DocType.
    Only works if Employee DocType exists (HR module installed).
    """

    resolver_type = "reporting_manager"

    def validate_config(self) -> None:
        # Check if Employee doctype exists
        if not frappe.db.exists("DocType", "Employee"):
            raise ResolverConfigError(
                "ReportingManagerResolver requires Employee DocType. "
                "Use hierarchy_walk for custom hierarchy DocTypes."
            )

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "start_from": {
                    "type": "string",
                    "enum": ["owner", "document_field"],
                    "default": "owner",
                    "description": "How to find the starting employee"
                },
                "employee_field": {
                    "type": "string",
                    "description": "Field containing employee (when start_from='document_field')"
                },
                "levels_up": {
                    "type": "integer",
                    "default": 1,
                    "description": "Number of levels to walk up (1 = direct manager)"
                },
                "skip_levels": {
                    "type": "integer",
                    "default": 0,
                    "description": "Number of levels to skip"
                },
                "fallback_resolver": {
                    "type": "object",
                    "description": "Fallback resolver if no manager found"
                }
            }
        }

    def resolve(self, doc, context: dict = None) -> list[str]:
        # Build hierarchy_walk config
        config = {
            "hierarchy_doctype": "Employee",
            "parent_field": "reports_to",
            "user_field": "user_id",
            "start_from": self.config.get("start_from", "owner"),
            "start_field": self.config.get("employee_field"),
            "level_mode": "fixed",
            "levels_up": self.config.get("levels_up", 1),
            "skip_levels": self.config.get("skip_levels", 0),
            "fallback_resolver": self.config.get("fallback_resolver")
        }

        resolver = HierarchyWalkResolver(config)
        return resolver.resolve(doc, context)
