# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class XStateWorkflowSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		anthropic_api_key: DF.Password | None
		default_llm_model: DF.Literal[
			"gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "grok-2", "grok-2-mini"
		]
		max_tokens: DF.Int
		openai_api_key: DF.Password | None
		xai_api_key: DF.Password | None
	# end: auto-generated types

	pass
