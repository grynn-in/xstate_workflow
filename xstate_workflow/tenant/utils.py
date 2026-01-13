# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Tenant Utility Functions.

Functions for managing multi-tenant isolation in workflows.
Tenant is typically Company in ERPNext context.
"""

from typing import TYPE_CHECKING

import frappe
from frappe import _

if TYPE_CHECKING:
    from frappe.model.document import Document


def get_tenant_from_doc(doc: "Document") -> str | None:
    """
    Extract tenant from a document.

    Checks multiple common tenant fields in order of priority.

    Args:
        doc: Frappe document

    Returns:
        Tenant value (typically Company name) or None
    """
    # Check common tenant fields in priority order
    tenant_fields = ["company", "tenant", "default_company"]

    for field in tenant_fields:
        if hasattr(doc, field) and doc.get(field):
            return doc.get(field)

    # Try to get from linked document
    # For child tables, check parent
    if hasattr(doc, "parent") and doc.parent:
        try:
            parent_doc = frappe.get_doc(doc.parenttype, doc.parent)
            return get_tenant_from_doc(parent_doc)
        except Exception:
            pass

    return None


def get_user_tenant(user: str = None) -> str | None:
    """
    Get the primary tenant for a user.

    Uses the user's default company or first allowed company.

    Args:
        user: User ID (defaults to session user)

    Returns:
        Tenant value or None
    """
    user = user or frappe.session.user

    if user == "Administrator":
        return None  # Administrator sees all tenants

    # Check user's default company
    default_company = frappe.db.get_value("User", user, "default_company")
    if default_company:
        return default_company

    # Check UserPermission for Company
    allowed_companies = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Company"
        },
        pluck="for_value",
        limit=1
    )

    if allowed_companies:
        return allowed_companies[0]

    # Fallback: get first company user has access to
    # This requires Company DocType to exist
    try:
        companies = frappe.get_all(
            "Company",
            limit=1,
            pluck="name"
        )
        if companies:
            return companies[0]
    except Exception:
        pass

    return None


def scope_filters_by_tenant(
    filters: dict,
    tenant: str = None,
    tenant_field: str = "tenant"
) -> dict:
    """
    Add tenant scope to query filters.

    Args:
        filters: Existing filter dict
        tenant: Tenant value (auto-detected if None)
        tenant_field: Name of tenant field (default: "tenant")

    Returns:
        Updated filters dict with tenant scope
    """
    if filters is None:
        filters = {}

    # Get tenant if not provided
    if tenant is None:
        tenant = get_user_tenant()

    # Don't scope if no tenant (e.g., Administrator)
    if tenant:
        filters[tenant_field] = tenant

    return filters


def get_tenant_scoped_query(
    doctype: str,
    fields: list = None,
    filters: dict = None,
    tenant: str = None,
    tenant_field: str = "tenant",
    **kwargs
) -> list:
    """
    Execute a tenant-scoped query.

    Wrapper around frappe.get_all that adds tenant filtering.

    Args:
        doctype: DocType to query
        fields: Fields to return
        filters: Query filters
        tenant: Tenant value (auto-detected if None)
        tenant_field: Name of tenant field
        **kwargs: Additional arguments for frappe.get_all

    Returns:
        Query results
    """
    scoped_filters = scope_filters_by_tenant(
        filters or {},
        tenant,
        tenant_field
    )

    return frappe.get_all(
        doctype,
        fields=fields,
        filters=scoped_filters,
        **kwargs
    )


def validate_tenant_access(
    doc: "Document",
    user: str = None,
    throw: bool = True
) -> bool:
    """
    Validate user has access to document's tenant.

    Args:
        doc: Document to check
        user: User to check (defaults to session user)
        throw: If True, throw error on failure

    Returns:
        True if access is valid

    Raises:
        frappe.PermissionError if throw=True and no access
    """
    user = user or frappe.session.user

    # Administrator always has access
    if user == "Administrator":
        return True

    doc_tenant = get_tenant_from_doc(doc)

    # No tenant restriction on document
    if not doc_tenant:
        return True

    user_tenant = get_user_tenant(user)

    # User has no tenant restriction
    if not user_tenant:
        return True

    # Check if tenant matches
    if doc_tenant == user_tenant:
        return True

    # Check if user has permission for this company
    has_permission = frappe.db.exists(
        "User Permission",
        {
            "user": user,
            "allow": "Company",
            "for_value": doc_tenant
        }
    )

    if has_permission:
        return True

    if throw:
        frappe.throw(
            _("You don't have access to documents from {0}").format(doc_tenant),
            frappe.PermissionError
        )

    return False


def set_tenant_on_insert(doc: "Document", method: str = None):
    """
    Hook to automatically set tenant field on document insert.

    Args:
        doc: Document being inserted
        method: Hook method name (unused)
    """
    if not hasattr(doc, "tenant") or doc.tenant:
        return

    # Try to get tenant from document itself
    tenant = get_tenant_from_doc(doc)

    if not tenant:
        # Fall back to user's tenant
        tenant = get_user_tenant()

    if tenant:
        doc.tenant = tenant


def get_permission_query_conditions(doctype: str, user: str = None) -> str:
    """
    Generate permission query conditions for tenant filtering.

    Use in DocType's permission_query_conditions.

    Args:
        doctype: DocType name
        user: User ID

    Returns:
        SQL WHERE clause string
    """
    user = user or frappe.session.user

    if user == "Administrator":
        return ""

    tenant = get_user_tenant(user)

    if not tenant:
        return ""

    # Check if doctype has tenant field
    meta = frappe.get_meta(doctype)
    if not meta.has_field("tenant"):
        return ""

    return f"`tab{doctype}`.`tenant` = '{frappe.db.escape(tenant)}'"


def has_permission(doc: "Document", ptype: str = "read", user: str = None) -> bool:
    """
    Permission check including tenant validation.

    Use in DocType's has_permission.

    Args:
        doc: Document to check
        ptype: Permission type
        user: User ID

    Returns:
        True if permission granted
    """
    user = user or frappe.session.user

    # Basic permission check
    if not frappe.has_permission(doc.doctype, ptype, doc=doc, user=user):
        return False

    # Tenant validation
    return validate_tenant_access(doc, user, throw=False)
