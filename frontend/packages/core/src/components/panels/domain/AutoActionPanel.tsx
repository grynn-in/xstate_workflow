import { memo, useCallback } from 'react';
import type { AutoActionNodeData, AutoActionType, FrappeField } from '../../../types';

export interface AutoActionPanelProps {
  data: AutoActionNodeData;
  doctypeFields?: FrappeField[];
  onDataChange: (data: Partial<AutoActionNodeData>) => void;
}

const ACTION_TYPES: Array<{ value: AutoActionType; label: string; description: string }> = [
  { value: 'submit_document', label: 'Submit Document', description: 'Submit the document (docstatus = 1)' },
  { value: 'cancel_document', label: 'Cancel Document', description: 'Cancel the document (docstatus = 2)' },
  { value: 'update_field', label: 'Update Field', description: 'Update a specific field value' },
  { value: 'update_status', label: 'Update Status', description: 'Update workflow_state field' },
  { value: 'send_notification', label: 'Send Notification', description: 'Send email or system notification' },
  { value: 'call_api', label: 'Call API', description: 'Make HTTP request to external API' },
  { value: 'run_method', label: 'Run Method', description: 'Execute a document method' },
];

function AutoActionPanelComponent({
  data,
  doctypeFields = [],
  onDataChange,
}: AutoActionPanelProps) {
  const handleActionTypeChange = useCallback((actionType: AutoActionType) => {
    onDataChange({
      actionType,
      actionConfig: {}, // Reset config when type changes
    });
  }, [onDataChange]);

  const handleConfigChange = useCallback((updates: Partial<AutoActionNodeData['actionConfig']>) => {
    onDataChange({
      actionConfig: {
        ...data.actionConfig,
        ...updates,
      },
    });
  }, [data.actionConfig, onDataChange]);

  return (
    <div className="xsw-domain-panel xsw-auto-action-panel">
      <div className="xsw-panel-header">Auto Action Configuration</div>

      {/* Action Type Selection */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Action Type</div>
        <select
          className="xsw-select"
          value={data.actionType || ''}
          onChange={(e) => handleActionTypeChange(e.target.value as AutoActionType)}
        >
          <option value="">Select action type...</option>
          {ACTION_TYPES.map(action => (
            <option key={action.value} value={action.value}>
              {action.label}
            </option>
          ))}
        </select>
        {data.actionType && (
          <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
            {ACTION_TYPES.find(a => a.value === data.actionType)?.description}
          </p>
        )}
      </div>

      {/* Submit/Cancel - no additional config needed */}
      {(data.actionType === 'submit_document' || data.actionType === 'cancel_document') && (
        <div className="xsw-panel-section">
          <div
            style={{
              padding: '12px',
              background: '#fef3c7',
              borderRadius: '6px',
              fontSize: '14px',
              color: '#92400e',
            }}
          >
            This action will {data.actionType === 'submit_document' ? 'submit' : 'cancel'} the document
            when the workflow reaches this node.
          </div>
        </div>
      )}

      {/* Update Field Config */}
      {data.actionType === 'update_field' && (
        <>
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Field to Update</div>
            <select
              className="xsw-select"
              value={data.actionConfig?.field || ''}
              onChange={(e) => handleConfigChange({ field: e.target.value })}
            >
              <option value="">Select field...</option>
              {doctypeFields.map(field => (
                <option key={field.fieldname} value={field.fieldname}>
                  {field.label} ({field.fieldtype})
                </option>
              ))}
            </select>
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">New Value</div>
            <input
              type="text"
              className="xsw-input"
              placeholder="Value or {{context_variable}}"
              value={data.actionConfig?.value as string || ''}
              onChange={(e) => handleConfigChange({ value: e.target.value })}
            />
            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
              Use {"{{variable}}"} to reference context values
            </p>
          </div>
        </>
      )}

      {/* Update Status Config */}
      {data.actionType === 'update_status' && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Status Value</div>
          <input
            type="text"
            className="xsw-input"
            placeholder="e.g., Approved, Rejected, Pending Review"
            value={data.actionConfig?.status || ''}
            onChange={(e) => handleConfigChange({ status: e.target.value })}
          />
        </div>
      )}

      {/* Send Notification Config */}
      {data.actionType === 'send_notification' && (
        <>
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Notification Type</div>
            <select
              className="xsw-select"
              value={data.actionConfig?.notification_type || 'System'}
              onChange={(e) => handleConfigChange({ notification_type: e.target.value as 'Email' | 'System' })}
            >
              <option value="System">System Notification</option>
              <option value="Email">Email</option>
            </select>
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Recipients</div>
            <input
              type="text"
              className="xsw-input"
              placeholder="user1@example.com, user2@example.com"
              value={data.actionConfig?.recipients?.join(', ') || ''}
              onChange={(e) => handleConfigChange({
                recipients: e.target.value.split(',').map(r => r.trim()).filter(Boolean)
              })}
            />
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Subject</div>
            <input
              type="text"
              className="xsw-input"
              placeholder="Notification subject"
              value={data.actionConfig?.subject || ''}
              onChange={(e) => handleConfigChange({ subject: e.target.value })}
            />
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Message</div>
            <textarea
              className="xsw-input"
              rows={3}
              placeholder="Notification message. Use {{field_name}} for variables."
              value={data.actionConfig?.message || ''}
              onChange={(e) => handleConfigChange({ message: e.target.value })}
              style={{ resize: 'vertical' }}
            />
          </div>
        </>
      )}

      {/* Call API Config */}
      {data.actionType === 'call_api' && (
        <>
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">URL</div>
            <input
              type="text"
              className="xsw-input"
              placeholder="https://api.example.com/webhook"
              value={data.actionConfig?.url || ''}
              onChange={(e) => handleConfigChange({ url: e.target.value })}
            />
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Method</div>
            <select
              className="xsw-select"
              value={data.actionConfig?.method || 'POST'}
              onChange={(e) => handleConfigChange({ method: e.target.value as 'GET' | 'POST' | 'PUT' | 'DELETE' })}
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Headers (JSON)</div>
            <textarea
              className="xsw-input"
              rows={2}
              placeholder='{"Authorization": "Bearer token"}'
              value={data.actionConfig?.headers ? JSON.stringify(data.actionConfig.headers, null, 2) : ''}
              onChange={(e) => {
                try {
                  handleConfigChange({ headers: JSON.parse(e.target.value) });
                } catch {
                  // Invalid JSON, don't update
                }
              }}
              style={{ resize: 'vertical', fontFamily: 'monospace' }}
            />
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Payload (JSON)</div>
            <textarea
              className="xsw-input"
              rows={3}
              placeholder='{"key": "{{field_name}}"}'
              value={data.actionConfig?.payload ? JSON.stringify(data.actionConfig.payload, null, 2) : ''}
              onChange={(e) => {
                try {
                  handleConfigChange({ payload: JSON.parse(e.target.value) });
                } catch {
                  // Invalid JSON, don't update
                }
              }}
              style={{ resize: 'vertical', fontFamily: 'monospace' }}
            />
          </div>
        </>
      )}

      {/* Run Method Config */}
      {data.actionType === 'run_method' && (
        <>
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Method Name</div>
            <input
              type="text"
              className="xsw-input"
              placeholder="e.g., calculate_total, send_reminder"
              value={data.actionConfig?.methodName || ''}
              onChange={(e) => handleConfigChange({ methodName: e.target.value })}
            />
            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
              The method must exist on the document class
            </p>
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Arguments (JSON)</div>
            <textarea
              className="xsw-input"
              rows={2}
              placeholder='{"arg1": "value"}'
              value={data.actionConfig?.args ? JSON.stringify(data.actionConfig.args, null, 2) : ''}
              onChange={(e) => {
                try {
                  handleConfigChange({ args: JSON.parse(e.target.value) });
                } catch {
                  // Invalid JSON, don't update
                }
              }}
              style={{ resize: 'vertical', fontFamily: 'monospace' }}
            />
          </div>
        </>
      )}
    </div>
  );
}

export const AutoActionPanel = memo(AutoActionPanelComponent);
