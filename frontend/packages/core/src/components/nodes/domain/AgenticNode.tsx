import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { AgenticNodeData } from '../../../types';
import { getEventColor } from '../../../types';

export interface AgenticNodeProps {
  id: string;
  data: AgenticNodeData;
  selected?: boolean;
}

function AgenticNodeComponent({ data, selected }: AgenticNodeProps) {
  const {
    label,
    agentType,
    enabledTools,
    frappeAccess,
    transitionMode,
    decisionRoutes,
    customEvents,
    maxIterations,
    timeoutSeconds,
    outgoingEvents,
  } = data;

  const toolCount = enabledTools?.filter(t => t.enabled).length || 0;
  const routeCount = decisionRoutes?.length || 0;
  const eventCount = customEvents?.length || 0;

  // Format agent type for display
  const agentTypeLabel = {
    react: 'ReAct',
    tool_executor: 'Tool Exec',
    plan_execute: 'Plan & Exec',
    custom: 'Custom',
  }[agentType || 'react'] || 'ReAct';

  return (
    <div
      className={clsx(
        'xsw-domain-node',
        'xsw-agentic-node',
        selected && 'selected'
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="xsw-handle"
      />

      {/* Header with AI icon */}
      <div className="xsw-agentic-header">
        <div className="xsw-agentic-icon">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M21 10.12h-6.78l2.74-2.82c-2.73-2.7-7.15-2.8-9.88-.1-2.73 2.71-2.73 7.08 0 9.79s7.15 2.71 9.88 0C18.32 15.65 19 14.08 19 12.1h2c0 1.98-.88 4.55-2.64 6.29-3.51 3.48-9.21 3.48-12.72 0-3.5-3.47-3.53-9.11-.02-12.58s9.14-3.47 12.65 0L21 3v7.12zM12.5 8v4.25l3.5 2.08-.72 1.21L11 13V8h1.5z"/>
          </svg>
        </div>
        <span className="xsw-agentic-label">{label || 'AI Agent'}</span>
        <span className="xsw-agentic-type-badge">{agentTypeLabel}</span>
      </div>

      {/* Separator */}
      <div className="xsw-node-separator" />

      {/* Agent info */}
      <div className="xsw-agentic-info">
        {toolCount > 0 && (
          <div className="xsw-info-row">
            <span className="xsw-info-label">Tools:</span>
            <span className="xsw-info-value">{toolCount} enabled</span>
          </div>
        )}
        {frappeAccess && frappeAccess !== 'none' && (
          <div className="xsw-info-row">
            <span className="xsw-info-label">Access:</span>
            <span className={clsx('xsw-info-value', `access-${frappeAccess}`)}>
              {frappeAccess === 'read_only' ? 'Read Only' : 'Full CRUD'}
            </span>
          </div>
        )}
        {maxIterations && (
          <div className="xsw-info-row">
            <span className="xsw-info-label">Max Iter:</span>
            <span className="xsw-info-value">{maxIterations}</span>
          </div>
        )}
        {timeoutSeconds && (
          <div className="xsw-info-row">
            <span className="xsw-info-label">Timeout:</span>
            <span className="xsw-info-value">{timeoutSeconds}s</span>
          </div>
        )}
      </div>

      {/* Transition mode indicator */}
      <div className="xsw-agentic-transitions">
        {transitionMode === 'simple' && (
          <span className="xsw-transition-badge simple">Success/Fail</span>
        )}
        {transitionMode === 'decision' && (
          <span className="xsw-transition-badge decision">
            {routeCount} routes
          </span>
        )}
        {transitionMode === 'custom_events' && (
          <span className="xsw-transition-badge events">
            {eventCount} events
          </span>
        )}
        {transitionMode === 'all' && (
          <span className="xsw-transition-badge all">Multi-mode</span>
        )}
      </div>

      {/* Output Handles - dynamic based on outgoing events */}
      {outgoingEvents && outgoingEvents.length > 1 ? (
        <>
          {/* Event labels row */}
          <div className="xsw-event-handles-labels">
            {outgoingEvents.map((event) => (
              <span
                key={`label-${event}`}
                className="xsw-event-handle-label"
                style={{ color: getEventColor(event) }}
              >
                {event}
              </span>
            ))}
          </div>
          {/* Dynamic handles positioned at percentages */}
          {outgoingEvents.map((event, index) => {
            const position = ((index + 1) / (outgoingEvents.length + 1)) * 100;
            return (
              <Handle
                key={event}
                type="source"
                position={Position.Bottom}
                id={event}
                className="xsw-handle xsw-handle-event"
                style={{
                  left: `${position}%`,
                  backgroundColor: getEventColor(event),
                }}
              />
            );
          })}
        </>
      ) : (
        /* Default single centered handle */
        <Handle
          type="source"
          position={Position.Bottom}
          className="xsw-handle"
        />
      )}
    </div>
  );
}

export const AgenticNode = memo(AgenticNodeComponent);
