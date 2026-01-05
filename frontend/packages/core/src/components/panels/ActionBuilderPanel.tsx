import { memo, useState, useCallback } from 'react';
import type { ActionConfig } from '../../types';

export interface ActionBuilderPanelProps {
  actions: string[];
  actionType: 'entry' | 'exit' | 'transition';
  availableActions?: ActionConfig[];
  onActionsChange: (actions: string[]) => void;
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
  onActionsChange,
  onClose,
}: ActionBuilderPanelProps) {
  const [selectedActions, setSelectedActions] = useState<string[]>(actions);
  const [category, setCategory] = useState<ActionCategory>('builtin');
  const [newActionName, setNewActionName] = useState('');
  const [newActionDescription, setNewActionDescription] = useState('');

  const allActions = [...BUILTIN_ACTIONS, ...availableActions];

  const handleAddAction = useCallback((actionName: string) => {
    if (!selectedActions.includes(actionName)) {
      setSelectedActions([...selectedActions, actionName]);
    }
  }, [selectedActions]);

  const handleRemoveAction = useCallback((actionName: string) => {
    setSelectedActions(selectedActions.filter(a => a !== actionName));
  }, [selectedActions]);

  const handleAddCustomAction = useCallback(() => {
    if (newActionName && !selectedActions.includes(newActionName)) {
      setSelectedActions([...selectedActions, newActionName]);
      setNewActionName('');
      setNewActionDescription('');
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
    }
  }, [selectedActions]);

  const handleMoveDown = useCallback((index: number) => {
    if (index < selectedActions.length - 1) {
      const newActions = [...selectedActions];
      [newActions[index], newActions[index + 1]] = [newActions[index + 1], newActions[index]];
      setSelectedActions(newActions);
    }
  }, [selectedActions]);

  const getCategoryLabel = (cat: ActionCategory): string => {
    switch (cat) {
      case 'builtin': return 'Built-in';
      case 'python': return 'Python';
      case 'webhook': return 'Webhook';
      default: return cat;
    }
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {selectedActions.map((actionName, index) => {
              const actionInfo = allActions.find(a => a.name === actionName);
              return (
                <div
                  key={actionName}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px',
                    background: '#f9fafb',
                    borderRadius: '4px',
                  }}
                >
                  <span style={{ flex: 1 }}>
                    <span className="xsw-badge xsw-badge-action">{actionName}</span>
                    {actionInfo?.description && (
                      <span style={{ fontSize: '11px', color: '#6b7280', marginLeft: '8px' }}>
                        {actionInfo.description}
                      </span>
                    )}
                  </span>
                  <div style={{ display: 'flex', gap: '2px' }}>
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
                      onClick={() => handleRemoveAction(actionName)}
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
                {selectedActions.includes(action.name) ? (
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
            <textarea
              className="xsw-input"
              rows={2}
              value={newActionDescription}
              onChange={(e) => setNewActionDescription(e.target.value)}
              placeholder="Description (optional)"
              style={{ marginBottom: '8px', resize: 'vertical' }}
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
