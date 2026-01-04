// Copyright (c) 2024, Grynn GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on('State Machine', {
    refresh: function(frm) {
        // Add "Open Visual Builder" button for saved documents
        if (!frm.is_new()) {
            frm.add_custom_button(__('Open Visual Builder'), function() {
                // Open in new tab
                const url = `/workflow-builder?machine=${encodeURIComponent(frm.doc.name)}`;
                window.open(url, '_blank');
            }, __('Actions'));

            // Make the button primary/prominent
            frm.change_custom_button_type(__('Open Visual Builder'), __('Actions'), 'primary');
        }

        // Add link to create new from visual builder
        if (frm.is_new()) {
            frm.set_intro(__('You can also <a href="/workflow-builder" target="_blank">create a workflow visually</a> using the drag-and-drop builder.'));
        }
    },

    // Auto-generate machine_id from title if not set
    title: function(frm) {
        if (frm.is_new() && !frm.doc.machine_id && frm.doc.title) {
            // Convert title to snake_case for machine_id
            const machine_id = frm.doc.title
                .toLowerCase()
                .replace(/[^a-z0-9]+/g, '_')
                .replace(/^_+|_+$/g, '');
            frm.set_value('machine_id', machine_id);
        }
    },

    // Validate JSON config on change
    json_config: function(frm) {
        if (frm.doc.json_config) {
            try {
                JSON.parse(frm.doc.json_config);
                // Valid JSON - clear any error styling
            } catch (e) {
                frappe.msgprint({
                    title: __('Invalid JSON'),
                    indicator: 'red',
                    message: __('The XState JSON Config contains invalid JSON: ') + e.message
                });
            }
        }
    }
});
