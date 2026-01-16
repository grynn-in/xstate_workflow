import { useCallback, useEffect, useState, useRef, type DragEvent } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  type OnSelectionChangeFunc,
  type ReactFlowInstance,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  nodeTypes,
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
  type FrappeField,
} from '@xstate-workflow/core';
import '@xstate-workflow/core/styles';

import {
  loadMachine,
  getDocTypeFields,
  getDocTypes,
  getRoles,
  getUsers,
  getMcpConnections,
  type MCPConnectionInfo,
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
  const [availableDoctypes, setAvailableDoctypes] = useState<string[]>([]);
  const [availableUsers, setAvailableUsers] = useState<Array<{ name: string; full_name: string }>>([]);
  const [availableMcpConnections, setAvailableMcpConnections] = useState<MCPConnectionInfo[]>([]);
  const [availableContextVars, setAvailableContextVars] = useState<string[]>([]);
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
        // Load roles, doctypes, users, and MCP connections in parallel
        const [roles, doctypes, users, mcpConnections] = await Promise.all([
          getRoles(),
          getDocTypes(),
          getUsers(),
          getMcpConnections(),
        ]);
        setAvailableRoles(roles);
        setAvailableDoctypes(doctypes);
        setAvailableUsers(users);
        setAvailableMcpConnections(mcpConnections);

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
            // Extract context vars
            if (config.context) {
              setAvailableContextVars(Object.keys(config.context));
            }
          } else if (data.json_config) {
            const xstate = JSON.parse(data.json_config);
            const config = xstateToWorkflow(xstate);
            loadConfig(config);
            // Extract context vars
            if (config.context) {
              setAvailableContextVars(Object.keys(config.context));
            }
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

  // Track selection with a ref to avoid React Flow's internal state issues
  const lastSelectionRef = useRef<{ nodeId?: string; edgeId?: string }>({});

  // Handle selection changes - only update on new selections, ignore spurious deselections
  const onSelectionChange: OnSelectionChangeFunc = useCallback(
    ({ nodes: selectedNodes, edges: selectedEdges }) => {
      const newNodeId = selectedNodes.length > 0 ? selectedNodes[0].id : undefined;
      const newEdgeId = selectedEdges.length > 0 ? selectedEdges[0].id : undefined;

      // If a node is selected
      if (newNodeId) {
        lastSelectionRef.current = { nodeId: newNodeId };
        setSelectedNode(selectedNodes[0] as WorkflowNode);
        setSelectedEdge(undefined);
      }
      // If an edge is selected
      else if (newEdgeId) {
        lastSelectionRef.current = { edgeId: newEdgeId };
        setSelectedEdge(selectedEdges[0] as WorkflowEdge);
        setSelectedNode(undefined);
      }
      // Empty selection - only clear if this looks intentional (both were already empty)
      else if (!lastSelectionRef.current.nodeId && !lastSelectionRef.current.edgeId) {
        setSelectedNode(undefined);
        setSelectedEdge(undefined);
      }
      // Otherwise ignore spurious deselection events
    },
    [setSelectedNode, setSelectedEdge]
  );

  // Handle explicit pane click to deselect
  const onPaneClick = useCallback(() => {
    lastSelectionRef.current = {};
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
      <ResizablePanel
        position="left"
        defaultWidth={180}
        minWidth={140}
        maxWidth={300}
        collapsedWidth={24}
      >
        <NodePalette onAddNode={handleAddNode} />
      </ResizablePanel>

      {/* Canvas */}
      <div style={{ flex: 1, position: 'relative', minWidth: 0 }} ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onSelectionChange={onSelectionChange}
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
      <ResizablePanel
        position="right"
        defaultWidth={280}
        minWidth={240}
        maxWidth={400}
        collapsedWidth={24}
      >
        <PropertiesPanel
          selectedNode={selectedNode}
          selectedEdge={selectedEdge}
          onNodeChange={updateNode}
          onEdgeChange={updateEdge}
          doctypeFields={doctypeFields}
          availableRoles={availableRoles}
          availableDoctypes={availableDoctypes}
          availableUsers={availableUsers}
          availableMcpConnections={availableMcpConnections}
          availableContextVars={availableContextVars}
          onFetchDoctypeFields={getDocTypeFields}
        />
      </ResizablePanel>
    </div>
  );
}
