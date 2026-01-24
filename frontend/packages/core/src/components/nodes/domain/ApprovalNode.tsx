import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { ApprovalNodeData } from '../../../types';
import { getEventColor } from '../../../types';

export interface ApprovalNodeProps {
  id: string;
  data: ApprovalNodeData;
  selected?: boolean;
}

function ApprovalNodeComponent({ data, selected }: ApprovalNodeProps) {
  const { label, resolver, availableActions, slaHours, priority, outgoingEvents } = data;

  return (
    <div
      className={clsx(
        'xsw-domain-node',
        'xsw-approval-node',
        selected && 'selected',
        priority && `priority-${priority.toLowerCase()}`
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="xsw-handle"
      />

      {/* Header with user icon */}
      <div className="xsw-approval-header">
        <div className="xsw-approval-icon">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
          </svg>
        </div>
        <span className="xsw-approval-label">{label || 'Approval'}</span>
        {priority && (
          <span className={clsx('xsw-priority-badge', priority.toLowerCase())}>
            {priority}
          </span>
        )}
      </div>

      {/* Separator */}
      <div className="xsw-node-separator" />

      {/* Resolver info */}
      <div className="xsw-approval-info">
        <div className="xsw-info-row">
          <span className="xsw-info-label">Resolver:</span>
          <span className="xsw-info-value">{resolver?.type || 'Not set'}</span>
        </div>
        {slaHours && (
          <div className="xsw-info-row">
            <span className="xsw-info-label">SLA:</span>
            <span className="xsw-info-value">{slaHours}h</span>
          </div>
        )}
      </div>

      {/* Available actions */}
      {availableActions && availableActions.length > 0 && (
        <div className="xsw-approval-actions">
          {availableActions.map((action) => (
            <span
              key={action}
              className={clsx(
                'xsw-action-badge',
                action.toLowerCase() === 'approve' && 'approve',
                action.toLowerCase() === 'reject' && 'reject'
              )}
            >
              {action}
            </span>
          ))}
        </div>
      )}

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
          {/* Hidden default handle for delayed/always edges (no sourceHandle) */}
          <Handle
            type="source"
            position={Position.Bottom}
            className="xsw-handle"
            style={{ opacity: 0, width: 1, height: 1, minWidth: 0, minHeight: 0, left: '50%' }}
          />
        </>
      ) : (
        <Handle
          type="source"
          position={Position.Bottom}
          className="xsw-handle"
        />
      )}
    </div>
  );
}

export const ApprovalNode = memo(ApprovalNodeComponent);
