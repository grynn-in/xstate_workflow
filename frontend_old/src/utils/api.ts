// Frappe API utilities

import type { SaveMachineResponse, MachineListItem, ReactFlowConfig } from '../types';

// Declare frappe global (provided by Frappe framework)
declare const frappe: {
  call: (options: {
    method: string;
    args?: Record<string, unknown>;
    callback?: (response: { message: unknown }) => void;
    async?: boolean;
    freeze?: boolean;
    freeze_message?: string;
  }) => Promise<{ message: unknown }>;
  xcall: (method: string, args?: Record<string, unknown>) => Promise<unknown>;
  msgprint: (msg: string | { message: string; title?: string; indicator?: string }) => void;
  show_alert: (msg: string | { message: string; indicator?: string }, seconds?: number) => void;
  throw: (msg: string) => never;
};

/**
 * Save machine configuration to backend
 */
export async function saveMachine(
  machineId: string,
  xstateConfig: string,
  reactFlowConfig: string,
  title?: string,
  attachedDoctype?: string
): Promise<SaveMachineResponse> {
  const response = await frappe.xcall('xstate_workflow.workflow_engine.save_machine', {
    machine_id: machineId,
    json_config: xstateConfig,
    react_flow_config: reactFlowConfig,
    title: title || machineId,
    attached_doctype: attachedDoctype
  });

  return response as SaveMachineResponse;
}

/**
 * Load machine configuration from backend
 */
export async function loadMachine(machineId: string): Promise<{
  machine_id: string;
  title: string;
  version: number;
  json_config: string;
  react_flow_config: string | null;
  attached_doctype: string;
  guards: Array<{ name: string; code?: string }>;
  actions: Array<{ name: string; type: string; code?: string }>;
}> {
  const response = await frappe.xcall('xstate_workflow.workflow_engine.get_machine', {
    machine_id: machineId
  });

  return response as {
    machine_id: string;
    title: string;
    version: number;
    json_config: string;
    react_flow_config: string | null;
    attached_doctype: string;
    guards: Array<{ name: string; code?: string }>;
    actions: Array<{ name: string; type: string; code?: string }>;
  };
}

/**
 * List all available machines
 */
export async function listMachines(attachedTo?: string): Promise<MachineListItem[]> {
  const response = await frappe.xcall('xstate_workflow.workflow_engine.list_machines', {
    attached_to: attachedTo
  });

  return response as MachineListItem[];
}

/**
 * Convert React Flow config to XState using backend
 */
export async function convertToXState(reactFlowConfig: ReactFlowConfig): Promise<string> {
  const response = await frappe.xcall('xstate_workflow.workflow_engine.convert_react_flow_to_xstate', {
    react_flow_json: JSON.stringify(reactFlowConfig)
  });

  return response as string;
}

/**
 * Convert XState config to React Flow using backend
 */
export async function convertToReactFlow(xstateConfig: string): Promise<ReactFlowConfig> {
  const response = await frappe.xcall('xstate_workflow.workflow_engine.convert_xstate_to_react_flow', {
    xstate_json: xstateConfig
  });

  return JSON.parse(response as string) as ReactFlowConfig;
}

/**
 * Get list of available DocTypes for workflow attachment
 */
export async function getDocTypes(): Promise<string[]> {
  const response = await frappe.xcall('frappe.client.get_list', {
    doctype: 'DocType',
    filters: { istable: 0, issingle: 0 },
    fields: ['name'],
    limit_page_length: 0
  });

  return (response as Array<{ name: string }>).map(d => d.name);
}

/**
 * Show success message
 */
export function showSuccess(message: string): void {
  frappe.show_alert({ message, indicator: 'green' }, 3);
}

/**
 * Show error message
 */
export function showError(message: string): void {
  frappe.msgprint({ message, title: 'Error', indicator: 'red' });
}

/**
 * Download JSON file
 */
export function downloadJson(data: object, filename: string): void {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Read JSON file from file input
 */
export function readJsonFile(file: File): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const json = JSON.parse(e.target?.result as string);
        resolve(json);
      } catch (err) {
        reject(new Error('Invalid JSON file'));
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
}
