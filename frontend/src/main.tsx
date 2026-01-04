// Entry point for React Flow Workflow Builder

import React from 'react';
import ReactDOM from 'react-dom/client';
import WorkflowBuilder from './components/WorkflowBuilder';

// Global CSS
const globalStyles = `
  .workflow-builder-container {
    width: 100%;
    height: 100vh;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  }

  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* React Flow overrides */
  .react-flow__node {
    cursor: pointer;
  }

  .react-flow__edge {
    cursor: pointer;
  }

  .react-flow__controls button {
    background: #1e293b;
    border-color: #334155;
    color: white;
  }

  .react-flow__controls button:hover {
    background: #334155;
  }

  /* Selection styles */
  .state-node.selected {
    box-shadow: 0 0 0 2px #fff, 0 0 0 4px #6366f1;
  }

  /* Scrollbar styles */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  ::-webkit-scrollbar-track {
    background: #1e293b;
  }

  ::-webkit-scrollbar-thumb {
    background: #475569;
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: #64748b;
  }
`;

// Inject styles
const styleElement = document.createElement('style');
styleElement.textContent = globalStyles;
document.head.appendChild(styleElement);

// Mount function for external use
function mountWorkflowBuilder(container: HTMLElement, machineId?: string) {
  const root = ReactDOM.createRoot(container);
  root.render(
    <React.StrictMode>
      <div className="workflow-builder-container">
        <WorkflowBuilder machineId={machineId} />
      </div>
    </React.StrictMode>
  );

  return root;
}

// Auto-mount if container exists
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('workflow-builder-root');
  if (container) {
    // Get machine ID from URL or data attribute
    // Support both 'machine' and 'machine_id' URL params
    const urlParams = new URLSearchParams(window.location.search);
    const machineId = urlParams.get('machine') || urlParams.get('machine_id') || container.dataset.machineId;

    // If no machineId, it's a blank canvas for new workflow
    mountWorkflowBuilder(container, machineId || undefined);
  }
});

// Export for manual mounting
(window as Window & { mountWorkflowBuilder?: typeof mountWorkflowBuilder }).mountWorkflowBuilder = mountWorkflowBuilder;

export { mountWorkflowBuilder };
export default WorkflowBuilder;
