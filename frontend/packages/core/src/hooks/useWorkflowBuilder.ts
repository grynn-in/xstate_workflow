import { useCallback, useState } from 'react';
import {
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  type Connection,
  type Node,
  type Edge,
} from '@xyflow/react';
import type {
  WorkflowNode,
  WorkflowEdge,
  WorkflowBuilderConfig,
  WorkflowNodeData,
  WorkflowEdgeData,
  XStateNodeType,
  DomainNodeType,
  StartNodeData,
  EndNodeData,
  ApprovalNodeData,
  ParallelApprovalNodeData,
  ThresholdGateNodeData,
  ClassificationBranchNodeData,
  AutoActionNodeData,
  AgenticNodeData,
  RestFetchNodeData,
} from '../types';

let nodeIdCounter = 0;

function generateNodeId(): string {
  return `node_${Date.now()}_${++nodeIdCounter}`;
}

function generateEdgeId(): string {
  return `edge_${Date.now()}_${++nodeIdCounter}`;
}

// Domain node types that need special initialization
const DOMAIN_NODE_TYPES: DomainNodeType[] = [
  'start', 'end', 'approval', 'parallel_approval',
  'threshold_gate', 'classification_branch', 'auto_action',
  'agentic', 'rest_fetch'
];

function isDomainNodeType(type: string): type is DomainNodeType {
  return DOMAIN_NODE_TYPES.includes(type as DomainNodeType);
}

/**
 * Get default node data based on node type
 */
function getDefaultNodeData(type: string, isFirst: boolean): WorkflowNodeData {
  const baseData: WorkflowNodeData = {
    label: `new_${type}`,
    xstateType: 'atomic',
    isInitial: isFirst,
  };

  if (!isDomainNodeType(type)) {
    // XState primitive types
    return {
      ...baseData,
      xstateType: type as XStateNodeType,
    };
  }

  // Domain node types - each needs domainType and specific defaults
  switch (type) {
    case 'start':
      return {
        ...baseData,
        label: 'Start',
        domainType: 'start',
        isInitial: true,
      } as StartNodeData;

    case 'end':
      return {
        ...baseData,
        label: 'End',
        xstateType: 'final',
        domainType: 'end',
        finalStatus: 'Completed',
      } as EndNodeData;

    case 'approval':
      return {
        ...baseData,
        label: 'Approval',
        domainType: 'approval',
        resolver: { type: 'role', role: '' },
        availableActions: ['Approve', 'Reject'],
        priority: 'Medium',
      } as ApprovalNodeData;

    case 'parallel_approval':
      return {
        ...baseData,
        label: 'Parallel Approval',
        domainType: 'parallel_approval',
        approvers: [],
        completionRule: 'all_required',
        onReject: 'reject_all',
        priority: 'Medium',
      } as ParallelApprovalNodeData;

    case 'threshold_gate':
      return {
        ...baseData,
        label: 'Threshold Gate',
        domainType: 'threshold_gate',
        checkType: 'field',
        threshold: { field: '', operator: 'gt', value: 0 },
      } as ThresholdGateNodeData;

    case 'classification_branch':
      return {
        ...baseData,
        label: 'Classification',
        domainType: 'classification_branch',
        field: '',
        branches: [],
      } as ClassificationBranchNodeData;

    case 'auto_action':
      return {
        ...baseData,
        label: 'Auto Action',
        domainType: 'auto_action',
        actionType: 'update_field',
        actionConfig: {},
      } as AutoActionNodeData;

    case 'agentic':
      return {
        ...baseData,
        label: 'AI Agent',
        domainType: 'agentic',
        agentType: 'react',
        systemPrompt: '',
        frappeAccess: 'read_only',
        transitionMode: 'simple',
        maxIterations: 10,
        timeoutSeconds: 300,
      } as AgenticNodeData;

    case 'rest_fetch':
      return {
        ...baseData,
        label: 'REST Fetch',
        domainType: 'rest_fetch',
        url: '',
        method: 'GET',
        authType: 'none',
        saveResponseTo: 'api_response',
        onSuccess: 'SUCCESS',
        onError: 'ERROR',
        timeoutSeconds: 30,
      } as RestFetchNodeData;

    default:
      return baseData;
  }
}

export interface UseWorkflowBuilderOptions {
  initialConfig?: WorkflowBuilderConfig;
  onChange?: (config: WorkflowBuilderConfig) => void;
}

export interface UseWorkflowBuilderReturn {
  // State
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  selectedNode: WorkflowNode | undefined;
  selectedEdge: WorkflowEdge | undefined;

  // Setters
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>;
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>;
  setSelectedNode: (node: WorkflowNode | undefined) => void;
  setSelectedEdge: (edge: WorkflowEdge | undefined) => void;

  // Actions
  onNodesChange: (changes: any) => void;
  onEdgesChange: (changes: any) => void;
  onConnect: (connection: Connection) => void;
  addNode: (type: XStateNodeType | DomainNodeType, position: { x: number; y: number }) => void;
  updateNode: (nodeId: string, data: Partial<WorkflowNodeData>) => void;
  updateEdge: (edgeId: string, data: Partial<WorkflowEdgeData>) => void;
  deleteSelected: () => void;
  getConfig: () => WorkflowBuilderConfig;
  loadConfig: (config: WorkflowBuilderConfig) => void;
}

export function useWorkflowBuilder(options: UseWorkflowBuilderOptions = {}): UseWorkflowBuilderReturn {
  const { initialConfig } = options;

  const [nodes, setNodes, onNodesChange] = useNodesState(
    (initialConfig?.nodes || []) as unknown as Node[]
  );

  // Ensure all edges have markerEnd for arrows
  const initialEdges = (initialConfig?.edges || []).map((edge) => ({
    ...edge,
    markerEnd: edge.markerEnd || {
      type: MarkerType.ArrowClosed,
      width: 20,
      height: 20,
    },
  }));
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    initialEdges as unknown as Edge[]
  );

  const [selectedNodeId, setSelectedNodeId] = useState<string | undefined>();
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | undefined>();

  // Find selected elements
  const selectedNode = nodes.find((n) => n.id === selectedNodeId) as WorkflowNode | undefined;
  const selectedEdge = edges.find((e) => e.id === selectedEdgeId) as WorkflowEdge | undefined;

  // Handle connection
  const onConnect = useCallback(
    (connection: Connection) => {
      const edgeData: WorkflowEdgeData = {
        transitionType: 'event',
        event: 'EVENT',
      };
      const newEdge = {
        ...connection,
        id: generateEdgeId(),
        type: 'transition',
        data: edgeData,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 20,
          height: 20,
        },
      } as Edge;

      setEdges((eds) => addEdge(newEdge, eds));
    },
    [setEdges]
  );

  // Add a new node
  const addNode = useCallback(
    (type: XStateNodeType | DomainNodeType, position: { x: number; y: number }) => {
      const isFirst = nodes.length === 0;
      const newNode: WorkflowNode = {
        id: generateNodeId(),
        type,
        position,
        data: getDefaultNodeData(type, isFirst),
      };

      setNodes((nds) => [...nds, newNode as unknown as Node]);
    },
    [nodes.length, setNodes]
  );

  // Update node data
  const updateNode = useCallback(
    (nodeId: string, data: Partial<WorkflowNodeData>) => {
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === nodeId) {
            return {
              ...node,
              data: { ...node.data, ...data },
            };
          }
          return node;
        })
      );

      // If setting a new initial state, unset others
      if (data.isInitial === true) {
        setNodes((nds) =>
          nds.map((node) => {
            const nodeData = node.data as unknown as WorkflowNodeData;
            if (node.id !== nodeId && nodeData.isInitial) {
              return {
                ...node,
                data: { ...node.data, isInitial: false },
              };
            }
            return node;
          })
        );
      }
    },
    [setNodes]
  );

  // Update edge data
  const updateEdge = useCallback(
    (edgeId: string, data: Partial<WorkflowEdgeData>) => {
      setEdges((eds) =>
        eds.map((edge) => {
          if (edge.id === edgeId) {
            return {
              ...edge,
              data: { ...edge.data, ...data },
            };
          }
          return edge;
        })
      );
    },
    [setEdges]
  );

  // Delete selected element
  const deleteSelected = useCallback(() => {
    if (selectedNodeId) {
      setNodes((nds) => nds.filter((n) => n.id !== selectedNodeId));
      // Also delete connected edges
      setEdges((eds) =>
        eds.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId)
      );
      setSelectedNodeId(undefined);
    }
    if (selectedEdgeId) {
      setEdges((eds) => eds.filter((e) => e.id !== selectedEdgeId));
      setSelectedEdgeId(undefined);
    }
  }, [selectedNodeId, selectedEdgeId, setNodes, setEdges]);

  // Get current config
  const getConfig = useCallback((): WorkflowBuilderConfig => {
    return {
      id: initialConfig?.id || 'workflow',
      name: initialConfig?.name || 'Workflow',
      version: (initialConfig?.version || 0) + 1,
      nodes: nodes as unknown as WorkflowNode[],
      edges: edges as unknown as WorkflowEdge[],
      context: initialConfig?.context || {},
    };
  }, [nodes, edges, initialConfig]);

  // Load config
  const loadConfig = useCallback(
    (config: WorkflowBuilderConfig) => {
      setNodes(config.nodes as unknown as Node[]);
      // Ensure all edges have markerEnd for arrows
      const edgesWithMarkers = (config.edges || []).map((edge) => ({
        ...edge,
        markerEnd: edge.markerEnd || {
          type: MarkerType.ArrowClosed,
          width: 20,
          height: 20,
        },
      }));
      setEdges(edgesWithMarkers as unknown as Edge[]);
      setSelectedNodeId(undefined);
      setSelectedEdgeId(undefined);
    },
    [setNodes, setEdges]
  );

  // Set selected node
  const setSelectedNode = useCallback((node: WorkflowNode | undefined) => {
    setSelectedNodeId(node?.id);
    if (node) setSelectedEdgeId(undefined);
  }, []);

  // Set selected edge
  const setSelectedEdge = useCallback((edge: WorkflowEdge | undefined) => {
    setSelectedEdgeId(edge?.id);
    if (edge) setSelectedNodeId(undefined);
  }, []);

  return {
    nodes: nodes as unknown as WorkflowNode[],
    edges: edges as unknown as WorkflowEdge[],
    selectedNode,
    selectedEdge,
    setNodes,
    setEdges,
    setSelectedNode,
    setSelectedEdge,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    updateNode,
    updateEdge,
    deleteSelected,
    getConfig,
    loadConfig,
  };
}
