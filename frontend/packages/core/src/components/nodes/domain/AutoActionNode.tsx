import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { AutoActionNodeData, AutoActionType } from '../../../types';

export interface AutoActionNodeProps {
  id: string;
  data: AutoActionNodeData;
  selected?: boolean;
}

const ACTION_ICONS: Record<AutoActionType, JSX.Element> = {
  submit_document: (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z" />
    </svg>
  ),
  cancel_document: (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
    </svg>
  ),
  update_field: (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" />
    </svg>
  ),
  update_status: (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M17 3H7c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H7V5h10v14zM8 15h8v2H8zm0-4h8v2H8zm0-4h8v2H8z" />
    </svg>
  ),
  send_notification: (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
    </svg>
  ),
  call_api: (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
    </svg>
  ),
  run_method: (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z" />
    </svg>
  ),
};

const ACTION_LABELS: Record<AutoActionType, string> = {
  submit_document: 'Submit',
  cancel_document: 'Cancel',
  update_field: 'Update Field',
  update_status: 'Update Status',
  send_notification: 'Notify',
  call_api: 'API Call',
  run_method: 'Run Method',
};

function AutoActionNodeComponent({ data, selected }: AutoActionNodeProps) {
  const { label, actionType, actionConfig } = data;
  const icon = ACTION_ICONS[actionType] || ACTION_ICONS.run_method;
  const actionLabel = ACTION_LABELS[actionType] || actionType;

  // Build detail text based on action type
  let detailText = '';
  if (actionConfig) {
    switch (actionType) {
      case 'update_field':
        detailText = actionConfig.field ? `${actionConfig.field} = ${actionConfig.value}` : '';
        break;
      case 'update_status':
        detailText = actionConfig.status || '';
        break;
      case 'send_notification':
        detailText = actionConfig.notification_type || '';
        break;
      case 'call_api':
        detailText = actionConfig.method || 'POST';
        break;
      case 'run_method':
        detailText = actionConfig.methodName || '';
        break;
    }
  }

  return (
    <div
      className={clsx(
        'xsw-domain-node',
        'xsw-auto-action-node',
        selected && 'selected',
        `action-${actionType}`
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="xsw-handle"
      />

      {/* Header with lightning icon */}
      <div className="xsw-auto-action-header">
        <div className="xsw-auto-action-icon">{icon}</div>
        <span className="xsw-auto-action-label">{label || actionLabel}</span>
      </div>

      {/* Action type badge */}
      <div className="xsw-auto-action-type">{actionLabel}</div>

      {/* Detail text */}
      {detailText && (
        <div className="xsw-auto-action-detail">{detailText}</div>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="xsw-handle"
      />
    </div>
  );
}

export const AutoActionNode = memo(AutoActionNodeComponent);
