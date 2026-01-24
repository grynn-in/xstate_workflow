import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { RestFetchNodeData } from '../../../types';
import { getEventColor } from '../../../types';

export interface RestFetchNodeProps {
  id: string;
  data: RestFetchNodeData;
  selected?: boolean;
}

function RestFetchNodeComponent({ data, selected }: RestFetchNodeProps) {
  const {
    label,
    url,
    method,
    authType,
    saveResponseTo,
    timeoutSeconds,
    outgoingEvents,
  } = data;

  // Get a shortened URL for display
  const displayUrl = url
    ? url.length > 30
      ? url.substring(0, 27) + '...'
      : url
    : 'No URL configured';

  // Method badge color
  const methodColor = {
    GET: '#22c55e',
    POST: '#3b82f6',
    PUT: '#f59e0b',
    PATCH: '#8b5cf6',
    DELETE: '#ef4444',
  }[method || 'GET'] || '#6b7280';

  return (
    <div
      className={clsx(
        'xsw-domain-node',
        'xsw-rest-fetch-node',
        selected && 'selected'
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="xsw-handle"
      />

      {/* Header with REST icon */}
      <div className="xsw-rest-fetch-header">
        <div className="xsw-rest-fetch-icon">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
          </svg>
        </div>
        <span className="xsw-rest-fetch-label">{label || 'REST Fetch'}</span>
        <span
          className="xsw-rest-fetch-method-badge"
          style={{ background: methodColor }}
        >
          {method || 'GET'}
        </span>
      </div>

      {/* Separator */}
      <div className="xsw-node-separator" />

      {/* REST info */}
      <div className="xsw-rest-fetch-info">
        <div className="xsw-info-row">
          <span className="xsw-info-label">URL:</span>
          <span className="xsw-info-value xsw-info-url" title={url}>
            {displayUrl}
          </span>
        </div>
        {authType && authType !== 'none' && (
          <div className="xsw-info-row">
            <span className="xsw-info-label">Auth:</span>
            <span className="xsw-info-value">
              {authType === 'api_key' ? 'API Key' :
               authType === 'bearer' ? 'Bearer' :
               authType === 'basic' ? 'Basic' : authType}
            </span>
          </div>
        )}
        {saveResponseTo && (
          <div className="xsw-info-row">
            <span className="xsw-info-label">Save to:</span>
            <span className="xsw-info-value">{saveResponseTo}</span>
          </div>
        )}
        {timeoutSeconds && (
          <div className="xsw-info-row">
            <span className="xsw-info-label">Timeout:</span>
            <span className="xsw-info-value">{timeoutSeconds}s</span>
          </div>
        )}
      </div>

      {/* Output Handles - dynamic based on outgoing events */}
      {outgoingEvents && outgoingEvents.length > 1 ? (
        outgoingEvents.map((event, index) => {
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
        })
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

export const RestFetchNode = memo(RestFetchNodeComponent);
