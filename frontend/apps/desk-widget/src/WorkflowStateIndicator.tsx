import { useEffect, useState, useCallback } from 'react';
import { getMachineState } from '@xstate-workflow/frappe-adapter';

interface WorkflowState {
  has_workflow: boolean;
  current_state?: string;
  status?: string;
  machine?: string;
  available_events?: Array<{
    event: string;
    target: string | null;
    enabled: boolean;
  }>;
}

interface WorkflowStateIndicatorProps {
  doctype: string;
  docname: string;
  onStateChange?: (newState: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  idle: '#6b7280',
  active: '#3b82f6',
  final: '#10b981',
  error: '#ef4444',
  archived: '#9ca3af',
};

const STATE_TYPE_COLORS: Record<string, string> = {
  draft: '#6b7280',
  pending: '#f59e0b',
  approved: '#10b981',
  rejected: '#ef4444',
  completed: '#10b981',
  cancelled: '#6b7280',
};

function getStateColor(state: string): string {
  // Check for known state types
  const lowerState = state.toLowerCase();
  for (const [key, color] of Object.entries(STATE_TYPE_COLORS)) {
    if (lowerState.includes(key)) {
      return color;
    }
  }
  return '#3b82f6'; // Default blue
}

export function WorkflowStateIndicator({
  doctype,
  docname,
  onStateChange,
}: WorkflowStateIndicatorProps) {
  const [state, setState] = useState<WorkflowState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadState = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await getMachineState(doctype, docname);
      setState(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workflow state');
    } finally {
      setIsLoading(false);
    }
  }, [doctype, docname]);

  useEffect(() => {
    loadState();

    // Subscribe to realtime updates
    if (typeof frappe !== 'undefined' && frappe.realtime) {
      const handler = (data: { doctype: string; docname: string; to_state: string }) => {
        if (data.doctype === doctype && data.docname === docname) {
          loadState();
          onStateChange?.(data.to_state);
        }
      };

      frappe.realtime.on('workflow_transition', handler);
      return () => {
        frappe.realtime.off('workflow_transition', handler);
      };
    }
  }, [doctype, docname, loadState, onStateChange]);

  if (isLoading) {
    return (
      <div className="xsw-state-indicator xsw-state-loading">
        <span className="xsw-state-spinner"></span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="xsw-state-indicator xsw-state-error" title={error}>
        <span style={{ color: '#ef4444' }}>Error</span>
      </div>
    );
  }

  if (!state?.has_workflow) {
    return null;
  }

  const stateColor = getStateColor(state.current_state || '');
  const statusColor = STATUS_COLORS[state.status || 'idle'];

  return (
    <div className="xsw-state-indicator" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      {/* Status dot */}
      <span
        className="xsw-status-dot"
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: statusColor,
        }}
        title={`Status: ${state.status}`}
      />

      {/* State badge */}
      <span
        className="xsw-state-badge"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: 500,
          backgroundColor: `${stateColor}15`,
          color: stateColor,
          border: `1px solid ${stateColor}30`,
        }}
      >
        {state.current_state}
      </span>

      {/* Available transitions count */}
      {state.available_events && state.available_events.length > 0 && (
        <span
          className="xsw-transitions-count"
          style={{
            fontSize: '11px',
            color: '#6b7280',
          }}
          title={`${state.available_events.filter(e => e.enabled).length} available transitions`}
        >
          ({state.available_events.filter(e => e.enabled).length} actions)
        </span>
      )}

      {/* Refresh button */}
      <button
        className="xsw-refresh-btn"
        onClick={loadState}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: '2px',
          color: '#6b7280',
          fontSize: '12px',
        }}
        title="Refresh state"
      >
        &#x21bb;
      </button>

      {/* View Workflow Diagram link */}
      {state.machine && (
        <a
          href={`/xstate-viewer/${encodeURIComponent(state.machine)}?doctype=${encodeURIComponent(doctype)}&docname=${encodeURIComponent(docname)}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            marginLeft: '8px',
            fontSize: '11px',
            color: '#6b7280',
            textDecoration: 'none',
          }}
          title="View workflow diagram"
        >
          &#128202; View Diagram
        </a>
      )}
    </div>
  );
}

// Declare frappe global
declare const frappe: {
  realtime: {
    on: (event: string, handler: (data: unknown) => void) => void;
    off: (event: string, handler: (data: unknown) => void) => void;
  };
};
