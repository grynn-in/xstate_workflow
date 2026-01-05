// Properties panel for editing node/edge properties

import React, { useState, useEffect } from 'react';
import type { PropertiesPanelProps, StateType } from '../types';

const stateTypes: { value: StateType; label: string; description: string }[] = [
  { value: 'initial', label: 'Initial', description: 'Starting state (green)' },
  { value: 'atomic', label: 'Atomic', description: 'Simple state (blue)' },
  { value: 'compound', label: 'Compound', description: 'Contains child states (purple)' },
  { value: 'parallel', label: 'Parallel', description: 'Concurrent regions (orange)' },
  { value: 'final', label: 'Final', description: 'End state (red)' },
  { value: 'history', label: 'History', description: 'Remember previous state (gray)' }
];

export default function PropertiesPanel({
  selectedNode,
  selectedEdge,
  onNodeUpdate,
  onEdgeUpdate,
  onNodeDelete,
  onEdgeDelete,
  availableGuards,
  availableActions
}: PropertiesPanelProps) {
  const [localLabel, setLocalLabel] = useState('');
  const [localEvent, setLocalEvent] = useState('');
  const [localGuard, setLocalGuard] = useState('');
  const [localActions, setLocalActions] = useState<string[]>([]);
  const [localEntryActions, setLocalEntryActions] = useState<string[]>([]);
  const [localExitActions, setLocalExitActions] = useState<string[]>([]);

  // Sync local state with selected element
  useEffect(() => {
    if (selectedNode) {
      setLocalLabel(selectedNode.data.label || '');
      setLocalEntryActions(selectedNode.data.entryActions || []);
      setLocalExitActions(selectedNode.data.exitActions || []);
    }
  }, [selectedNode]);

  useEffect(() => {
    if (selectedEdge) {
      setLocalEvent(selectedEdge.data?.event || '');
      setLocalGuard(selectedEdge.data?.guard || '');
      setLocalActions(selectedEdge.data?.actions || []);
    }
  }, [selectedEdge]);

  if (!selectedNode && !selectedEdge) {
    return (
      <div
        style={{
          width: '280px',
          background: '#1e293b',
          borderLeft: '1px solid #334155',
          padding: '20px',
          color: '#94a3b8',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          height: '100%'
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.5 }}>👆</div>
        <p style={{ fontSize: '14px' }}>
          Select a state or transition to edit its properties
        </p>
      </div>
    );
  }

  // Node properties
  if (selectedNode) {
    return (
      <div
        style={{
          width: '280px',
          background: '#1e293b',
          borderLeft: '1px solid #334155',
          padding: '16px',
          overflowY: 'auto'
        }}
      >
        <h3 style={{ color: 'white', margin: '0 0 16px', fontSize: '16px' }}>
          State Properties
        </h3>

        {/* Label */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ color: '#94a3b8', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
            State Name (ID)
          </label>
          <input
            type="text"
            value={localLabel}
            onChange={(e) => setLocalLabel(e.target.value)}
            onBlur={() => onNodeUpdate(selectedNode.id, { label: localLabel })}
            style={{
              width: '100%',
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '4px',
              padding: '8px 10px',
              color: 'white',
              fontSize: '13px'
            }}
          />
        </div>

        {/* State Type */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ color: '#94a3b8', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
            State Type
          </label>
          <select
            value={selectedNode.data.stateType}
            onChange={(e) => onNodeUpdate(selectedNode.id, { stateType: e.target.value as StateType })}
            style={{
              width: '100%',
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '4px',
              padding: '8px 10px',
              color: 'white',
              fontSize: '13px'
            }}
          >
            {stateTypes.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label} - {type.description}
              </option>
            ))}
          </select>
        </div>

        {/* Entry Actions */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ color: '#94a3b8', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
            Entry Actions
          </label>
          <ActionList
            actions={localEntryActions}
            availableActions={availableActions.filter(a => a.type === 'entry' || a.type === 'transition')}
            onChange={(actions) => {
              setLocalEntryActions(actions);
              onNodeUpdate(selectedNode.id, { entryActions: actions });
            }}
          />
        </div>

        {/* Exit Actions */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ color: '#94a3b8', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
            Exit Actions
          </label>
          <ActionList
            actions={localExitActions}
            availableActions={availableActions.filter(a => a.type === 'exit' || a.type === 'transition')}
            onChange={(actions) => {
              setLocalExitActions(actions);
              onNodeUpdate(selectedNode.id, { exitActions: actions });
            }}
          />
        </div>

        {/* Delete button */}
        <button
          onClick={() => onNodeDelete(selectedNode.id)}
          style={{
            width: '100%',
            padding: '10px',
            background: '#dc2626',
            border: 'none',
            borderRadius: '4px',
            color: 'white',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer',
            marginTop: '16px'
          }}
        >
          🗑 Delete State
        </button>
      </div>
    );
  }

  // Edge properties
  if (selectedEdge) {
    return (
      <div
        style={{
          width: '280px',
          background: '#1e293b',
          borderLeft: '1px solid #334155',
          padding: '16px',
          overflowY: 'auto'
        }}
      >
        <h3 style={{ color: 'white', margin: '0 0 16px', fontSize: '16px' }}>
          Transition Properties
        </h3>

        {/* Source → Target */}
        <div style={{ marginBottom: '16px', color: '#94a3b8', fontSize: '12px' }}>
          {selectedEdge.source} → {selectedEdge.target}
        </div>

        {/* Event Name */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ color: '#94a3b8', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
            Event Name
          </label>
          <input
            type="text"
            value={localEvent}
            onChange={(e) => setLocalEvent(e.target.value)}
            onBlur={() => onEdgeUpdate(selectedEdge.id, { event: localEvent })}
            placeholder="e.g., SUBMIT, APPROVE"
            style={{
              width: '100%',
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '4px',
              padding: '8px 10px',
              color: 'white',
              fontSize: '13px',
              textTransform: 'uppercase'
            }}
          />
        </div>

        {/* Guard */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ color: '#94a3b8', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
            Guard (Condition)
          </label>
          <select
            value={localGuard}
            onChange={(e) => {
              setLocalGuard(e.target.value);
              onEdgeUpdate(selectedEdge.id, { guard: e.target.value || undefined });
            }}
            style={{
              width: '100%',
              background: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '4px',
              padding: '8px 10px',
              color: 'white',
              fontSize: '13px'
            }}
          >
            <option value="">No guard</option>
            {availableGuards.map((guard) => (
              <option key={guard.name} value={guard.name}>
                {guard.name} {guard.description ? `- ${guard.description}` : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Actions */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ color: '#94a3b8', fontSize: '12px', display: 'block', marginBottom: '6px' }}>
            Transition Actions
          </label>
          <ActionList
            actions={localActions}
            availableActions={availableActions.filter(a => a.type === 'transition')}
            onChange={(actions) => {
              setLocalActions(actions);
              onEdgeUpdate(selectedEdge.id, { actions });
            }}
          />
        </div>

        {/* Delete button */}
        <button
          onClick={() => onEdgeDelete(selectedEdge.id)}
          style={{
            width: '100%',
            padding: '10px',
            background: '#dc2626',
            border: 'none',
            borderRadius: '4px',
            color: 'white',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer',
            marginTop: '16px'
          }}
        >
          🗑 Delete Transition
        </button>
      </div>
    );
  }

  return null;
}

// Helper component for action lists
function ActionList({
  actions,
  availableActions,
  onChange
}: {
  actions: string[];
  availableActions: { name: string; description?: string }[];
  onChange: (actions: string[]) => void;
}) {
  const [newAction, setNewAction] = useState('');

  const addAction = () => {
    if (newAction && !actions.includes(newAction)) {
      onChange([...actions, newAction]);
      setNewAction('');
    }
  };

  const removeAction = (index: number) => {
    onChange(actions.filter((_, i) => i !== index));
  };

  return (
    <div>
      {/* Current actions */}
      {actions.length > 0 && (
        <div style={{ marginBottom: '8px' }}>
          {actions.map((action, index) => (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: '#0f172a',
                padding: '6px 10px',
                borderRadius: '4px',
                marginBottom: '4px'
              }}
            >
              <span style={{ color: '#e2e8f0', fontSize: '12px' }}>{action}</span>
              <button
                onClick={() => removeAction(index)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#ef4444',
                  cursor: 'pointer',
                  padding: '2px 6px',
                  fontSize: '14px'
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add new action */}
      <div style={{ display: 'flex', gap: '4px' }}>
        <select
          value={newAction}
          onChange={(e) => setNewAction(e.target.value)}
          style={{
            flex: 1,
            background: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '4px',
            padding: '6px 8px',
            color: 'white',
            fontSize: '12px'
          }}
        >
          <option value="">Select action...</option>
          {availableActions
            .filter((a) => !actions.includes(a.name))
            .map((action) => (
              <option key={action.name} value={action.name}>
                {action.name}
              </option>
            ))}
        </select>
        <button
          onClick={addAction}
          disabled={!newAction}
          style={{
            background: newAction ? '#10b981' : '#334155',
            border: 'none',
            borderRadius: '4px',
            color: 'white',
            padding: '6px 12px',
            cursor: newAction ? 'pointer' : 'not-allowed',
            fontSize: '12px'
          }}
        >
          Add
        </button>
      </div>
    </div>
  );
}
