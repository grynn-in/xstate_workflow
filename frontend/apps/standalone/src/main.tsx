import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';

// Get configuration from data attributes or URL params
function getConfig(): { machineId?: string; attachedDoctype?: string } {
  const root = document.getElementById('workflow-builder-root');
  const urlParams = new URLSearchParams(window.location.search);

  return {
    machineId: root?.dataset.machineId || urlParams.get('machine') || undefined,
    attachedDoctype: root?.dataset.doctype || urlParams.get('doctype') || undefined,
  };
}

// Mount the application
function mount() {
  const root = document.getElementById('workflow-builder-root');
  if (!root) {
    console.error('Workflow builder root element not found');
    return;
  }

  const config = getConfig();

  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App
        machineId={config.machineId}
        attachedDoctype={config.attachedDoctype}
      />
    </React.StrictMode>
  );
}

// Auto-mount if DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mount);
} else {
  mount();
}

// Export for manual mounting
export { App, mount };
