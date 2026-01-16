import { useCallback, useEffect, useState, useRef, type DragEvent } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  type NodeMouseHandler,
  type EdgeMouseHandler,
  type ReactFlowInstance,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  allNodeTypes,
  edgeTypes,
  PropertiesPanel,
  NodePalette,
  ResizablePanel,
  useWorkflowBuilder,
  workflowToXState,
  xstateToWorkflow,
  type WorkflowBuilderConfig,
  type WorkflowNode,
  type WorkflowEdge,
  type XStateNodeType,
} from '@xstate-workflow/core';
import '@xstate-workflow/core/styles';

import {
  saveMachine,
  loadMachine,
  showSuccess,
  showError,
  getDocTypes,
  getDocTypeFields,
  getRoles,
  getUsers,
  type FrappeField,
} from '@xstate-workflow/frappe-adapter';

interface AppProps {
  machineId?: string;
  attachedDoctype?: string;
}

export function App({ machineId: initialMachineId, attachedDoctype }: AppProps) {
  const [machineId, setMachineId] = useState<string | undefined>(initialMachineId);
  const [machineTitle, setMachineTitle] = useState('New Workflow');
  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  // Data for property panels
  const [doctypesList, setDoctypesList] = useState<string[]>([]);
  const [doctypeFields, setDoctypeFields] = useState<FrappeField[]>([]);
  const [availableRoles, setAvailableRoles] = useState<string[]>([]);
  const [availableUsers, setAvailableUsers] = useState<Array<{ name: string; full_name: string }>>([]);

  const {
    nodes,
    edges,
    selectedNode,
    selectedEdge,
    setSelectedNode,
    setSelectedEdge,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    updateNode,
    updateEdge,
    getConfig,
    loadConfig,
  } = useWorkflowBuilder({
    onChange: () => setHasUnsavedChanges(true),
  });

  // Fetch doctypes, roles, and users on mount
  useEffect(() => {
    getDocTypes().then(setDoctypesList).catch(console.error);
    getRoles().then(setAvailableRoles).catch(console.error);
    getUsers().then(setAvailableUsers).catch(console.error);
  }, []);

  // Fetch doctype fields when attachedDoctype changes
  useEffect(() => {
    if (attachedDoctype) {
      getDocTypeFields(attachedDoctype).then(setDoctypeFields).catch(console.error);
    } else {
      setDoctypeFields([]);
    }
  }, [attachedDoctype]);

  // Load existing machine
  useEffect(() => {
    console.log('useEffect triggered, initialMachineId:', initialMachineId);
    if (initialMachineId) {
      console.log('Calling loadMachine...');
      loadMachine(initialMachineId)
        .then((data) => {
          console.log('Loaded machine data:', data);
          console.log('json_config exists:', !!data.json_config);
          setMachineTitle(data.title);

          if (data.json_config) {
            // Always convert from XState config to get full node data (labels, metadata)
            const xstate = JSON.parse(data.json_config);

            // Use workflow_builder_config for positions if available
            let existingLayout: WorkflowBuilderConfig | undefined;
            if (data.workflow_builder_config) {
              try {
                existingLayout = JSON.parse(data.workflow_builder_config) as WorkflowBuilderConfig;
              } catch {
                // Ignore parsing errors
              }
            }

            const config = xstateToWorkflow(xstate, existingLayout);
            console.log('Converted config:', JSON.stringify(config, null, 2));
            console.log('Nodes:', config.nodes.map(n => ({ id: n.id, type: n.type, label: n.data?.label })));
            loadConfig(config);
          }

          setHasUnsavedChanges(false);
        })
        .catch((err) => {
          console.error('Load machine error:', err);
          showError(`Failed to load workflow: ${err.message}`);
        });
    }
  }, [initialMachineId, loadConfig]);

  // Handle node click
  const onNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      setSelectedNode(node as WorkflowNode);
    },
    [setSelectedNode]
  );

  // Handle edge click
  const onEdgeClick: EdgeMouseHandler = useCallback(
    (_, edge) => {
      setSelectedEdge(edge as WorkflowEdge);
    },
    [setSelectedEdge]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    setSelectedNode(undefined);
    setSelectedEdge(undefined);
  }, [setSelectedNode, setSelectedEdge]);

  // Handle save
  const handleSave = useCallback(async () => {
    setIsSaving(true);
    try {
      const config = getConfig();
      const xstate = workflowToXState(config);

      const result = await saveMachine(
        machineId || null,
        machineTitle,
        xstate,
        config,
        attachedDoctype
      );

      setMachineId(result.name);
      setHasUnsavedChanges(false);
      showSuccess('Workflow saved successfully');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      showError(`Failed to save: ${message}`);
    } finally {
      setIsSaving(false);
    }
  }, [getConfig, machineId, machineTitle, attachedDoctype]);

  // Handle add node from palette (click)
  const handleAddNode = useCallback(
    (type: XStateNodeType, position: { x: number; y: number }) => {
      addNode(type, position);
      setHasUnsavedChanges(true);
    },
    [addNode]
  );

  // Handle drop from palette
  const onDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/xstate-node-type') as XStateNodeType;
      if (!type || !reactFlowInstance || !reactFlowWrapper.current) return;

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      addNode(type, position);
      setHasUnsavedChanges(true);
    },
    [reactFlowInstance, addNode]
  );

  // Handle export
  const handleExport = useCallback(() => {
    const config = getConfig();
    const xstate = workflowToXState(config);
    const blob = new Blob([JSON.stringify(xstate, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${machineTitle.toLowerCase().replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [getConfig, machineTitle]);

  return (
    <div className="xsw-layout">
      {/* Toolbar */}
      <div className="xsw-layout-toolbar">
        <div className="xsw-toolbar">
          <div className="xsw-toolbar-left">
            <span style={{ fontSize: '20px' }}>⬡</span>
            <input
              type="text"
              className="xsw-input"
              style={{ width: '200px', fontWeight: 600 }}
              value={machineTitle}
              onChange={(e) => {
                setMachineTitle(e.target.value);
                setHasUnsavedChanges(true);
              }}
            />
            {attachedDoctype && (
              <span className="xsw-toolbar-doctype">{attachedDoctype}</span>
            )}
            {hasUnsavedChanges && (
              <span style={{ color: '#f59e0b', fontSize: '12px' }}>● Unsaved</span>
            )}
          </div>
          <div className="xsw-toolbar-right">
            <button
              className="xsw-button xsw-button-secondary"
              onClick={handleExport}
            >
              Export
            </button>
            <button
              className="xsw-button xsw-button-primary"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="xsw-layout-main">
        {/* Node Palette - Left Panel */}
        <ResizablePanel
          position="left"
          defaultWidth={200}
          minWidth={150}
          maxWidth={350}
          collapsedWidth={24}
        >
          <NodePalette onAddNode={handleAddNode} />
        </ResizablePanel>

        {/* Canvas */}
        <div className="xsw-layout-canvas" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={allNodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={onPaneClick}
            onInit={setReactFlowInstance}
            onDragOver={onDragOver}
            onDrop={onDrop}
            fitView
            className="xsw-canvas"
            defaultEdgeOptions={{
              type: 'transition',
            }}
          >
            <Controls />
            <MiniMap className="xsw-minimap" />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          </ReactFlow>
        </div>

        {/* Properties Panel - Right Panel */}
        <ResizablePanel
          position="right"
          defaultWidth={320}
          minWidth={280}
          maxWidth={500}
          collapsedWidth={24}
        >
          <PropertiesPanel
            selectedNode={selectedNode}
            selectedEdge={selectedEdge}
            onNodeChange={updateNode}
            onEdgeChange={updateEdge}
            doctypeFields={doctypeFields}
            availableRoles={availableRoles}
            availableDoctypes={doctypesList}
            availableUsers={availableUsers}
            onFetchDoctypeFields={getDocTypeFields}
          />
        </ResizablePanel>
      </div>
    </div>
  );
}
