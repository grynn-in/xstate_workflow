import { useCallback, useEffect, useState, useRef, useMemo, type DragEvent } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  type OnSelectionChangeFunc,
  type ReactFlowInstance,
  type NodeDragHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Import from core-v2 which re-exports core + v2 enhancements
import {
  allNodeTypes,
  edgeTypes,
  PropertiesPanel,
  NodePalette,
  ResizablePanel,
  HelperLines,
  useWorkflowBuilderWithHistory,
  useCopyPaste,
  useHelperLines,
  workflowToXState,
  xstateToWorkflow,
  elkLayout,
  type WorkflowBuilderConfig,
  type WorkflowNode,
  type WorkflowEdge,
  type XStateNodeType,
  type FrappeField,
  type EdgePathType,
} from '@xstate-workflow/core-v2';
import '@xstate-workflow/core/styles';
import '@xstate-workflow/core-v2/styles';

import {
  saveMachine,
  loadMachine,
  listMachines,
  showSuccess,
  showError,
  getDocTypes,
  getDocTypeFields,
  getRoles,
  getUsers,
  getMcpConnections,
  type MachineListItem,
  type MCPConnectionInfo,
} from '@xstate-workflow/frappe-adapter';

interface AppProps {
  machineId?: string;
  attachedDoctype?: string;
}

export function App({ machineId: initialMachineId, attachedDoctype: initialAttachedDoctype }: AppProps) {
  const [machineId, setMachineId] = useState<string | undefined>(initialMachineId);
  const [machineTitle, setMachineTitle] = useState('New Workflow');
  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  // DocType and fields state
  const [attachedDoctype, setAttachedDoctype] = useState<string | undefined>(initialAttachedDoctype);
  const [doctypesList, setDoctypesList] = useState<string[]>([]);
  const [doctypeFields, setDoctypeFields] = useState<FrappeField[]>([]);
  const [availableRoles, setAvailableRoles] = useState<string[]>([]);
  const [availableUsers, setAvailableUsers] = useState<Array<{ name: string; full_name: string }>>([]);
  const [availableMcpConnections, setAvailableMcpConnections] = useState<MCPConnectionInfo[]>([]);
  const [availableContextVars, setAvailableContextVars] = useState<string[]>([]);

  // Workflow list for selector
  const [workflowsList, setWorkflowsList] = useState<MachineListItem[]>([]);

  // Edge style toggle (bezier = curved with draggable control, smoothstep = orthogonal)
  const [edgePathType, setEdgePathType] = useState<EdgePathType>('bezier');

  const {
    nodes,
    edges,
    selectedNode,
    selectedEdge,
    setSelectedNode,
    setSelectedEdge,
    setNodes,
    setEdges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    updateNode,
    updateEdge,
    getConfig,
    loadConfig,
    undo,
    redo,
    canUndo,
    canRedo,
    takeSnapshot,
  } = useWorkflowBuilderWithHistory({
    onChange: () => setHasUnsavedChanges(true),
    maxHistorySize: 50,
    debounceMs: 500,
  });

  // Copy/Paste functionality
  const {
    copy,
    paste,
    cut,
    canPaste,
  } = useCopyPaste({
    nodes: nodes as WorkflowNode[],
    edges: edges as WorkflowEdge[],
    selectedNodeIds: selectedNode ? [selectedNode.id] : [],
    pasteOffset: { x: 50, y: 50 },
    onCopy: () => {
      // Optional: show toast notification
    },
    onPaste: (newNodes, newEdges) => {
      // Add pasted nodes and edges
      setNodes((prev) => [...prev, ...newNodes] as any);
      setEdges((prev) => [...prev, ...newEdges] as any);
      setHasUnsavedChanges(true);
      takeSnapshot();
    },
    onCut: (nodeIds) => {
      // Remove cut nodes and their connected edges
      setNodes((prev) => prev.filter((n) => !nodeIds.includes(n.id)));
      setEdges((prev) =>
        prev.filter((e) => !nodeIds.includes(e.source) && !nodeIds.includes(e.target))
      );
      setSelectedNode(undefined);
      setHasUnsavedChanges(true);
      takeSnapshot();
    },
  });

  // Apply edge path type to all edges
  const edgesWithPathType = useMemo(() => {
    return edges.map((edge) => ({
      ...edge,
      data: {
        ...edge.data,
        edgePathType,
      },
    }));
  }, [edges, edgePathType]);

  // Helper lines for node alignment
  const {
    horizontalLines,
    verticalLines,
    onNodeDrag: onHelperLinesDrag,
    onNodeDragEnd: onHelperLinesDragEnd,
  } = useHelperLines({
    nodes: nodes.map((n) => ({
      id: n.id,
      position: n.position,
      measured: n.measured,
    })),
    threshold: 5,
    enableSnapping: false, // Can be enabled for snap-to-grid behavior
  });

  // Handle node drag for helper lines
  const handleNodeDrag: NodeDragHandler = useCallback(
    (_, node) => {
      onHelperLinesDrag(node.id, node.position);
    },
    [onHelperLinesDrag]
  );

  // Handle node drag end
  const handleNodeDragStop: NodeDragHandler = useCallback(
    () => {
      onHelperLinesDragEnd();
    },
    [onHelperLinesDragEnd]
  );

  // Fetch doctypes list, roles, users, MCP connections, and workflows on mount
  useEffect(() => {
    getDocTypes().then(setDoctypesList).catch(console.error);
    getRoles().then(setAvailableRoles).catch(console.error);
    getUsers().then(setAvailableUsers).catch(console.error);
    getMcpConnections().then(setAvailableMcpConnections).catch(console.error);
    listMachines(undefined, true).then(setWorkflowsList).catch(console.error);
  }, []);

  // Fetch doctype fields when attachedDoctype changes
  useEffect(() => {
    if (attachedDoctype) {
      getDocTypeFields(attachedDoctype)
        .then(setDoctypeFields)
        .catch(console.error);
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

            // Extract context variables from config
            if (config.context) {
              setAvailableContextVars(Object.keys(config.context));
            }
          }

          setHasUnsavedChanges(false);
        })
        .catch((err) => {
          console.error('Load machine error:', err);
          showError(`Failed to load workflow: ${err.message}`);
        });
    }
  }, [initialMachineId, loadConfig]);

  // Keyboard shortcuts for undo/redo and copy/paste/cut
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Check if focus is on an input/textarea (don't intercept typing)
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        return;
      }

      // Ctrl+Z / Cmd+Z for undo
      if ((event.ctrlKey || event.metaKey) && event.key === 'z' && !event.shiftKey) {
        event.preventDefault();
        if (canUndo) {
          undo();
        }
      }

      // Ctrl+Shift+Z / Cmd+Shift+Z for redo (common on Mac)
      // Ctrl+Y / Cmd+Y for redo (common on Windows)
      if (
        ((event.ctrlKey || event.metaKey) && event.key === 'z' && event.shiftKey) ||
        ((event.ctrlKey || event.metaKey) && event.key === 'y')
      ) {
        event.preventDefault();
        if (canRedo) {
          redo();
        }
      }

      // Ctrl+C / Cmd+C for copy
      if ((event.ctrlKey || event.metaKey) && event.key === 'c') {
        event.preventDefault();
        copy();
      }

      // Ctrl+V / Cmd+V for paste
      if ((event.ctrlKey || event.metaKey) && event.key === 'v') {
        event.preventDefault();
        if (canPaste) {
          paste();
        }
      }

      // Ctrl+X / Cmd+X for cut
      if ((event.ctrlKey || event.metaKey) && event.key === 'x') {
        event.preventDefault();
        cut();
      }

      // Delete / Backspace for delete selected
      if (event.key === 'Delete' || event.key === 'Backspace') {
        if (selectedNode) {
          event.preventDefault();
          const nodeId = selectedNode.id;
          setNodes((prev) => prev.filter((n) => n.id !== nodeId));
          setEdges((prev) =>
            prev.filter((e) => e.source !== nodeId && e.target !== nodeId)
          );
          setSelectedNode(undefined);
          setHasUnsavedChanges(true);
          takeSnapshot();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [undo, redo, canUndo, canRedo, copy, paste, cut, canPaste, selectedNode, setNodes, setEdges, setSelectedNode, takeSnapshot]);

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
  const handleSave = useCallback(async () => {
    setIsSaving(true);
    try {
      const config = getConfig();
      const xstate = workflowToXState(config);

      // Generate a machine ID if this is a new workflow
      const effectiveMachineId = machineId || `workflow_${Date.now()}`;

      const result = await saveMachine(
        effectiveMachineId,
        machineTitle,
        xstate,
        config,
        attachedDoctype
      );

      setMachineId(result.name);
      setHasUnsavedChanges(false);
      showSuccess('Workflow saved successfully');

      // Refresh workflow list to include newly saved workflow
      listMachines(undefined, true).then(setWorkflowsList).catch(console.error);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      showError(`Failed to save: ${message}`);
    } finally {
      setIsSaving(false);
    }
  }, [getConfig, machineId, machineTitle, attachedDoctype]);

  // Handle loading a different workflow
  const handleLoadWorkflow = useCallback(async (selectedMachineId: string) => {
    if (!selectedMachineId) {
      // "New Workflow" selected - reset to blank
      setMachineId(undefined);
      setMachineTitle('New Workflow');
      setAttachedDoctype(undefined);
      loadConfig({ nodes: [], edges: [] });
      setHasUnsavedChanges(false);
      return;
    }

    if (hasUnsavedChanges) {
      const confirmed = window.confirm('You have unsaved changes. Discard and load another workflow?');
      if (!confirmed) return;
    }

    try {
      const data = await loadMachine(selectedMachineId);
      setMachineId(selectedMachineId);
      setMachineTitle(data.title);
      setAttachedDoctype(data.attached_doctype);

      if (data.json_config) {
        const xstate = JSON.parse(data.json_config);
        let existingLayout: WorkflowBuilderConfig | undefined;
        if (data.workflow_builder_config) {
          try {
            existingLayout = JSON.parse(data.workflow_builder_config) as WorkflowBuilderConfig;
          } catch {
            // Ignore parsing errors
          }
        }
        const config = xstateToWorkflow(xstate, existingLayout);
        loadConfig(config);

        // Extract context variables from config
        if (config.context) {
          setAvailableContextVars(Object.keys(config.context));
        }
      } else {
        loadConfig({ nodes: [], edges: [] });
      }

      setHasUnsavedChanges(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      showError(`Failed to load workflow: ${message}`);
    }
  }, [hasUnsavedChanges, loadConfig]);

  // Handle delete selected
  const handleDelete = useCallback(() => {
    if (selectedNode) {
      const nodeId = selectedNode.id;
      setNodes((prev) => prev.filter((n) => n.id !== nodeId));
      setEdges((prev) =>
        prev.filter((e) => e.source !== nodeId && e.target !== nodeId)
      );
      setSelectedNode(undefined);
      setHasUnsavedChanges(true);
      takeSnapshot();
    } else if (selectedEdge) {
      const edgeId = selectedEdge.id;
      setEdges((prev) => prev.filter((e) => e.id !== edgeId));
      setSelectedEdge(undefined);
      setHasUnsavedChanges(true);
      takeSnapshot();
    }
  }, [selectedNode, selectedEdge, setNodes, setEdges, setSelectedNode, setSelectedEdge, takeSnapshot]);

  // Handle auto-layout using ELK algorithm
  const handleAutoLayout = useCallback(async () => {
    if (nodes.length === 0) return;

    try {
      // Run ELK layout algorithm
      const { nodes: layoutNodes } = await elkLayout(
        nodes.map((n) => ({ ...n })),
        edges.map((e) => ({ ...e })),
        {
          direction: 'LR', // Left-to-right for workflows
          spacing: [120, 200], // [nodeToNode, betweenLayers]
        }
      );

      // Update node positions
      setNodes(layoutNodes);

      setHasUnsavedChanges(true);
      takeSnapshot();

      // Fit view after layout
      if (reactFlowInstance) {
        setTimeout(() => {
          reactFlowInstance.fitView({ padding: 0.2 });
        }, 50);
      }
    } catch (error) {
      console.error('ELK layout error:', error);
    }
  }, [nodes, edges, setNodes, takeSnapshot, reactFlowInstance]);

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
            <span style={{ fontSize: '20px' }}>&#x2B21;</span>
            <select
              className="xsw-select"
              value={machineId || ''}
              onChange={(e) => handleLoadWorkflow(e.target.value)}
              style={{ width: '200px' }}
              title="Select an existing workflow to edit, or choose 'New Workflow' to start fresh"
            >
              <option value="">+ New Workflow</option>
              {workflowsList.map((wf) => (
                <option key={wf.machine_id} value={wf.machine_id}>
                  {wf.title || wf.machine_id}
                </option>
              ))}
            </select>
            <input
              type="text"
              className="xsw-input"
              style={{ width: '180px', fontWeight: 600 }}
              value={machineTitle}
              title="Workflow name - displayed in the dashboard and used for identification"
              onChange={(e) => {
                setMachineTitle(e.target.value);
                setHasUnsavedChanges(true);
              }}
            />
            <select
              className="xsw-select"
              value={attachedDoctype || ''}
              onChange={(e) => {
                setAttachedDoctype(e.target.value || undefined);
                setHasUnsavedChanges(true);
              }}
              style={{ width: '160px' }}
              title="DocType this workflow is attached to - enables field-based guards and actions"
            >
              <option value="">Select DocType...</option>
              {doctypesList.map((dt) => (
                <option key={dt} value={dt}>{dt}</option>
              ))}
            </select>
            {hasUnsavedChanges && (
              <span style={{ color: '#f59e0b', fontSize: '12px' }}>&#x25CF; Unsaved</span>
            )}
            <span
              style={{
                marginLeft: '8px',
                padding: '2px 6px',
                fontSize: '10px',
                fontWeight: 600,
                background: '#3b82f6',
                color: 'white',
                borderRadius: '4px',
              }}
            >
              V2
            </span>
          </div>
          <div className="xsw-toolbar-right">
            {/* Undo/Redo buttons */}
            <div style={{ display: 'flex', gap: '2px', marginRight: '8px' }}>
              <button
                className="xsw-button xsw-button-secondary"
                onClick={undo}
                disabled={!canUndo}
                title="Undo (Ctrl+Z)"
                style={{ padding: '4px 8px', minWidth: 'auto' }}
              >
                &#x21B6;
              </button>
              <button
                className="xsw-button xsw-button-secondary"
                onClick={redo}
                disabled={!canRedo}
                title="Redo (Ctrl+Shift+Z)"
                style={{ padding: '4px 8px', minWidth: 'auto' }}
              >
                &#x21B7;
              </button>
            </div>
            {/* Delete button */}
            <button
              className="xsw-button xsw-button-secondary"
              onClick={handleDelete}
              disabled={!selectedNode && !selectedEdge}
              title="Delete selected (Delete)"
              style={{ padding: '4px 8px', minWidth: 'auto', marginRight: '8px' }}
            >
              &#x1F5D1;
            </button>
            {/* Auto-layout button */}
            <button
              className="xsw-button xsw-button-secondary"
              onClick={handleAutoLayout}
              disabled={nodes.length === 0}
              title="Auto-arrange nodes using ELK layered algorithm"
              style={{ marginRight: '8px' }}
            >
              Auto-layout
            </button>
            {/* Edge style toggle */}
            <select
              className="xsw-select"
              value={edgePathType}
              onChange={(e) => setEdgePathType(e.target.value as EdgePathType)}
              style={{ width: '110px', marginRight: '8px' }}
              title="Edge drawing style"
            >
              <option value="bezier">Bezier</option>
              <option value="smoothstep">Orthogonal</option>
            </select>
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
            edges={edgesWithPathType}
            nodeTypes={allNodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onSelectionChange={onSelectionChange}
            onPaneClick={onPaneClick}
            onNodeDrag={handleNodeDrag}
            onNodeDragStop={handleNodeDragStop}
            onInit={setReactFlowInstance}
            onDragOver={onDragOver}
            onDrop={onDrop}
            fitView
            className="xsw-canvas"
            defaultEdgeOptions={{
              type: 'transition',
              data: { edgePathType },
            }}
          >
            <Controls />
            <MiniMap className="xsw-minimap" />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
            <HelperLines
              horizontalLines={horizontalLines}
              verticalLines={verticalLines}
            />
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
            availableMcpConnections={availableMcpConnections}
            availableContextVars={availableContextVars}
            onFetchDoctypeFields={getDocTypeFields}
          />
        </ResizablePanel>
      </div>
    </div>
  );
}
