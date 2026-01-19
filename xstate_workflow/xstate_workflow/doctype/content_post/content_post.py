# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ContentPost(Document):
	"""
	Content Post - stores input configuration and AI-generated content.

	Fields:
		INPUT (you configure):
		- industry_focus: What industry to research
		- content_themes: Optional hints for topics
		- target_platforms: Where to publish
		- target_audience: Who you're writing for

		OUTPUT (AI fills via workflow):
		- title: AI-generated title
		- topic: AI-generated topic brief
		- twitter_version: Tweet content
		- linkedin_version: LinkedIn post
		- newsletter_version: Newsletter content
		- hashtags: Suggested hashtags
		- published_urls: Links to published posts

	The workflow (configured in State Machine UI) handles:
	1. Researching trending topics
	2. Generating platform-specific content
	3. Human review/approval
	4. Publishing to platforms
	"""

	def validate(self):
		"""Basic validation."""
		if self.twitter_version and len(self.twitter_version) > 280:
			frappe.throw(
				_("Twitter version must be 280 characters or less. Current: {0}").format(
					len(self.twitter_version)
				)
			)
