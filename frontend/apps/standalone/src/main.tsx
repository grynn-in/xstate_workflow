import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import { InstanceViewer } from './InstanceViewer';

// Get configuration from data attributes or URL params for builder
function getBuilderConfig(): { machineId?: string; attachedDoctype?: string } {
  const root = document.getElementById('workflow-builder-root');
  const urlParams = new URLSearchParams(window.location.search);

  return {
    machineId: root?.dataset.machineId || urlParams.get('machine') || undefined,
    attachedDoctype: root?.dataset.doctype || urlParams.get('doctype') || undefined,
  };
}

// Get configuration from data attributes or URL params for viewer
function getViewerConfig(): { machineId: string; doctype: string; docname: string } | null {
  const root = document.getElementById('workflow-viewer-root');
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
  const root = document.getElementById('workflow-builder-root');
  if (!root) {
    return false;
  }

  const config = getBuilderConfig();

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
  const root = document.getElementById('workflow-viewer-root');
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

// Mount the appropriate application
function mount() {
  // Try viewer first (more specific root element)
  if (mountViewer()) {
    return;
  }

  // Then try builder
  if (mountBuilder()) {
    return;
  }

  console.error('No workflow root element found (expected workflow-builder-root or workflow-viewer-root)');
}

// Auto-mount if DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mount);
} else {
  mount();
}

// Export for manual mounting
export { App, InstanceViewer, mount, mountBuilder, mountViewer };
