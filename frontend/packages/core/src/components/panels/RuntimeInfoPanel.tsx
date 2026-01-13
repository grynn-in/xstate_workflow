import { memo } from 'react';
import { clsx } from 'clsx';
import type { TransitionLogEntry, AvailableEvent } from '../../hooks/useInstanceViewer';

export interface RuntimeInfoPanelProps {
  /** Current state name */
  currentState: string | null;
  /** Machine status */
  status: 'idle' | 'active' | 'final' | 'error' | 'archived' | null;
  /** Available events/transitions */
  availableEvents: AvailableEvent[];
  /** Transition history log */
  transitionLog: TransitionLogEntry[];
  /** Reference doctype */
  doctype: string;
  /** Reference document name */
  docname: string;
  /** Total transition count */
  transitionCount?: number;
  /** Last transition timestamp */
  lastTransitionAt?: string | null;
}

function RuntimeInfoPanelComponent({
  currentState,
  status,
  availableEvents,
  transitionLog,
  doctype,
  docname,
  transitionCount = 0,
  lastTransitionAt,
}: RuntimeInfoPanelProps) {
  const enabledEvents = availableEvents.filter((e) => e.enabled);

  // Format timestamp for display
  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  // Get document URL (Frappe ERPNext URL pattern)
  const getDocumentUrl = () => {
    const slug = doctype.toLowerCase().replace(/ /g, '-');
    return `/app/${slug}/${encodeURIComponent(docname)}`;
  };

  return (
    <div className="xsw-runtime-panel xsw-panel">
      <div className="xsw-panel-header">Document State</div>

      {/* Current State Section */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Current State</div>
        <div className="xsw-current-state-display">
          <span className="xsw-state-dot" />
          <span className="xsw-state-name">{currentState || 'Unknown'}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
          <span className={clsx('xsw-status-badge', status)}>{status || 'unknown'}</span>
          {transitionCount > 0 && (
            <span style={{ fontSize: '12px', color: '#6b7280' }}>
              {transitionCount} transition{transitionCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {lastTransitionAt && (
          <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
            Last: {formatTime(lastTransitionAt)}
          </div>
        )}
      </div>

      {/* Available Transitions Section */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">
          Available Transitions ({enabledEvents.length})
        </div>
        <div className="xsw-transitions-list">
          {availableEvents.map((evt, idx) => (
            <div
              key={idx}
              className={clsx('xsw-transition-item', evt.enabled ? 'enabled' : 'disabled')}
            >
              <span className="xsw-event-name">{evt.event}</span>
              <span className="xsw-event-arrow">&rarr;</span>
              <span className="xsw-event-target">{evt.target || 'self'}</span>
              {evt.guards?.length > 0 && (
                <span
                  className="xsw-guard-indicator"
                  title={`Guard: ${evt.guards.join(', ')}`}
                >
                  {evt.enabled ? '' : '(blocked)'}
                </span>
              )}
            </div>
          ))}
          {availableEvents.length === 0 && (
            <div className="xsw-no-transitions">No transitions available</div>
          )}
        </div>
      </div>

      {/* Transition History Section */}
      <div className="xsw-panel-section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div className="xsw-panel-section-title">
          Transition History ({transitionLog.length})
        </div>
        <div className="xsw-history-list">
          {transitionLog
            .slice()
            .reverse()
            .slice(0, 15)
            .map((log, idx) => (
              <div
                key={idx}
                className={clsx('xsw-history-item', !log.success && 'failed')}
              >
                <div className="xsw-history-states">
                  <span>{log.from_state}</span>
                  <span className="xsw-history-arrow">&rarr;</span>
                  <span>{log.to_state}</span>
                </div>
                <div className="xsw-history-meta">
                  <span className="xsw-history-event">{log.event}</span>
                  <span className="xsw-history-time">{formatTime(log.timestamp)}</span>
                  {log.user && <span className="xsw-history-user">{log.user}</span>}
                  {log.error && (
                    <span style={{ color: '#dc3545' }} title={log.error}>
                      Error
                    </span>
                  )}
                </div>
              </div>
            ))}
          {transitionLog.length === 0 && (
            <div className="xsw-no-history">No transitions yet</div>
          )}
        </div>
      </div>

      {/* Document Link Section */}
      <div className="xsw-panel-section">
        <a
          href={getDocumentUrl()}
          className="xsw-button xsw-button-secondary"
          style={{ width: '100%', textAlign: 'center', textDecoration: 'none' }}
        >
          View Document
        </a>
      </div>
    </div>
  );
}

export const RuntimeInfoPanel = memo(RuntimeInfoPanelComponent);
