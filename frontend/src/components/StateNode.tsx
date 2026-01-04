// Custom State Node for React Flow

import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { StateNodeData } from '../types';

const stateTypeStyles: Record<string, React.CSSProperties> = {
  initial: {
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    borderColor: '#059669',
    color: 'white'
  },
  atomic: {
    background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    borderColor: '#2563eb',
    color: 'white'
  },
  compound: {
    background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
    borderColor: '#7c3aed',
    color: 'white'
  },
  parallel: {
    background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    borderColor: '#d97706',
    color: 'white'
  },
  final: {
    background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
    borderColor: '#dc2626',
    color: 'white'
  },
  history: {
    background: 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)',
    borderColor: '#4b5563',
    color: 'white'
  }
};

const stateTypeIcons: Record<string, string> = {
  initial: '▶',
  atomic: '●',
  compound: '◉',
  parallel: '≡',
  final: '◼',
  history: 'H'
};

function StateNode({ data, selected }: NodeProps<StateNodeData>) {
  const style = stateTypeStyles[data.stateType] || stateTypeStyles.atomic;
  const icon = stateTypeIcons[data.stateType] || '●';

  const hasEntryActions = data.entryActions && data.entryActions.length > 0;
  const hasExitActions = data.exitActions && data.exitActions.length > 0;

  return (
    <div
      className={`state-node ${selected ? 'selected' : ''}`}
      style={{
        ...style,
        padding: '12px 16px',
        borderRadius: data.stateType === 'final' ? '50%' : '8px',
        border: `2px solid ${style.borderColor}`,
        minWidth: data.stateType === 'final' ? '80px' : '140px',
        minHeight: data.stateType === 'final' ? '80px' : 'auto',
        boxShadow: selected
          ? '0 0 0 2px #fff, 0 0 0 4px #3b82f6'
          : '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        transition: 'box-shadow 0.2s, transform 0.2s',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      {/* Handles for connections */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: '#fff',
          border: '2px solid #6366f1',
          width: '10px',
          height: '10px'
        }}
      />

      {/* State icon and label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '14px', opacity: 0.8 }}>{icon}</span>
        <span style={{ fontWeight: 600, fontSize: '14px' }}>{data.label}</span>
      </div>

      {/* State type badge */}
      <div
        style={{
          fontSize: '10px',
          opacity: 0.7,
          marginTop: '4px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}
      >
        {data.stateType}
      </div>

      {/* Action indicators */}
      {(hasEntryActions || hasExitActions) && (
        <div
          style={{
            display: 'flex',
            gap: '6px',
            marginTop: '6px',
            fontSize: '10px'
          }}
        >
          {hasEntryActions && (
            <span
              title={`Entry: ${data.entryActions.join(', ')}`}
              style={{
                background: 'rgba(255,255,255,0.2)',
                padding: '2px 6px',
                borderRadius: '4px'
              }}
            >
              ⤵ {data.entryActions.length}
            </span>
          )}
          {hasExitActions && (
            <span
              title={`Exit: ${data.exitActions.join(', ')}`}
              style={{
                background: 'rgba(255,255,255,0.2)',
                padding: '2px 6px',
                borderRadius: '4px'
              }}
            >
              ⤴ {data.exitActions.length}
            </span>
          )}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: '#fff',
          border: '2px solid #6366f1',
          width: '10px',
          height: '10px'
        }}
      />
    </div>
  );
}

export default memo(StateNode);
