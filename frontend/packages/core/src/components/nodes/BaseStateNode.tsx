import { memo, type ReactNode } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { WorkflowNodeData } from '../../types';
import { getEventColor } from '../../types';

/**
 * Extended node data with runtime state properties for instance viewer
 */
export interface RuntimeNodeData extends WorkflowNodeData {
  /** Node is the currently active state */
  isCurrentState?: boolean;
  /** Node has been visited in transition history */
  isVisitedState?: boolean;
  /** Node is an available transition target */
  isAvailableTarget?: boolean;
  /** Node would be available but is blocked by guard */
  isDisabledTarget?: boolean;
}

export interface BaseStateNodeProps {
  id: string;
  data: RuntimeNodeData;
  selected?: boolean;
  children?: ReactNode;
}

function BaseStateNodeComponent({ data, selected, children }: BaseStateNodeProps) {
  const {
    label,
    xstateType,
    isInitial,
    entryActions,
    exitActions,
    description,
    outgoingEvents,
    // Runtime state props
    isCurrentState,
    isVisitedState,
    isAvailableTarget,
    isDisabledTarget,
  } = data;

  const nodeType = isInitial ? 'initial' : xstateType;
  const entryCount = entryActions?.length || 0;
  const exitCount = exitActions?.length || 0;

  return (
    <div
      className={clsx(
        'xsw-node',
        nodeType,
        selected && 'selected',
        // Runtime state classes
        isCurrentState && 'xsw-node-current',
        isVisitedState && 'xsw-node-visited',
        isAvailableTarget && 'xsw-node-available',
        isDisabledTarget && 'xsw-node-disabled'
      )}
    >
      {/* Current state badge */}
      {isCurrentState && (
        <div className="xsw-current-badge">
          <span className="xsw-current-pulse" />
          Current
        </div>
      )}
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="xsw-handle"
      />

      {/* Node Header */}
      <div className="xsw-node-header">
        <div className={clsx('xsw-node-indicator', nodeType)} />
        <span className="xsw-node-label" title={label}>
          {label}
        </span>
        {xstateType === 'history' && (
          <span className="xsw-history-badge">
            {data.historyType === 'deep' ? 'H*' : 'H'}
          </span>
        )}
      </div>

      {/* Description */}
      {description && (
        <div className="xsw-node-description" style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
          {description}
        </div>
      )}

      {/* Separator */}
      {(entryCount > 0 || exitCount > 0) && <div className="xsw-node-separator" />}

      {/* Action Badges */}
      {(entryCount > 0 || exitCount > 0) && (
        <div className="xsw-node-badges">
          {entryCount > 0 && (
            <span className="xsw-badge xsw-badge-entry">
              entry: {entryCount}
            </span>
          )}
          {exitCount > 0 && (
            <span className="xsw-badge xsw-badge-exit">
              exit: {exitCount}
            </span>
          )}
        </div>
      )}

      {/* Additional content for compound/parallel states */}
      {children}

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
            // Calculate position: evenly spread across the bottom
            // For 2 events: 33%, 66%
            // For 3 events: 25%, 50%, 75%
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

export const BaseStateNode = memo(BaseStateNodeComponent);
