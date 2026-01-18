# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Base classes for Assignment Resolvers.

Assignment resolvers determine who should be assigned to handle an approval task
based on configurable rules. The resolver framework is pluggable, allowing
custom resolvers to be registered.
"""

from abc import ABC, abstractmethod
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime, getdate


class AssignmentResolver(ABC):
    """
    Base class for all assignment resolvers.

    Subclasses must implement:
    - resolver_type: str - Unique identifier for this resolver type
    - resolve() - Main resolution logic

    Optionally override:
    - validate_config() - Validate resolver configuration
    - get_config_schema() - Return JSON schema for configuration
    """

    resolver_type: str = None

    def __init__(self, config: dict = None):
        """
        Initialize resolver with configuration.

        Args:
            config: Resolver-specific configuration dict
        """
        self.config = config or {}
        self.validate_config()

    @abstractmethod
    def resolve(self, doc, context: dict = None) -> list[str]:
        """
        Resolve and return list of user IDs who can handle the task.

        Args:
            doc: The Frappe document being processed
            context: Workflow context dict with additional data

        Returns:
            List of user IDs (email addresses) who can be assigned

        Raises:
            ResolverError: If resolution fails
        """
        raise NotImplementedError

    def validate_config(self) -> None:
        """
        Validate the resolver configuration.
        Override in subclasses to add validation logic.

        Raises:
            ResolverConfigError: If configuration is invalid
        """
        pass

    def get_config_schema(self) -> dict:
        """
        Return JSON schema for resolver configuration.
        Used by the UI to render configuration forms.

        Returns:
            JSON schema dict
        """
        return {}

    def check_delegation(self, user: str, scope: dict = None) -> str:
        """
        Check if user has an active delegation and return delegate if so.

        Args:
            user: User ID to check
            scope: Optional dict with doctype/workflow to check scoped delegations

        Returns:
            Delegate user ID if delegation active, original user otherwise
        """
        if not user:
            return user

        delegation = get_active_delegation(user, scope)
        if delegation:
            # Prevent infinite delegation loops - limit depth
            visited = scope.get("_visited_users", set()) if scope else set()
            if delegation in visited:
                frappe.log_error(
                    f"Delegation loop detected: {user} -> {delegation}",
                    "Assignment Resolver"
                )
                return user

            visited.add(user)
            new_scope = {**(scope or {}), "_visited_users": visited}
            return self.check_delegation(delegation, new_scope)

        return user

    def apply_delegation(self, users: list[str], scope: dict = None) -> list[str]:
        """
        Apply delegation rules to a list of users.

        Args:
            users: List of user IDs
            scope: Optional scope dict for delegation checking

        Returns:
            List with delegations applied
        """
        result = []
        for user in users:
            delegated = self.check_delegation(user, scope)
            if delegated and delegated not in result:
                result.append(delegated)
        return result


class ResolverError(Exception):
    """Base exception for resolver errors."""
    pass


class ResolverConfigError(ResolverError):
    """Raised when resolver configuration is invalid."""
    pass


class ResolverNotFoundError(ResolverError):
    """Raised when a resolver type is not found in registry."""
    pass


class NoAssigneeFoundError(ResolverError):
    """Raised when resolver cannot find any valid assignees."""
    pass


def get_active_delegation(user: str, scope: dict = None) -> str | None:
    """
    Get active delegation for a user.

    Args:
        user: User ID to check
        scope: Optional dict with:
            - doctype: Filter to specific DocType
            - workflow: Filter to specific workflow

    Returns:
        Delegate user ID if active delegation exists, None otherwise
    """
    today = getdate()

    filters = {
        "delegator": user,
        "is_active": 1,
        "from_date": ["<=", today],
        "to_date": [">=", today]
    }

    delegations = frappe.get_all(
        "User Delegation",
        filters=filters,
        fields=["delegate", "scope", "name"],
        order_by="creation desc"
    )

    if not delegations:
        return None

    # Check scope matching
    for delegation in delegations:
        if delegation.scope == "All":
            return delegation.delegate

        if scope:
            # Check scoped delegation matches
            if delegation.scope == "Specific DocTypes" and scope.get("doctype"):
                scoped_doctypes = frappe.get_all(
                    "User Delegation DocType",
                    filters={"parent": delegation.name},
                    pluck="doctype"
                )
                if scope["doctype"] in scoped_doctypes:
                    return delegation.delegate

            elif delegation.scope == "Specific Workflows" and scope.get("workflow"):
                scoped_workflows = frappe.get_all(
                    "User Delegation Workflow",
                    filters={"parent": delegation.name},
                    pluck="workflow"
                )
                if scope["workflow"] in scoped_workflows:
                    return delegation.delegate

    return None


def get_field_value(doc, field_path: str) -> Any:
    """
    Get a field value from a document, supporting dot notation for linked docs.

    Args:
        doc: Frappe document
        field_path: Field name or dot-notation path (e.g., "customer.customer_name")

    Returns:
        Field value or None if not found
    """
    if not field_path:
        return None

    parts = field_path.split(".")
    current = doc

    for i, part in enumerate(parts):
        if current is None:
            return None

        if hasattr(current, part):
            value = getattr(current, part)
        elif isinstance(current, dict):
            value = current.get(part)
        else:
            return None

        # If this is a Link field and not the last part, fetch the linked doc
        if i < len(parts) - 1 and value:
            meta = frappe.get_meta(current.doctype if hasattr(current, "doctype") else type(current).__name__)
            field_meta = meta.get_field(part) if meta else None

            if field_meta and field_meta.fieldtype == "Link":
                try:
                    current = frappe.get_doc(field_meta.options, value)
                except frappe.DoesNotExistError:
                    return None
            else:
                current = value
        else:
            current = value

    return current


def get_users_with_role(role: str, tenant: str = None) -> list[str]:
    """
    Get all users with a specific role.

    Args:
        role: Role name
        tenant: Optional tenant/company to filter users

    Returns:
        List of user IDs
    """
    users = frappe.get_all(
        "Has Role",
        filters={"role": role, "parenttype": "User"},
        pluck="parent"
    )

    # Filter to enabled users
    enabled_users = frappe.get_all(
        "User",
        filters={
            "name": ["in", users],
            "enabled": 1
        },
        pluck="name"
    )

    # Filter by tenant if specified
    if tenant and enabled_users:
        # Users belong to tenant if they have the company in their allowed companies
        # or if their default company matches
        tenant_users = []
        for user in enabled_users:
            # Always include Administrator - they're not restricted by tenant
            if user == "Administrator":
                tenant_users.append(user)
                continue

            # System Manager users are typically not restricted by tenant either
            user_roles = frappe.get_roles(user)
            if "System Manager" in user_roles:
                tenant_users.append(user)
                continue

            # Check default company
            if frappe.db.get_default("company", user) == tenant:
                tenant_users.append(user)
                continue

            # Check allowed companies (if User Permission exists)
            allowed = frappe.get_all(
                "User Permission",
                filters={
                    "user": user,
                    "allow": "Company",
                    "for_value": tenant
                }
            )
            if allowed:
                tenant_users.append(user)

        return tenant_users

    return enabled_users


def get_linked_doc_user(
    doc,
    link_field: str,
    user_field: str,
    linked_doctype: str = None
) -> str | None:
    """
    Get user from a linked document's field.

    Generic helper that works with any DocType structure.

    Args:
        doc: Source Frappe document
        link_field: Field on doc that links to another DocType
        user_field: Field on linked doc that contains the User
        linked_doctype: Optional - DocType of linked doc (auto-detected if not provided)

    Returns:
        User ID or None if not found

    Example:
        # Get manager from cost center
        get_linked_doc_user(invoice, "cost_center", "custom_manager")

        # Get approver from department
        get_linked_doc_user(expense, "department", "custom_head")
    """
    if not doc or not link_field or not user_field:
        return None

    # Get the linked doc name from the source doc
    linked_name = get_field_value(doc, link_field)
    if not linked_name:
        return None

    # Determine the linked DocType if not provided
    if not linked_doctype:
        meta = frappe.get_meta(doc.doctype)
        field_meta = meta.get_field(link_field)
        if not field_meta or field_meta.fieldtype != "Link":
            return None
        linked_doctype = field_meta.options

    # Get the user field value from the linked doc
    try:
        return frappe.db.get_value(linked_doctype, linked_name, user_field)
    except Exception:
        return None


def get_hierarchy_user(
    start_record: str,
    hierarchy_doctype: str,
    parent_field: str,
    user_field: str,
    levels_up: int = 1,
    max_depth: int = 10
) -> str | None:
    """
    Walk up a hierarchy and return user at specified level.

    Generic helper that works with any hierarchical DocType.

    Args:
        start_record: Name of the starting record in the hierarchy
        hierarchy_doctype: DocType name (e.g., "Employee", "Approver", custom DocType)
        parent_field: Field that links to parent record (e.g., "reports_to", "parent_approver")
        user_field: Field containing the User link (e.g., "user_id", "user")
        levels_up: How many levels to walk up (1 = direct parent)
        max_depth: Safety limit to prevent infinite loops

    Returns:
        User ID at the target level, or None if not found

    Example:
        # Get direct manager's user
        get_hierarchy_user("EMP-001", "Employee", "reports_to", "user_id", levels_up=1)

        # Get skip-level manager (manager's manager)
        get_hierarchy_user("EMP-001", "Employee", "reports_to", "user_id", levels_up=2)
    """
    if not start_record or not hierarchy_doctype:
        return None

    current = start_record
    visited = set()

    for level in range(max_depth):
        if current in visited:
            # Circular reference detected
            frappe.log_error(
                f"Circular hierarchy detected in {hierarchy_doctype}: {current}",
                "Assignment Resolver"
            )
            return None

        visited.add(current)

        # Get parent
        parent = frappe.db.get_value(hierarchy_doctype, current, parent_field)
        if not parent:
            # Reached root of hierarchy
            return None

        current = parent

        # Check if we've reached the target level
        if level + 1 >= levels_up:
            return frappe.db.get_value(hierarchy_doctype, current, user_field)

    return None


def walk_hierarchy_until(
    start_record: str,
    hierarchy_doctype: str,
    parent_field: str,
    user_field: str,
    condition_fn,
    max_depth: int = 10,
    include_start: bool = False,
    collect_all: bool = False
) -> str | list[str] | None:
    """
    Walk up a hierarchy until a condition is met.

    Generic helper that works with any hierarchical DocType.

    Args:
        start_record: Name of the starting record in the hierarchy
        hierarchy_doctype: DocType name
        parent_field: Field that links to parent record
        user_field: Field containing the User link
        condition_fn: Function(record_name, user) -> bool that returns True when to stop
        max_depth: Safety limit
        include_start: Whether to include starting record in evaluation
        collect_all: If True, return list of all users up to condition; if False, return single user

    Returns:
        User ID when condition met, list of users if collect_all, or None

    Example:
        # Walk until finding someone with "Approver" role
        walk_hierarchy_until(
            "EMP-001", "Employee", "reports_to", "user_id",
            condition_fn=lambda rec, user: "Approver" in frappe.get_roles(user)
        )
    """
    if not start_record or not hierarchy_doctype:
        return [] if collect_all else None

    current = start_record
    visited = set()
    collected_users = []

    # Optionally evaluate starting record
    if include_start:
        start_user = frappe.db.get_value(hierarchy_doctype, current, user_field)
        if start_user:
            if collect_all:
                collected_users.append(start_user)
            if condition_fn(current, start_user):
                return collected_users if collect_all else start_user

    for _ in range(max_depth):
        if current in visited:
            break

        visited.add(current)

        # Get parent
        parent = frappe.db.get_value(hierarchy_doctype, current, parent_field)
        if not parent:
            break

        current = parent

        # Get user at this level
        user = frappe.db.get_value(hierarchy_doctype, current, user_field)
        if user:
            if collect_all:
                collected_users.append(user)
            if condition_fn(current, user):
                return collected_users if collect_all else user

    return collected_users if collect_all else None


def validate_hierarchy_config(
    hierarchy_doctype: str,
    parent_field: str,
    user_field: str
) -> tuple[bool, str]:
    """
    Validate that a hierarchy configuration is valid.

    Args:
        hierarchy_doctype: DocType name to validate
        parent_field: Field that should link to parent
        user_field: Field that should contain User

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check DocType exists
    if not frappe.db.exists("DocType", hierarchy_doctype):
        return False, f"DocType '{hierarchy_doctype}' does not exist"

    meta = frappe.get_meta(hierarchy_doctype)

    # Check parent field exists and is a Link to same DocType
    parent_field_meta = meta.get_field(parent_field)
    if not parent_field_meta:
        return False, f"Field '{parent_field}' does not exist in {hierarchy_doctype}"

    if parent_field_meta.fieldtype != "Link":
        return False, f"Field '{parent_field}' must be a Link field"

    if parent_field_meta.options != hierarchy_doctype:
        return False, f"Field '{parent_field}' must link to {hierarchy_doctype} (links to {parent_field_meta.options})"

    # Check user field exists and is a Link to User
    user_field_meta = meta.get_field(user_field)
    if not user_field_meta:
        return False, f"Field '{user_field}' does not exist in {hierarchy_doctype}"

    if user_field_meta.fieldtype != "Link" or user_field_meta.options != "User":
        return False, f"Field '{user_field}' must be a Link to User"

    return True, ""
