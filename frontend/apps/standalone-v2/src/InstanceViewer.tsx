import { useMemo, useEffect, useRef } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Import from core-v2 which re-exports core + v2 enhancements
import {
  nodeTypes,
  RuntimeInfoPanel,
  useInstanceViewer,
  type WorkflowNode,
  type WorkflowEdge,
} from '@xstate-workflow/core-v2';
import { useTransitionAnimation, usePathHighlighting, TransitionEdgeV2 } from '@xstate-workflow/core-v2';
import '@xstate-workflow/core/styles';
import '@xstate-workflow/core-v2/styles';

// V2 edge types with animation support
const edgeTypesV2 = {
  transition: TransitionEdgeV2,
};

interface InstanceViewerProps {
  machineId: string;
  doctype: string;
  docname: string;
}

/**
 * Status badge component for displaying workflow status
 */
function StatusBadge({
  status,
  currentState,
}: {
  status: string | null;
  currentState: string | null;
}) {
  const statusColors: Record<string, { bg: string; text: string }> = {
    idle: { bg: '#f3f4f6', text: '#6b7280' },
    active: { bg: 'rgba(59, 130, 246, 0.1)', text: '#3b82f6' },
    final: { bg: 'rgba(16, 185, 129, 0.1)', text: '#10b981' },
    error: { bg: 'rgba(220, 53, 69, 0.1)', text: '#dc3545' },
    archived: { bg: '#f3f4f6', text: '#9ca3af' },
  };

  const colors = statusColors[status || 'idle'] || statusColors.idle;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 12px',
        borderRadius: '9999px',
        fontSize: '13px',
        fontWeight: 500,
        background: colors.bg,
        color: colors.text,
      }}
    >
      <span
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: colors.text,
        }}
      />
      {currentState || 'Loading...'}
    </span>
  );
}

/**
 * Instance Viewer Component V2
 *
 * Displays a read-only view of a workflow with the current runtime state highlighted.
 * Enhanced with transition animations and path highlighting.
 */
export function InstanceViewer({ machineId, doctype, docname }: InstanceViewerProps) {
  const {
    nodes,
    edges,
    currentState,
    status,
    availableEvents,
    transitionLog,
    transitionCount,
    lastTransitionAt,
    isLoading,
    error,
    hasWorkflow,
    currentNodeId,
    visitedNodeIds,
    availableTargetNodeIds,
    refresh,
  } = useInstanceViewer({
    machineId,
    doctype,
    docname,
    pollInterval: 5000,
  });

  // Track previous state to detect transitions
  const prevStateRef = useRef<string | null>(null);
  const prevTransitionCountRef = useRef<number>(0);

  // Animation hook for transition effects
  const { animatingEdges, triggerAnimationByNodes, isAnimating } = useTransitionAnimation({
    edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target })),
    duration: 800,
    onAnimationComplete: (edgeId, fromNode, toNode) => {
      console.log(`Animation complete: ${fromNode} -> ${toNode} (edge: ${edgeId})`);
    },
  });

  // Path highlighting hook for showing transition sequence
  const {
    isEdgeVisited,
    getEdgeSequence,
    pathStats,
  } = usePathHighlighting({
    edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target })),
    nodes: nodes.map(n => ({ id: n.id, data: { label: n.data?.label } })),
    transitionLog: transitionLog.map(t => ({
      from_state: t.from_state || '',
      to_state: t.to_state || '',
      event: t.event,
    })),
    currentState: currentState || '',
  });

  // Trigger animation when state changes
  useEffect(() => {
    // Check if transition count increased (more reliable than state change)
    if (transitionCount > prevTransitionCountRef.current && transitionLog.length > 0) {
      const lastTransition = transitionLog[transitionLog.length - 1];
      if (lastTransition.from_state && lastTransition.to_state) {
        // Find node IDs from state names
        const fromNodeId = nodes.find(n => n.data?.label === lastTransition.from_state || n.id === lastTransition.from_state)?.id;
        const toNodeId = nodes.find(n => n.data?.label === lastTransition.to_state || n.id === lastTransition.to_state)?.id;

        if (fromNodeId && toNodeId) {
          console.log(`Triggering animation: ${fromNodeId} -> ${toNodeId}`);
          triggerAnimationByNodes(fromNodeId, toNodeId);
        }
      }
    }
    prevTransitionCountRef.current = transitionCount;
    prevStateRef.current = currentState;
  }, [transitionCount, currentState, transitionLog, nodes, triggerAnimationByNodes]);

  // Apply runtime state to nodes
  const nodesWithRuntimeState: WorkflowNode[] = useMemo(() => {
    return nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isCurrentState: node.id === currentNodeId,
        isVisitedState: visitedNodeIds.includes(node.id) && node.id !== currentNodeId,
        isAvailableTarget: availableTargetNodeIds.includes(node.id),
        isDisabledTarget: false, // Could be computed from available events with guards
      },
      // Prevent dragging in view mode
      draggable: false,
    }));
  }, [nodes, currentNodeId, visitedNodeIds, availableTargetNodeIds]);

  // Apply runtime state to edges (with animation and path highlighting)
  const edgesWithRuntimeState: WorkflowEdge[] = useMemo(() => {
    return edges.map((edge) => {
      const sourceNode = nodes.find((n) => n.id === edge.source);
      const isFromCurrent = sourceNode?.id === currentNodeId;
      const isAvailable =
        isFromCurrent &&
        availableEvents.some(
          (e) => e.event === edge.data?.event && e.enabled
        );
      const isDisabled =
        isFromCurrent &&
        availableEvents.some(
          (e) => e.event === edge.data?.event && !e.enabled
        );

      // Check if this edge is currently animating
      const edgeIsAnimating = isAnimating(edge.id);

      // Get path highlighting data
      const visited = isEdgeVisited(edge.id);
      const sequenceNumber = getEdgeSequence(edge.id);

      return {
        ...edge,
        type: 'transition', // Ensure using our custom edge type
        data: {
          ...edge.data,
          isFromCurrentState: isFromCurrent,
          isAvailableTransition: isAvailable,
          isVisitedTransition: visited,
          isDisabledTransition: isDisabled,
          isAnimating: edgeIsAnimating,
          sequenceNumber: sequenceNumber,
        },
      };
    });
  }, [edges, nodes, currentNodeId, availableEvents, isAnimating, animatingEdges, isEdgeVisited, getEdgeSequence]);

  // Show loading state
  if (isLoading && nodes.length === 0) {
    return (
      <div
        className="xsw-layout xsw-view-mode"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <div style={{ fontSize: '24px', marginBottom: '8px' }}>Loading...</div>
          <div style={{ fontSize: '14px' }}>Fetching workflow state</div>
        </div>
      </div>
    );
  }

  // Show error state
  if (error && !hasWorkflow) {
    return (
      <div
        className="xsw-layout xsw-view-mode"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div style={{ textAlign: 'center', color: '#dc3545' }}>
          <div style={{ fontSize: '24px', marginBottom: '8px' }}>Error</div>
          <div style={{ fontSize: '14px' }}>{error}</div>
          <button
            className="xsw-button xsw-button-secondary"
            style={{ marginTop: '16px' }}
            onClick={refresh}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="xsw-layout xsw-view-mode">
      {/* Toolbar */}
      <div className="xsw-layout-toolbar">
        <div className="xsw-toolbar">
          <div className="xsw-toolbar-left">
            <span style={{ fontSize: '20px' }}>&#128065;</span>
            <span className="xsw-toolbar-title">Workflow Viewer</span>
            <span className="xsw-toolbar-doctype">
              {doctype}: {docname}
            </span>
            <StatusBadge status={status} currentState={currentState} />
            {pathStats.totalTransitions > 0 && (
              <span
                style={{
                  marginLeft: '8px',
                  padding: '2px 8px',
                  fontSize: '11px',
                  background: 'rgba(34, 197, 94, 0.1)',
                  color: '#16a34a',
                  borderRadius: '4px',
                }}
                title={`${pathStats.uniqueNodesVisited} nodes, ${pathStats.uniqueEdgesVisited} edges visited`}
              >
                {pathStats.totalTransitions} transition{pathStats.totalTransitions !== 1 ? 's' : ''}
              </span>
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
            <button
              className="xsw-button xsw-button-secondary"
              onClick={refresh}
              disabled={isLoading}
            >
              {isLoading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="xsw-layout-canvas">
        <ReactFlow
          nodes={nodesWithRuntimeState}
          edges={edgesWithRuntimeState}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypesV2}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnDrag={true}
          zoomOnScroll={true}
          fitView
          className="xsw-canvas"
        >
          <Controls showInteractive={false} />
          <MiniMap className="xsw-minimap" />
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        </ReactFlow>
      </div>

      {/* Runtime Info Panel */}
      <div className="xsw-layout-panel">
        <RuntimeInfoPanel
          currentState={currentState}
          status={status}
          availableEvents={availableEvents}
          transitionLog={transitionLog}
          doctype={doctype}
          docname={docname}
          transitionCount={transitionCount}
          lastTransitionAt={lastTransitionAt}
        />
      </div>
    </div>
  );
}
