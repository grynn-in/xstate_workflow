import type {
  WorkflowBuilderConfig,
  XStateMachineConfig,
  FrappeField,
} from '@xstate-workflow/core';

// Frappe global type declaration
declare global {
  interface Window {
    frappe: {
      xcall: <T = unknown>(method: string, args?: Record<string, unknown>) => Promise<T>;
      call: <T = unknown>(options: {
        method: string;
        args?: Record<string, unknown>;
        callback?: (response: T) => void;
        async?: boolean;
      }) => Promise<T>;
      msgprint: (message: string) => void;
      show_alert: (options: { message: string; indicator?: string }) => void;
    };
  }
}

const frappe = typeof window !== 'undefined' ? window.frappe : null;

/**
 * API response types
 */
export interface SaveMachineResponse {
  name: string;
  version: number;
}

export interface LoadMachineResponse {
  name: string;
  title: string;
  description?: string;
  attached_doctype?: string;
  json_config: string;
  workflow_builder_config?: string;
  version: number;
  guards: Array<{ guard_name: string; description?: string }>;
  actions: Array<{ action_name: string; action_type: string; description?: string }>;
}

export interface ListMachinesResponse {
  machines: Array<{
    name: string;
    title: string;
    attached_doctype?: string;
    is_active: boolean;
    version: number;
  }>;
}

/**
 * Save a workflow machine configuration
 */
export async function saveMachine(
  machineId: string | null,
  title: string,
  xstateConfig: XStateMachineConfig,
  workflowConfig: WorkflowBuilderConfig,
  attachedDoctype?: string
): Promise<SaveMachineResponse> {
  if (!frappe) {
    throw new Error('Frappe not available');
  }

  return frappe.xcall<SaveMachineResponse>(
    'xstate_workflow.workflow_engine.save_machine',
    {
      machine_id: machineId,
      title,
      json_config: JSON.stringify(xstateConfig),
      workflow_builder_config: JSON.stringify(workflowConfig),
      attached_doctype: attachedDoctype,
    }
  );
}

/**
 * Load a workflow machine configuration
 */
export async function loadMachine(machineId: string): Promise<LoadMachineResponse> {
  if (!frappe) {
    throw new Error('Frappe not available');
  }

  return frappe.xcall<LoadMachineResponse>(
    'xstate_workflow.workflow_engine.get_machine',
    { machine_id: machineId }
  );
}

/**
 * List all workflow machines
 */
export async function listMachines(attachedDoctype?: string): Promise<ListMachinesResponse> {
  if (!frappe) {
    throw new Error('Frappe not available');
  }

  return frappe.xcall<ListMachinesResponse>(
    'xstate_workflow.workflow_engine.list_machines',
    { attached_doctype: attachedDoctype }
  );
}

/**
 * Get all available DocTypes
 */
export async function getDocTypes(): Promise<string[]> {
  if (!frappe) {
    throw new Error('Frappe not available');
  }

  const response = await frappe.xcall<{ message: Array<{ name: string }> }>(
    'frappe.client.get_list',
    {
      doctype: 'DocType',
      filters: { istable: 0, issingle: 0 },
      fields: ['name'],
      order_by: 'name asc',
      limit_page_length: 0,
    }
  );

  return (response.message || []).map((d) => d.name);
}

/**
 * Trigger a workflow event
 */
export async function triggerEvent(
  doctype: string,
  docname: string,
  event: string,
  data?: Record<string, unknown>
): Promise<{ success: boolean; new_state: string; context: Record<string, unknown> }> {
  if (!frappe) {
    throw new Error('Frappe not available');
  }

  return frappe.xcall(
    'xstate_workflow.workflow_engine.trigger_event_sync',
    { doctype, docname, event, data }
  );
}

/**
 * Get current workflow state for a document
 */
export async function getWorkflowState(
  doctype: string,
  docname: string
): Promise<{
  current_state: string;
  status: string;
  context: Record<string, unknown>;
  available_events: Array<{ event: string; target: string; has_guard: boolean }>;
}> {
  if (!frappe) {
    throw new Error('Frappe not available');
  }

  return frappe.xcall(
    'xstate_workflow.workflow_engine.get_machine_state',
    { doctype, docname }
  );
}

/**
 * Show success message
 */
export function showSuccess(message: string): void {
  if (frappe) {
    frappe.show_alert({ message, indicator: 'green' });
  }
}

/**
 * Show error message
 */
export function showError(message: string): void {
  if (frappe) {
    frappe.msgprint(message);
  }
}

/**
 * Get DocType fields with proper formatting for guard builder
 */
export async function getDocTypeFields(doctype: string): Promise<FrappeField[]> {
  if (!frappe) {
    throw new Error('Frappe not available');
  }

  try {
    // Use frappe.xcall to get doc meta which includes all fields
    const meta = await frappe.xcall<{
      docs: Array<{
        fields: Array<{
          fieldname: string;
          fieldtype: string;
          label: string;
          options?: string;
          reqd?: number;
        }>;
      }>;
    }>(
      'frappe.client.get',
      {
        doctype: 'DocType',
        name: doctype,
      }
    );

    if (!meta?.docs?.[0]?.fields) {
      return [];
    }

    // Filter out section breaks, column breaks, etc.
    const dataFieldTypes = [
      'Data', 'Link', 'Select', 'Int', 'Float', 'Currency',
      'Date', 'Datetime', 'Time', 'Check', 'Text', 'Small Text',
      'Long Text', 'Code', 'Read Only', 'Password', 'Rating',
      'Duration', 'Color', 'Percent', 'Dynamic Link'
    ];

    return meta.docs[0].fields
      .filter(f => dataFieldTypes.includes(f.fieldtype))
      .map(f => ({
        fieldname: f.fieldname,
        fieldtype: f.fieldtype,
        label: f.label || f.fieldname,
        options: f.options,
        reqd: f.reqd === 1,
      }));
  } catch (err) {
    console.error('Failed to get DocType fields:', err);
    return [];
  }
}

/**
 * Get all roles for trigger configuration
 */
export async function getRoles(): Promise<string[]> {
  if (!frappe) {
    throw new Error('Frappe not available');
  }

  try {
    const response = await frappe.xcall<Array<{ name: string }>>(
      'frappe.client.get_list',
      {
        doctype: 'Role',
        filters: { disabled: 0 },
        fields: ['name'],
        order_by: 'name asc',
        limit_page_length: 0,
      }
    );

    return (response || []).map(r => r.name);
  } catch (err) {
    console.error('Failed to get roles:', err);
    return ['System Manager', 'Administrator'];
  }
}

/**
 * Get current workflow state for a document (alias for getWorkflowState with better typing)
 */
export async function getMachineState(
  doctype: string,
  docname: string
): Promise<{
  has_workflow: boolean;
  instance_name?: string;
  machine?: string;
  current_state?: string;
  status?: string;
  context?: Record<string, unknown>;
  available_events?: Array<{
    event: string;
    target: string | null;
    guards: string[];
    actions: string[];
    enabled: boolean;
  }>;
  transition_count?: number;
}> {
  if (!frappe) {
    throw new Error('Frappe not available');
  }

  return frappe.xcall(
    'xstate_workflow.workflow_engine.get_machine_state',
    { doctype, docname }
  );
}
