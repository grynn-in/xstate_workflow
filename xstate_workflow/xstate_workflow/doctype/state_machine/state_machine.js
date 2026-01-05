// Copyright (c) 2024, Grynn GmbH and contributors
// For license information, please see license.txt

frappe.ui.form.on('State Machine', {
    refresh: function(frm) {
        // Add visual builder buttons
        if (!frm.is_new()) {
            // Embedded builder toggle
            frm.add_custom_button(__('Visual Builder'), function() {
                xsw_toggle_embedded_builder(frm);
            }, __('Actions'));

            // Open in new tab option
            frm.add_custom_button(__('Open in New Tab'), function() {
                const url = `/workflow-builder?machine=${encodeURIComponent(frm.doc.name)}`;
                window.open(url, '_blank');
            }, __('Actions'));

            // View workflow instances
            frm.add_custom_button(__('View Instances'), function() {
                frappe.set_route('List', 'Machine Instance', {
                    machine: frm.doc.name
                });
            }, __('Actions'));

            // Test workflow if active and attached to a doctype
            if (frm.doc.is_active && frm.doc.attached_doctype) {
                frm.add_custom_button(__('Test Workflow'), function() {
                    xsw_test_workflow(frm);
                }, __('Actions'));
            }

            // Make visual builder button primary
            frm.change_custom_button_type(__('Visual Builder'), __('Actions'), 'primary');
        }

        // Add link to create new from visual builder
        if (frm.is_new()) {
            frm.set_intro(__('You can also <a href="/workflow-builder" target="_blank">create a workflow visually</a> using the drag-and-drop builder.'));
        }

        // Render embedded builder if it was previously open
        if (frm.xsw_builder_open) {
            setTimeout(() => xsw_render_embedded_builder(frm), 100);
        }

        // Show workflow states summary
        if (frm.doc.json_config && !frm.is_new()) {
            xsw_render_states_summary(frm);
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
    },

    // Cleanup on form unload
    onload: function(frm) {
        frm.xsw_builder_open = false;
    }
});

/**
 * Toggle the embedded visual builder
 */
function xsw_toggle_embedded_builder(frm) {
    if (frm.xsw_builder_open) {
        xsw_close_embedded_builder(frm);
    } else {
        xsw_open_embedded_builder(frm);
    }
}

/**
 * Open the embedded visual builder
 */
function xsw_open_embedded_builder(frm) {
    frm.xsw_builder_open = true;

    // Create container if it doesn't exist
    let container = frm.fields_dict.json_config.$wrapper.find('.xsw-embedded-builder');
    if (!container.length) {
        container = $(`
            <div class="xsw-embedded-builder" style="
                margin-top: 15px;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                overflow: hidden;
                background: #fff;
            ">
                <div class="xsw-builder-header" style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 12px;
                    background: var(--bg-color);
                    border-bottom: 1px solid var(--border-color);
                ">
                    <span style="font-weight: 500;">Visual Workflow Builder</span>
                    <button class="btn btn-xs btn-default xsw-close-btn">
                        Close
                    </button>
                </div>
                <div id="xsw-builder-container" style="height: 500px;"></div>
            </div>
        `);

        frm.fields_dict.json_config.$wrapper.append(container);

        // Bind close button
        container.find('.xsw-close-btn').on('click', function() {
            xsw_close_embedded_builder(frm);
        });
    }

    container.show();
    xsw_render_embedded_builder(frm);

    // Scroll to builder
    setTimeout(() => {
        container[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

/**
 * Close the embedded visual builder
 */
function xsw_close_embedded_builder(frm) {
    frm.xsw_builder_open = false;

    const container = frm.fields_dict.json_config.$wrapper.find('.xsw-embedded-builder');
    if (container.length) {
        // Unmount React component
        if (window.XStateWorkflowWidget) {
            window.XStateWorkflowWidget.unmountWorkflowBuilder('xsw-builder-container');
        }
        container.hide();
    }
}

/**
 * Render the embedded visual builder
 */
function xsw_render_embedded_builder(frm) {
    // Check if the widget library is loaded
    if (!window.XStateWorkflowWidget) {
        frappe.msgprint({
            title: __('Widget Not Loaded'),
            indicator: 'red',
            message: __('The visual builder widget is not loaded. Please refresh the page.')
        });
        return;
    }

    // Parse existing configs for the builder
    let initialConfig = null;
    if (frm.doc.json_config) {
        try {
            initialConfig = {
                xstate: JSON.parse(frm.doc.json_config),
                visual: frm.doc.workflow_builder_config ? JSON.parse(frm.doc.workflow_builder_config) : null
            };
        } catch (e) {
            console.warn('Could not parse existing config:', e);
        }
    }

    // Mount the builder
    window.XStateWorkflowWidget.mountWorkflowBuilder('xsw-builder-container', {
        machineId: frm.doc.name,
        attachedDoctype: frm.doc.attached_doctype,
        initialConfig: initialConfig,
        onSave: function(config) {
            // Update form fields with new config
            frm.set_value('json_config', JSON.stringify(config.xstate, null, 2));
            frm.set_value('workflow_builder_config', JSON.stringify(config.visual));

            frappe.show_alert({
                message: __('Workflow updated. Click Save to persist changes.'),
                indicator: 'green'
            });

            // Mark form as dirty
            frm.dirty();
        },
        onClose: function() {
            xsw_close_embedded_builder(frm);
        }
    });
}

/**
 * Render a summary of workflow states
 */
function xsw_render_states_summary(frm) {
    try {
        const config = JSON.parse(frm.doc.json_config);
        const states = config.states || {};
        const stateNames = Object.keys(states);

        if (stateNames.length === 0) return;

        // Remove existing summary
        frm.fields_dict.json_config.$wrapper.find('.xsw-states-summary').remove();

        const $summary = $(`
            <div class="xsw-states-summary" style="margin-bottom: 10px;">
                <div class="text-muted small" style="margin-bottom: 5px;">${__('Workflow States')}:</div>
                <div class="xsw-states-badges"></div>
            </div>
        `);

        const $badges = $summary.find('.xsw-states-badges');
        stateNames.forEach(function(name) {
            const stateConfig = states[name];
            const isInitial = name === config.initial;
            const isFinal = stateConfig.type === 'final';
            const isParallel = stateConfig.type === 'parallel';
            const hasChildren = stateConfig.states && Object.keys(stateConfig.states).length > 0;

            let icon = '○';
            let colorClass = 'badge-secondary';

            if (isInitial) {
                icon = '●';
                colorClass = 'badge-success';
            } else if (isFinal) {
                icon = '◉';
                colorClass = 'badge-danger';
            } else if (isParallel) {
                icon = '║';
                colorClass = 'badge-warning';
            } else if (hasChildren) {
                icon = '▣';
                colorClass = 'badge-info';
            }

            $badges.append(`
                <span class="badge ${colorClass}" style="margin-right: 4px; margin-bottom: 4px;">
                    ${icon} ${name}
                </span>
            `);
        });

        frm.fields_dict.json_config.$wrapper.prepend($summary);
    } catch (e) {
        // Silent fail for summary
    }
}

/**
 * Test the workflow with a sample document
 */
function xsw_test_workflow(frm) {
    const d = new frappe.ui.Dialog({
        title: __('Test Workflow'),
        fields: [
            {
                fieldname: 'info_html',
                fieldtype: 'HTML',
                options: `<p class="text-muted">${__('Select a document to test this workflow.')}</p>`
            },
            {
                fieldname: 'test_docname',
                fieldtype: 'Link',
                label: __('Document'),
                options: frm.doc.attached_doctype,
                reqd: 1
            },
            {
                fieldname: 'section_action',
                fieldtype: 'Section Break',
                label: __('Action')
            },
            {
                fieldname: 'action_type',
                fieldtype: 'Select',
                label: __('Action Type'),
                options: 'Get Current State\nTrigger Event\nReset Instance',
                default: 'Get Current State'
            },
            {
                fieldname: 'event_name',
                fieldtype: 'Data',
                label: __('Event Name'),
                depends_on: "eval:doc.action_type=='Trigger Event'",
                mandatory_depends_on: "eval:doc.action_type=='Trigger Event'"
            }
        ],
        primary_action_label: __('Execute'),
        primary_action: function(values) {
            if (values.action_type === 'Get Current State') {
                frappe.xcall('xstate_workflow.workflow_engine.get_machine_state', {
                    doctype: frm.doc.attached_doctype,
                    docname: values.test_docname
                }).then(function(result) {
                    d.hide();
                    if (result.has_workflow) {
                        frappe.msgprint({
                            title: __('Current State'),
                            message: `<strong>${__('State')}:</strong> ${result.current_state}<br>
                                     <strong>${__('Available Events')}:</strong> ${(result.available_events || []).map(e => e.event).join(', ') || 'None'}`,
                            indicator: 'blue'
                        });
                    } else {
                        frappe.msgprint({
                            title: __('No Instance'),
                            message: __('No workflow instance found for this document.'),
                            indicator: 'orange'
                        });
                    }
                });
            } else if (values.action_type === 'Trigger Event') {
                frappe.xcall('xstate_workflow.workflow_engine.trigger_event_sync', {
                    doctype: frm.doc.attached_doctype,
                    docname: values.test_docname,
                    event: values.event_name,
                    data: '{}'
                }).then(function(result) {
                    d.hide();
                    frappe.msgprint({
                        title: result.success ? __('Success') : __('Failed'),
                        message: result.success ?
                            __('Transitioned from {0} to {1}', [result.previous_state, result.new_state]) :
                            result.error || __('Transition failed'),
                        indicator: result.success ? 'green' : 'red'
                    });
                });
            } else if (values.action_type === 'Reset Instance') {
                frappe.xcall('xstate_workflow.workflow_engine.reset_instance', {
                    doctype: frm.doc.attached_doctype,
                    docname: values.test_docname
                }).then(function(result) {
                    d.hide();
                    frappe.msgprint({
                        title: __('Instance Reset'),
                        message: __('Workflow instance has been reset to initial state.'),
                        indicator: 'blue'
                    });
                });
            }
        }
    });

    d.show();
}
