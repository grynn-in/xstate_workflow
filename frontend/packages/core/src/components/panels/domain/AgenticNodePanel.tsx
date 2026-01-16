import { memo, useCallback, useMemo, useState } from 'react';
import type { AgenticNodeData, AllowedMethod, CustomAgentEvent } from '../../../types';

// Validation result type
interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

// Test result type
interface TestResult {
  success: boolean;
  decision?: string;
  confidence?: number;
  reasoning?: string;
  iterations_used?: number;
  error?: string;
  duration_ms?: number;
}

// Validation function for agent configuration
function validateConfiguration(data: AgenticNodeData): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Required: System prompt
  if (!data.systemPrompt || data.systemPrompt.trim().length === 0) {
    errors.push('System prompt is required');
  } else if (data.systemPrompt.length < 20) {
    warnings.push('System prompt is very short - consider adding more detail');
  }

  // Check if any tools are enabled
  const enabledTools = data.enabledTools?.filter(t => t.enabled) || [];
  if (enabledTools.length === 0) {
    warnings.push('No tools enabled - agent will have limited capabilities');
  }

  // Check Frappe access vs tools
  if (data.frappeAccess === 'none') {
    const frappeTools = enabledTools.filter(t =>
      ['frappe_read', 'frappe_write', 'frappe_search', 'frappe_method'].includes(t.name)
    );
    if (frappeTools.length > 0) {
      errors.push('Frappe tools enabled but access level is "none"');
    }
  }

  // Check write tool without full_crud
  if (data.frappeAccess === 'read_only') {
    const hasWriteTool = enabledTools.some(t => t.name === 'frappe_write');
    if (hasWriteTool) {
      errors.push('Frappe Write tool enabled but access level is "read_only"');
    }
  }

  // Check decision routes for decision mode
  if (data.transitionMode === 'decision' || data.transitionMode === 'all') {
    if (!data.decisionRoutes || data.decisionRoutes.length === 0) {
      warnings.push('Decision mode enabled but no routes configured');
    } else {
      const emptyRoutes = data.decisionRoutes.filter(r => !r.condition?.trim());
      if (emptyRoutes.length > 0) {
        errors.push('Some decision routes have empty conditions');
      }
    }
  }

  // Check custom events
  if (data.transitionMode === 'custom_events' || data.transitionMode === 'all') {
    if (!data.customEvents || data.customEvents.length === 0) {
      warnings.push('Custom events mode enabled but no events configured');
    } else {
      const emptyEvents = data.customEvents.filter(e => !e.name?.trim());
      if (emptyEvents.length > 0) {
        errors.push('Some custom events have empty names');
      }
    }
  }

  // Check execution settings
  if (data.maxIterations && data.maxIterations < 1) {
    errors.push('Max iterations must be at least 1');
  }
  if (data.timeoutSeconds && data.timeoutSeconds < 10) {
    errors.push('Timeout must be at least 10 seconds');
  }

  // Check retry settings
  if (data.retryOnFailure && data.maxRetries && data.maxRetries < 1) {
    errors.push('Max retries must be at least 1 if retry is enabled');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

// Available tools registry
const AVAILABLE_TOOLS = [
  { name: 'frappe_read', label: 'Frappe Read', description: 'Read documents from Frappe' },
  { name: 'frappe_write', label: 'Frappe Write', description: 'Create/update documents' },
  { name: 'frappe_search', label: 'Frappe Search', description: 'Search across DocTypes' },
  { name: 'frappe_method', label: 'Frappe Method', description: 'Call whitelisted methods' },
  { name: 'web_search', label: 'Web Search', description: 'Search the web' },
  { name: 'calculator', label: 'Calculator', description: 'Perform calculations' },
  { name: 'code_executor', label: 'Code Executor', description: 'Execute Python code (sandboxed)' },
];

// Common whitelisted Frappe methods
const COMMON_FRAPPE_METHODS = [
  'frappe.client.get',
  'frappe.client.get_list',
  'frappe.client.get_count',
  'frappe.client.get_value',
  'frappe.client.set_value',
  'frappe.client.insert',
  'frappe.client.save',
  'frappe.client.delete',
  'frappe.client.submit',
  'frappe.client.cancel',
];

export interface AgenticNodePanelProps {
  data: AgenticNodeData;
  availableRoles?: string[];
  onDataChange: (data: Partial<AgenticNodeData>) => void;
  // Optional: for testing functionality
  testDoctype?: string;
  testDocname?: string;
  onTestAgent?: (config: AgenticNodeData) => Promise<TestResult>;
}

function AgenticNodePanelComponent({
  data,
  availableRoles = [],
  onDataChange,
  testDoctype,
  testDocname,
  onTestAgent,
}: AgenticNodePanelProps) {
  // Validation state
  const validation = useMemo(() => validateConfiguration(data), [data]);

  // Test state
  const [isTestingAgent, setIsTestingAgent] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  // Handle test agent button click
  const handleTestAgent = useCallback(async () => {
    if (!onTestAgent || !validation.isValid) return;

    setIsTestingAgent(true);
    setTestResult(null);

    try {
      const result = await onTestAgent(data);
      setTestResult(result);
    } catch (error) {
      setTestResult({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    } finally {
      setIsTestingAgent(false);
    }
  }, [data, onTestAgent, validation.isValid]);

  const handleToolToggle = useCallback((toolName: string, enabled: boolean) => {
    const tools = [...(data.enabledTools || [])];
    const idx = tools.findIndex(t => t.name === toolName);
    if (idx >= 0) {
      tools[idx] = { ...tools[idx], enabled };
    } else {
      tools.push({ name: toolName, enabled });
    }
    onDataChange({ enabledTools: tools });
  }, [data.enabledTools, onDataChange]);

  const handleAddAllowedMethod = useCallback(() => {
    const methods = [...(data.allowedMethods || [])];
    methods.push({ method: '', allowed_roles: [] });
    onDataChange({ allowedMethods: methods });
  }, [data.allowedMethods, onDataChange]);

  const handleMethodChange = useCallback((index: number, updates: Partial<AllowedMethod>) => {
    const methods = [...(data.allowedMethods || [])];
    methods[index] = { ...methods[index], ...updates };
    onDataChange({ allowedMethods: methods });
  }, [data.allowedMethods, onDataChange]);

  const handleRemoveMethod = useCallback((index: number) => {
    const methods = [...(data.allowedMethods || [])];
    methods.splice(index, 1);
    onDataChange({ allowedMethods: methods });
  }, [data.allowedMethods, onDataChange]);

  const handleAddDecisionRoute = useCallback(() => {
    const routes = [...(data.decisionRoutes || [])];
    routes.push({ condition: '' });
    onDataChange({ decisionRoutes: routes });
  }, [data.decisionRoutes, onDataChange]);

  const handleRouteChange = useCallback((index: number, condition: string) => {
    const routes = [...(data.decisionRoutes || [])];
    routes[index] = { ...routes[index], condition };
    onDataChange({ decisionRoutes: routes });
  }, [data.decisionRoutes, onDataChange]);

  const handleRemoveRoute = useCallback((index: number) => {
    const routes = [...(data.decisionRoutes || [])];
    routes.splice(index, 1);
    onDataChange({ decisionRoutes: routes });
  }, [data.decisionRoutes, onDataChange]);

  const handleAddCustomEvent = useCallback(() => {
    const events = [...(data.customEvents || [])];
    events.push({ name: '', description: '' });
    onDataChange({ customEvents: events });
  }, [data.customEvents, onDataChange]);

  const handleEventChange = useCallback((index: number, updates: Partial<CustomAgentEvent>) => {
    const events = [...(data.customEvents || [])];
    events[index] = { ...events[index], ...updates };
    onDataChange({ customEvents: events });
  }, [data.customEvents, onDataChange]);

  const handleRemoveEvent = useCallback((index: number) => {
    const events = [...(data.customEvents || [])];
    events.splice(index, 1);
    onDataChange({ customEvents: events });
  }, [data.customEvents, onDataChange]);

  return (
    <div className="xsw-domain-panel xsw-agentic-panel">
      <div className="xsw-panel-header">AI Agent Configuration</div>

      {/* Agent Type */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Agent Type</div>
        <select
          className="xsw-select"
          value={data.agentType || 'react'}
          onChange={(e) => onDataChange({ agentType: e.target.value as AgenticNodeData['agentType'] })}
        >
          <option value="react">ReAct Agent (Reasoning + Acting)</option>
          <option value="tool_executor">Tool Executor (Direct tool calls)</option>
          <option value="plan_execute">Plan & Execute (Multi-step planning)</option>
          <option value="custom">Custom Agent</option>
        </select>
      </div>

      {/* System Prompt */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">System Prompt</div>
        <textarea
          className="xsw-textarea"
          rows={4}
          placeholder="Instructions for the AI agent..."
          value={data.systemPrompt || ''}
          onChange={(e) => onDataChange({ systemPrompt: e.target.value })}
        />
      </div>

      {/* Model Selection */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Model</div>
        <select
          className="xsw-select"
          value={data.model || ''}
          onChange={(e) => onDataChange({ model: e.target.value || undefined })}
        >
          <option value="">Default (from settings)</option>
          <option value="gpt-4">GPT-4</option>
          <option value="gpt-4-turbo">GPT-4 Turbo</option>
          <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
          <option value="claude-3-opus">Claude 3 Opus</option>
          <option value="claude-3-sonnet">Claude 3 Sonnet</option>
          <option value="claude-3-haiku">Claude 3 Haiku</option>
        </select>
      </div>

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Tools */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Enabled Tools</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {AVAILABLE_TOOLS.map(tool => {
            const isEnabled = data.enabledTools?.find(t => t.name === tool.name)?.enabled || false;
            return (
              <label key={tool.name} className="xsw-checkbox">
                <input
                  type="checkbox"
                  checked={isEnabled}
                  onChange={(e) => handleToolToggle(tool.name, e.target.checked)}
                />
                <div>
                  <span style={{ fontWeight: 500 }}>{tool.label}</span>
                  <div style={{ fontSize: '11px', color: '#6b7280' }}>{tool.description}</div>
                </div>
              </label>
            );
          })}
        </div>
      </div>

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Frappe Access */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Frappe Access Level</div>
        <select
          className="xsw-select"
          value={data.frappeAccess || 'none'}
          onChange={(e) => onDataChange({ frappeAccess: e.target.value as AgenticNodeData['frappeAccess'] })}
        >
          <option value="none">No Access</option>
          <option value="read_only">Read Only</option>
          <option value="full_crud">Full CRUD</option>
        </select>
      </div>

      {/* Whitelisted Methods with Role Checks */}
      {data.frappeAccess && data.frappeAccess !== 'none' && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">
            Allowed Methods (Whitelisted)
            <span style={{ fontSize: '11px', color: '#6b7280', fontWeight: 'normal', display: 'block', marginTop: '2px' }}>
              Only these methods can be called by the agent
            </span>
          </div>

          {data.allowedMethods?.map((method, index) => (
            <div key={index} style={{
              padding: '8px',
              background: '#f8fafc',
              borderRadius: '4px',
              marginBottom: '8px',
              border: '1px solid #e2e8f0'
            }}>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                <select
                  className="xsw-select"
                  style={{ flex: 1 }}
                  value={COMMON_FRAPPE_METHODS.includes(method.method) ? method.method : '__custom__'}
                  onChange={(e) => {
                    if (e.target.value !== '__custom__') {
                      handleMethodChange(index, { method: e.target.value });
                    }
                  }}
                >
                  <option value="">Select method...</option>
                  {COMMON_FRAPPE_METHODS.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                  <option value="__custom__">Custom method...</option>
                </select>
                <button
                  className="xsw-button xsw-button-secondary"
                  style={{ padding: '4px 8px', minWidth: 'auto' }}
                  onClick={() => handleRemoveMethod(index)}
                >
                  x
                </button>
              </div>

              {!COMMON_FRAPPE_METHODS.includes(method.method) && method.method !== '' && (
                <input
                  type="text"
                  className="xsw-input"
                  placeholder="Full method path (e.g., myapp.api.my_method)"
                  style={{ marginBottom: '8px' }}
                  value={method.method}
                  onChange={(e) => handleMethodChange(index, { method: e.target.value })}
                />
              )}

              <div>
                <label style={{ fontSize: '11px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                  Allowed Roles (empty = all roles)
                </label>
                <select
                  className="xsw-select"
                  multiple
                  size={3}
                  value={method.allowed_roles || []}
                  onChange={(e) => {
                    const selected = Array.from(e.target.selectedOptions, opt => opt.value);
                    handleMethodChange(index, { allowed_roles: selected });
                  }}
                >
                  {availableRoles.map(role => (
                    <option key={role} value={role}>{role}</option>
                  ))}
                </select>
              </div>
            </div>
          ))}

          <button
            className="xsw-button xsw-button-secondary"
            style={{ width: '100%' }}
            onClick={handleAddAllowedMethod}
          >
            + Add Allowed Method
          </button>
        </div>
      )}

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Transition Mode */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Transition Mode</div>
        <select
          className="xsw-select"
          value={data.transitionMode || 'simple'}
          onChange={(e) => onDataChange({ transitionMode: e.target.value as AgenticNodeData['transitionMode'] })}
        >
          <option value="simple">Simple (Success/Failure)</option>
          <option value="decision">Decision-based Routing</option>
          <option value="custom_events">Custom Events</option>
          <option value="all">All Modes Combined</option>
        </select>
        <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
          {data.transitionMode === 'simple' && 'Agent completes with success or failure'}
          {data.transitionMode === 'decision' && 'Agent routes based on classification/decision'}
          {data.transitionMode === 'custom_events' && 'Agent emits named events for transitions'}
          {data.transitionMode === 'all' && 'All transition modes available'}
        </div>
      </div>

      {/* Decision Routes */}
      {(data.transitionMode === 'decision' || data.transitionMode === 'all') && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Decision Routes</div>
          {data.decisionRoutes?.map((route, index) => (
            <div key={index} style={{ display: 'flex', gap: '8px', marginBottom: '4px' }}>
              <input
                type="text"
                className="xsw-input"
                style={{ flex: 1 }}
                placeholder="Condition (e.g., approved, needs_review)"
                value={route.condition}
                onChange={(e) => handleRouteChange(index, e.target.value)}
              />
              <button
                className="xsw-button xsw-button-secondary"
                style={{ padding: '4px 8px', minWidth: 'auto' }}
                onClick={() => handleRemoveRoute(index)}
              >
                x
              </button>
            </div>
          ))}
          <button
            className="xsw-button xsw-button-secondary"
            style={{ width: '100%', marginTop: '4px' }}
            onClick={handleAddDecisionRoute}
          >
            + Add Route
          </button>
        </div>
      )}

      {/* Custom Events */}
      {(data.transitionMode === 'custom_events' || data.transitionMode === 'all') && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Custom Events</div>
          {data.customEvents?.map((event, index) => (
            <div key={index} style={{ marginBottom: '8px' }}>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '4px' }}>
                <input
                  type="text"
                  className="xsw-input"
                  style={{ flex: 1 }}
                  placeholder="Event name"
                  value={event.name}
                  onChange={(e) => handleEventChange(index, { name: e.target.value })}
                />
                <button
                  className="xsw-button xsw-button-secondary"
                  style={{ padding: '4px 8px', minWidth: 'auto' }}
                  onClick={() => handleRemoveEvent(index)}
                >
                  x
                </button>
              </div>
              <input
                type="text"
                className="xsw-input"
                placeholder="Description"
                value={event.description}
                onChange={(e) => handleEventChange(index, { description: e.target.value })}
              />
            </div>
          ))}
          <button
            className="xsw-button xsw-button-secondary"
            style={{ width: '100%', marginTop: '4px' }}
            onClick={handleAddCustomEvent}
          >
            + Add Custom Event
          </button>
        </div>
      )}

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Execution Settings */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Execution Settings</div>

        <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
          Max Iterations
        </label>
        <input
          type="number"
          className="xsw-input"
          min={1}
          max={100}
          value={data.maxIterations || 10}
          onChange={(e) => onDataChange({ maxIterations: parseInt(e.target.value, 10) || 10 })}
          style={{ marginBottom: '8px' }}
        />

        <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
          Timeout (seconds)
        </label>
        <input
          type="number"
          className="xsw-input"
          min={10}
          max={3600}
          value={data.timeoutSeconds || 300}
          onChange={(e) => onDataChange({ timeoutSeconds: parseInt(e.target.value, 10) || 300 })}
          style={{ marginBottom: '8px' }}
        />

        <label className="xsw-checkbox">
          <input
            type="checkbox"
            checked={data.retryOnFailure || false}
            onChange={(e) => onDataChange({ retryOnFailure: e.target.checked })}
          />
          <span>Retry on failure</span>
        </label>

        {data.retryOnFailure && (
          <div style={{ marginTop: '8px' }}>
            <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
              Max Retries
            </label>
            <input
              type="number"
              className="xsw-input"
              min={1}
              max={10}
              value={data.maxRetries || 3}
              onChange={(e) => onDataChange({ maxRetries: parseInt(e.target.value, 10) || 3 })}
            />
          </div>
        )}
      </div>

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
              ⚠ Errors
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
              ⚡ Warnings
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
            ✓ Configuration is valid
          </div>
        )}
      </div>

      {/* Test Agent Section */}
      {onTestAgent && (
        <>
          <div className="xsw-node-separator" style={{ margin: '16px 0' }} />
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Test Agent</div>

            {testDoctype && testDocname && (
              <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '8px' }}>
                Test document: {testDoctype}/{testDocname}
              </div>
            )}

            <button
              className="xsw-button xsw-button-primary"
              style={{ width: '100%' }}
              onClick={handleTestAgent}
              disabled={!validation.isValid || isTestingAgent}
            >
              {isTestingAgent ? 'Testing Agent...' : 'Test Agent'}
            </button>

            {!validation.isValid && (
              <div style={{ fontSize: '11px', color: '#dc2626', marginTop: '4px' }}>
                Fix validation errors before testing
              </div>
            )}

            {/* Test Results */}
            {testResult && (
              <div style={{
                marginTop: '12px',
                padding: '12px',
                background: testResult.success ? '#f0fdf4' : '#fef2f2',
                border: `1px solid ${testResult.success ? '#bbf7d0' : '#fecaca'}`,
                borderRadius: '4px',
              }}>
                <div style={{
                  fontWeight: 500,
                  marginBottom: '8px',
                  color: testResult.success ? '#15803d' : '#dc2626',
                }}>
                  {testResult.success ? '✓ Test Passed' : '✗ Test Failed'}
                </div>

                {testResult.error && (
                  <div style={{ fontSize: '11px', color: '#dc2626', marginBottom: '8px' }}>
                    <strong>Error:</strong> {testResult.error}
                  </div>
                )}

                {testResult.decision && (
                  <div style={{ fontSize: '12px', marginBottom: '4px' }}>
                    <strong>Decision:</strong> {testResult.decision}
                    {testResult.confidence !== undefined && (
                      <span style={{ color: '#6b7280' }}> ({Math.round(testResult.confidence * 100)}% confidence)</span>
                    )}
                  </div>
                )}

                {testResult.reasoning && (
                  <div style={{ fontSize: '11px', color: '#4b5563', marginBottom: '4px' }}>
                    <strong>Reasoning:</strong> {testResult.reasoning}
                  </div>
                )}

                {testResult.iterations_used !== undefined && (
                  <div style={{ fontSize: '11px', color: '#6b7280' }}>
                    Iterations: {testResult.iterations_used}
                  </div>
                )}

                {testResult.duration_ms !== undefined && (
                  <div style={{ fontSize: '11px', color: '#6b7280' }}>
                    Duration: {(testResult.duration_ms / 1000).toFixed(2)}s
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export const AgenticNodePanel = memo(AgenticNodePanelComponent);
