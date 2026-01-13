# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Assignment Resolver Registry.

This module provides a pluggable resolver system for determining who should
be assigned to handle approval tasks in workflows.

Usage:
    from xstate_workflow.resolvers import get_resolver, resolve_assignment

    # Get a resolver instance
    resolver = get_resolver("role", {"role": "Approver", "strategy": "round_robin"})
    users = resolver.resolve(doc, context)

    # Or use the convenience function
    users = resolve_assignment(doc, resolver_config, context)

Available resolver types:
    - role: Assign to users with a specific role
    - static_user: Assign to a specific user
    - document_field: Read user from a document field
    - linked_doc_field: Read user from a linked document's field
    - hierarchy_walk: Walk up any hierarchical DocType
    - delegation_matrix: Query Delegation Authority table
"""

from typing import TYPE_CHECKING

from .base import (
    AssignmentResolver,
    ResolverError,
    ResolverConfigError,
    ResolverNotFoundError,
    NoAssigneeFoundError,
    get_field_value,
    get_users_with_role,
    get_linked_doc_user,
    get_hierarchy_user,
    walk_hierarchy_until,
    validate_hierarchy_config,
    get_active_delegation,
)

if TYPE_CHECKING:
    pass

# Registry of resolver classes
_RESOLVER_REGISTRY: dict[str, type[AssignmentResolver]] = {}


def register_resolver(resolver_class: type[AssignmentResolver]) -> type[AssignmentResolver]:
    """
    Register a resolver class in the registry.

    Can be used as a decorator:
        @register_resolver
        class MyResolver(AssignmentResolver):
            resolver_type = "my_resolver"
            ...

    Args:
        resolver_class: The resolver class to register

    Returns:
        The same class (for decorator usage)

    Raises:
        ValueError: If resolver_type is not set or already registered
    """
    if not resolver_class.resolver_type:
        raise ValueError(f"Resolver class {resolver_class.__name__} must have resolver_type set")

    if resolver_class.resolver_type in _RESOLVER_REGISTRY:
        # Allow re-registration (for hot-reloading during development)
        pass

    _RESOLVER_REGISTRY[resolver_class.resolver_type] = resolver_class
    return resolver_class


def get_resolver(resolver_type: str, config: dict = None) -> AssignmentResolver:
    """
    Get a resolver instance by type.

    Args:
        resolver_type: The resolver type identifier
        config: Configuration dict for the resolver

    Returns:
        Configured resolver instance

    Raises:
        ResolverNotFoundError: If resolver type is not registered
    """
    if resolver_type not in _RESOLVER_REGISTRY:
        raise ResolverNotFoundError(f"Unknown resolver type: {resolver_type}")

    resolver_class = _RESOLVER_REGISTRY[resolver_type]
    return resolver_class(config)


def get_registered_resolvers() -> dict[str, type[AssignmentResolver]]:
    """
    Get all registered resolver classes.

    Returns:
        Dict mapping resolver_type to resolver class
    """
    return dict(_RESOLVER_REGISTRY)


def resolve_assignment(
    doc,
    resolver_config: dict,
    context: dict = None,
    apply_delegation: bool = True
) -> list[str]:
    """
    Resolve assignment using configuration dict.

    Convenience function that creates a resolver and runs it.

    Args:
        doc: The Frappe document being processed
        resolver_config: Dict with "type" and resolver-specific config
        context: Workflow context dict
        apply_delegation: Whether to check for user delegations

    Returns:
        List of user IDs

    Raises:
        ResolverError: If resolution fails

    Example:
        users = resolve_assignment(
            doc=invoice,
            resolver_config={
                "type": "hierarchy_walk",
                "hierarchy_doctype": "Employee",
                "parent_field": "reports_to",
                "user_field": "user_id",
                "level_mode": "fixed",
                "levels_up": 1
            },
            context={"amount": 50000}
        )
    """
    resolver_type = resolver_config.get("type")
    if not resolver_type:
        raise ResolverConfigError("Resolver config must have 'type' field")

    resolver = get_resolver(resolver_type, resolver_config)
    users = resolver.resolve(doc, context)

    if apply_delegation and users:
        scope = {
            "doctype": doc.doctype if hasattr(doc, "doctype") else None,
            "workflow": context.get("workflow_name") if context else None
        }
        users = resolver.apply_delegation(users, scope)

    return users


def get_resolver_schema(resolver_type: str) -> dict:
    """
    Get the JSON schema for a resolver's configuration.

    Args:
        resolver_type: The resolver type identifier

    Returns:
        JSON schema dict

    Raises:
        ResolverNotFoundError: If resolver type is not registered
    """
    if resolver_type not in _RESOLVER_REGISTRY:
        raise ResolverNotFoundError(f"Unknown resolver type: {resolver_type}")

    resolver_class = _RESOLVER_REGISTRY[resolver_type]
    # Create a temporary instance to get schema
    return resolver_class({}).get_config_schema()


def list_resolver_types() -> list[dict]:
    """
    List all available resolver types with their metadata.

    Returns:
        List of dicts with type, description, and schema
    """
    result = []
    for resolver_type, resolver_class in _RESOLVER_REGISTRY.items():
        result.append({
            "type": resolver_type,
            "description": resolver_class.__doc__.strip().split("\n")[0] if resolver_class.__doc__ else "",
            "schema": resolver_class({}).get_config_schema()
        })
    return result


# Import and register built-in resolvers
# This is done at the end to avoid circular imports
def _register_builtin_resolvers():
    """Register all built-in resolver implementations."""
    from . import role_resolver
    from . import user_resolver
    from . import linked_doc_resolver
    from . import hierarchy_resolver
    from . import delegation_resolver


# Don't auto-register on import to avoid import errors during development
# Call _register_builtin_resolvers() explicitly or let it happen on first use


def _ensure_resolvers_registered():
    """Ensure built-in resolvers are registered. Called lazily."""
    if not _RESOLVER_REGISTRY:
        try:
            _register_builtin_resolvers()
        except ImportError:
            # During initial development, some resolver files may not exist yet
            pass


# Lazy registration wrapper for get_resolver
_original_get_resolver = get_resolver


def get_resolver(resolver_type: str, config: dict = None) -> AssignmentResolver:
    """Get a resolver instance by type (with lazy registration)."""
    _ensure_resolvers_registered()
    return _original_get_resolver(resolver_type, config)


__all__ = [
    # Base classes and exceptions
    "AssignmentResolver",
    "ResolverError",
    "ResolverConfigError",
    "ResolverNotFoundError",
    "NoAssigneeFoundError",

    # Registry functions
    "register_resolver",
    "get_resolver",
    "get_registered_resolvers",
    "resolve_assignment",
    "get_resolver_schema",
    "list_resolver_types",

    # Helper functions
    "get_field_value",
    "get_users_with_role",
    "get_linked_doc_user",
    "get_hierarchy_user",
    "walk_hierarchy_until",
    "validate_hierarchy_config",
    "get_active_delegation",
]
