import { useEffect, useState, useCallback } from 'react';
import { getMachineState, cancelWorkflow, startWorkflow } from '@xstate-workflow/frappe-adapter';

interface WorkflowState {
  has_workflow: boolean;
  current_state?: string;
  status?: string;
  machine?: string;
  workflow_attached?: boolean;
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
  cancelled: '#f97316',
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
  const [isProcessing, setIsProcessing] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [cancelReason, setCancelReason] = useState('');

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

  const handleStartWorkflow = async () => {
    try {
      setIsProcessing(true);
      const result = await startWorkflow(doctype, docname);
      if (result.success) {
        loadState();
        onStateChange?.(result.current_state || '');
      } else {
        setError(result.message || 'Failed to start workflow');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start workflow');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancelWorkflow = async () => {
    try {
      setIsProcessing(true);
      const result = await cancelWorkflow(doctype, docname, cancelReason);
      if (result.success) {
        setShowCancelConfirm(false);
        setCancelReason('');
        loadState();
        onStateChange?.('cancelled');
      } else {
        setError(result.message || 'Failed to cancel workflow');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel workflow');
    } finally {
      setIsProcessing(false);
    }
  };

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

  // Show Start button for cancelled workflows or when workflow attached but not started
  const showStartButton = state?.status === 'cancelled' ||
    (!state?.has_workflow && state?.workflow_attached);

  // Show Cancel button for active workflows (not cancelled, not final)
  const showCancelButton = state?.has_workflow &&
    state?.status !== 'cancelled' &&
    state?.status !== 'final';

  if (!state?.has_workflow && !state?.workflow_attached) {
    return null;
  }

  const stateColor = getStateColor(state?.current_state || '');
  const statusColor = STATUS_COLORS[state?.status || 'idle'];

  return (
    <div className="xsw-state-indicator" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
      {/* Status dot and state badge - only show if workflow has been started */}
      {state?.has_workflow && (
        <>
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
            {state.status === 'cancelled' ? 'Cancelled' : state.current_state}
          </span>
        </>
      )}

      {/* Available transitions count */}
      {state?.available_events && state.available_events.length > 0 && state.status !== 'cancelled' && (
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

      {/* Start Workflow button */}
      {showStartButton && (
        <button
          className="xsw-start-btn"
          onClick={handleStartWorkflow}
          disabled={isProcessing}
          style={{
            padding: '4px 10px',
            fontSize: '11px',
            fontWeight: 500,
            color: '#fff',
            backgroundColor: '#10b981',
            border: 'none',
            borderRadius: '4px',
            cursor: isProcessing ? 'not-allowed' : 'pointer',
            opacity: isProcessing ? 0.6 : 1,
          }}
          title={state?.status === 'cancelled' ? 'Restart workflow' : 'Start workflow'}
        >
          {isProcessing ? 'Starting...' : (state?.status === 'cancelled' ? 'Restart Workflow' : 'Start Workflow')}
        </button>
      )}

      {/* Cancel Workflow button */}
      {showCancelButton && (
        <button
          className="xsw-cancel-btn"
          onClick={() => setShowCancelConfirm(true)}
          disabled={isProcessing}
          style={{
            padding: '4px 10px',
            fontSize: '11px',
            fontWeight: 500,
            color: '#fff',
            backgroundColor: '#ef4444',
            border: 'none',
            borderRadius: '4px',
            cursor: isProcessing ? 'not-allowed' : 'pointer',
            opacity: isProcessing ? 0.6 : 1,
          }}
          title="Cancel workflow"
        >
          Cancel Workflow
        </button>
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
      {state?.machine && (
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

      {/* Cancel Confirmation Modal */}
      {showCancelConfirm && (
        <div
          className="xsw-modal-overlay"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setShowCancelConfirm(false)}
        >
          <div
            className="xsw-modal-content"
            style={{
              backgroundColor: '#fff',
              padding: '20px',
              borderRadius: '8px',
              maxWidth: '400px',
              width: '90%',
              boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 600 }}>
              Cancel Workflow?
            </h3>
            <p style={{ margin: '0 0 16px 0', color: '#6b7280', fontSize: '14px' }}>
              This will cancel all pending approval tasks. You can restart the workflow later.
            </p>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#374151' }}>
                Reason (optional)
              </label>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="Enter reason for cancellation..."
                style={{
                  width: '100%',
                  padding: '8px',
                  borderRadius: '4px',
                  border: '1px solid #d1d5db',
                  fontSize: '14px',
                  resize: 'vertical',
                  minHeight: '60px',
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowCancelConfirm(false)}
                style={{
                  padding: '8px 16px',
                  fontSize: '14px',
                  color: '#374151',
                  backgroundColor: '#f3f4f6',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                Keep Workflow
              </button>
              <button
                onClick={handleCancelWorkflow}
                disabled={isProcessing}
                style={{
                  padding: '8px 16px',
                  fontSize: '14px',
                  color: '#fff',
                  backgroundColor: '#ef4444',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isProcessing ? 'not-allowed' : 'pointer',
                  opacity: isProcessing ? 0.6 : 1,
                }}
              >
                {isProcessing ? 'Cancelling...' : 'Yes, Cancel Workflow'}
              </button>
            </div>
          </div>
        </div>
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
