import { StrictMode } from 'react';
import { createRoot, Root } from 'react-dom/client';
import { WorkflowBuilderWidget } from './WorkflowBuilderWidget';
import { WorkflowStateIndicator } from './WorkflowStateIndicator';
import { WorkflowActionButtons } from './WorkflowActionButtons';

// Store roots for cleanup
const roots = new Map<string, Root>();

/**
 * Mount the workflow builder widget into a container
 * Called from State Machine form script
 */
export function mountWorkflowBuilder(
  containerId: string,
  options: {
    machineId?: string;
    attachedDoctype?: string;
    onSave?: (config: unknown) => void;
    onClose?: () => void;
  } = {}
): void {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error(`Container #${containerId} not found`);
    return;
  }

  // Cleanup existing root
  if (roots.has(containerId)) {
    roots.get(containerId)?.unmount();
  }

  const root = createRoot(container);
  roots.set(containerId, root);

  root.render(
    <StrictMode>
      <WorkflowBuilderWidget
        machineId={options.machineId}
        attachedDoctype={options.attachedDoctype}
        onSave={options.onSave}
        onClose={options.onClose}
      />
    </StrictMode>
  );
}

/**
 * Unmount the workflow builder widget
 */
export function unmountWorkflowBuilder(containerId: string): void {
  if (roots.has(containerId)) {
    roots.get(containerId)?.unmount();
    roots.delete(containerId);
  }
}

/**
 * Mount workflow state indicator on a document form
 * Shows current state badge and available transitions
 */
export function mountStateIndicator(
  containerId: string,
  options: {
    doctype: string;
    docname: string;
    onStateChange?: (newState: string) => void;
  }
): void {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error(`Container #${containerId} not found`);
    return;
  }

  // Cleanup existing root
  if (roots.has(containerId)) {
    roots.get(containerId)?.unmount();
  }

  const root = createRoot(container);
  roots.set(containerId, root);

  root.render(
    <StrictMode>
      <WorkflowStateIndicator
        doctype={options.doctype}
        docname={options.docname}
        onStateChange={options.onStateChange}
      />
    </StrictMode>
  );
}

/**
 * Mount workflow action buttons on a document form
 * Renders buttons based on available transitions
 */
export function mountActionButtons(
  containerId: string,
  options: {
    doctype: string;
    docname: string;
    onTransition?: (event: string, result: unknown) => void;
  }
): void {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error(`Container #${containerId} not found`);
    return;
  }

  // Cleanup existing root
  if (roots.has(containerId)) {
    roots.get(containerId)?.unmount();
  }

  const root = createRoot(container);
  roots.set(containerId, root);

  root.render(
    <StrictMode>
      <WorkflowActionButtons
        doctype={options.doctype}
        docname={options.docname}
        onTransition={options.onTransition}
      />
    </StrictMode>
  );
}

/**
 * Unmount any widget by container ID
 */
export function unmountWidget(containerId: string): void {
  if (roots.has(containerId)) {
    roots.get(containerId)?.unmount();
    roots.delete(containerId);
  }
}

// Expose to window for Frappe integration
declare global {
  interface Window {
    XStateWorkflowWidget: {
      mountWorkflowBuilder: typeof mountWorkflowBuilder;
      unmountWorkflowBuilder: typeof unmountWorkflowBuilder;
      mountStateIndicator: typeof mountStateIndicator;
      mountActionButtons: typeof mountActionButtons;
      unmountWidget: typeof unmountWidget;
    };
  }
}

window.XStateWorkflowWidget = {
  mountWorkflowBuilder,
  unmountWorkflowBuilder,
  mountStateIndicator,
  mountActionButtons,
  unmountWidget,
};
