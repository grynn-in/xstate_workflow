import { useState, useEffect, useCallback, useMemo } from 'react';
import type { WorkflowNode, WorkflowEdge, WorkflowBuilderConfig } from '../types';

/**
 * Transition log entry type
 */
export interface TransitionLogEntry {
  timestamp: string;
  event: string;
  from_state: string;
  to_state: string;
  success: boolean;
  error?: string;
  user?: string;
}

/**
 * Available event type
 */
export interface AvailableEvent {
  event: string;
  target: string | null;
  guards: string[];
  actions: string[];
  enabled: boolean;
}

/**
 * Options for the instance viewer hook
 */
export interface UseInstanceViewerOptions {
  machineId: string;
  doctype: string;
  docname: string;
  pollInterval?: number;
  onError?: (error: string) => void;
}

/**
 * Return type for the instance viewer hook
 */
export interface UseInstanceViewerReturn {
  // Workflow config (nodes/edges)
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];

  // Runtime state
  currentState: string | null;
  status: 'idle' | 'active' | 'final' | 'error' | 'archived' | null;
  availableEvents: AvailableEvent[];
  transitionLog: TransitionLogEntry[];
  transitionCount: number;
  lastEvent: string | null;
  lastTransitionAt: string | null;

  // Machine info
  machineName: string | null;
  instanceName: string | null;

  // Loading states
  isLoading: boolean;
  error: string | null;
  hasWorkflow: boolean;

  // Computed for visualization
  currentNodeId: string | null;
  visitedNodeIds: string[];
  availableTargetNodeIds: string[];

  // Actions
  refresh: () => Promise<void>;
}

// Frappe API type
declare const frappe: {
  xcall: <T>(method: string, args?: Record<string, unknown>) => Promise<T>;
} | undefined;

/**
 * Hook for viewing workflow instance state in a diagram.
 * Fetches machine config and runtime state, computes visualization data.
 */
export function useInstanceViewer(options: UseInstanceViewerOptions): UseInstanceViewerReturn {
  const {
    machineId,
    doctype,
    docname,
    pollInterval = 5000,
    onError,
  } = options;

  // Machine config state
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [edges, setEdges] = useState<WorkflowEdge[]>([]);

  // Runtime state
  const [currentState, setCurrentState] = useState<string | null>(null);
  const [status, setStatus] = useState<UseInstanceViewerReturn['status']>(null);
  const [availableEvents, setAvailableEvents] = useState<AvailableEvent[]>([]);
  const [transitionLog, setTransitionLog] = useState<TransitionLogEntry[]>([]);
  const [transitionCount, setTransitionCount] = useState(0);
  const [lastEvent, setLastEvent] = useState<string | null>(null);
  const [lastTransitionAt, setLastTransitionAt] = useState<string | null>(null);

  // Machine info
  const [machineName, setMachineName] = useState<string | null>(null);
  const [instanceName, setInstanceName] = useState<string | null>(null);

  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasWorkflow, setHasWorkflow] = useState(false);
  const [configLoaded, setConfigLoaded] = useState(false);

  // Load machine configuration
  const loadMachineConfig = useCallback(async () => {
    if (!machineId || typeof frappe === 'undefined') return;

    try {
      const response = await frappe.xcall<{
        machine_id: string;
        workflow_builder_config?: string;
      }>('xstate_workflow.workflow_engine.get_machine', {
        machine_id: machineId,
      });

      if (response.workflow_builder_config) {
        const config: WorkflowBuilderConfig = JSON.parse(response.workflow_builder_config);
        setNodes(config.nodes || []);
        setEdges(config.edges || []);
      }
      setConfigLoaded(true);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load machine config';
      setError(errorMsg);
      onError?.(errorMsg);
    }
  }, [machineId, onError]);

  // Load runtime state
  const loadRuntimeState = useCallback(async () => {
    if (!doctype || !docname || typeof frappe === 'undefined') return;

    try {
      const response = await frappe.xcall<{
        has_workflow: boolean;
        instance_name?: string;
        machine?: string;
        current_state?: string;
        status?: 'idle' | 'active' | 'final' | 'error' | 'archived';
        available_events?: AvailableEvent[];
        transition_count?: number;
        transition_log?: TransitionLogEntry[];
        last_event?: string;
        last_transition_at?: string;
        message?: string;
      }>('xstate_workflow.workflow_engine.get_machine_state_with_history', {
        doctype,
        docname,
      });

      setHasWorkflow(response.has_workflow);

      if (response.has_workflow) {
        setCurrentState(response.current_state || null);
        setStatus(response.status || null);
        setAvailableEvents(response.available_events || []);
        setTransitionLog(response.transition_log || []);
        setTransitionCount(response.transition_count || 0);
        setLastEvent(response.last_event || null);
        setLastTransitionAt(response.last_transition_at || null);
        setMachineName(response.machine || null);
        setInstanceName(response.instance_name || null);
        setError(null);
      } else {
        setError(response.message || 'No workflow attached');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load workflow state';
      setError(errorMsg);
      onError?.(errorMsg);
    }
  }, [doctype, docname, onError]);

  // Combined refresh function
  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      if (!configLoaded) {
        await loadMachineConfig();
      }
      await loadRuntimeState();
    } finally {
      setIsLoading(false);
    }
  }, [configLoaded, loadMachineConfig, loadRuntimeState]);

  // Initial load
  useEffect(() => {
    refresh();
  }, [machineId, doctype, docname]); // eslint-disable-line react-hooks/exhaustive-deps

  // Polling for updates
  useEffect(() => {
    if (!pollInterval || pollInterval <= 0) return;

    const intervalId = setInterval(() => {
      loadRuntimeState();
    }, pollInterval);

    return () => clearInterval(intervalId);
  }, [pollInterval, loadRuntimeState]);

  // Compute current node ID by matching state label
  const currentNodeId = useMemo(() => {
    if (!currentState || nodes.length === 0) return null;

    const matchingNode = nodes.find(
      (node) => node.data.label === currentState || node.id === currentState
    );
    return matchingNode?.id || null;
  }, [currentState, nodes]);

  // Compute visited node IDs from transition log
  const visitedNodeIds = useMemo(() => {
    const visited = new Set<string>();

    for (const entry of transitionLog) {
      if (entry.success) {
        // Find node by state name
        const fromNode = nodes.find(
          (n) => n.data.label === entry.from_state || n.id === entry.from_state
        );
        const toNode = nodes.find(
          (n) => n.data.label === entry.to_state || n.id === entry.to_state
        );

        if (fromNode) visited.add(fromNode.id);
        if (toNode) visited.add(toNode.id);
      }
    }

    return Array.from(visited);
  }, [transitionLog, nodes]);

  // Compute available target node IDs
  const availableTargetNodeIds = useMemo(() => {
    const targets = new Set<string>();

    for (const event of availableEvents) {
      if (event.enabled && event.target) {
        const targetNode = nodes.find(
          (n) => n.data.label === event.target || n.id === event.target
        );
        if (targetNode) {
          targets.add(targetNode.id);
        }
      }
    }

    return Array.from(targets);
  }, [availableEvents, nodes]);

  return {
    // Workflow config
    nodes,
    edges,

    // Runtime state
    currentState,
    status,
    availableEvents,
    transitionLog,
    transitionCount,
    lastEvent,
    lastTransitionAt,

    // Machine info
    machineName,
    instanceName,

    // Loading states
    isLoading,
    error,
    hasWorkflow,

    // Computed visualization
    currentNodeId,
    visitedNodeIds,
    availableTargetNodeIds,

    // Actions
    refresh,
  };
}
