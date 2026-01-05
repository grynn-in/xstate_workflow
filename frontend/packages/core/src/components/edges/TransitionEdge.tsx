import { memo } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type Position,
} from '@xyflow/react';
import { clsx } from 'clsx';
import type { WorkflowEdgeData } from '../../types';

export interface TransitionEdgeProps {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourcePosition: Position;
  targetPosition: Position;
  data?: WorkflowEdgeData;
  selected?: boolean;
  markerEnd?: string;
}

function TransitionEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  markerEnd,
}: TransitionEdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const transitionType = data?.transitionType || 'event';
  const hasGuard = !!data?.guard;
  const hasActions = (data?.actions?.length || 0) > 0;

  // Determine stroke dash array based on transition type
  const getStrokeDasharray = () => {
    switch (transitionType) {
      case 'delayed':
        return '5, 5';
      case 'always':
        return '2, 2';
      default:
        return undefined;
    }
  };

  // Build the label text
  const getLabelText = () => {
    if (transitionType === 'delayed' && data?.delay) {
      const unit = data.delayUnit || 'ms';
      return `after ${data.delay}${unit}`;
    }
    if (transitionType === 'always') {
      return 'always';
    }
    return data?.event || '';
  };

  const labelText = getLabelText();

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        className={clsx(
          'xsw-edge-path',
          transitionType,
          selected && 'selected'
        )}
        style={{
          strokeDasharray: getStrokeDasharray(),
          stroke: selected ? '#2490ef' : '#374151',
          strokeWidth: selected ? 3 : 2,
        }}
      />
      {labelText && (
        <EdgeLabelRenderer>
          <div
            className="xsw-edge-label"
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
          >
            <span className="xsw-edge-label-event">{labelText}</span>
            {(hasGuard || hasActions) && (
              <span className="xsw-edge-label-icons">
                {hasGuard && <span title="Has guard condition">🛡</span>}
                {hasActions && <span title="Has actions">⚡</span>}
              </span>
            )}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export const TransitionEdge = memo(TransitionEdgeComponent);
