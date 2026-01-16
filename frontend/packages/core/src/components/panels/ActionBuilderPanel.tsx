import { memo, useState, useCallback } from 'react';
import type { ActionConfig, ConfiguredAction, FrappeField } from '../../types';

// Helper to normalize action to ConfiguredAction
function normalizeAction(action: string | ConfiguredAction): ConfiguredAction {
  if (typeof action === 'string') {
    return { name: action };
  }
  return action;
}

// Helper to get action name
function getActionName(action: string | ConfiguredAction): string {
  return typeof action === 'string' ? action : action.name;
}

export interface ActionBuilderPanelProps {
  actions: Array<string | ConfiguredAction>;
  actionType: 'entry' | 'exit' | 'transition';
  availableActions?: ActionConfig[];
  doctypeFields?: FrappeField[];
  onActionsChange: (actions: Array<string | ConfiguredAction>) => void;
  onClose: () => void;
}

type ActionCategory = 'builtin' | 'python' | 'webhook';

const BUILTIN_ACTIONS: ActionConfig[] = [
  {
    name: 'set_field',
    type: 'transition',
    category: 'builtin',
    description: 'Set a document field value',
    params: { field: '', value: '' },
  },
  {
    name: 'notify_user',
    type: 'transition',
    category: 'builtin',
    description: 'Send notification to a user',
    params: { user: '', message: '' },
  },
  {
    name: 'send_email',
    type: 'transition',
    category: 'builtin',
    description: 'Send email notification',
    params: { recipients: '', subject: '', message: '' },
  },
  {
    name: 'log_activity',
    type: 'transition',
    category: 'builtin',
    description: 'Log activity to timeline',
    params: { message: '' },
  },
  {
    name: 'assign_to',
    type: 'transition',
    category: 'builtin',
    description: 'Assign document to user',
    params: { user: '' },
  },
  {
    name: 'update_status',
    type: 'transition',
    category: 'builtin',
    description: 'Update document status field',
    params: { status: '' },
  },
];

function ActionBuilderPanelComponent({
  actions,
  actionType,
  availableActions = [],
  doctypeFields = [],
  onActionsChange,
  onClose,
}: ActionBuilderPanelProps) {
  // Normalize all actions to ConfiguredAction format
  const [selectedActions, setSelectedActions] = useState<ConfiguredAction[]>(
    actions.map(normalizeAction)
  );
  const [category, setCategory] = useState<ActionCategory>('builtin');
  const [newActionName, setNewActionName] = useState('');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const allActions = [...BUILTIN_ACTIONS, ...availableActions];

  const handleAddAction = useCallback((actionName: string) => {
    if (!selectedActions.find(a => a.name === actionName)) {
      const actionDef = allActions.find(a => a.name === actionName);
      // Initialize with default params if defined
      const newAction: ConfiguredAction = {
        name: actionName,
        params: actionDef?.params ? { ...actionDef.params } : undefined,
      };
      setSelectedActions([...selectedActions, newAction]);
      // Auto-open params editor for actions that need configuration
      if (actionDef?.params && Object.keys(actionDef.params).length > 0) {
        setEditingIndex(selectedActions.length);
      }
    }
  }, [selectedActions, allActions]);

  const handleRemoveAction = useCallback((index: number) => {
    const newActions = [...selectedActions];
    newActions.splice(index, 1);
    setSelectedActions(newActions);
    if (editingIndex === index) {
      setEditingIndex(null);
    } else if (editingIndex !== null && editingIndex > index) {
      setEditingIndex(editingIndex - 1);
    }
  }, [selectedActions, editingIndex]);

  const handleAddCustomAction = useCallback(() => {
    if (newActionName && !selectedActions.find(a => a.name === newActionName)) {
      setSelectedActions([...selectedActions, { name: newActionName }]);
      setNewActionName('');
    }
  }, [newActionName, selectedActions]);

  const handleSave = useCallback(() => {
    onActionsChange(selectedActions);
    onClose();
  }, [selectedActions, onActionsChange, onClose]);

  const handleMoveUp = useCallback((index: number) => {
    if (index > 0) {
      const newActions = [...selectedActions];
      [newActions[index - 1], newActions[index]] = [newActions[index], newActions[index - 1]];
      setSelectedActions(newActions);
      if (editingIndex === index) setEditingIndex(index - 1);
      else if (editingIndex === index - 1) setEditingIndex(index);
    }
  }, [selectedActions, editingIndex]);

  const handleMoveDown = useCallback((index: number) => {
    if (index < selectedActions.length - 1) {
      const newActions = [...selectedActions];
      [newActions[index], newActions[index + 1]] = [newActions[index + 1], newActions[index]];
      setSelectedActions(newActions);
      if (editingIndex === index) setEditingIndex(index + 1);
      else if (editingIndex === index + 1) setEditingIndex(index);
    }
  }, [selectedActions, editingIndex]);

  const handleParamChange = useCallback((index: number, paramName: string, value: unknown) => {
    const newActions = [...selectedActions];
    newActions[index] = {
      ...newActions[index],
      params: {
        ...newActions[index].params,
        [paramName]: value,
      },
    };
    setSelectedActions(newActions);
  }, [selectedActions]);

  const getCategoryLabel = (cat: ActionCategory): string => {
    switch (cat) {
      case 'builtin': return 'Built-in';
      case 'python': return 'Python';
      case 'webhook': return 'Webhook';
      default: return cat;
    }
  };

  const renderParamsEditor = (action: ConfiguredAction, index: number) => {
    const actionDef = allActions.find(a => a.name === action.name);
    if (!actionDef?.params || Object.keys(actionDef.params).length === 0) {
      return <p style={{ color: '#6b7280', fontSize: '12px', fontStyle: 'italic' }}>No parameters required</p>;
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {/* set_field action */}
        {action.name === 'set_field' && (
          <>
            <div>
              <label style={{ fontSize: '12px', color: '#374151', display: 'block', marginBottom: '4px' }}>
                Field to Update
              </label>
              <select
                className="xsw-select"
                value={(action.params?.field as string) || ''}
                onChange={(e) => handleParamChange(index, 'field', e.target.value)}
              >
                <option value="">Select field...</option>
                {doctypeFields.map(f => (
                  <option key={f.fieldname} value={f.fieldname}>
                    {f.label} ({f.fieldname})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#374151', display: 'block', marginBottom: '4px' }}>
                Value <span style={{ color: '#6b7280' }}>(use {'{{doc.field}}'} for dynamic values)</span>
              </label>
              <input
                className="xsw-input"
                placeholder="Value or {{context.variable}}"
                value={(action.params?.value as string) || ''}
                onChange={(e) => handleParamChange(index, 'value', e.target.value)}
              />
            </div>
          </>
        )}

        {/* send_email action */}
        {action.name === 'send_email' && (
          <>
            <div>
              <label style={{ fontSize: '12px', color: '#374151', display: 'block', marginBottom: '4px' }}>
                Recipients <span style={{ color: '#6b7280' }}>(comma-separated or {'{{doc.owner}}'})</span>
              </label>
              <input
                className="xsw-input"
                placeholder="email@example.com or {{doc.owner}}"
                value={(action.params?.recipients as string) || ''}
                onChange={(e) => handleParamChange(index, 'recipients', e.target.value)}
              />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#374151', display: 'block', marginBottom: '4px' }}>
                Subject
              </label>
              <input
                className="xsw-input"
                placeholder="Email subject"
                value={(action.params?.subject as string) || ''}
                onChange={(e) => handleParamChange(index, 'subject', e.target.value)}
              />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#374151', display: 'block', marginBottom: '4px' }}>
                Message
              </label>
              <textarea
                className="xsw-input"
                rows={3}
                placeholder="Email body - supports {{variables}}"
                value={(action.params?.message as string) || ''}
                onChange={(e) => handleParamChange(index, 'message', e.target.value)}
                style={{ resize: 'vertical' }}
              />
            </div>
          </>
        )}

        {/* notify_user action */}
        {action.name === 'notify_user' && (
          <>
            <div>
              <label style={{ fontSize: '12px', color: '#374151', display: 'block', marginBottom: '4px' }}>
                User <span style={{ color: '#6b7280' }}>(email or {'{{doc.owner}}'})</span>
              </label>
              <input
                className="xsw-input"
                placeholder="user@example.com or {{doc.owner}}"
                value={(action.params?.user as string) || ''}
                onChange={(e) => handleParamChange(index, 'user', e.target.value)}
              />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#374151', display: 'block', marginBottom: '4px' }}>
                Message
              </label>
              <textarea
                className="xsw-input"
                rows={2}
                placeholder="Notification message"
                value={(action.params?.message as string) || ''}
                onChange={(e) => handleParamChange(index, 'message', e.target.value)}
                style={{ resize: 'vertical' }}
              />
            </div>
          </>
        )}

        {/* update_status action */}
        {action.name === 'update_status' && (
          <div>
            <label style={{ fontSize: '12px', color: '#374151', display: 'block', marginBottom: '4px' }}>
              New Status Value
            </label>
            <input
              className="xsw-input"
              placeholder="e.g., Approved, Rejected, Completed"
              value={(action.params?.status as string) || ''}
              onChange={(e) => handleParamChange(index, 'status', e.target.value)}
            />
          </div>
        )}

        {/* assign_to action */}
        {action.name === 'assign_to' && (
          <div>
            <label style={{ fontSize: '12px', color: '#374151', display: 'block', marginBottom: '4px' }}>
              Assign To <span style={{ color: '#6b7280' }}>(email or {'{{doc.owner}}'})</span>
            </label>
            <input
              className="xsw-input"
              placeholder="user@example.com or {{doc.owner}}"
              value={(action.params?.user as string) || ''}
              onChange={(e) => handleParamChange(index, 'user', e.target.value)}
            />
          </div>
        )}

        {/* log_activity action */}
        {action.name === 'log_activity' && (
          <div>
            <label style={{ fontSize: '12px', color: '#374151', display: 'block', marginBottom: '4px' }}>
              Activity Message
            </label>
            <textarea
              className="xsw-input"
              rows={2}
              placeholder="Activity message - supports {{variables}}"
              value={(action.params?.message as string) || ''}
              onChange={(e) => handleParamChange(index, 'message', e.target.value)}
              style={{ resize: 'vertical' }}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="xsw-action-builder">
      <div className="xsw-panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{actionType.charAt(0).toUpperCase() + actionType.slice(1)} Actions</span>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px' }}
        >
          ×
        </button>
      </div>

      {/* Selected Actions */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Selected Actions ({selectedActions.length})</div>
        {selectedActions.length === 0 ? (
          <p style={{ color: '#9ca3af', fontSize: '14px' }}>No actions selected</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {selectedActions.map((action, index) => {
              const actionInfo = allActions.find(a => a.name === action.name);
              const isEditing = editingIndex === index;
              const hasParams = actionInfo?.params && Object.keys(actionInfo.params).length > 0;

              return (
                <div
                  key={`${action.name}-${index}`}
                  style={{
                    padding: '8px',
                    background: isEditing ? '#f0f9ff' : '#f9fafb',
                    borderRadius: '6px',
                    border: isEditing ? '1px solid #3b82f6' : '1px solid transparent',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ flex: 1 }}>
                      <span className="xsw-badge xsw-badge-action">{action.name}</span>
                      {actionInfo?.description && (
                        <span style={{ fontSize: '11px', color: '#6b7280', marginLeft: '8px' }}>
                          {actionInfo.description}
                        </span>
                      )}
                    </span>
                    <div style={{ display: 'flex', gap: '2px' }}>
                      {hasParams && (
                        <button
                          onClick={() => setEditingIndex(isEditing ? null : index)}
                          style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: isEditing ? '#3b82f6' : '#6b7280',
                            fontSize: '14px',
                          }}
                          title="Configure parameters"
                        >
                          ⚙
                        </button>
                      )}
                      <button
                        onClick={() => handleMoveUp(index)}
                        disabled={index === 0}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: index === 0 ? 'not-allowed' : 'pointer',
                          opacity: index === 0 ? 0.3 : 1,
                        }}
                      >
                        ↑
                      </button>
                      <button
                        onClick={() => handleMoveDown(index)}
                        disabled={index === selectedActions.length - 1}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: index === selectedActions.length - 1 ? 'not-allowed' : 'pointer',
                          opacity: index === selectedActions.length - 1 ? 0.3 : 1,
                        }}
                      >
                        ↓
                      </button>
                      <button
                        onClick={() => handleRemoveAction(index)}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: '#dc3545',
                        }}
                      >
                        ×
                      </button>
                    </div>
                  </div>

                  {/* Parameter Editor */}
                  {isEditing && (
                    <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #e5e7eb' }}>
                      {renderParamsEditor(action, index)}
                    </div>
                  )}

                  {/* Show configured params summary when not editing */}
                  {!isEditing && action.params && Object.keys(action.params).some(k => action.params![k]) && (
                    <div style={{ marginTop: '4px', fontSize: '11px', color: '#6b7280' }}>
                      {Object.entries(action.params)
                        .filter(([, v]) => v)
                        .map(([k, v]) => `${k}: ${String(v).substring(0, 20)}${String(v).length > 20 ? '...' : ''}`)
                        .join(' | ')}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Category Tabs */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Add Action</div>
        <div style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
          {(['builtin', 'python', 'webhook'] as ActionCategory[]).map((cat) => (
            <button
              key={cat}
              className={`xsw-button ${category === cat ? 'xsw-button-primary' : 'xsw-button-secondary'}`}
              style={{ flex: 1 }}
              onClick={() => setCategory(cat)}
            >
              {getCategoryLabel(cat)}
            </button>
          ))}
        </div>

        {/* Built-in Actions */}
        {category === 'builtin' && (
          <div style={{ maxHeight: '200px', overflow: 'auto' }}>
            {BUILTIN_ACTIONS.map((action) => (
              <div
                key={action.name}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px',
                  borderBottom: '1px solid #e5e7eb',
                  cursor: 'pointer',
                }}
                onClick={() => handleAddAction(action.name)}
              >
                <div>
                  <div style={{ fontWeight: 500 }}>{action.name}</div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>{action.description}</div>
                </div>
                {selectedActions.find(a => a.name === action.name) ? (
                  <span style={{ color: '#10b981' }}>✓</span>
                ) : (
                  <span style={{ color: '#9ca3af' }}>+</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Python Actions */}
        {category === 'python' && (
          <div>
            <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '12px' }}>
              Reference a Python function defined in XSM Action doctype
            </p>
            <input
              type="text"
              className="xsw-input"
              value={newActionName}
              onChange={(e) => setNewActionName(e.target.value)}
              placeholder="Function name (e.g., send_approval_email)"
              style={{ marginBottom: '8px' }}
            />
            <button
              className="xsw-button xsw-button-secondary"
              style={{ width: '100%' }}
              onClick={handleAddCustomAction}
              disabled={!newActionName}
            >
              Add Python Action
            </button>
          </div>
        )}

        {/* Webhook Actions */}
        {category === 'webhook' && (
          <div>
            <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '12px' }}>
              Call an external webhook URL when this action fires
            </p>
            <input
              type="text"
              className="xsw-input"
              value={newActionName}
              onChange={(e) => setNewActionName(e.target.value)}
              placeholder="Webhook name (e.g., notify_slack)"
              style={{ marginBottom: '8px' }}
            />
            <button
              className="xsw-button xsw-button-secondary"
              style={{ width: '100%' }}
              onClick={handleAddCustomAction}
              disabled={!newActionName}
            >
              Add Webhook Action
            </button>
          </div>
        )}
      </div>

      {/* Save */}
      <div className="xsw-panel-section" style={{ display: 'flex', gap: '8px' }}>
        <button
          className="xsw-button xsw-button-secondary"
          style={{ flex: 1 }}
          onClick={onClose}
        >
          Cancel
        </button>
        <button
          className="xsw-button xsw-button-primary"
          style={{ flex: 1 }}
          onClick={handleSave}
        >
          Save Actions
        </button>
      </div>
    </div>
  );
}

export const ActionBuilderPanel = memo(ActionBuilderPanelComponent);
