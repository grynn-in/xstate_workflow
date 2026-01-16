import { memo, useState, useCallback, useEffect } from 'react';
import type {
  WorkflowNode,
  WorkflowEdge,
  FrappeField,
  GuardConfig,
  ApprovalNodeData,
  ParallelApprovalNodeData,
  ThresholdGateNodeData,
  AutoActionNodeData,
  ClassificationBranchNodeData,
  AgenticNodeData,
  RestFetchNodeData,
} from '../../types';
import { GuardBuilderPanel } from './GuardBuilderPanel';
import { ActionBuilderPanel } from './ActionBuilderPanel';
import { TriggerConfigPanel } from './TriggerConfigPanel';
import { ApprovalNodePanel } from './domain/ApprovalNodePanel';
import { ParallelApprovalPanel } from './domain/ParallelApprovalPanel';
import { ThresholdGatePanel } from './domain/ThresholdGatePanel';
import { AutoActionPanel } from './domain/AutoActionPanel';
import { ClassificationBranchPanel } from './domain/ClassificationBranchPanel';
import { AgenticNodePanel, type MCPConnectionInfo } from './domain/AgenticNodePanel';
import { RestFetchPanel } from './domain/RestFetchPanel';

export interface PropertiesPanelProps {
  selectedNode?: WorkflowNode;
  selectedEdge?: WorkflowEdge;
  doctypeFields?: FrappeField[];
  availableRoles?: string[];
  availableDoctypes?: string[];
  availableUsers?: Array<{ name: string; full_name: string }>;
  // Agentic node specific props
  availableMcpConnections?: MCPConnectionInfo[];
  availableContextVars?: string[];
  onNodeChange?: (nodeId: string, data: Partial<WorkflowNode['data']>) => void;
  onEdgeChange?: (edgeId: string, data: Partial<WorkflowEdge['data']>) => void;
  onFetchDoctypeFields?: (doctype: string) => Promise<FrappeField[]>;
}

type PanelMode = 'properties' | 'guard' | 'entry-actions' | 'exit-actions' | 'transition-actions' | 'trigger';

function PropertiesPanelComponent({
  selectedNode,
  selectedEdge,
  doctypeFields = [],
  availableRoles = ['System Manager', 'Administrator'],
  availableDoctypes = [],
  availableUsers = [],
  availableMcpConnections = [],
  availableContextVars = [],
  onNodeChange,
  onEdgeChange,
  onFetchDoctypeFields,
}: PropertiesPanelProps) {
  const [panelMode, setPanelMode] = useState<PanelMode>('properties');

  // Reset panel mode when selection changes
  useEffect(() => {
    setPanelMode('properties');
  }, [selectedNode?.id, selectedEdge?.id]);

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
    // Check if this is a domain node
    const domainType = (selectedNode.data as { domainType?: string }).domainType;

    // Handler for domain node data changes
    const handleDomainDataChange = (data: Partial<WorkflowNode['data']>) => {
      onNodeChange?.(selectedNode.id, data);
    };

    // Render domain-specific panels
    if (domainType) {
      return (
        <div className="xsw-panel" style={{ overflow: 'auto' }}>
          {/* Common label section for all domain nodes */}
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Label</div>
            <input
              type="text"
              className="xsw-input"
              value={selectedNode.data.label}
              onChange={(e) => onNodeChange?.(selectedNode.id, { label: e.target.value })}
            />
          </div>

          {/* Domain-specific panel */}
          {domainType === 'approval' && (
            <ApprovalNodePanel
              data={selectedNode.data as ApprovalNodeData}
              doctypeFields={doctypeFields}
              availableRoles={availableRoles}
              availableDoctypes={availableDoctypes}
              availableUsers={availableUsers}
              onDataChange={handleDomainDataChange}
              onFetchDoctypeFields={onFetchDoctypeFields}
            />
          )}

          {domainType === 'parallel_approval' && (
            <ParallelApprovalPanel
              data={selectedNode.data as ParallelApprovalNodeData}
              doctypeFields={doctypeFields}
              availableRoles={availableRoles}
              availableDoctypes={availableDoctypes}
              availableUsers={availableUsers}
              onDataChange={handleDomainDataChange}
              onFetchDoctypeFields={onFetchDoctypeFields}
            />
          )}

          {domainType === 'threshold_gate' && (
            <ThresholdGatePanel
              data={selectedNode.data as ThresholdGateNodeData}
              doctypeFields={doctypeFields}
              onDataChange={handleDomainDataChange}
            />
          )}

          {domainType === 'auto_action' && (
            <AutoActionPanel
              data={selectedNode.data as AutoActionNodeData}
              doctypeFields={doctypeFields}
              onDataChange={handleDomainDataChange}
            />
          )}

          {domainType === 'classification_branch' && (
            <ClassificationBranchPanel
              data={selectedNode.data as ClassificationBranchNodeData}
              doctypeFields={doctypeFields}
              onDataChange={handleDomainDataChange}
            />
          )}

          {domainType === 'agentic' && (
            <AgenticNodePanel
              data={selectedNode.data as AgenticNodeData}
              availableRoles={availableRoles}
              availableDocFields={doctypeFields.map(f => f.fieldname)}
              availableContextVars={availableContextVars}
              availableMcpConnections={availableMcpConnections}
              onDataChange={handleDomainDataChange}
            />
          )}

          {domainType === 'rest_fetch' && (
            <RestFetchPanel
              data={selectedNode.data as RestFetchNodeData}
              doctypeFields={doctypeFields.map(f => f.fieldname)}
              availableContextVars={availableContextVars}
              onDataChange={handleDomainDataChange}
            />
          )}

          {/* Start and End nodes just need label */}
          {(domainType === 'start' || domainType === 'end') && (
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
          )}
        </div>
      );
    }

    // Default XState node properties panel
    return (
      <div className="xsw-panel">
        <div className="xsw-panel-header">
          State Properties
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title" title="Display name shown on the state node in the diagram">Label</div>
          <input
            type="text"
            className="xsw-input"
            title="The name displayed on this state in the workflow diagram"
            value={selectedNode.data.label}
            onChange={(e) => onNodeChange?.(selectedNode.id, { label: e.target.value })}
          />
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title" title="Optional notes about this state's purpose (not shown in diagram)">Description</div>
          <textarea
            className="xsw-input"
            rows={2}
            placeholder="Optional description..."
            title="Add notes to document what this state represents"
            value={selectedNode.data.description || ''}
            onChange={(e) => onNodeChange?.(selectedNode.id, { description: e.target.value })}
            style={{ resize: 'vertical' }}
          />
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title" title="Atomic: Simple state. Compound: Contains child states. Parallel: Multiple active regions. Final: End state. History: Remembers previous state.">State Type</div>
          <select
            className="xsw-select"
            title="Choose the type of state node"
            value={selectedNode.data.xstateType}
            onChange={(e) => onNodeChange?.(selectedNode.id, {
              xstateType: e.target.value as WorkflowNode['data']['xstateType'],
            })}
          >
            <option value="atomic" title="A simple state with no child states">Atomic</option>
            <option value="compound" title="A state that contains nested child states">Compound</option>
            <option value="parallel" title="A state with multiple active regions running in parallel">Parallel</option>
            <option value="history" title="Remembers and returns to the previous state">History</option>
            <option value="final" title="An end state that completes the workflow">Final</option>
          </select>
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title" title="Python functions that run when entering this state (e.g., send_email, update_field)">Entry Actions</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '8px' }}>
            {selectedNode.data.entryActions?.length ? (
              selectedNode.data.entryActions.map((action, i) => (
                <span key={i} className="xsw-badge xsw-badge-entry">
                  {typeof action === 'string' ? action : action.name}
                </span>
              ))
            ) : (
              <span style={{ color: '#9ca3af', fontSize: '14px' }}>None</span>
            )}
          </div>
          <button
            className="xsw-button xsw-button-secondary"
            style={{ width: '100%' }}
            title="Add Python functions to execute when workflow enters this state"
            onClick={() => setPanelMode('entry-actions')}
          >
            Configure Entry Actions
          </button>
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title" title="Python functions that run when leaving this state">Exit Actions</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '8px' }}>
            {selectedNode.data.exitActions?.length ? (
              selectedNode.data.exitActions.map((action, i) => (
                <span key={i} className="xsw-badge xsw-badge-exit">
                  {typeof action === 'string' ? action : action.name}
                </span>
              ))
            ) : (
              <span style={{ color: '#9ca3af', fontSize: '14px' }}>None</span>
            )}
          </div>
          <button
            className="xsw-button xsw-button-secondary"
            style={{ width: '100%' }}
            title="Add Python functions to execute when workflow exits this state"
            onClick={() => setPanelMode('exit-actions')}
          >
            Configure Exit Actions
          </button>
        </div>

        {selectedNode.data.xstateType === 'history' && (
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title" title="Shallow: Remember only immediate child state. Deep: Remember entire nested state hierarchy.">History Type</div>
            <select
              className="xsw-select"
              title="How deep should the history state remember?"
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
          <label className="xsw-checkbox" title="Check this to make this the starting state. Every workflow needs exactly one initial state.">
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
          <div className="xsw-panel-section-title" title="Event: Triggered by a named event. Delayed: Auto-triggers after time. Always: Triggers immediately.">Transition Type</div>
          <select
            className="xsw-select"
            title="How this transition is triggered"
            value={selectedEdge.data.transitionType}
            onChange={(e) => onEdgeChange?.(selectedEdge.id, {
              transitionType: e.target.value as WorkflowEdge['data']['transitionType'],
            })}
          >
            <option value="event" title="Transition occurs when a specific event is triggered">Event</option>
            <option value="delayed" title="Transition occurs automatically after a delay">Delayed (after)</option>
            <option value="always" title="Transition occurs immediately when entering the source state">Always</option>
          </select>
        </div>

        {selectedEdge.data.transitionType === 'event' && (
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title" title="The event name that triggers this transition. Use UPPERCASE by convention.">Event Name</div>
            <input
              type="text"
              className="xsw-input"
              title="Use UPPERCASE names like SUBMIT, APPROVE, REJECT"
              value={selectedEdge.data.event || ''}
              placeholder="e.g., SUBMIT, APPROVE"
              onChange={(e) => onEdgeChange?.(selectedEdge.id, { event: e.target.value })}
            />
          </div>
        )}

        {selectedEdge.data.transitionType === 'delayed' && (
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title" title="Time to wait before auto-transitioning to the target state">Delay</div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="number"
                className="xsw-input"
                style={{ flex: 1 }}
                title="Amount of time to wait"
                value={selectedEdge.data.delay || 0}
                onChange={(e) => onEdgeChange?.(selectedEdge.id, { delay: parseInt(e.target.value, 10) })}
              />
              <select
                className="xsw-select"
                style={{ width: '100px' }}
                title="Time unit for the delay"
                value={selectedEdge.data.delayUnit || 'ms'}
                onChange={(e) => onEdgeChange?.(selectedEdge.id, {
                  delayUnit: e.target.value as WorkflowEdge['data']['delayUnit'],
                })}
              >
                <option value="ms">ms</option>
                <option value="seconds">sec</option>
                <option value="minutes">min</option>
                <option value="hours">hours</option>
                <option value="days">days</option>
              </select>
            </div>
            <label className="xsw-checkbox" style={{ marginTop: '8px' }} title="Only count working hours (Mon-Fri, 9 AM - 6 PM). Weekends and holidays are excluded from the delay calculation.">
              <input
                type="checkbox"
                checked={selectedEdge.data.businessHoursOnly || false}
                onChange={(e) => onEdgeChange?.(selectedEdge.id, { businessHoursOnly: e.target.checked })}
              />
              <span>Business hours only</span>
            </label>
          </div>
        )}

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title" title="A condition that must be true for this transition to occur. Use guards to create conditional branching.">Guard Condition</div>
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
            title="Add a condition that must be true for this transition to occur"
            onClick={() => setPanelMode('guard')}
          >
            Configure Guard
          </button>
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title" title="Python functions to run during this transition (e.g., log_transition, notify_user)">Transition Actions</div>
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
            title="Add Python functions to execute when this transition occurs"
            onClick={() => setPanelMode('transition-actions')}
          >
            Configure Actions
          </button>
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title" title="Configure how users can trigger this transition: buttons, automatic events, or delayed timers">Trigger</div>
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
            title="Set up buttons, auto-triggers, or delayed triggers for this transition"
            onClick={() => setPanelMode('trigger')}
          >
            Configure Triggers
          </button>
        </div>

        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title" title="Visually separate overlapping edges by offsetting this edge's path">Path Offset</div>
          <p style={{ color: '#6b7280', fontSize: '12px', marginBottom: '8px' }}>
            Adjust to move overlapping edges apart
          </p>
          <input
            type="range"
            min="-100"
            max="100"
            step="5"
            title="Drag to offset this edge's visual path"
            value={selectedEdge.data.pathOffset || 0}
            onChange={(e) => onEdgeChange?.(selectedEdge.id, { pathOffset: parseInt(e.target.value, 10) })}
            style={{ width: '100%' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#9ca3af' }}>
            <span>-100</span>
            <span>{selectedEdge.data.pathOffset || 0}px</span>
            <span>100</span>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

export const PropertiesPanel = memo(PropertiesPanelComponent);
