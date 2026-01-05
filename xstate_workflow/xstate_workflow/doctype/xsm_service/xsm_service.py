# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.model.document import Document


class XSMService(Document):
    def validate(self):
        """Validate service configuration based on type"""
        if self.service_type in ("python", "background_job"):
            self._validate_python_config()
        elif self.service_type == "http":
            self._validate_http_config()

    def _validate_python_config(self):
        """Validate Python service configuration"""
        if not self.python_path:
            frappe.throw(_("Python Path is required for {0} service type").format(self.service_type))

        # Validate Python path format
        if "." not in self.python_path:
            frappe.throw(_("Python Path must be a full module path (e.g., myapp.services.my_function)"))

        # Try to import the module to validate it exists
        try:
            module_path, func_name = self.python_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[func_name])
            if not hasattr(module, func_name):
                frappe.throw(_("Function '{0}' not found in module '{1}'").format(func_name, module_path))
            func = getattr(module, func_name)
            if not callable(func):
                frappe.throw(_("'{0}' is not a callable function").format(self.python_path))
        except ImportError as e:
            frappe.throw(_("Could not import module: {0}").format(str(e)))

    def _validate_http_config(self):
        """Validate HTTP service configuration"""
        if not self.http_url:
            frappe.throw(_("HTTP URL is required for http service type"))

        # Validate URL format
        if not self.http_url.startswith(("http://", "https://")):
            frappe.throw(_("HTTP URL must start with http:// or https://"))

        # Validate headers JSON if provided
        if self.http_headers:
            try:
                headers = json.loads(self.http_headers)
                if not isinstance(headers, dict):
                    frappe.throw(_("HTTP Headers must be a JSON object"))
            except json.JSONDecodeError:
                frappe.throw(_("HTTP Headers must be valid JSON"))

    def get_headers_dict(self):
        """Return HTTP headers as Python dict"""
        if not self.http_headers:
            return {}
        try:
            return json.loads(self.http_headers)
        except json.JSONDecodeError:
            return {}

    @frappe.whitelist()
    def test_service(self):
        """Test the service with sample data"""
        from xstate_workflow.workflow_engine import (
            _execute_http_service,
            _execute_python_service_sync
        )

        test_context = {"test": True, "timestamp": str(frappe.utils.now())}
        test_event = {"type": "TEST"}

        try:
            if self.service_type == "http":
                import requests
                response = requests.request(
                    method=self.http_method or "POST",
                    url=self.http_url,
                    headers=self.get_headers_dict(),
                    json=test_context,
                    timeout=min(self.timeout or 60, 30)  # Max 30s for test
                )
                return {
                    "success": response.ok,
                    "status_code": response.status_code,
                    "response": response.text[:500] if response.text else None
                }
            elif self.service_type in ("python", "background_job"):
                # Create a mock doc for testing
                result = _execute_python_service_sync(
                    self.python_path,
                    test_context,
                    test_event,
                    None  # No ref doc for test
                )
                return {
                    "success": True,
                    "result": result
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
