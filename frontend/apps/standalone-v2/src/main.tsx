import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import { InstanceViewer } from './InstanceViewer';
import { Dashboard } from './Dashboard';

// Get configuration from data attributes or URL params for builder
function getBuilderConfig(): { machineId?: string; attachedDoctype?: string } {
  const root = document.getElementById('workflow-builder-v2-root');
  const urlParams = new URLSearchParams(window.location.search);

  return {
    machineId: root?.dataset.machineId || urlParams.get('machine') || undefined,
    attachedDoctype: root?.dataset.doctype || urlParams.get('doctype') || undefined,
  };
}

// Get configuration from data attributes or URL params for viewer
function getViewerConfig(): { machineId: string; doctype: string; docname: string } | null {
  const root = document.getElementById('workflow-viewer-v2-root');
  if (!root) return null;

  const urlParams = new URLSearchParams(window.location.search);

  const machineId = root.dataset.machineId || urlParams.get('machine_id') || urlParams.get('machine') || '';
  const doctype = root.dataset.doctype || urlParams.get('doctype') || '';
  const docname = root.dataset.docname || urlParams.get('docname') || urlParams.get('name') || '';

  if (!machineId || !doctype || !docname) {
    return null;
  }

  return { machineId, doctype, docname };
}

// Mount the builder application
function mountBuilder() {
  console.log('mountBuilder V2 called');
  const root = document.getElementById('workflow-builder-v2-root');
  if (!root) {
    console.log('No workflow-builder-v2-root found');
    return false;
  }

  const config = getBuilderConfig();
  console.log('Builder V2 config:', config);

  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App
        machineId={config.machineId}
        attachedDoctype={config.attachedDoctype}
      />
    </React.StrictMode>
  );

  return true;
}

// Mount the viewer application
function mountViewer() {
  const root = document.getElementById('workflow-viewer-v2-root');
  if (!root) {
    return false;
  }

  const config = getViewerConfig();
  if (!config) {
    // Missing params - error is shown by HTML template
    return false;
  }

  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <InstanceViewer
        machineId={config.machineId}
        doctype={config.doctype}
        docname={config.docname}
      />
    </React.StrictMode>
  );

  return true;
}

// Mount the dashboard application
function mountDashboard() {
  const root = document.getElementById('workflow-dashboard-v2-root');
  if (!root) {
    return false;
  }

  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <Dashboard />
    </React.StrictMode>
  );

  return true;
}

// Mount the appropriate application
function mount() {
  // Try dashboard first
  if (mountDashboard()) {
    return;
  }

  // Try viewer (more specific root element)
  if (mountViewer()) {
    return;
  }

  // Then try builder
  if (mountBuilder()) {
    return;
  }

  console.error('No workflow V2 root element found (expected workflow-dashboard-v2-root, workflow-viewer-v2-root, or workflow-builder-v2-root)');
}

// Auto-mount if DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mount);
} else {
  mount();
}

// Export for manual mounting
export { App, InstanceViewer, Dashboard, mount, mountBuilder, mountViewer, mountDashboard };
