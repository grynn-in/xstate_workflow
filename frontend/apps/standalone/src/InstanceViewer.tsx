import { useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  nodeTypes,
  edgeTypes,
  RuntimeInfoPanel,
  useInstanceViewer,
  type WorkflowNode,
  type WorkflowEdge,
} from '@xstate-workflow/core';
import '@xstate-workflow/core/styles';

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
 * Instance Viewer Component
 *
 * Displays a read-only view of a workflow with the current runtime state highlighted.
 * Used to visualize where a specific document is in its workflow.
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

  // Apply runtime state to edges
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

      return {
        ...edge,
        data: {
          ...edge.data,
          isFromCurrentState: isFromCurrent,
          isAvailableTransition: isAvailable,
          isVisitedTransition: false, // Could compute from transition log
          isDisabledTransition: isDisabled,
        },
      };
    });
  }, [edges, nodes, currentNodeId, availableEvents]);

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
          edgeTypes={edgeTypes}
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
