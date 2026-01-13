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
    },

    /**
     * Open workflow viewer in new tab for a specific document
     * @param {string} machine_id - Machine ID
     * @param {string} doctype - Document type
     * @param {string} docname - Document name
     */
    open_viewer: function (machine_id, doctype, docname) {
      var url = '/xstate-viewer/' + encodeURIComponent(machine_id) +
        '?doctype=' + encodeURIComponent(doctype) +
        '&docname=' + encodeURIComponent(docname);
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

      // Add Workflow tab
      add_workflow_tab(frm, state);

      // Update page indicator
      update_page_indicator(frm, state);
    });
  }

  /**
   * Add workflow section to form dashboard
   */
  function add_workflow_tab(frm, state) {
    // Remove existing section if any
    $('.xstate-workflow-section').remove();

    var machine_name = state.machine || '';
    var viewer_url = machine_name ? '/xstate-viewer/' + encodeURIComponent(machine_name) +
      '?doctype=' + encodeURIComponent(frm.doc.doctype) +
      '&docname=' + encodeURIComponent(frm.doc.name) : '';

    var state_color = get_state_color(state.current_state);
    var state_display = state.current_state.replace(/_/g, ' ').replace(/\b\w/g, function(l) { return l.toUpperCase(); });

    var html = '<div class="xstate-workflow-section" style="padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 10px 15px;">' +
      '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">' +
        '<div>' +
          '<strong style="font-size: 14px;">⚡ Workflow</strong>' +
          '<span class="indicator-pill ' + state_color + '" style="margin-left: 10px;">' + state_display + '</span>' +
        '</div>' +
        (viewer_url ? '<a href="' + viewer_url + '" target="_blank" class="btn btn-xs btn-default">View Diagram</a>' : '') +
      '</div>' +
      '<div class="text-muted" style="font-size: 12px;">' +
        'Status: ' + (state.status || 'active') +
        (state.last_event ? ' | Last: ' + state.last_event : '') +
      '</div>' +
    '</div>';

    // Direct DOM append to form-dashboard
    $('.form-dashboard').append(html);
    frm.workflow_tab_added = true;

    console.log('XState Workflow: Section added to dashboard');
  }

  /**
   * Render the workflow tab content
   */
  function render_workflow_tab_content(frm, state) {
    var machine_name = state.machine || '';
    var viewer_url = machine_name ? '/xstate-viewer/' + encodeURIComponent(machine_name) +
      '?doctype=' + encodeURIComponent(frm.doc.doctype) +
      '&docname=' + encodeURIComponent(frm.doc.name) : '';

    var html = '<div class="workflow-tab-content" style="padding: 20px;">' +
      // Header with state and diagram link
      '<div class="workflow-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #e5e5e5;">' +
        '<div class="workflow-state-info">' +
          '<h4 style="margin: 0 0 5px 0;">' + __('Workflow Status') + '</h4>' +
          '<span class="workflow-state-badge" style="display: inline-block; padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 14px; background: ' + get_state_bg_color(state.current_state) + '; color: ' + get_state_text_color(state.current_state) + ';">' +
            state.current_state.replace(/_/g, ' ').replace(/\b\w/g, function(l) { return l.toUpperCase(); }) +
          '</span>' +
          '<span class="workflow-status-label" style="margin-left: 10px; color: #6b7280; font-size: 13px;">(' + (state.status || 'active') + ')</span>' +
        '</div>' +
        (viewer_url ? '<a href="' + viewer_url + '" target="_blank" class="btn btn-primary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">' +
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>' +
          __('View Diagram') +
        '</a>' : '') +
      '</div>' +

      // Workflow Actions
      '<div class="workflow-actions-section" style="margin-bottom: 25px;">' +
        '<h5 style="margin-bottom: 12px; color: #374151;">' + __('Available Actions') + '</h5>' +
        '<div class="workflow-action-buttons" id="workflow-action-buttons-' + frm.doc.name.replace(/[^a-zA-Z0-9]/g, '_') + '">' +
          render_action_buttons(state) +
        '</div>' +
      '</div>' +

      // Pending Approvals
      '<div class="workflow-approvals-section" style="margin-bottom: 25px;">' +
        '<h5 style="margin-bottom: 12px; color: #374151;">' + __('Pending Approvals') + '</h5>' +
        '<div class="workflow-approvals-list" id="workflow-approvals-list-' + frm.doc.name.replace(/[^a-zA-Z0-9]/g, '_') + '">' +
          '<div class="text-muted">' + __('Loading...') + '</div>' +
        '</div>' +
      '</div>' +

      // Transition History
      '<div class="workflow-history-section">' +
        '<h5 style="margin-bottom: 12px; color: #374151;">' + __('Transition History') + '</h5>' +
        '<div class="workflow-history-list" id="workflow-history-list-' + frm.doc.name.replace(/[^a-zA-Z0-9]/g, '_') + '">' +
          '<div class="text-muted">' + __('Loading...') + '</div>' +
        '</div>' +
      '</div>' +

      // Links
      '<div class="workflow-links" style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #e5e5e5;">' +
        '<a href="/my-approvals" class="text-muted" style="margin-right: 20px;">' + __('📋 My Approvals') + '</a>' +
        (machine_name ? '<a href="/app/state-machine/' + encodeURIComponent(machine_name) + '" class="text-muted" target="_blank">' + __('⚙️ Workflow Settings') + '</a>' : '') +
      '</div>' +
    '</div>';

    frm.workflow_tab_pane.html(html);

    // Bind action button events
    frm.workflow_tab_pane.find('.workflow-action-btn').on('click', function() {
      var event = $(this).data('event');
      handle_workflow_action(frm, event);
    });
  }

  /**
   * Render action buttons HTML
   */
  function render_action_buttons(state) {
    var events = state.available_events || [];
    var enabled_events = events.filter(function(e) { return e.enabled; });

    if (enabled_events.length === 0) {
      return '<div class="text-muted">' + __('No actions available in current state') + '</div>';
    }

    var html = '<div class="btn-group" role="group">';
    enabled_events.forEach(function(evt) {
      var btn_class = get_button_class(evt.event);
      var icon = get_event_icon(evt.event);
      html += '<button class="btn ' + btn_class + ' workflow-action-btn" data-event="' + evt.event + '" style="margin-right: 8px;">' +
        icon + ' ' + format_event_name(evt.event) +
      '</button>';
    });
    html += '</div>';

    return html;
  }

  /**
   * Load approval tasks for the workflow tab
   */
  function load_approval_tasks_for_tab(frm) {
    var container_id = 'workflow-approvals-list-' + frm.doc.name.replace(/[^a-zA-Z0-9]/g, '_');
    var $container = $('#' + container_id);

    frappe.xcall('xstate_workflow.api.approval.get_document_approval_tasks', {
      doctype: frm.doc.doctype,
      docname: frm.doc.name
    }).then(function(tasks) {
      if (!tasks || tasks.length === 0) {
        $container.html('<div class="text-muted">' + __('No approval tasks for this document') + '</div>');
        return;
      }

      var html = '<div class="approval-tasks-list">';
      tasks.forEach(function(task) {
        var status_color = task.status === 'Pending' ? '#f59e0b' :
                          task.status === 'Completed' ? '#10b981' : '#6b7280';
        var status_bg = task.status === 'Pending' ? '#fef3c7' :
                       task.status === 'Completed' ? '#d1fae5' : '#f3f4f6';

        html += '<div class="approval-task-item" style="padding: 12px; margin-bottom: 8px; background: #f9fafb; border-radius: 8px; border-left: 3px solid ' + status_color + ';">' +
          '<div style="display: flex; justify-content: space-between; align-items: flex-start;">' +
            '<div>' +
              '<strong>' + (task.node_label || task.node_id) + '</strong>' +
              '<div class="text-muted" style="font-size: 12px; margin-top: 4px;">' +
                (task.assigned_to ? __('Assigned to: {0}', [task.assigned_to]) :
                 task.assigned_role ? __('Role: {0}', [task.assigned_role]) : '') +
              '</div>' +
              (task.action_taken ? '<div style="font-size: 12px; margin-top: 4px;">' + __('Action: {0}', [task.action_taken]) +
                (task.completed_by ? ' ' + __('by {0}', [task.completed_by]) : '') + '</div>' : '') +
            '</div>' +
            '<span style="padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; background: ' + status_bg + '; color: ' + status_color + ';">' + task.status + '</span>' +
          '</div>';

        // Add action buttons for pending tasks that user can action
        if (task.status === 'Pending' && task.can_action) {
          var actions = task.available_actions || ['Approve', 'Reject'];
          html += '<div style="margin-top: 10px;">';
          actions.forEach(function(action) {
            var btn_class = action.toLowerCase() === 'approve' ? 'btn-success' :
                           action.toLowerCase() === 'reject' ? 'btn-danger' : 'btn-secondary';
            html += '<button class="btn btn-sm ' + btn_class + ' approval-action-btn" ' +
              'data-task="' + task.name + '" data-action="' + action + '" style="margin-right: 6px;">' +
              action + '</button>';
          });
          html += '</div>';
        }

        html += '</div>';
      });
      html += '</div>';

      $container.html(html);

      // Bind approval action buttons
      $container.find('.approval-action-btn').on('click', function() {
        var taskName = $(this).data('task');
        var action = $(this).data('action');
        handle_approval_action(frm, taskName, action);
      });
    }).catch(function() {
      $container.html('<div class="text-muted">' + __('No approval tasks') + '</div>');
    });
  }

  /**
   * Load transition history for the workflow tab
   */
  function load_transition_history(frm, state) {
    var container_id = 'workflow-history-list-' + frm.doc.name.replace(/[^a-zA-Z0-9]/g, '_');
    var $container = $('#' + container_id);

    frappe.xcall('xstate_workflow.api.workflow.get_transition_history', {
      doctype: frm.doc.doctype,
      docname: frm.doc.name
    }).then(function(history) {
      if (!history || history.length === 0) {
        $container.html('<div class="text-muted">' + __('No transition history') + '</div>');
        return;
      }

      var html = '<div class="timeline" style="position: relative; padding-left: 20px;">';
      history.forEach(function(entry, index) {
        var is_latest = index === 0;
        html += '<div class="timeline-item" style="position: relative; padding-bottom: 16px; padding-left: 20px; border-left: 2px solid ' + (is_latest ? '#3b82f6' : '#e5e7eb') + ';">' +
          '<div class="timeline-dot" style="position: absolute; left: -7px; top: 0; width: 12px; height: 12px; border-radius: 50%; background: ' + (is_latest ? '#3b82f6' : '#9ca3af') + ';"></div>' +
          '<div class="timeline-content">' +
            '<div style="font-weight: 500;">' +
              '<span style="color: #6b7280;">' + (entry.from_state || 'Start') + '</span>' +
              ' → ' +
              '<span style="color: #1f2937;">' + entry.to_state + '</span>' +
            '</div>' +
            '<div style="font-size: 12px; color: #6b7280; margin-top: 2px;">' +
              '<span class="badge" style="background: #e0e7ff; color: #4338ca; padding: 2px 6px; border-radius: 4px; font-size: 11px;">' + entry.event + '</span>' +
              ' • ' + frappe.datetime.prettyDate(entry.timestamp) +
              (entry.user ? ' • ' + entry.user : '') +
            '</div>' +
          '</div>' +
        '</div>';
      });
      html += '</div>';

      $container.html(html);
    }).catch(function() {
      // Fallback: show basic info from state
      var html = '<div class="text-muted">';
      if (state.last_event) {
        html += __('Last action: {0}', [format_event_name(state.last_event)]);
        if (state.last_transition_at) {
          html += ' (' + frappe.datetime.prettyDate(state.last_transition_at) + ')';
        }
      } else {
        html += __('No transitions recorded');
      }
      html += '</div>';
      $container.html(html);
    });
  }

  /**
   * Get background color for state badge
   */
  function get_state_bg_color(state) {
    var lowerState = state.toLowerCase();
    if (lowerState.includes('approved') || lowerState.includes('completed')) return '#d1fae5';
    if (lowerState.includes('rejected') || lowerState.includes('cancelled')) return '#fee2e2';
    if (lowerState.includes('pending')) return '#fef3c7';
    if (lowerState.includes('draft')) return '#f3f4f6';
    return '#dbeafe';
  }

  /**
   * Get text color for state badge
   */
  function get_state_text_color(state) {
    var lowerState = state.toLowerCase();
    if (lowerState.includes('approved') || lowerState.includes('completed')) return '#065f46';
    if (lowerState.includes('rejected') || lowerState.includes('cancelled')) return '#991b1b';
    if (lowerState.includes('pending')) return '#92400e';
    if (lowerState.includes('draft')) return '#374151';
    return '#1e40af';
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

    // Build viewer URL if we have the machine name
    var viewer_link = '';
    if (state.machine) {
      var viewer_url = '/xstate-viewer/' + encodeURIComponent(state.machine) +
        '?doctype=' + encodeURIComponent(cur_frm.doc.doctype) +
        '&docname=' + encodeURIComponent(cur_frm.doc.name);
      viewer_link = '<a href="' + viewer_url + '" class="text-muted small" target="_blank" style="margin-left: 12px;">' +
        '<span>📊</span> ' + __('View Workflow Diagram') +
        '</a>';
    }

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
      '<div class="workflow-approvals-link mt-2">' +
      '<a href="/my-approvals" class="text-muted small">' +
      '<span>📋</span> ' + __('View My Approvals') +
      '</a>' +
      viewer_link +
      '</div>' +
      '</div>';
  }

  /**
   * Add approval task section to form showing pending tasks for this document
   */
  function add_approval_task_section(frm) {
    if (frm.approval_section_added) return;

    frappe.xcall('xstate_workflow.api.approval.get_document_approval_tasks', {
      doctype: frm.doc.doctype,
      docname: frm.doc.name
    }).then(function(tasks) {
      if (!tasks || tasks.length === 0) return;

      frm.approval_section_added = true;

      var pending_tasks = tasks.filter(function(t) { return t.status === 'Pending'; });
      var html = render_approval_tasks_section(pending_tasks, frm);

      frm.dashboard.add_section($(html), __('Pending Approvals'));

      // Bind action buttons
      frm.dashboard.wrapper.find('.approval-action-btn').on('click', function() {
        var taskName = $(this).data('task');
        var action = $(this).data('action');
        handle_approval_action(frm, taskName, action);
      });
    }).catch(function(err) {
      console.log('No approval tasks:', err);
    });
  }

  /**
   * Render approval tasks section HTML
   */
  function render_approval_tasks_section(tasks, frm) {
    if (!tasks || tasks.length === 0) {
      return '<div class="text-muted small">' + __('No pending approvals for this document') + '</div>';
    }

    var html = '<div class="approval-tasks-section">';

    tasks.forEach(function(task) {
      var actions_html = '';
      var available_actions = task.available_actions || ['Approve', 'Reject'];

      // Check if current user can action this task
      var can_action = task.can_action;

      if (can_action) {
        available_actions.forEach(function(action) {
          var btn_class = action.toLowerCase() === 'approve' ? 'btn-success' :
                         action.toLowerCase() === 'reject' ? 'btn-danger' : 'btn-secondary';
          actions_html += '<button class="btn btn-sm ' + btn_class + ' approval-action-btn" ' +
            'data-task="' + task.name + '" data-action="' + action + '">' +
            action + '</button> ';
        });
      }

      html += '<div class="approval-task-item" style="padding: 8px 0; border-bottom: 1px solid #eee;">' +
        '<div class="d-flex justify-content-between align-items-center">' +
        '<div>' +
        '<strong>' + (task.node_label || task.node_id) + '</strong>' +
        '<div class="text-muted small">' +
        (task.assigned_to ? __('Assigned to: {0}', [task.assigned_to]) :
         task.assigned_role ? __('Assigned to role: {0}', [task.assigned_role]) : '') +
        '</div>' +
        '</div>' +
        '<div class="approval-task-actions">' + actions_html + '</div>' +
        '</div>' +
        '</div>';
    });

    html += '<div class="mt-2"><a href="/my-approvals" class="small">' + __('View all approvals →') + '</a></div>';
    html += '</div>';

    return html;
  }

  /**
   * Handle approval action from form
   */
  function handle_approval_action(frm, taskName, action) {
    var d = new frappe.ui.Dialog({
      title: action + ' - ' + __('Approval Task'),
      fields: [
        {
          fieldname: 'comments',
          fieldtype: 'Small Text',
          label: __('Comments (optional)')
        }
      ],
      primary_action_label: action,
      primary_action: function(values) {
        d.hide();
        frappe.dom.freeze(__('Processing...'));

        frappe.xcall('xstate_workflow.api.approval.complete_approval_task', {
          task_name: taskName,
          action: action,
          comments: values.comments || ''
        }).then(function(result) {
          frappe.dom.unfreeze();
          frappe.show_alert({
            message: __('Task {0}d successfully', [action.toLowerCase()]),
            indicator: 'green'
          }, 3);
          frm.reload_doc();
        }).catch(function(err) {
          frappe.dom.unfreeze();
          frappe.msgprint({
            title: __('Error'),
            message: err.message || __('Failed to complete task'),
            indicator: 'red'
          });
        });
      }
    });

    d.show();
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

  // Check and add workflow section to current form
  function check_and_add_workflow() {
    if (typeof cur_frm === 'undefined' || !cur_frm || !cur_frm.doc || !cur_frm.doc.name) return;
    if (cur_frm.doc.__islocal) return;
    if (cur_frm.workflow_section_added) return;

    var attached_doctypes = frappe.boot.xstate_workflow?.attached_doctypes || [];
    if (attached_doctypes.includes(cur_frm.doc.doctype)) {
      console.log('XState Workflow: Adding section to', cur_frm.doc.doctype, cur_frm.doc.name);
      add_workflow_section(cur_frm);
    }
  }

  // Use frappe.router to detect page changes
  frappe.router.on('change', function() {
    // Wait for form to be ready
    setTimeout(check_and_add_workflow, 500);
    setTimeout(check_and_add_workflow, 1500);
  });

  // Also check on initial load and periodically
  $(function() {
    setTimeout(check_and_add_workflow, 1000);
    setTimeout(check_and_add_workflow, 2000);
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
