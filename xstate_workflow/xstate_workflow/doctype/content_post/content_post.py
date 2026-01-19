# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document


class ContentPost(Document):
	def before_insert(self):
		"""Set default values."""
		if not self.status:
			self.status = "Draft"

	def validate(self):
		"""Validate content post data."""
		# Validate Twitter version length
		if self.twitter_version and len(self.twitter_version) > 280:
			frappe.throw(_("Twitter version must be 280 characters or less. Current: {0}").format(
				len(self.twitter_version)
			))

	def on_update(self):
		"""Handle status changes."""
		if self.has_value_changed("status"):
			self.publish_realtime_update()

	def publish_realtime_update(self):
		"""Publish status update via realtime."""
		try:
			frappe.publish_realtime(
				"content_post_updated",
				{
					"name": self.name,
					"status": self.status,
					"title": self.title,
				},
				doctype="Content Post",
				docname=self.name,
			)
		except Exception:
			pass

	def get_published_urls_dict(self) -> dict:
		"""Get published URLs as a dictionary."""
		if not self.published_urls:
			return {}

		try:
			return json.loads(self.published_urls)
		except json.JSONDecodeError:
			return {}

	def set_published_urls(self, urls: dict):
		"""Set published URLs from a dictionary."""
		self.published_urls = json.dumps(urls, indent=2)

	def add_published_url(self, platform: str, url: str):
		"""Add a published URL for a platform."""
		urls = self.get_published_urls_dict()
		urls[platform] = url
		self.set_published_urls(urls)

	def get_platforms_list(self) -> list[str]:
		"""Get target platforms as a list."""
		if not self.target_platforms:
			return []
		return [p.strip() for p in self.target_platforms.split(",")]

	@frappe.whitelist()
	def trigger_generation(self):
		"""Trigger AI content generation workflow event."""
		from xstate_workflow.workflow_engine import trigger_event_sync

		if self.status != "Draft":
			frappe.throw(_("Can only generate content from Draft status"))

		return trigger_event_sync(
			"Content Post",
			self.name,
			"GENERATE_CONTENT",
			json.dumps({"triggered_by": frappe.session.user})
		)

	@frappe.whitelist()
	def trigger_publish(self, scheduled: bool = False):
		"""Trigger publishing workflow event."""
		from xstate_workflow.workflow_engine import trigger_event_sync

		if self.status != "Approved":
			frappe.throw(_("Can only publish from Approved status"))

		event = "SCHEDULE" if scheduled else "PUBLISH_NOW"
		return trigger_event_sync(
			"Content Post",
			self.name,
			event,
			json.dumps({"triggered_by": frappe.session.user})
		)

	@frappe.whitelist()
	def retry_generation(self):
		"""Retry content generation after failure."""
		from xstate_workflow.workflow_engine import trigger_event_sync

		if self.status != "Failed":
			frappe.throw(_("Can only retry from Failed status"))

		return trigger_event_sync(
			"Content Post",
			self.name,
			"RETRY",
			json.dumps({"triggered_by": frappe.session.user})
		)
