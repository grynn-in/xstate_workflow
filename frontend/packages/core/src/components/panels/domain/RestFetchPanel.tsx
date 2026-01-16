import { memo, useCallback, useState, useMemo } from 'react';
import type { RestFetchNodeData } from '../../../types';

// Validation result type
interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

// Validation function for REST fetch configuration
function validateConfiguration(data: RestFetchNodeData): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Required: URL
  if (!data.url || data.url.trim().length === 0) {
    errors.push('URL is required');
  } else if (!data.url.startsWith('http://') && !data.url.startsWith('https://') && !data.url.startsWith('{{')) {
    warnings.push('URL should start with http:// or https:// (or use {{variable}} template)');
  }

  // Required: Save response to
  if (!data.saveResponseTo || data.saveResponseTo.trim().length === 0) {
    errors.push('Context variable name is required to save response');
  }

  // Check auth configuration
  if (data.authType && data.authType !== 'none' && !data.authCredential) {
    errors.push('Auth credential is required when authentication is enabled');
  }

  // Check body for POST/PUT
  if ((data.method === 'POST' || data.method === 'PUT') && data.body) {
    try {
      // Check if it's valid JSON (unless it contains template variables)
      if (!data.body.includes('{{')) {
        JSON.parse(data.body);
      }
    } catch {
      warnings.push('Request body may not be valid JSON');
    }
  }

  // Timeout validation
  if (data.timeoutSeconds && data.timeoutSeconds < 1) {
    errors.push('Timeout must be at least 1 second');
  }
  if (data.timeoutSeconds && data.timeoutSeconds > 300) {
    warnings.push('Timeout is very long (> 5 minutes)');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export interface RestFetchPanelProps {
  data: RestFetchNodeData;
  doctypeFields?: string[];
  availableContextVars?: string[];
  onDataChange: (data: Partial<RestFetchNodeData>) => void;
}

function RestFetchPanelComponent({
  data,
  doctypeFields = [],
  availableContextVars = [],
  onDataChange,
}: RestFetchPanelProps) {
  // Validation state
  const validation = useMemo(() => validateConfiguration(data), [data]);

  // UI state for collapsible sections
  const [showHeaders, setShowHeaders] = useState(false);

  // Handle header changes
  const handleAddHeader = useCallback(() => {
    const headers = { ...(data.headers || {}) };
    const key = `Header-${Object.keys(headers).length + 1}`;
    headers[key] = '';
    onDataChange({ headers });
  }, [data.headers, onDataChange]);

  const handleHeaderChange = useCallback((oldKey: string, newKey: string, value: string) => {
    const headers = { ...(data.headers || {}) };
    if (oldKey !== newKey) {
      delete headers[oldKey];
    }
    headers[newKey] = value;
    onDataChange({ headers });
  }, [data.headers, onDataChange]);

  const handleRemoveHeader = useCallback((key: string) => {
    const headers = { ...(data.headers || {}) };
    delete headers[key];
    onDataChange({ headers });
  }, [data.headers, onDataChange]);

  // Available template variables for URL/body substitution
  const templateVars = useMemo(() => {
    const vars = new Set<string>();
    doctypeFields.forEach(f => vars.add(f));
    availableContextVars.forEach(v => vars.add(v));
    return Array.from(vars);
  }, [doctypeFields, availableContextVars]);

  return (
    <div className="xsw-domain-panel xsw-rest-fetch-panel">
      <div className="xsw-panel-header">REST Fetch Configuration</div>

      {/* URL */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">URL</div>
        <input
          type="text"
          className="xsw-input"
          placeholder="https://api.example.com/endpoint"
          value={data.url || ''}
          onChange={(e) => onDataChange({ url: e.target.value })}
        />
        <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
          Use {'{{field}}'} for template substitution (e.g., {'{{customer}}'})
        </div>
      </div>

      {/* Method */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">HTTP Method</div>
        <select
          className="xsw-select"
          value={data.method || 'GET'}
          onChange={(e) => onDataChange({ method: e.target.value as RestFetchNodeData['method'] })}
        >
          <option value="GET">GET</option>
          <option value="POST">POST</option>
          <option value="PUT">PUT</option>
        </select>
      </div>

      {/* Authentication */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Authentication</div>
        <select
          className="xsw-select"
          value={data.authType || 'none'}
          onChange={(e) => onDataChange({ authType: e.target.value as RestFetchNodeData['authType'] })}
          style={{ marginBottom: '8px' }}
        >
          <option value="none">No Authentication</option>
          <option value="api_key">API Key (Header)</option>
          <option value="bearer">Bearer Token</option>
          <option value="basic">Basic Auth</option>
        </select>

        {data.authType && data.authType !== 'none' && (
          <input
            type="text"
            className="xsw-input"
            placeholder={
              data.authType === 'api_key' ? 'API Key value or config:key_name' :
              data.authType === 'bearer' ? 'Bearer token or config:token_name' :
              'username:password or config:cred_name'
            }
            value={data.authCredential || ''}
            onChange={(e) => onDataChange({ authCredential: e.target.value })}
          />
        )}
        {data.authType && data.authType !== 'none' && (
          <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
            Use 'config:key_name' to reference credentials from Site Config
          </div>
        )}
      </div>

      {/* Headers (collapsible) */}
      <div className="xsw-panel-section">
        <div
          className="xsw-panel-section-title"
          style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
          onClick={() => setShowHeaders(!showHeaders)}
        >
          <span>Custom Headers</span>
          <span style={{ fontSize: '12px' }}>{showHeaders ? '▼' : '▶'}</span>
        </div>

        {showHeaders && (
          <div style={{ marginTop: '8px' }}>
            {Object.entries(data.headers || {}).map(([key, value]) => (
              <div key={key} style={{ display: 'flex', gap: '4px', marginBottom: '4px' }}>
                <input
                  type="text"
                  className="xsw-input"
                  placeholder="Header name"
                  value={key}
                  onChange={(e) => handleHeaderChange(key, e.target.value, value)}
                  style={{ flex: 1 }}
                />
                <input
                  type="text"
                  className="xsw-input"
                  placeholder="Value"
                  value={value}
                  onChange={(e) => handleHeaderChange(key, key, e.target.value)}
                  style={{ flex: 2 }}
                />
                <button
                  className="xsw-button xsw-button-secondary"
                  style={{ padding: '4px 8px', minWidth: 'auto' }}
                  onClick={() => handleRemoveHeader(key)}
                >
                  ×
                </button>
              </div>
            ))}
            <button
              className="xsw-button xsw-button-secondary"
              style={{ width: '100%', marginTop: '4px' }}
              onClick={handleAddHeader}
            >
              + Add Header
            </button>
          </div>
        )}
      </div>

      {/* Request Body (for POST/PUT) */}
      {(data.method === 'POST' || data.method === 'PUT') && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Request Body (JSON)</div>
          <textarea
            className="xsw-textarea"
            rows={4}
            placeholder='{"key": "{{field}}"}'
            value={data.body || ''}
            onChange={(e) => onDataChange({ body: e.target.value })}
            style={{ fontFamily: 'monospace', fontSize: '12px' }}
          />
          <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
            Use {'{{field}}'} for template substitution
          </div>
        </div>
      )}

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Response Handling */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Save Response To</div>
        <input
          type="text"
          className="xsw-input"
          placeholder="context_variable_name"
          value={data.saveResponseTo || ''}
          onChange={(e) => onDataChange({ saveResponseTo: e.target.value })}
        />
        <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
          Response will be stored in workflow context under this key
        </div>
      </div>

      {/* Timeout */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Timeout (seconds)</div>
        <input
          type="number"
          className="xsw-input"
          min={1}
          max={300}
          value={data.timeoutSeconds || 30}
          onChange={(e) => onDataChange({ timeoutSeconds: parseInt(e.target.value, 10) || 30 })}
        />
      </div>

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Transition Events */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Success Event</div>
        <input
          type="text"
          className="xsw-input"
          placeholder="REST_SUCCESS"
          value={data.onSuccess || ''}
          onChange={(e) => onDataChange({ onSuccess: e.target.value })}
        />
        <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
          Event triggered on successful API response
        </div>
      </div>

      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Error Event</div>
        <input
          type="text"
          className="xsw-input"
          placeholder="REST_ERROR"
          value={data.onError || ''}
          onChange={(e) => onDataChange({ onError: e.target.value })}
        />
        <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
          Event triggered on API error or timeout
        </div>
      </div>

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Available Template Variables */}
      {templateVars.length > 0 && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Available Template Variables</div>
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '4px',
            fontSize: '11px',
            maxHeight: '100px',
            overflowY: 'auto',
          }}>
            {templateVars.map(v => (
              <span
                key={v}
                style={{
                  background: '#e2e8f0',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
                title={`Click to copy {{${v}}}`}
                onClick={() => navigator.clipboard?.writeText(`{{${v}}}`)}
              >
                {`{{${v}}}`}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Validation Section */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Configuration Status</div>

        {/* Errors */}
        {validation.errors.length > 0 && (
          <div style={{
            padding: '8px',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '4px',
            marginBottom: '8px',
          }}>
            <div style={{ fontWeight: 500, color: '#dc2626', marginBottom: '4px', fontSize: '12px' }}>
              Errors
            </div>
            <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '11px', color: '#b91c1c' }}>
              {validation.errors.map((error, idx) => (
                <li key={idx}>{error}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Warnings */}
        {validation.warnings.length > 0 && (
          <div style={{
            padding: '8px',
            background: '#fffbeb',
            border: '1px solid #fed7aa',
            borderRadius: '4px',
            marginBottom: '8px',
          }}>
            <div style={{ fontWeight: 500, color: '#d97706', marginBottom: '4px', fontSize: '12px' }}>
              Warnings
            </div>
            <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '11px', color: '#b45309' }}>
              {validation.warnings.map((warning, idx) => (
                <li key={idx}>{warning}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Valid indicator */}
        {validation.isValid && validation.warnings.length === 0 && (
          <div style={{
            padding: '8px',
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
            borderRadius: '4px',
            fontSize: '12px',
            color: '#15803d',
          }}>
            Configuration is valid
          </div>
        )}
      </div>
    </div>
  );
}

export const RestFetchPanel = memo(RestFetchPanelComponent);
