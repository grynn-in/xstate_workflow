# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Multi-Tenant Support Module.

Provides utilities for tenant isolation and scoping in workflows.
"""

from .utils import (
    get_tenant_from_doc,
    get_user_tenant,
    scope_filters_by_tenant,
    get_tenant_scoped_query,
)

__all__ = [
    "get_tenant_from_doc",
    "get_user_tenant",
    "scope_filters_by_tenant",
    "get_tenant_scoped_query",
]
