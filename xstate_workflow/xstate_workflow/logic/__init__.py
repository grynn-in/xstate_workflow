# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Logic modules for XState workflows.

Each module can define:
- guards: Dict of guard_name -> function(context, event) -> bool
- actions: Dict of action_name -> function(context, event) -> context
"""
