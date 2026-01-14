# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Test cases for Mermaid State Diagram Generation

These tests follow test-driven development - tests are written first,
then the mermaid_generator module is implemented to pass them.
"""

import unittest
import frappe
from frappe.tests.utils import FrappeTestCase


class TestMermaidDiagramGeneration(FrappeTestCase):
    """Tests for generating Mermaid stateDiagram-v2 from XState config"""

    def test_generate_basic_diagram(self):
        """Test generating a basic state diagram without history"""
        from xstate_workflow.mermaid_generator import generate_mermaid_diagram

        config = {
            "id": "test",
            "initial": "draft",
            "states": {
                "draft": {"on": {"SUBMIT": "pending"}},
                "pending": {"on": {"APPROVE": "approved", "REJECT": "rejected"}},
                "approved": {"type": "final"},
                "rejected": {"type": "final"},
            },
        }

        result = generate_mermaid_diagram(config, current_state=None, transition_log=[])

        self.assertIn("stateDiagram-v2", result)
        self.assertIn("[*] --> draft", result)
        self.assertIn("draft --> pending: SUBMIT", result)
        self.assertIn("pending --> approved: APPROVE", result)
        self.assertIn("pending --> rejected: REJECT", result)
        # Final states should have transition to [*]
        self.assertIn("approved --> [*]", result)
        self.assertIn("rejected --> [*]", result)

    def test_highlight_current_state(self):
        """Test that current state gets CSS class for highlighting"""
        from xstate_workflow.mermaid_generator import generate_mermaid_diagram

        config = {
            "id": "test",
            "initial": "draft",
            "states": {
                "draft": {"on": {"SUBMIT": "pending"}},
                "pending": {"type": "final"},
            },
        }

        result = generate_mermaid_diagram(
            config, current_state="pending", transition_log=[]
        )

        # Mermaid uses classDef and class syntax for styling
        self.assertIn("classDef current", result)
        self.assertIn("class pending current", result)

    def test_highlight_visited_states(self):
        """Test that visited states from transition log are highlighted"""
        from xstate_workflow.mermaid_generator import generate_mermaid_diagram

        config = {
            "id": "test",
            "initial": "draft",
            "states": {
                "draft": {"on": {"SUBMIT": "pending"}},
                "pending": {"on": {"APPROVE": "approved"}},
                "approved": {"type": "final"},
            },
        }

        transition_log = [
            {"from_state": None, "to_state": "draft", "event": "INIT"},
            {"from_state": "draft", "to_state": "pending", "event": "SUBMIT"},
        ]

        result = generate_mermaid_diagram(
            config, current_state="pending", transition_log=transition_log
        )

        self.assertIn("classDef visited", result)
        self.assertIn("class draft visited", result)

    def test_transition_with_guard(self):
        """Test transitions with guards show guard name"""
        from xstate_workflow.mermaid_generator import generate_mermaid_diagram

        config = {
            "id": "test",
            "initial": "draft",
            "states": {
                "draft": {
                    "on": {
                        "SUBMIT": [
                            {"target": "needs_approval", "guard": "amount_over_limit"},
                            {"target": "approved"},
                        ]
                    }
                },
                "needs_approval": {"type": "final"},
                "approved": {"type": "final"},
            },
        }

        result = generate_mermaid_diagram(
            config, current_state="draft", transition_log=[]
        )

        # Guard should be shown in brackets
        self.assertIn("draft --> needs_approval: SUBMIT [amount_over_limit]", result)
        self.assertIn("draft --> approved: SUBMIT", result)

    def test_generate_tooltip_data(self):
        """Test generating tooltip data from transition log"""
        from xstate_workflow.mermaid_generator import generate_tooltip_data

        transition_log = [
            {
                "timestamp": "2024-01-15 10:30:00",
                "event": "SUBMIT",
                "from_state": "draft",
                "to_state": "pending",
                "user": "admin@example.com",
            }
        ]

        tooltip_data = generate_tooltip_data(transition_log)

        # Check draft state has exit info
        self.assertIn("draft", tooltip_data)
        self.assertEqual(len(tooltip_data["draft"]["visits"]), 1)
        self.assertEqual(tooltip_data["draft"]["visits"][0]["type"], "exit")
        self.assertEqual(tooltip_data["draft"]["visits"][0]["event"], "SUBMIT")
        self.assertEqual(
            tooltip_data["draft"]["visits"][0]["user"], "admin@example.com"
        )

        # Check pending state has entry info
        self.assertIn("pending", tooltip_data)
        self.assertEqual(len(tooltip_data["pending"]["visits"]), 1)
        self.assertEqual(tooltip_data["pending"]["visits"][0]["type"], "entry")
        self.assertEqual(tooltip_data["pending"]["visits"][0]["event"], "SUBMIT")

    def test_empty_transition_log(self):
        """Test handling empty transition log"""
        from xstate_workflow.mermaid_generator import generate_mermaid_diagram

        config = {
            "id": "test",
            "initial": "draft",
            "states": {
                "draft": {"on": {"SUBMIT": "pending"}},
                "pending": {"type": "final"},
            },
        }

        result = generate_mermaid_diagram(
            config, current_state="draft", transition_log=[]
        )

        # Should still generate valid diagram
        self.assertIn("stateDiagram-v2", result)
        self.assertIn("[*] --> draft", result)
        self.assertIn("draft --> pending: SUBMIT", result)

    def test_escape_special_characters(self):
        """Test that special characters in state names are escaped"""
        from xstate_workflow.mermaid_generator import generate_mermaid_diagram

        config = {
            "id": "test",
            "initial": "draft-state",
            "states": {
                "draft-state": {"on": {"SUBMIT_FOR_REVIEW": "in-review"}},
                "in-review": {"type": "final"},
            },
        }

        result = generate_mermaid_diagram(
            config, current_state="draft-state", transition_log=[]
        )

        # Hyphens should be converted to underscores for Mermaid compatibility
        self.assertIn("draft_state", result)
        self.assertIn("in_review", result)

    def test_multiple_transitions_same_event(self):
        """Test multiple transitions from same event with different guards"""
        from xstate_workflow.mermaid_generator import generate_mermaid_diagram

        config = {
            "id": "test",
            "initial": "draft",
            "states": {
                "draft": {
                    "on": {
                        "SUBMIT": [
                            {
                                "target": "pending_purchase_approval",
                                "guard": "check_any_variance",
                            },
                            {"target": "approved", "guard": "no_variance"},
                        ]
                    }
                },
                "pending_purchase_approval": {
                    "on": {"APPROVE": "pending_accounts_approval", "REJECT": "rejected"}
                },
                "pending_accounts_approval": {
                    "on": {
                        "APPROVE": "approved",
                        "REJECT": "rejected",
                        "RETURN": "pending_purchase_approval",
                    }
                },
                "approved": {"type": "final"},
                "rejected": {"type": "final"},
            },
        }

        result = generate_mermaid_diagram(
            config, current_state="pending_accounts_approval", transition_log=[]
        )

        # Both conditional transitions should be present
        self.assertIn(
            "draft --> pending_purchase_approval: SUBMIT [check_any_variance]", result
        )
        self.assertIn("draft --> approved: SUBMIT [no_variance]", result)
        # Return transition creates a cycle
        self.assertIn(
            "pending_accounts_approval --> pending_purchase_approval: RETURN", result
        )

    def test_tooltip_data_multiple_visits(self):
        """Test tooltip data with multiple visits to same state"""
        from xstate_workflow.mermaid_generator import generate_tooltip_data

        transition_log = [
            {
                "timestamp": "2024-01-15 10:00:00",
                "event": "SUBMIT",
                "from_state": "draft",
                "to_state": "pending",
                "user": "user1@example.com",
            },
            {
                "timestamp": "2024-01-15 11:00:00",
                "event": "RETURN",
                "from_state": "pending",
                "to_state": "draft",
                "user": "user2@example.com",
            },
            {
                "timestamp": "2024-01-15 12:00:00",
                "event": "SUBMIT",
                "from_state": "draft",
                "to_state": "pending",
                "user": "user1@example.com",
            },
        ]

        tooltip_data = generate_tooltip_data(transition_log)

        # Draft should have multiple visits (entry and exits)
        self.assertIn("draft", tooltip_data)
        self.assertGreater(len(tooltip_data["draft"]["visits"]), 1)

        # Pending should have multiple visits too
        self.assertIn("pending", tooltip_data)
        self.assertGreater(len(tooltip_data["pending"]["visits"]), 1)

    def test_no_duplicate_transitions(self):
        """Test that duplicate transitions are not generated"""
        from xstate_workflow.mermaid_generator import generate_mermaid_diagram

        config = {
            "id": "test",
            "initial": "draft",
            "states": {
                "draft": {"on": {"SUBMIT": "pending"}},
                "pending": {"type": "final"},
            },
        }

        result = generate_mermaid_diagram(
            config, current_state="draft", transition_log=[]
        )

        # Count occurrences of the transition
        count = result.count("draft --> pending: SUBMIT")
        self.assertEqual(count, 1, "Transition should appear exactly once")


class TestMermaidViewerIntegration(FrappeTestCase):
    """Integration tests for mermaid diagram in viewer context"""

    def test_generate_mermaid_for_purchase_invoice_workflow(self):
        """Test generating mermaid diagram for the purchase invoice variance workflow"""
        from xstate_workflow.mermaid_generator import generate_mermaid_diagram

        # This is the actual config from the purchase_invoice_variance_approval machine
        config = {
            "id": "purchase_invoice_variance_approval",
            "initial": "draft",
            "states": {
                "draft": {
                    "on": {
                        "SUBMIT": [
                            {
                                "target": "pending_purchase_approval",
                                "guard": "check_any_variance",
                            },
                            {"target": "approved", "guard": "no_variance"},
                        ]
                    }
                },
                "pending_purchase_approval": {
                    "on": {
                        "APPROVE": "pending_accounts_approval",
                        "REJECT": "rejected",
                        "ESCALATE": "pending_accounts_approval",
                    }
                },
                "pending_accounts_approval": {
                    "on": {
                        "APPROVE": "approved",
                        "REJECT": "rejected",
                        "RETURN": "pending_purchase_approval",
                    }
                },
                "approved": {"type": "final"},
                "rejected": {"type": "final"},
            },
        }

        transition_log = [
            {
                "timestamp": "2024-01-15 10:00:00",
                "event": "SUBMIT",
                "from_state": "draft",
                "to_state": "pending_purchase_approval",
                "user": "admin",
            },
            {
                "timestamp": "2024-01-15 11:00:00",
                "event": "APPROVE",
                "from_state": "pending_purchase_approval",
                "to_state": "pending_accounts_approval",
                "user": "purchase_manager",
            },
        ]

        result = generate_mermaid_diagram(
            config,
            current_state="pending_accounts_approval",
            transition_log=transition_log,
        )

        # Verify the diagram structure
        self.assertIn("stateDiagram-v2", result)
        self.assertIn("[*] --> draft", result)

        # Current state should be highlighted
        self.assertIn("class pending_accounts_approval current", result)

        # Visited states should be highlighted
        self.assertIn("draft", result)
        self.assertIn("pending_purchase_approval", result)

        # All transitions should be present
        self.assertIn("SUBMIT [check_any_variance]", result)
        self.assertIn("SUBMIT [no_variance]", result)
        self.assertIn("APPROVE", result)
        self.assertIn("REJECT", result)
        self.assertIn("RETURN", result)
