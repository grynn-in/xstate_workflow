# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Data Input Resolver.

Resolves pre-loaded data for agentic nodes based on configuration.
Supports selecting specific document fields, linked documents, and context variables.
"""

from typing import Any

import frappe
from frappe import _


class DataInputResolver:
	"""
	Resolve pre-loaded data for AI agents based on node configuration.

	This class handles the data input configuration that allows builders
	to specify exactly what data should be pre-loaded for an agent:
	- Selected fields from the current document
	- Linked document data
	- Workflow context variables
	"""

	def resolve(
		self,
		config: dict | None,
		ref_doc,
		context: dict | None,
		doctype: str = None,
		docname: str = None,
	) -> dict:
		"""
		Resolve pre-loaded data based on configuration.

		Args:
			config: Data input configuration with documentFields, linkedDocuments, contextVariables
			ref_doc: Reference document (Frappe Document or dict)
			context: Workflow context dictionary
			doctype: DocType name (optional, used if ref_doc is dict)
			docname: Document name (optional, used if ref_doc is dict)

		Returns:
			Dictionary with resolved data:
			{
				"document": { ... selected fields ... },
				"linked": { "field_name": { ... linked doc data ... }, ... },
				"context": { ... selected context vars ... },
				"metadata": { "doctype": "...", "docname": "..." }
			}
		"""
		result = {
			"document": {},
			"linked": {},
			"context": {},
			"metadata": {},
		}

		# Handle ref_doc being dict or Document
		doc_data = self._get_doc_as_dict(ref_doc)

		# Get doctype/docname from doc or params
		actual_doctype = doctype or doc_data.get("doctype")
		actual_docname = docname or doc_data.get("name")

		result["metadata"] = {
			"doctype": actual_doctype,
			"docname": actual_docname,
		}

		# If no config or empty config, return full document
		if not config:
			result["document"] = doc_data
			result["context"] = context or {}
			return result

		# Resolve document fields
		document_fields = config.get("documentFields") or config.get("document_fields")
		if document_fields:
			result["document"] = self._resolve_document_fields(doc_data, document_fields)
		else:
			# If no specific fields configured, include all
			result["document"] = doc_data

		# Resolve linked documents
		linked_docs = config.get("linkedDocuments") or config.get("linked_documents")
		if linked_docs:
			result["linked"] = self._resolve_linked_documents(
				doc_data, linked_docs, actual_doctype
			)

		# Resolve context variables
		context_vars = config.get("contextVariables") or config.get("context_variables")
		if context_vars:
			result["context"] = self._resolve_context_variables(context or {}, context_vars)
		else:
			# If no specific context vars configured, include all
			result["context"] = context or {}

		return result

	def _get_doc_as_dict(self, ref_doc) -> dict:
		"""
		Convert document to dictionary.

		Args:
			ref_doc: Frappe Document or dict

		Returns:
			Document data as dictionary
		"""
		if hasattr(ref_doc, "as_dict"):
			return ref_doc.as_dict()
		elif isinstance(ref_doc, dict):
			return ref_doc
		else:
			return {}

	def _resolve_document_fields(self, doc_data: dict, fields: list[str]) -> dict:
		"""
		Resolve selected fields from document.

		Args:
			doc_data: Document data dictionary
			fields: List of field names to include

		Returns:
			Dictionary with only selected fields
		"""
		result = {}

		for field in fields:
			if not field:
				continue

			# Handle nested field access (e.g., "items.item_code")
			if "." in field:
				value = self._get_nested_value(doc_data, field)
			else:
				value = doc_data.get(field)

			# Skip if field doesn't exist, but don't fail
			if value is not None:
				result[field] = value
			else:
				# Log warning but continue
				frappe.log_error(
					title="Data Input Warning",
					message=f"Field '{field}' not found in document, skipping",
				)

		return result

	def _get_nested_value(self, data: dict, path: str) -> Any:
		"""
		Get nested value from dictionary using dot notation.

		Args:
			data: Source dictionary
			path: Dot-separated path (e.g., "items.0.item_code")

		Returns:
			Value at path or None if not found
		"""
		parts = path.split(".")
		current = data

		for part in parts:
			if current is None:
				return None

			if isinstance(current, dict):
				current = current.get(part)
			elif isinstance(current, list):
				try:
					index = int(part)
					current = current[index] if 0 <= index < len(current) else None
				except ValueError:
					# Not an index, try to get from all items
					current = [item.get(part) for item in current if isinstance(item, dict)]
			else:
				return None

		return current

	def _resolve_linked_documents(
		self, doc_data: dict, linked_docs: list[dict], doctype: str
	) -> dict:
		"""
		Resolve linked document data.

		Args:
			doc_data: Current document data
			linked_docs: List of linked document configs:
				[{"linkField": "supplier", "fields": ["supplier_name", "tax_id"]}, ...]
			doctype: Current document's DocType (for metadata lookup)

		Returns:
			Dictionary of linked document data: {"supplier": {...}, ...}
		"""
		result = {}

		for linked_config in linked_docs:
			if not linked_config:
				continue

			link_field = linked_config.get("linkField") or linked_config.get("link_field")
			fields = linked_config.get("fields", [])

			if not link_field:
				continue

			# Get the link value from current document
			link_value = doc_data.get(link_field)
			if not link_value:
				result[link_field] = None
				continue

			# Determine the linked DocType (passing doc_data for dynamic link resolution)
			linked_doctype = self._get_linked_doctype(doctype, link_field, doc_data)
			if not linked_doctype:
				result[link_field] = None
				continue

			# Fetch linked document
			try:
				if fields:
					linked_data = frappe.get_value(
						linked_doctype, link_value, fields, as_dict=True
					)
				else:
					linked_doc = frappe.get_doc(linked_doctype, link_value)
					linked_data = linked_doc.as_dict()

				result[link_field] = linked_data

			except frappe.DoesNotExistError:
				# Linked document doesn't exist
				result[link_field] = None
				frappe.log_error(
					title="Data Input Warning",
					message=f"Linked document {linked_doctype}/{link_value} not found",
				)
			except frappe.PermissionError:
				# No permission to read linked document
				result[link_field] = {"error": "No permission to access linked document"}
			except Exception as e:
				result[link_field] = None
				frappe.log_error(
					title="Data Input Error",
					message=f"Error fetching linked document: {e}",
				)

		return result

	def _get_linked_doctype(
		self, doctype: str, link_field: str, doc_data: dict = None
	) -> str | None:
		"""
		Get the DocType that a link field points to.

		Supports both regular Link fields and Dynamic Link fields.

		Args:
			doctype: DocType containing the link field
			link_field: Name of the link field
			doc_data: Document data (required for Dynamic Link resolution)

		Returns:
			Linked DocType name or None
		"""
		if not doctype:
			return None

		try:
			meta = frappe.get_meta(doctype)
			field = meta.get_field(link_field)

			if field and field.fieldtype == "Link":
				return field.options

			# Handle Dynamic Link
			if field and field.fieldtype == "Dynamic Link":
				# The 'options' field contains the name of the field that holds the DocType
				doctype_field_name = field.options

				if not doctype_field_name:
					return None

				# Get the DocType value from the document
				if doc_data:
					linked_doctype = doc_data.get(doctype_field_name)
					if linked_doctype and frappe.db.exists("DocType", linked_doctype):
						return linked_doctype

				# Fall back to trying to get from field metadata
				return None

		except Exception as e:
			frappe.log_error(
				title="Dynamic Link Resolution Error",
				message=f"Error resolving linked doctype for {doctype}.{link_field}: {e}",
			)

		return None

	def _resolve_context_variables(
		self, context: dict, variables: list[str]
	) -> dict:
		"""
		Resolve selected context variables.

		Args:
			context: Workflow context dictionary
			variables: List of variable names to include

		Returns:
			Dictionary with only selected context variables
		"""
		result = {}

		for var_name in variables:
			if not var_name:
				continue

			# Handle nested access
			if "." in var_name:
				value = self._get_nested_value(context, var_name)
			else:
				value = context.get(var_name)

			if value is not None:
				result[var_name] = value

		return result


def resolve_data_input(
	config: dict | None,
	ref_doc,
	context: dict | None,
	doctype: str = None,
	docname: str = None,
) -> dict:
	"""
	Convenience function to resolve data input.

	Args:
		config: Data input configuration
		ref_doc: Reference document
		context: Workflow context
		doctype: DocType name (optional)
		docname: Document name (optional)

	Returns:
		Resolved data dictionary
	"""
	resolver = DataInputResolver()
	return resolver.resolve(
		config=config,
		ref_doc=ref_doc,
		context=context,
		doctype=doctype,
		docname=docname,
	)


def format_data_for_agent(resolved_data: dict) -> str:
	"""
	Format resolved data as a string for inclusion in agent prompt.

	Args:
		resolved_data: Output from DataInputResolver.resolve()

	Returns:
		Formatted string describing the available data
	"""
	import json

	sections = []

	# Document data section
	doc_data = resolved_data.get("document", {})
	if doc_data:
		sections.append("## Current Document Data\n")
		sections.append("```json\n")
		sections.append(json.dumps(doc_data, indent=2, default=str))
		sections.append("\n```\n")

	# Linked documents section
	linked_data = resolved_data.get("linked", {})
	if linked_data:
		sections.append("\n## Linked Document Data\n")
		for field_name, data in linked_data.items():
			sections.append(f"\n### {field_name}\n")
			if data:
				sections.append("```json\n")
				sections.append(json.dumps(data, indent=2, default=str))
				sections.append("\n```\n")
			else:
				sections.append("_No linked document found_\n")

	# Context variables section
	context_data = resolved_data.get("context", {})
	if context_data:
		sections.append("\n## Workflow Context\n")
		sections.append("```json\n")
		sections.append(json.dumps(context_data, indent=2, default=str))
		sections.append("\n```\n")

	# Metadata
	metadata = resolved_data.get("metadata", {})
	if metadata:
		doctype = metadata.get("doctype", "Unknown")
		docname = metadata.get("docname", "Unknown")
		sections.insert(0, f"# Data for {doctype}: {docname}\n\n")

	return "".join(sections)
