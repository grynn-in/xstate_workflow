// Custom Transition Edge for React Flow

import React, { memo } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps
} from '@xyflow/react';
import type { TransitionEdgeData } from '../types';

function TransitionEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected
}: EdgeProps<TransitionEdgeData>) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition
  });

  const hasGuard = Boolean(data?.guard);
  const hasActions = (data?.actions?.length ?? 0) > 0;
  const eventName = data?.event || 'event';

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: selected ? '#6366f1' : '#94a3b8',
          strokeWidth: selected ? 3 : 2,
          transition: 'stroke 0.2s, stroke-width 0.2s'
        }}
        markerEnd="url(#arrow)"
      />

      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
            cursor: 'pointer'
          }}
          className="nodrag nopan"
        >
          <div
            style={{
              background: selected ? '#6366f1' : '#1e293b',
              color: 'white',
              padding: '4px 10px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 500,
              boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              border: selected ? '2px solid #818cf8' : 'none'
            }}
          >
            {/* Event name */}
            <span>{eventName}</span>

            {/* Guard indicator */}
            {hasGuard && (
              <span
                title={`Guard: ${data.guard}`}
                style={{
                  background: 'rgba(255,255,255,0.2)',
                  padding: '2px 4px',
                  borderRadius: '2px',
                  fontSize: '10px'
                }}
              >
                🛡
              </span>
            )}

            {/* Actions indicator */}
            {hasActions && (
              <span
                title={`Actions: ${data.actions?.join(', ')}`}
                style={{
                  background: 'rgba(255,255,255,0.2)',
                  padding: '2px 4px',
                  borderRadius: '2px',
                  fontSize: '10px'
                }}
              >
                ⚡{data.actions?.length}
              </span>
            )}

            {/* Conditional indicator */}
            {data?.isConditional && (
              <span
                title="Conditional transition"
                style={{
                  background: 'rgba(255,255,255,0.2)',
                  padding: '2px 4px',
                  borderRadius: '2px',
                  fontSize: '10px'
                }}
              >
                ?
              </span>
            )}
          </div>
        </div>
      </EdgeLabelRenderer>

      {/* Arrow marker definition */}
      <defs>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="10"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path
            d="M 0 0 L 10 5 L 0 10 z"
            fill={selected ? '#6366f1' : '#94a3b8'}
          />
        </marker>
      </defs>
    </>
  );
}

export default memo(TransitionEdge);
