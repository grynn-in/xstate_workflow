# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Mermaid State Diagram Generator for XState Workflow

Generates Mermaid stateDiagram-v2 definitions from XState JSON configs.
Server-side generation for optimal performance.
"""

from typing import Any


def generate_mermaid_diagram(
    config: dict,
    current_state: str | None = None,
    transition_log: list | None = None,
    all_states: list | None = None,
) -> str:
    """
    Generate a Mermaid stateDiagram-v2 definition from XState config.

    Args:
        config: XState JSON configuration dict
        current_state: Currently active state name
        transition_log: List of transition log entries
        all_states: Optional list of all state names

    Returns:
        Mermaid diagram definition string
    """
    transition_log = transition_log or []
    lines = ["stateDiagram-v2"]

    # Track visited states from transition log
    visited_states = set()
    for entry in transition_log:
        if entry.get("from_state"):
            visited_states.add(entry["from_state"])
        if entry.get("to_state"):
            visited_states.add(entry["to_state"])

    # Get initial state and states config
    initial_state = config.get("initial", "")
    states = config.get("states", {})

    # Add initial transition
    if initial_state:
        lines.append(f"    [*] --> {_escape_state_id(initial_state)}")

    # Process each state and its transitions
    _process_states(states, lines)

    # Add styling classes
    lines.append("")
    lines.append("    %% Styling")
    lines.append(
        "    classDef current fill:#3b82f6,stroke:#1d4ed8,stroke-width:3px,color:#fff"
    )
    lines.append("    classDef visited fill:#d1fae5,stroke:#10b981,stroke-width:2px")
    lines.append("    classDef final fill:#f3f4f6,stroke:#6b7280,stroke-width:2px")

    # Apply current state class
    if current_state:
        escaped_current = _escape_state_id(current_state.split(".")[-1])
        lines.append(f"    class {escaped_current} current")

    # Apply visited state classes (excluding current state)
    visited_not_current = [s for s in visited_states if s and s != current_state]
    if visited_not_current:
        escaped_visited = [_escape_state_id(s.split(".")[-1]) for s in visited_not_current]
        lines.append(f"    class {','.join(escaped_visited)} visited")

    return "\n".join(lines)


def _process_states(states: dict, lines: list, parent_path: str = "") -> None:
    """Process states and add transitions to the diagram."""
    for state_name, state_config in states.items():
        escaped_name = _escape_state_id(state_name)

        # Check if this is a compound state (has nested states)
        nested_states = state_config.get("states")
        if nested_states:
            lines.append(f"    state {escaped_name} {{")
            # Add initial state for compound
            nested_initial = state_config.get("initial")
            if nested_initial:
                lines.append(f"        [*] --> {_escape_state_id(nested_initial)}")
            _process_states(nested_states, lines, state_name)
            lines.append("    }")

        # Process transitions
        on_transitions = state_config.get("on", {})
        for event_name, transition in on_transitions.items():
            _add_transition(lines, escaped_name, event_name, transition)

        # Add final state marker
        if state_config.get("type") == "final":
            lines.append(f"    {escaped_name} --> [*]")


def _add_transition(
    lines: list, from_state: str, event_name: str, transition: Any
) -> None:
    """Add a transition to the diagram."""
    if isinstance(transition, str):
        # Simple string target
        to_state = _escape_state_id(transition)
        lines.append(f"    {from_state} --> {to_state}: {event_name}")

    elif isinstance(transition, dict):
        # Object with target and optional guard
        target = transition.get("target")
        if target:
            to_state = _escape_state_id(target)
            guard = transition.get("guard") or transition.get("cond")
            if guard:
                lines.append(f"    {from_state} --> {to_state}: {event_name} [{guard}]")
            else:
                lines.append(f"    {from_state} --> {to_state}: {event_name}")

    elif isinstance(transition, list):
        # Multiple conditional transitions
        for t in transition:
            if isinstance(t, dict):
                target = t.get("target")
                if target:
                    to_state = _escape_state_id(target)
                    guard = t.get("guard") or t.get("cond")
                    if guard:
                        lines.append(
                            f"    {from_state} --> {to_state}: {event_name} [{guard}]"
                        )
                    else:
                        lines.append(f"    {from_state} --> {to_state}: {event_name}")
            elif isinstance(t, str):
                to_state = _escape_state_id(t)
                lines.append(f"    {from_state} --> {to_state}: {event_name}")


def _escape_state_id(state_id: str) -> str:
    """
    Escape state ID for Mermaid compatibility.

    Mermaid doesn't handle certain characters well in state IDs.
    """
    # Replace problematic characters
    return state_id.replace("-", "_").replace(" ", "_").replace(".", "_")


def generate_tooltip_data(transition_log: list) -> dict:
    """
    Generate tooltip data for each state from transition history.

    Args:
        transition_log: List of transition log entries

    Returns:
        Dict mapping state names to tooltip data with visit history
    """
    tooltip_data = {}

    for entry in transition_log:
        from_state = entry.get("from_state")
        to_state = entry.get("to_state")

        # Record exit info for from_state
        if from_state:
            if from_state not in tooltip_data:
                tooltip_data[from_state] = {"visits": []}
            tooltip_data[from_state]["visits"].append(
                {
                    "type": "exit",
                    "event": entry.get("event"),
                    "timestamp": entry.get("timestamp"),
                    "user": entry.get("user"),
                    "to_state": to_state,
                }
            )

        # Record entry info for to_state
        if to_state:
            if to_state not in tooltip_data:
                tooltip_data[to_state] = {"visits": []}
            tooltip_data[to_state]["visits"].append(
                {
                    "type": "entry",
                    "event": entry.get("event"),
                    "timestamp": entry.get("timestamp"),
                    "user": entry.get("user"),
                    "from_state": from_state,
                }
            )

    return tooltip_data
