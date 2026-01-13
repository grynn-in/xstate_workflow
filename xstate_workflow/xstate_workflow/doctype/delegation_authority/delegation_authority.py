# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class DelegationAuthority(Document):
    def validate(self):
        """Validate authority data."""
        # Must have either user or role
        if not self.user and not self.role:
            frappe.throw(_("Either User or Role must be specified"))

        # Validate amount range
        if self.min_amount and self.max_amount:
            if float(self.min_amount) > float(self.max_amount):
                frappe.throw(_("Minimum Amount cannot be greater than Maximum Amount"))

        # Validate user exists and is enabled
        if self.user:
            user_enabled = frappe.db.get_value("User", self.user, "enabled")
            if not user_enabled:
                frappe.throw(_("User '{0}' is disabled").format(self.user))

        # Validate role exists
        if self.role:
            if not frappe.db.exists("Role", self.role):
                frappe.throw(_("Role '{0}' does not exist").format(self.role))

    @staticmethod
    def get_authority_for_user(
        user: str,
        amount: float = None,
        doctype: str = None,
        cost_center: str = None,
        department: str = None
    ) -> "DelegationAuthority | None":
        """
        Get delegation authority for a user.

        Args:
            user: User ID
            amount: Optional amount to check
            doctype: Optional DocType to filter
            cost_center: Optional Cost Center to filter
            department: Optional Department to filter

        Returns:
            Matching DelegationAuthority or None
        """
        filters = {
            "is_active": 1
        }

        # Build user/role filter
        user_roles = frappe.get_roles(user)
        or_filters = [
            {"user": user}
        ]
        for role in user_roles:
            or_filters.append({"role": role})

        # Add amount filter if provided
        if amount is not None:
            filters["max_amount"] = [">=", amount]

        # Add scope filters
        if doctype:
            filters["doctype"] = ["in", [doctype, None, ""]]
        if cost_center:
            filters["cost_center"] = ["in", [cost_center, None, ""]]
        if department:
            filters["department"] = ["in", [department, None, ""]]

        # Query
        authorities = frappe.get_all(
            "Delegation Authority",
            filters=filters,
            or_filters=or_filters,
            fields=["name", "user", "role", "max_amount", "min_amount"],
            order_by="max_amount asc"
        )

        # Filter by min_amount
        for auth in authorities:
            min_amt = float(auth.min_amount or 0)
            if amount is None or amount >= min_amt:
                return frappe.get_doc("Delegation Authority", auth.name)

        return None

    @staticmethod
    def has_authority(
        user: str,
        amount: float,
        doctype: str = None,
        cost_center: str = None,
        department: str = None
    ) -> bool:
        """
        Check if user has authority for the given amount.

        Args:
            user: User ID
            amount: Amount to check
            doctype: Optional DocType to filter
            cost_center: Optional Cost Center to filter
            department: Optional Department to filter

        Returns:
            True if user has authority, False otherwise
        """
        authority = DelegationAuthority.get_authority_for_user(
            user, amount, doctype, cost_center, department
        )
        return authority is not None

    @staticmethod
    def get_users_with_authority(
        amount: float,
        doctype: str = None,
        cost_center: str = None,
        department: str = None
    ) -> list[str]:
        """
        Get all users who have authority for the given amount.

        Args:
            amount: Amount to check
            doctype: Optional DocType to filter
            cost_center: Optional Cost Center to filter
            department: Optional Department to filter

        Returns:
            List of user IDs with authority
        """
        filters = {
            "is_active": 1,
            "max_amount": [">=", amount]
        }

        if doctype:
            filters["doctype"] = ["in", [doctype, None, ""]]
        if cost_center:
            filters["cost_center"] = ["in", [cost_center, None, ""]]
        if department:
            filters["department"] = ["in", [department, None, ""]]

        authorities = frappe.get_all(
            "Delegation Authority",
            filters=filters,
            fields=["user", "role", "min_amount"]
        )

        users = set()

        for auth in authorities:
            min_amt = float(auth.min_amount or 0)
            if amount < min_amt:
                continue

            if auth.user:
                if frappe.db.get_value("User", auth.user, "enabled"):
                    users.add(auth.user)

            elif auth.role:
                # Get all users with this role
                role_users = frappe.get_all(
                    "Has Role",
                    filters={"role": auth.role, "parenttype": "User"},
                    pluck="parent"
                )
                for u in role_users:
                    if frappe.db.get_value("User", u, "enabled"):
                        users.add(u)

        return list(users)
