import { memo, useState, useCallback } from 'react';
import type { WorkflowNode, WorkflowEdge, FrappeField, GuardConfig } from '../../types';
import { GuardBuilderPanel } from './GuardBuilderPanel';
import { ActionBuilderPanel } from './ActionBuilderPanel';
import { TriggerConfigPanel } from './TriggerConfigPanel';

export interface PropertiesPanelProps {
  selectedNode?: WorkflowNode;
  selectedEdge?: WorkflowEdge;
  doctypeFields?: FrappeField[];
  availableRoles?: string[];
  onNodeChange?: (nodeId: string, data: Partial<WorkflowNode['data']>) => void;
  onEdgeChange?: (edgeId: string, data: Partial<WorkflowEdge['data']>) => void;
}

type PanelMode = 'properties' | 'guard' | 'entry-actions' | 'exit-actions' | 'transition-actions' | 'trigger';

function PropertiesPanelComponent({
  selectedNode,
  selectedEdge,
  doctypeFields = [],
  availableRoles = ['System Manager', 'Administrator'],
  onNodeChange,
  onEdgeChange,
}: PropertiesPanelProps) {
  const [panelMode, setPanelMode] = useState<PanelMode>('properties');

  const handleGuardChange = useCallback((guard: GuardConfig | undefined) => {
    if (selectedEdge) {
      onEdgeChange?.(selectedEdge.id, { guard });
    }
  }, [selectedEdge, onEdgeChange]);

  const handleEntryActionsChange = useCallback((actions: string[]) => {
    if (selectedNode) {
      onNodeChange?.(selectedNode.id, { entryActions: actions });
    }
  }, [selectedNode, onNodeChange]);

  const handleExitActionsChange = useCallback((actions: string[]) => {
    if (selectedNode) {
      onNodeChange?.(selectedNode.id, { exitActions: actions });
    }
  }, [selectedNode, onNodeChange]);

  const handleTransitionActionsChange = useCallback((actions: string[]) => {
    if (selectedEdge) {
      onEdgeChange?.(selectedEdge.id, { actions });
    }
  }, [selectedEdge, onEdgeChange]);

  const handleTriggerChange = useCallback((trigger: WorkflowEdge['data']['trigger']) => {
    if (selectedEdge) {
      onEdgeChange?.(selectedEdge.id, { trigger });
    }
  }, [selectedEdge, onEdgeChange]);

  const closePanelMode = useCallback(() => {
    setPanelMode('properties');
  }, []);

  // Show guard builder
  if (panelMode === 'guard' && selectedEdge) {
    return (
      <div className="xsw-panel">
        <GuardBuilderPanel
          guard={selectedEdge.data.guard}
          fields={doctypeFields}
          onGuardChange={handleGuardChange}
          onClose={closePanelMode}
        />
      </div>
    );
  }

  // Show entry actions builder
  if (panelMode === 'entry-actions' && selectedNode) {
    return (
      <div className="xsw-panel">
        <ActionBuilderPanel
          actions={selectedNode.data.entryActions || []}
          actionType="entry"
          onActionsChange={handleEntryActionsChange}
          onClose={closePanelMode}
        />
      </div>
    );
  }

  // Show exit actions builder
  if (panelMode === 'exit-actions' && selectedNode) {
    return (
      <div className="xsw-panel">
        <ActionBuilderPanel
          actions={selectedNode.data.exitActions || []}
          actionType="exit"
          onActionsChange={handleExitActionsChange}
          onClose={closePanelMode}
        />
      </div>
    );
  }

  // Show transition actions builder
  if (panelMode === 'transition-actions' && selectedEdge) {
    return (
      <div className="xsw-panel">
        <ActionBuilderPanel
          actions={selectedEdge.data.actions || []}
          actionType="transition"
          onActionsChange={handleTransitionActionsChange}
          onClose={closePanelMode}
        />
      </div>
    );
  }

  // Show trigger config
  if (panelMode === 'trigger' && selectedEdge) {
    return (
      <div className="xsw-panel">
        <TriggerConfigPanel
          trigger={selectedEdge.data.trigger}
          eventName={selectedEdge.data.event}
          availableRoles={availableRoles}
          onTriggerChange={handleTriggerChange}
          onClose={closePanelMode}
        />
      </div>
    );
  }

  // Default: show properties panel
  if (!selectedNode && !selectedEdge) {
    return (
      <div className="xsw-panel">
        <div className="xsw-panel-header">Properties</div>
        <div className="xsw-panel-section">
          <p style={{ color: '#6b7280', fontSize: '14px' }}>
            Select a state or transition to view its properties.
          </p>
        </div>
      </div>
    );
  }

  if (selectedNode) {
    return (
      <div className="xsw-panel">
        <div className="xsw-panel-header">
          State Properties
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Label</div>
          <input
            type="text"
            className="xsw-input"
            value={selectedNode.data.label}
            onChange={(e) => onNodeChange?.(selectedNode.id, { label: e.target.value })}
          />
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Description</div>
          <textarea
            className="xsw-input"
            rows={2}
            placeholder="Optional description..."
            value={selectedNode.data.description || ''}
            onChange={(e) => onNodeChange?.(selectedNode.id, { description: e.target.value })}
            style={{ resize: 'vertical' }}
          />
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">State Type</div>
          <select
            className="xsw-select"
            value={selectedNode.data.xstateType}
            onChange={(e) => onNodeChange?.(selectedNode.id, {
              xstateType: e.target.value as WorkflowNode['data']['xstateType'],
            })}
          >
            <option value="atomic">Atomic</option>
            <option value="compound">Compound</option>
            <option value="parallel">Parallel</option>
            <option value="history">History</option>
            <option value="final">Final</option>
          </select>
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Entry Actions</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '8px' }}>
            {selectedNode.data.entryActions?.length ? (
              selectedNode.data.entryActions.map((action, i) => (
                <span key={i} className="xsw-badge xsw-badge-entry">
                  {action}
                </span>
              ))
            ) : (
              <span style={{ color: '#9ca3af', fontSize: '14px' }}>None</span>
            )}
          </div>
          <button
            className="xsw-button xsw-button-secondary"
            style={{ width: '100%' }}
            onClick={() => setPanelMode('entry-actions')}
          >
            Configure Entry Actions
          </button>
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Exit Actions</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '8px' }}>
            {selectedNode.data.exitActions?.length ? (
              selectedNode.data.exitActions.map((action, i) => (
                <span key={i} className="xsw-badge xsw-badge-exit">
                  {action}
                </span>
              ))
            ) : (
              <span style={{ color: '#9ca3af', fontSize: '14px' }}>None</span>
            )}
          </div>
          <button
            className="xsw-button xsw-button-secondary"
            style={{ width: '100%' }}
            onClick={() => setPanelMode('exit-actions')}
          >
            Configure Exit Actions
          </button>
        </div>

        {selectedNode.data.xstateType === 'history' && (
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">History Type</div>
            <select
              className="xsw-select"
              value={selectedNode.data.historyType || 'shallow'}
              onChange={(e) => onNodeChange?.(selectedNode.id, {
                historyType: e.target.value as 'shallow' | 'deep',
              })}
            >
              <option value="shallow">Shallow</option>
              <option value="deep">Deep</option>
            </select>
          </div>
        )}

        <div className="xsw-panel-section">
          <label className="xsw-checkbox">
            <input
              type="checkbox"
              checked={selectedNode.data.isInitial || false}
              onChange={(e) => onNodeChange?.(selectedNode.id, { isInitial: e.target.checked })}
            />
            <span>Initial State</span>
          </label>
        </div>
      </div>
    );
  }

  if (selectedEdge) {
    // Guard against missing data
    if (!selectedEdge.data) {
      return <div className="xsw-panel"><div className="xsw-panel-header">Transition Properties</div></div>;
    }

    // Handle guard display - guard could be string (legacy) or object
    const guard = selectedEdge.data?.guard;
    let guardDisplay: string | null = null;
    if (guard) {
      if (typeof guard === 'string') {
        guardDisplay = guard;
      } else if (typeof guard === 'object' && guard.type) {
        guardDisplay = guard.type === 'python'
          ? guard.name
          : guard.type === 'simple'
            ? `${guard.field} ${guard.operator}`
            : 'Compound guard';
      } else if (typeof guard === 'object' && guard.name) {
        guardDisplay = guard.name;
      }
    }

    const hasTrigger = selectedEdge.data?.trigger?.button?.enabled ||
                       selectedEdge.data?.trigger?.auto?.enabled ||
                       selectedEdge.data?.trigger?.delayed?.enabled;

    return (
      <div className="xsw-panel">
        <div className="xsw-panel-header">
          Transition Properties
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Transition Type</div>
          <select
            className="xsw-select"
            value={selectedEdge.data.transitionType}
            onChange={(e) => onEdgeChange?.(selectedEdge.id, {
              transitionType: e.target.value as WorkflowEdge['data']['transitionType'],
            })}
          >
            <option value="event">Event</option>
            <option value="delayed">Delayed (after)</option>
            <option value="always">Always</option>
          </select>
        </div>

        {selectedEdge.data.transitionType === 'event' && (
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Event Name</div>
            <input
              type="text"
              className="xsw-input"
              value={selectedEdge.data.event || ''}
              placeholder="e.g., SUBMIT, APPROVE"
              onChange={(e) => onEdgeChange?.(selectedEdge.id, { event: e.target.value })}
            />
          </div>
        )}

        {selectedEdge.data.transitionType === 'delayed' && (
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Delay</div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="number"
                className="xsw-input"
                style={{ flex: 1 }}
                value={selectedEdge.data.delay || 0}
                onChange={(e) => onEdgeChange?.(selectedEdge.id, { delay: parseInt(e.target.value, 10) })}
              />
              <select
                className="xsw-select"
                style={{ width: '100px' }}
                value={selectedEdge.data.delayUnit || 'ms'}
                onChange={(e) => onEdgeChange?.(selectedEdge.id, {
                  delayUnit: e.target.value as WorkflowEdge['data']['delayUnit'],
                })}
              >
                <option value="ms">ms</option>
                <option value="seconds">sec</option>
                <option value="minutes">min</option>
                <option value="hours">hours</option>
              </select>
            </div>
          </div>
        )}

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Guard Condition</div>
          {guardDisplay ? (
            <div className="xsw-badge xsw-badge-guard" style={{ marginBottom: '8px' }}>
              🛡 {guardDisplay}
            </div>
          ) : (
            <span style={{ color: '#9ca3af', fontSize: '14px', display: 'block', marginBottom: '8px' }}>
              No guard
            </span>
          )}
          <button
            className="xsw-button xsw-button-secondary"
            style={{ width: '100%' }}
            onClick={() => setPanelMode('guard')}
          >
            Configure Guard
          </button>
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Transition Actions</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '8px' }}>
            {selectedEdge.data.actions?.length ? (
              selectedEdge.data.actions.map((action, i) => (
                <span key={i} className="xsw-badge xsw-badge-action">
                  {action}
                </span>
              ))
            ) : (
              <span style={{ color: '#9ca3af', fontSize: '14px' }}>None</span>
            )}
          </div>
          <button
            className="xsw-button xsw-button-secondary"
            style={{ width: '100%' }}
            onClick={() => setPanelMode('transition-actions')}
          >
            Configure Actions
          </button>
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Trigger</div>
          {hasTrigger ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '8px' }}>
              {selectedEdge.data.trigger?.button?.enabled && (
                <span className="xsw-badge" style={{ background: '#dbeafe', color: '#1d4ed8' }}>
                  🖱 Button: {selectedEdge.data.trigger.button.label}
                </span>
              )}
              {selectedEdge.data.trigger?.auto?.enabled && (
                <span className="xsw-badge" style={{ background: '#fef3c7', color: '#92400e' }}>
                  ⚡ Auto: {selectedEdge.data.trigger.auto.event}
                </span>
              )}
              {selectedEdge.data.trigger?.delayed?.enabled && (
                <span className="xsw-badge" style={{ background: '#f3e8ff', color: '#7c3aed' }}>
                  ⏱ Delayed: {selectedEdge.data.trigger.delayed.delay} {selectedEdge.data.trigger.delayed.unit}
                </span>
              )}
            </div>
          ) : (
            <span style={{ color: '#9ca3af', fontSize: '14px', display: 'block', marginBottom: '8px' }}>
              No triggers configured
            </span>
          )}
          <button
            className="xsw-button xsw-button-secondary"
            style={{ width: '100%' }}
            onClick={() => setPanelMode('trigger')}
          >
            Configure Triggers
          </button>
        </div>
      </div>
    );
  }

  return null;
}

export const PropertiesPanel = memo(PropertiesPanelComponent);
