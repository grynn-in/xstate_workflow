/**
 * XState Workflow - Frappe Client Integration
 *
 * This script provides workflow integration for Frappe forms.
 * It adds workflow state display and action buttons to any DocType
 * that has an active workflow attached.
 */

(function () {
  'use strict';

  // Check if frappe is available
  if (typeof frappe === 'undefined') {
    console.warn('XState Workflow: frappe not found, skipping initialization');
    return;
  }

  // ===== Workflow Client API =====

  frappe.xstate_workflow = {
    /**
     * Trigger a workflow event on a document
     * @param {string} doctype - DocType name
     * @param {string} docname - Document name
     * @param {string} event - Event to trigger
     * @param {object} data - Optional event data
     * @returns {Promise}
     */
    trigger_event: function (doctype, docname, event, data) {
      return frappe.xcall('xstate_workflow.workflow_engine.trigger_event_sync', {
        doctype: doctype,
        docname: docname,
        event: event,
        data: JSON.stringify(data || {})
      });
    },

    /**
     * Get current workflow state for a document
     * @param {string} doctype - DocType name
     * @param {string} docname - Document name
     * @returns {Promise}
     */
    get_state: function (doctype, docname) {
      return frappe.xcall('xstate_workflow.workflow_engine.get_machine_state', {
        doctype: doctype,
        docname: docname
      });
    },

    /**
     * Reset workflow instance to initial state
     * @param {string} doctype - DocType name
     * @param {string} docname - Document name
     * @returns {Promise}
     */
    reset: function (doctype, docname) {
      return frappe.xcall('xstate_workflow.workflow_engine.reset_instance', {
        doctype: doctype,
        docname: docname
      });
    },

    /**
     * Open workflow builder in new tab
     * @param {string} machine_id - Optional machine ID to edit
     */
    open_builder: function (machine_id) {
      var url = '/workflow-builder';
      if (machine_id) {
        url += '?machine_id=' + encodeURIComponent(machine_id);
      }
      window.open(url, '_blank');
    }
  };

  // ===== Form Integration =====

  /**
   * Add workflow section to form
   */
  function add_workflow_section(frm) {
    // Skip if already added
    if (frm.workflow_section_added) return;

    // Get workflow state
    frappe.xstate_workflow.get_state(frm.doc.doctype, frm.doc.name).then(function (state) {
      if (!state.has_workflow) return;

      frm.workflow_section_added = true;
      frm.workflow_state = state;

      // Try to use React components if available
      if (window.XStateWorkflowWidget) {
        add_react_workflow_section(frm, state);
      } else {
        add_fallback_workflow_section(frm, state);
      }

      // Update page indicator
      update_page_indicator(frm, state);
    });
  }

  /**
   * Add React-based workflow section
   */
  function add_react_workflow_section(frm, state) {
    // Create containers for React components
    var $section = $('<div class="xsw-react-workflow-section"></div>');

    // State indicator container
    var $stateContainer = $('<div id="xsw-state-indicator-' + frm.doc.name.replace(/\s/g, '_') + '" class="xsw-state-indicator-wrapper" style="margin-bottom: 10px;"></div>');
    $section.append($stateContainer);

    // Action buttons container
    var $actionsContainer = $('<div id="xsw-action-buttons-' + frm.doc.name.replace(/\s/g, '_') + '" class="xsw-action-buttons-wrapper"></div>');
    $section.append($actionsContainer);

    // Add to dashboard
    frm.dashboard.add_section($section, __('Workflow'));

    // Mount React components
    setTimeout(function() {
      var containerId = 'xsw-state-indicator-' + frm.doc.name.replace(/\s/g, '_');
      window.XStateWorkflowWidget.mountStateIndicator(containerId, {
        doctype: frm.doc.doctype,
        docname: frm.doc.name,
        onStateChange: function(newState) {
          frm.reload_doc();
        }
      });

      var buttonsId = 'xsw-action-buttons-' + frm.doc.name.replace(/\s/g, '_');
      window.XStateWorkflowWidget.mountActionButtons(buttonsId, {
        doctype: frm.doc.doctype,
        docname: frm.doc.name,
        onTransition: function(event, result) {
          frm.reload_doc();
        }
      });
    }, 100);

    // Store cleanup function
    frm.xsw_cleanup = function() {
      var containerId = 'xsw-state-indicator-' + frm.doc.name.replace(/\s/g, '_');
      var buttonsId = 'xsw-action-buttons-' + frm.doc.name.replace(/\s/g, '_');
      if (window.XStateWorkflowWidget) {
        window.XStateWorkflowWidget.unmountWidget(containerId);
        window.XStateWorkflowWidget.unmountWidget(buttonsId);
      }
    };
  }

  /**
   * Add fallback (non-React) workflow section
   */
  function add_fallback_workflow_section(frm, state) {
    // Add workflow section HTML
    var $section = $(render_workflow_section(state));
    frm.fields_dict.workflow_state && frm.fields_dict.workflow_state.$wrapper
      ? frm.fields_dict.workflow_state.$wrapper.html($section)
      : frm.dashboard.add_section($section, __('Workflow'));

    // Bind action buttons
    $section.find('.workflow-action-btn').on('click', function () {
      var event = $(this).data('event');
      handle_workflow_action(frm, event);
    });
  }

  /**
   * Render workflow section HTML
   */
  function render_workflow_section(state) {
    var buttons_html = '';
    var events = state.available_events || [];

    events.forEach(function (evt) {
      if (!evt.enabled) return;

      var btn_class = get_button_class(evt.event);
      var icon = get_event_icon(evt.event);

      buttons_html += '<button class="btn ' + btn_class + ' workflow-action-btn" data-event="' +
        evt.event + '">' + icon + ' ' + format_event_name(evt.event) + '</button>';
    });

    return '<div class="workflow-section">' +
      '<div class="workflow-section-header">' +
      '<div class="workflow-section-title">' + __('Workflow State') + '</div>' +
      '<span class="workflow-state-badge ' + state.current_state.toLowerCase().replace(/ /g, '_') + '">' +
      state.current_state + '</span>' +
      '</div>' +
      '<div class="workflow-actions">' + buttons_html + '</div>' +
      (state.last_event ? '<div class="text-muted small">' +
        __('Last action') + ': ' + format_event_name(state.last_event) +
        (state.last_transition_at ? ' (' + frappe.datetime.prettyDate(state.last_transition_at) + ')' : '') +
        '</div>' : '') +
      '</div>';
  }

  /**
   * Handle workflow action button click
   */
  function handle_workflow_action(frm, event) {
    // Check if event needs confirmation or input
    var needs_reason = ['REJECT', 'REQUEST_CHANGES'].includes(event);

    if (needs_reason) {
      show_action_dialog(frm, event, function (values) {
        execute_action(frm, event, values);
      });
    } else {
      execute_action(frm, event, {});
    }
  }

  /**
   * Show dialog for actions that need input
   */
  function show_action_dialog(frm, event, callback) {
    var d = new frappe.ui.Dialog({
      title: format_event_name(event),
      fields: [
        {
          fieldname: 'reason',
          fieldtype: 'Small Text',
          label: __('Reason'),
          reqd: 1
        }
      ],
      primary_action_label: format_event_name(event),
      primary_action: function (values) {
        d.hide();
        callback(values);
      }
    });

    d.show();
  }

  /**
   * Execute workflow action
   */
  function execute_action(frm, event, data) {
    frappe.dom.freeze(__('Processing...'));

    frappe.xstate_workflow.trigger_event(frm.doc.doctype, frm.doc.name, event, data)
      .then(function (result) {
        frappe.dom.unfreeze();

        if (result.success) {
          frappe.show_alert({
            message: __('Workflow updated: {0}', [result.new_state]),
            indicator: 'green'
          }, 3);

          // Refresh form
          frm.reload_doc();
        } else {
          frappe.msgprint({
            title: __('Action Failed'),
            message: result.error || __('Unknown error'),
            indicator: 'red'
          });
        }
      })
      .catch(function (err) {
        frappe.dom.unfreeze();
        frappe.msgprint({
          title: __('Error'),
          message: err.message || __('Failed to execute action'),
          indicator: 'red'
        });
      });
  }

  /**
   * Update page indicator based on workflow state
   */
  function update_page_indicator(frm, state) {
    var indicator_color = get_state_color(state.current_state);
    frm.page.set_indicator(state.current_state, indicator_color);
  }

  // ===== Helper Functions =====

  function get_button_class(event) {
    var map = {
      'APPROVE': 'btn-success',
      'SUBMIT': 'btn-primary',
      'REJECT': 'btn-danger',
      'CANCEL': 'btn-danger',
      'REQUEST_CHANGES': 'btn-warning',
      'RESUBMIT': 'btn-primary'
    };
    return map[event] || 'btn-secondary';
  }

  function get_event_icon(event) {
    var map = {
      'APPROVE': '✓',
      'SUBMIT': '→',
      'REJECT': '✕',
      'CANCEL': '✕',
      'REQUEST_CHANGES': '↺',
      'RESUBMIT': '↻'
    };
    return map[event] || '•';
  }

  function get_state_color(state) {
    var map = {
      'draft': 'blue',
      'pending_approval': 'orange',
      'pending': 'orange',
      'approved': 'green',
      'rejected': 'red',
      'cancelled': 'grey'
    };
    return map[state.toLowerCase().replace(/ /g, '_')] || 'blue';
  }

  function format_event_name(event) {
    return event.replace(/_/g, ' ').replace(/\b\w/g, function (l) { return l.toUpperCase(); });
  }

  // ===== Event Listeners =====

  // Add workflow section when form refreshes
  $(document).on('form-refresh', function (e, frm) {
    if (!frm || !frm.doc || !frm.doc.name) return;

    // Check if this doctype has a workflow
    var attached_doctypes = frappe.boot.xstate_workflow?.attached_doctypes || [];
    if (attached_doctypes.includes(frm.doc.doctype)) {
      setTimeout(function () {
        add_workflow_section(frm);
      }, 100);
    }
  });

  // Listen for realtime workflow updates
  frappe.realtime.on('workflow_transition', function (data) {
    // Refresh form if it's the current document
    if (cur_frm && cur_frm.doc.doctype === data.doctype && cur_frm.doc.name === data.docname) {
      frappe.show_alert({
        message: __('Workflow updated to: {0}', [data.to_state]),
        indicator: 'blue'
      }, 3);

      cur_frm.reload_doc();
    }
  });

  // Add workflow builder link to desk
  if (frappe.boot.xstate_workflow?.is_workflow_manager) {
    frappe.router.on('change', function () {
      // Add to System Settings shortcut
      if (frappe.get_route_str() === 'Workspaces/Settings') {
        setTimeout(function () {
          var $shortcuts = $('.workspace-shortcuts');
          if ($shortcuts.length && !$shortcuts.find('.workflow-builder-shortcut').length) {
            $shortcuts.append(
              '<a class="shortcut-widget-box workflow-builder-shortcut" href="/workflow-builder" target="_blank">' +
              '<span class="ellipsis">⚡ Workflow Builder</span>' +
              '</a>'
            );
          }
        }, 500);
      }
    });
  }

  console.log('XState Workflow: Client initialized');
})();
