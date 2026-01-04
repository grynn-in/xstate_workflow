// Main Workflow Builder component

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type NodeChange,
  type EdgeChange,
  BackgroundVariant,
  Panel
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import StateNode from './StateNode';
import TransitionEdge from './TransitionEdge';
import Toolbar from './Toolbar';
import PropertiesPanel from './PropertiesPanel';
import SaveAsModal from './SaveAsModal';

import type {
  StateNode as StateNodeType,
  TransitionEdge as TransitionEdgeType,
  StateNodeData,
  TransitionEdgeData,
  GuardDefinition,
  ActionDefinition
} from '../types';

import { getLayoutedElements, getInitialNodePosition } from '../utils/layout';
import { reactFlowToXState, xstateToReactFlow, generateStateId } from '../utils/converter';
import { saveMachine, loadMachine, showSuccess, showError, downloadJson, readJsonFile } from '../utils/api';

// Register custom node and edge types
const nodeTypes = {
  stateNode: StateNode
};

const edgeTypes = {
  transitionEdge: TransitionEdge
};

// Default guards and actions
const defaultGuards: GuardDefinition[] = [
  { name: 'hasApprovalPermission', description: 'Check if user can approve' },
  { name: 'isNotOwner', description: 'Prevent self-approval' },
  { name: 'hasRequiredFields', description: 'Check required fields filled' },
  { name: 'isWithinAmountLimit', description: 'Check amount limit' },
  { name: 'always', description: 'Always true' }
];

const defaultActions: ActionDefinition[] = [
  { name: 'recordApproval', type: 'transition', description: 'Record who approved' },
  { name: 'recordRejection', type: 'transition', description: 'Record rejection' },
  { name: 'notifySubmission', type: 'entry', description: 'Send submission notification' },
  { name: 'notifyApproval', type: 'entry', description: 'Send approval notification' },
  { name: 'notifyRejection', type: 'entry', description: 'Send rejection notification' },
  { name: 'logTransition', type: 'transition', description: 'Log for audit' }
];

// Initial nodes for new workflow (blank canvas with one starter node)
const getInitialNodes = (): StateNodeType[] => [
  {
    id: 'draft',
    type: 'stateNode',
    position: { x: 100, y: 150 },
    data: {
      label: 'draft',
      stateType: 'initial',
      entryActions: [],
      exitActions: []
    }
  }
];

const initialEdges: TransitionEdgeType[] = [];

interface WorkflowBuilderProps {
  machineId?: string;
}

export default function WorkflowBuilder({ machineId: initialMachineId }: WorkflowBuilderProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<StateNodeData>(getInitialNodes());
  const [edges, setEdges, onEdgesChange] = useEdgesState<TransitionEdgeData>(initialEdges);
  const [machineId, setMachineId] = useState(initialMachineId || '');
  const [machineTitle, setMachineTitle] = useState('');
  const [attachedDoctype, setAttachedDoctype] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [selectedNode, setSelectedNode] = useState<StateNodeType | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<TransitionEdgeType | null>(null);
  const [guards, setGuards] = useState<GuardDefinition[]>(defaultGuards);
  const [actions, setActions] = useState<ActionDefinition[]>(defaultActions);

  // Track if this is a new (unsaved) workflow
  const [isNewWorkflow, setIsNewWorkflow] = useState(!initialMachineId);
  const [showSaveAsModal, setShowSaveAsModal] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing machine if machineId provided
  useEffect(() => {
    if (initialMachineId) {
      loadExistingMachine(initialMachineId);
    }
  }, [initialMachineId]);

  // Track unsaved changes
  useEffect(() => {
    if (!isNewWorkflow) {
      setHasUnsavedChanges(true);
    }
  }, [nodes, edges]);

  const loadExistingMachine = async (id: string) => {
    try {
      const machine = await loadMachine(id);

      // Try to load React Flow config first
      if (machine.react_flow_config) {
        const flowConfig = JSON.parse(machine.react_flow_config);
        setNodes(flowConfig.nodes || []);
        setEdges(flowConfig.edges || []);
      } else if (machine.json_config) {
        // Convert from XState config
        const flowConfig = xstateToReactFlow(JSON.parse(machine.json_config));
        setNodes(flowConfig.nodes);
        setEdges(flowConfig.edges);
      }

      // Load guards and actions from machine
      if (machine.guards?.length) {
        setGuards([...defaultGuards, ...machine.guards]);
      }
      if (machine.actions?.length) {
        setActions([...defaultActions, ...machine.actions]);
      }

      setMachineId(machine.machine_id);
      setMachineTitle(machine.title);
      setAttachedDoctype(machine.attached_doctype || '');
      setIsNewWorkflow(false);
      setHasUnsavedChanges(false);
      showSuccess(`Loaded workflow: ${machine.title}`);
    } catch (error) {
      console.error('Failed to load machine:', error);
      showError(`Failed to load workflow: ${(error as Error).message}`);
    }
  };

  // Handle new connections
  const onConnect = useCallback(
    (connection: Connection) => {
      const newEdge: TransitionEdgeType = {
        ...connection,
        id: `${connection.source}-${connection.target}-${Date.now()}`,
        type: 'transitionEdge',
        label: 'EVENT',
        data: {
          event: 'EVENT',
          actions: []
        }
      } as TransitionEdgeType;

      setEdges((eds) => addEdge(newEdge, eds));
    },
    [setEdges]
  );

  // Handle node selection
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: StateNodeType) => {
      setSelectedNode(node);
      setSelectedEdge(null);
    },
    []
  );

  // Handle edge selection
  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: TransitionEdgeType) => {
      setSelectedEdge(edge);
      setSelectedNode(null);
    },
    []
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  // Add new state
  const handleAddState = useCallback(() => {
    const existingIds = nodes.map((n) => n.id);
    const newId = generateStateId(existingIds);
    const position = getInitialNodePosition(nodes);

    const newNode: StateNodeType = {
      id: newId,
      type: 'stateNode',
      position,
      data: {
        label: newId,
        stateType: 'atomic',
        entryActions: [],
        exitActions: []
      }
    };

    setNodes((nds) => [...nds, newNode]);
  }, [nodes, setNodes]);

  // Update node data
  const handleNodeUpdate = useCallback(
    (id: string, data: Partial<StateNodeData>) => {
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === id) {
            // If label changed, we need to update the ID and all references
            if (data.label && data.label !== node.id) {
              const newId = data.label;

              // Update edges that reference this node
              setEdges((eds) =>
                eds.map((edge) => ({
                  ...edge,
                  source: edge.source === id ? newId : edge.source,
                  target: edge.target === id ? newId : edge.target
                }))
              );

              return {
                ...node,
                id: newId,
                data: { ...node.data, ...data }
              };
            }

            return {
              ...node,
              data: { ...node.data, ...data }
            };
          }
          return node;
        })
      );

      // Update selected node
      if (selectedNode?.id === id) {
        setSelectedNode((prev) =>
          prev ? { ...prev, data: { ...prev.data, ...data } } : null
        );
      }
    },
    [setNodes, setEdges, selectedNode]
  );

  // Update edge data
  const handleEdgeUpdate = useCallback(
    (id: string, data: Partial<TransitionEdgeData>) => {
      setEdges((eds) =>
        eds.map((edge) => {
          if (edge.id === id) {
            return {
              ...edge,
              label: data.event || edge.label,
              data: { ...edge.data, ...data } as TransitionEdgeData
            };
          }
          return edge;
        })
      );

      // Update selected edge
      if (selectedEdge?.id === id) {
        setSelectedEdge((prev) =>
          prev ? { ...prev, data: { ...prev.data, ...data } as TransitionEdgeData } : null
        );
      }
    },
    [setEdges, selectedEdge]
  );

  // Delete node
  const handleNodeDelete = useCallback(
    (id: string) => {
      setNodes((nds) => nds.filter((node) => node.id !== id));
      setEdges((eds) => eds.filter((edge) => edge.source !== id && edge.target !== id));
      setSelectedNode(null);
    },
    [setNodes, setEdges]
  );

  // Delete edge
  const handleEdgeDelete = useCallback(
    (id: string) => {
      setEdges((eds) => eds.filter((edge) => edge.id !== id));
      setSelectedEdge(null);
    },
    [setEdges]
  );

  // Auto layout
  const handleAutoLayout = useCallback(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      edges,
      'LR'
    );
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [nodes, edges, setNodes, setEdges]);

  // Save to backend (for existing workflows)
  const handleSave = useCallback(async () => {
    // If new workflow, show Save As modal
    if (isNewWorkflow || !machineId.trim()) {
      setShowSaveAsModal(true);
      return;
    }

    setIsSaving(true);

    try {
      const xstateConfig = reactFlowToXState(nodes as StateNodeType[], edges as TransitionEdgeType[], machineId);
      const reactFlowConfig = { machineId, nodes, edges };

      await saveMachine(
        machineId,
        JSON.stringify(xstateConfig, null, 2),
        JSON.stringify(reactFlowConfig),
        machineTitle || machineId,
        attachedDoctype
      );

      setHasUnsavedChanges(false);
      showSuccess('Workflow saved successfully!');
    } catch (error) {
      console.error('Save failed:', error);
      showError(`Save failed: ${(error as Error).message}`);
    } finally {
      setIsSaving(false);
    }
  }, [machineId, machineTitle, attachedDoctype, nodes, edges, isNewWorkflow]);

  // Save As New (from modal)
  const handleSaveAsNew = useCallback(async (
    newMachineId: string,
    newTitle: string,
    newAttachedDoctype: string
  ) => {
    setIsSaving(true);

    try {
      const xstateConfig = reactFlowToXState(
        nodes as StateNodeType[],
        edges as TransitionEdgeType[],
        newMachineId
      );
      const reactFlowConfig = { machineId: newMachineId, nodes, edges };

      await saveMachine(
        newMachineId,
        JSON.stringify(xstateConfig, null, 2),
        JSON.stringify(reactFlowConfig),
        newTitle,
        newAttachedDoctype
      );

      // Update local state
      setMachineId(newMachineId);
      setMachineTitle(newTitle);
      setAttachedDoctype(newAttachedDoctype);
      setIsNewWorkflow(false);
      setHasUnsavedChanges(false);
      setShowSaveAsModal(false);

      // Update URL without reload
      const newUrl = `/workflow-builder?machine=${encodeURIComponent(newMachineId)}`;
      window.history.pushState({}, '', newUrl);

      showSuccess(`Workflow "${newTitle}" created successfully!`);
    } catch (error) {
      console.error('Save failed:', error);
      showError(`Save failed: ${(error as Error).message}`);
    } finally {
      setIsSaving(false);
    }
  }, [nodes, edges]);

  // Export to JSON
  const handleExport = useCallback(() => {
    const exportMachineId = machineId || 'new_workflow';
    const xstateConfig = reactFlowToXState(
      nodes as StateNodeType[],
      edges as TransitionEdgeType[],
      exportMachineId
    );

    const exportData = {
      machineId: exportMachineId,
      xstate: xstateConfig,
      reactFlow: { nodes, edges }
    };

    downloadJson(exportData, `${exportMachineId}_workflow.json`);
    showSuccess('Workflow exported!');
  }, [machineId, nodes, edges]);

  // Import from JSON
  const handleImport = useCallback(async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';

    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const data = (await readJsonFile(file)) as {
          machineId?: string;
          xstate?: object;
          reactFlow?: { nodes: StateNodeType[]; edges: TransitionEdgeType[] };
        };

        if (data.reactFlow) {
          setNodes(data.reactFlow.nodes);
          setEdges(data.reactFlow.edges);
        } else if (data.xstate) {
          const flowConfig = xstateToReactFlow(data.xstate as Parameters<typeof xstateToReactFlow>[0]);
          setNodes(flowConfig.nodes);
          setEdges(flowConfig.edges);
        }

        if (data.machineId && isNewWorkflow) {
          setMachineId(data.machineId);
        }

        showSuccess('Workflow imported!');
      } catch (error) {
        showError(`Import failed: ${(error as Error).message}`);
      }
    };

    input.click();
  }, [setNodes, setEdges, isNewWorkflow]);

  // Open in Desk (for existing workflows)
  const handleOpenInDesk = useCallback(() => {
    if (machineId) {
      window.open(`/app/state-machine/${encodeURIComponent(machineId)}`, '_blank');
    }
  }, [machineId]);

  return (
    <div style={{ width: '100%', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Toolbar
        onAddState={handleAddState}
        onSave={handleSave}
        onExport={handleExport}
        onImport={handleImport}
        onAutoLayout={handleAutoLayout}
        machineId={machineId}
        machineTitle={machineTitle}
        onMachineIdChange={setMachineId}
        isSaving={isSaving}
        isNewWorkflow={isNewWorkflow}
        hasUnsavedChanges={hasUnsavedChanges}
        onOpenInDesk={handleOpenInDesk}
        onSaveAs={() => setShowSaveAsModal(true)}
      />

      <div style={{ flex: 1, display: 'flex' }}>
        <div style={{ flex: 1 }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange as (changes: NodeChange[]) => void}
            onEdgesChange={onEdgesChange as (changes: EdgeChange[]) => void}
            onConnect={onConnect}
            onNodeClick={onNodeClick as (event: React.MouseEvent, node: unknown) => void}
            onEdgeClick={onEdgeClick as (event: React.MouseEvent, edge: unknown) => void}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
            defaultEdgeOptions={{
              type: 'transitionEdge'
            }}
            style={{ background: '#0f172a' }}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
            <Controls
              style={{
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px'
              }}
            />
            <MiniMap
              style={{
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px'
              }}
              nodeColor={(node) => {
                const data = node.data as StateNodeData;
                switch (data.stateType) {
                  case 'initial':
                    return '#10b981';
                  case 'final':
                    return '#ef4444';
                  case 'compound':
                    return '#8b5cf6';
                  case 'parallel':
                    return '#f59e0b';
                  default:
                    return '#3b82f6';
                }
              }}
            />

            {/* Instructions panel */}
            <Panel position="bottom-center">
              <div
                style={{
                  background: 'rgba(30, 41, 59, 0.9)',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  color: '#94a3b8',
                  fontSize: '12px'
                }}
              >
                {isNewWorkflow ? (
                  <>Design your workflow, then click <strong>Save</strong> to create it</>
                ) : (
                  <>Drag to connect states • Click to select • Double-click to edit • Delete key to remove</>
                )}
              </div>
            </Panel>
          </ReactFlow>
        </div>

        <PropertiesPanel
          selectedNode={selectedNode}
          selectedEdge={selectedEdge}
          onNodeUpdate={handleNodeUpdate}
          onEdgeUpdate={handleEdgeUpdate}
          onNodeDelete={handleNodeDelete}
          onEdgeDelete={handleEdgeDelete}
          availableGuards={guards}
          availableActions={actions}
        />
      </div>

      {/* Save As Modal */}
      <SaveAsModal
        isOpen={showSaveAsModal}
        onClose={() => setShowSaveAsModal(false)}
        onSave={handleSaveAsNew}
        isSaving={isSaving}
        defaultMachineId={machineId}
      />
    </div>
  );
}
