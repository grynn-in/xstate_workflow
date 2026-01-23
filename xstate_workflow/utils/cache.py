# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Caching utilities for XState Workflow performance optimization.

This module provides caching mechanisms for frequently accessed data:
- State machine configurations
- Parsed JSON configs
- Guard and action function lookups
- Available events calculations
"""

import json
import functools
from typing import Any, Callable

import frappe
from frappe.utils import cint


# ============================================================================
# CONFIGURATION
# ============================================================================

# Cache TTL in seconds (default: 5 minutes)
MACHINE_CONFIG_TTL = 300
GUARD_CACHE_TTL = 300
EVENTS_CACHE_TTL = 60


# ============================================================================
# REDIS-BACKED CACHING
# ============================================================================

def get_cached_machine_config(machine_name: str) -> dict | None:
    """
    Get cached state machine configuration from Redis.

    Args:
        machine_name: State Machine name

    Returns:
        Parsed JSON config dict or None if not cached
    """
    cache_key = f"xsw:machine_config:{machine_name}"
    cached = frappe.cache().get_value(cache_key)

    if cached:
        return json.loads(cached)

    return None


def set_cached_machine_config(machine_name: str, config: dict, ttl: int = None):
    """
    Cache a state machine configuration in Redis.

    Args:
        machine_name: State Machine name
        config: Parsed JSON config dict
        ttl: Time to live in seconds (default: MACHINE_CONFIG_TTL)
    """
    cache_key = f"xsw:machine_config:{machine_name}"
    frappe.cache().set_value(
        cache_key,
        json.dumps(config),
        expires_in_sec=ttl or MACHINE_CONFIG_TTL
    )


def invalidate_machine_config_cache(machine_name: str):
    """
    Invalidate cached machine configuration.

    Called when a State Machine is updated.

    Args:
        machine_name: State Machine name
    """
    cache_key = f"xsw:machine_config:{machine_name}"
    frappe.cache().delete_value(cache_key)

    # Also invalidate related caches
    frappe.cache().delete_keys(f"xsw:events:{machine_name}:*")
    frappe.cache().delete_keys(f"xsw:guards:{machine_name}:*")


def get_machine_config_with_cache(machine_name: str) -> dict:
    """
    Get machine configuration with caching.

    Tries cache first, falls back to database.

    Args:
        machine_name: State Machine name

    Returns:
        Parsed JSON config dict
    """
    # Try cache first
    config = get_cached_machine_config(machine_name)
    if config:
        return config

    # Load from database
    if not frappe.db.exists("State Machine", machine_name):
        return {}

    machine = frappe.get_doc("State Machine", machine_name)
    config = json.loads(machine.json_config)

    # Cache for next time
    set_cached_machine_config(machine_name, config)

    return config


# ============================================================================
# AVAILABLE EVENTS CACHING
# ============================================================================

def get_cached_events(machine_name: str, state: str) -> list | None:
    """
    Get cached available events for a state.

    Note: This cache doesn't account for context-dependent guards.
    Use only for pre-computation of structure, not final guard evaluation.

    Args:
        machine_name: State Machine name
        state: Current state name

    Returns:
        List of event info dicts or None
    """
    cache_key = f"xsw:events:{machine_name}:{state}"
    cached = frappe.cache().get_value(cache_key)

    if cached:
        return json.loads(cached)

    return None


def set_cached_events(machine_name: str, state: str, events: list, ttl: int = None):
    """
    Cache available events for a state.

    Args:
        machine_name: State Machine name
        state: Current state name
        events: List of event info dicts
        ttl: Time to live in seconds
    """
    cache_key = f"xsw:events:{machine_name}:{state}"
    frappe.cache().set_value(
        cache_key,
        json.dumps(events),
        expires_in_sec=ttl or EVENTS_CACHE_TTL
    )


# ============================================================================
# LRU MEMOIZATION
# ============================================================================

def memoize_config_lookup(func: Callable) -> Callable:
    """
    Decorator to memoize config lookup functions within a request.

    Uses frappe.local for request-scoped caching.

    Args:
        func: Function to memoize

    Returns:
        Memoized function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create cache key from function name and arguments
        key = f"xsw_memo_{func.__name__}_{hash(str(args) + str(kwargs))}"

        if not hasattr(frappe.local, 'xsw_memo_cache'):
            frappe.local.xsw_memo_cache = {}

        cache = frappe.local.xsw_memo_cache

        if key in cache:
            return cache[key]

        result = func(*args, **kwargs)
        cache[key] = result

        return result

    return wrapper


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

def get_multiple_machine_configs(machine_names: list[str]) -> dict[str, dict]:
    """
    Batch load multiple machine configurations.

    More efficient than loading one by one.

    Args:
        machine_names: List of State Machine names

    Returns:
        Dict mapping machine_name to config
    """
    result = {}
    missing = []

    # Check cache first
    for name in machine_names:
        config = get_cached_machine_config(name)
        if config:
            result[name] = config
        else:
            missing.append(name)

    # Batch load missing from database
    if missing:
        machines = frappe.get_all(
            "State Machine",
            filters={"name": ["in", missing]},
            fields=["name", "json_config"]
        )

        for m in machines:
            config = json.loads(m.json_config)
            result[m.name] = config
            set_cached_machine_config(m.name, config)

    return result


def batch_get_instances(doc_refs: list[tuple[str, str]]) -> dict[str, Any]:
    """
    Batch load workflow instances for multiple documents.

    Args:
        doc_refs: List of (doctype, docname) tuples

    Returns:
        Dict mapping "doctype:docname" to instance or None
    """
    if not doc_refs:
        return {}

    # Build OR filter
    or_filters = []
    for doctype, docname in doc_refs:
        or_filters.append({
            "ref_doctype": doctype,
            "ref_docname": docname
        })

    instances = frappe.get_all(
        "Machine Instance",
        or_filters=or_filters,
        fields=["name", "ref_doctype", "ref_docname", "current_state", "status", "context"]
    )

    result = {}
    for inst in instances:
        key = f"{inst.ref_doctype}:{inst.ref_docname}"
        result[key] = inst

    return result


# ============================================================================
# STATE CONFIG LOOKUP OPTIMIZATION
# ============================================================================

@memoize_config_lookup
def find_state_config_cached(config_json: str, state_path: str) -> dict | None:
    """
    Find state configuration with memoization.

    Args:
        config_json: JSON string of machine config (for hashing)
        state_path: Dot-notation path to state

    Returns:
        State config dict or None
    """
    config = json.loads(config_json)
    return _find_state_recursive(config.get("states", {}), state_path.split("."))


def _find_state_recursive(states: dict, path_parts: list[str]) -> dict | None:
    """
    Recursively find a state in nested structure.

    Args:
        states: States dict to search
        path_parts: List of state names forming the path

    Returns:
        State config or None
    """
    if not path_parts:
        return None

    current = path_parts[0]
    remaining = path_parts[1:]

    if current not in states:
        return None

    state_config = states[current]

    if not remaining:
        return state_config

    # Look in nested states
    nested_states = state_config.get("states", {})
    return _find_state_recursive(nested_states, remaining)


# ============================================================================
# CACHE WARMING
# ============================================================================

def warm_machine_caches(machine_names: list[str] = None):
    """
    Pre-populate caches for frequently used machines.

    Called during boot or by scheduler.

    Args:
        machine_names: Specific machines to warm, or None for all active
    """
    if machine_names is None:
        machine_names = [m.name for m in frappe.get_all(
            "State Machine",
            filters={"is_active": 1},
            pluck="name"
        )]

    for name in machine_names:
        try:
            config = get_machine_config_with_cache(name)

            # Also cache events for common states
            initial_state = config.get("initial")
            if initial_state:
                from xstate_workflow.workflow_engine import get_next_events
                events = get_next_events(name, initial_state, {})
                set_cached_events(name, initial_state, events)

        except Exception as e:
            frappe.log_error(f"Cache warming failed for {name}: {e}")


def clear_all_workflow_caches():
    """
    Clear all workflow-related caches.

    Useful for debugging or after bulk updates.
    """
    frappe.cache().delete_keys("xsw:*")


# ============================================================================
# APPROVAL COUNTS CACHING
# ============================================================================

APPROVAL_COUNTS_TTL = 30  # seconds


def get_cached_approval_counts(user: str) -> dict | None:
    """
    Get cached approval task counts for a user.

    Args:
        user: User ID

    Returns:
        Dict of counts by status or None if not cached
    """
    cache_key = f"xsw:approval_counts:{user}"
    cached = frappe.cache().get_value(cache_key)

    if cached:
        return json.loads(cached)

    return None


def set_cached_approval_counts(user: str, counts: dict, ttl: int = None):
    """
    Cache approval task counts for a user.

    Args:
        user: User ID
        counts: Dict of counts by status
        ttl: Time to live in seconds (default: APPROVAL_COUNTS_TTL)
    """
    cache_key = f"xsw:approval_counts:{user}"
    frappe.cache().set_value(
        cache_key,
        json.dumps(counts),
        expires_in_sec=ttl or APPROVAL_COUNTS_TTL
    )


def invalidate_approval_counts(user: str = None):
    """
    Invalidate cached approval counts.

    Args:
        user: Specific user to invalidate, or None to invalidate all
    """
    if user:
        cache_key = f"xsw:approval_counts:{user}"
        frappe.cache().delete_value(cache_key)
    else:
        frappe.cache().delete_keys("xsw:approval_counts:*")
