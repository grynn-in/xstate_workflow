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
  type FrappeField,
} from '@xstate-workflow/core';
import '@xstate-workflow/core/styles';

import {
  loadMachine,
  getDocTypeFields,
  getRoles,
} from '@xstate-workflow/frappe-adapter';

interface WorkflowBuilderWidgetProps {
  machineId?: string;
  attachedDoctype?: string;
  onSave?: (config: { xstate: unknown; visual: WorkflowBuilderConfig }) => void;
  onClose?: () => void;
}

export function WorkflowBuilderWidget({
  machineId,
  attachedDoctype,
  onSave,
  onClose,
}: WorkflowBuilderWidgetProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [doctypeFields, setDoctypeFields] = useState<FrappeField[]>([]);
  const [availableRoles, setAvailableRoles] = useState<string[]>([]);
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
  } = useWorkflowBuilder({});

  // Load machine data and doctype fields
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        // Load roles
        const roles = await getRoles();
        setAvailableRoles(roles);

        // Load doctype fields if attached
        if (attachedDoctype) {
          const fields = await getDocTypeFields(attachedDoctype);
          setDoctypeFields(fields);
        }

        // Load existing machine config
        if (machineId) {
          const data = await loadMachine(machineId);
          if (data.workflow_builder_config) {
            const config = JSON.parse(data.workflow_builder_config) as WorkflowBuilderConfig;
            loadConfig(config);
          } else if (data.json_config) {
            const xstate = JSON.parse(data.json_config);
            const config = xstateToWorkflow(xstate);
            loadConfig(config);
          }
        }
      } catch (err) {
        console.error('Failed to load workflow data:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [machineId, attachedDoctype, loadConfig]);

  // Handle node click
  const onNodeClick: NodeMouseHandler = useCallback(
    (_, node) => {
      setSelectedNode(node as WorkflowNode);
      setSelectedEdge(undefined);
    },
    [setSelectedNode, setSelectedEdge]
  );

  // Handle edge click
  const onEdgeClick: EdgeMouseHandler = useCallback(
    (_, edge) => {
      setSelectedEdge(edge as WorkflowEdge);
      setSelectedNode(undefined);
    },
    [setSelectedEdge, setSelectedNode]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    setSelectedNode(undefined);
    setSelectedEdge(undefined);
  }, [setSelectedNode, setSelectedEdge]);

  // Handle save
  const handleSave = useCallback(() => {
    const config = getConfig();
    const xstate = workflowToXState(config);
    onSave?.({ xstate, visual: config });
  }, [getConfig, onSave]);

  // Handle add node from palette
  const handleAddNode = useCallback(
    (type: XStateNodeType, position: { x: number; y: number }) => {
      addNode(type, position);
    },
    [addNode]
  );

  // Handle drag over
  const onDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle drop
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
    },
    [reactFlowInstance, addNode]
  );

  if (isLoading) {
    return (
      <div className="xsw-loading" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        minHeight: '400px'
      }}>
        <div>Loading workflow builder...</div>
      </div>
    );
  }

  return (
    <div className="xsw-widget" style={{ height: '100%', display: 'flex' }}>
      {/* Node Palette */}
      <div style={{ width: '180px', borderRight: '1px solid #e5e7eb', background: '#f9fafb' }}>
        <NodePalette onAddNode={handleAddNode} />
      </div>

      {/* Canvas */}
      <div style={{ flex: 1, position: 'relative' }} ref={reactFlowWrapper}>
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
          <MiniMap style={{ height: 80, width: 120 }} />
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        </ReactFlow>

        {/* Action Buttons */}
        <div style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          display: 'flex',
          gap: '8px',
          zIndex: 10,
        }}>
          {onClose && (
            <button
              className="btn btn-default btn-sm"
              onClick={onClose}
            >
              Close
            </button>
          )}
          {onSave && (
            <button
              className="btn btn-primary btn-sm"
              onClick={handleSave}
            >
              Apply Changes
            </button>
          )}
        </div>
      </div>

      {/* Properties Panel */}
      <div style={{ width: '280px', borderLeft: '1px solid #e5e7eb', overflow: 'auto' }}>
        <PropertiesPanel
          selectedNode={selectedNode}
          selectedEdge={selectedEdge}
          onNodeChange={updateNode}
          onEdgeChange={updateEdge}
          doctypeFields={doctypeFields}
          availableRoles={availableRoles}
        />
      </div>
    </div>
  );
}
