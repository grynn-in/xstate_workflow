# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class UserDelegation(Document):
    def validate(self):
        """Validate delegation data."""
        # Validate dates
        if self.from_date and self.to_date:
            if getdate(self.from_date) > getdate(self.to_date):
                frappe.throw(_("From Date cannot be after To Date"))

        # Prevent self-delegation
        if self.delegator == self.delegate:
            frappe.throw(_("Cannot delegate to yourself"))

        # Check for circular delegation
        self.check_circular_delegation()

        # Validate users exist and are enabled
        self.validate_users()

    def validate_users(self):
        """Validate delegator and delegate users."""
        for field, label in [("delegator", "Delegator"), ("delegate", "Delegate")]:
            user = getattr(self, field)
            if user:
                user_enabled = frappe.db.get_value("User", user, "enabled")
                if not user_enabled:
                    frappe.throw(
                        _("{0} user '{1}' is disabled").format(label, user)
                    )

    def check_circular_delegation(self):
        """Check for circular delegation chains."""
        visited = {self.delegator}
        current = self.delegate

        # Walk delegation chain
        max_depth = 10
        for _ in range(max_depth):
            if current in visited:
                frappe.throw(
                    _("Circular delegation detected: {0} would create a loop").format(
                        " -> ".join(list(visited) + [current])
                    )
                )

            visited.add(current)

            # Find next delegation
            next_delegation = frappe.db.get_value(
                "User Delegation",
                {
                    "delegator": current,
                    "is_active": 1,
                    "from_date": ["<=", today()],
                    "to_date": [">=", today()],
                    "name": ["!=", self.name]  # Exclude current record
                },
                "delegate"
            )

            if not next_delegation:
                break

            current = next_delegation

    def on_update(self):
        """Clear cache when delegation changes."""
        frappe.cache().delete_key(f"user_delegation_{self.delegator}")

    def on_trash(self):
        """Clear cache when delegation is deleted."""
        frappe.cache().delete_key(f"user_delegation_{self.delegator}")

    @staticmethod
    def get_active_delegate(user: str, scope: dict = None) -> str | None:
        """
        Get active delegate for a user.

        Args:
            user: User ID to check
            scope: Optional dict with doctype/workflow filters

        Returns:
            Delegate user ID or None
        """
        from xstate_workflow.resolvers.base import get_active_delegation
        return get_active_delegation(user, scope)

    @staticmethod
    def is_delegation_active(delegator: str, delegate: str) -> bool:
        """Check if a specific delegation is currently active."""
        return frappe.db.exists(
            "User Delegation",
            {
                "delegator": delegator,
                "delegate": delegate,
                "is_active": 1,
                "from_date": ["<=", today()],
                "to_date": [">=", today()]
            }
        )
