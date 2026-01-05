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
  nodeTypes,
  edgeTypes,
  PropertiesPanel,
  NodePalette,
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

  // Load existing machine
  useEffect(() => {
    if (initialMachineId) {
      loadMachine(initialMachineId)
        .then((data) => {
          setMachineTitle(data.title);

          // If we have visual config, use it
          if (data.workflow_builder_config) {
            const config = JSON.parse(data.workflow_builder_config) as WorkflowBuilderConfig;
            loadConfig(config);
          } else if (data.json_config) {
            // Convert from XState config
            const xstate = JSON.parse(data.json_config);
            const config = xstateToWorkflow(xstate);
            loadConfig(config);
          }

          setHasUnsavedChanges(false);
        })
        .catch((err) => {
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

      {/* Node Palette */}
      <div className="xsw-layout-palette">
        <NodePalette onAddNode={handleAddNode} />
      </div>

      {/* Canvas */}
      <div className="xsw-layout-canvas" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
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

      {/* Properties Panel */}
      <div className="xsw-layout-panel">
        <PropertiesPanel
          selectedNode={selectedNode}
          selectedEdge={selectedEdge}
          onNodeChange={updateNode}
          onEdgeChange={updateEdge}
        />
      </div>
    </div>
  );
}
