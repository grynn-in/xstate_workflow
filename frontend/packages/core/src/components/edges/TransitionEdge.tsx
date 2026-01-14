import { memo } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type Position,
} from '@xyflow/react';
import { clsx } from 'clsx';
import type { WorkflowEdgeData } from '../../types';

/**
 * Extended edge data with runtime state properties for instance viewer
 */
export interface RuntimeEdgeData extends WorkflowEdgeData {
  /** Edge originates from the current state */
  isFromCurrentState?: boolean;
  /** Edge can be triggered (event is available and enabled) */
  isAvailableTransition?: boolean;
  /** Edge was used in transition history */
  isVisitedTransition?: boolean;
  /** Edge would be available but is blocked by guard */
  isDisabledTransition?: boolean;
}

export interface TransitionEdgeProps {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourcePosition: Position;
  targetPosition: Position;
  data?: RuntimeEdgeData;
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
  // Use custom pathOffset if provided, otherwise default to 0
  const offset = data?.pathOffset ?? 0;

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 8,
    offset,
  });

  const transitionType = data?.transitionType || 'event';
  const hasGuard = !!data?.guard;
  const hasActions = (data?.actions?.length || 0) > 0;

  // Runtime state props
  const isFromCurrentState = data?.isFromCurrentState;
  const isAvailableTransition = data?.isAvailableTransition;
  const isVisitedTransition = data?.isVisitedTransition;
  const isDisabledTransition = data?.isDisabledTransition;

  // Determine stroke dash array based on transition type and runtime state
  const getStrokeDasharray = () => {
    // Available transitions get animated dashes
    if (isAvailableTransition) {
      return '8, 4';
    }
    switch (transitionType) {
      case 'delayed':
        return '5, 5';
      case 'always':
        return '2, 2';
      default:
        return undefined;
    }
  };

  // Determine stroke color based on runtime state
  const getStrokeColor = () => {
    if (selected) return '#2490ef';
    if (isAvailableTransition) return '#3b82f6'; // Blue for available
    if (isVisitedTransition) return '#6b7280'; // Gray for visited
    if (isDisabledTransition) return '#9ca3af'; // Light gray for disabled
    return '#374151'; // Default
  };

  // Determine stroke width based on runtime state
  const getStrokeWidth = () => {
    if (selected) return 3;
    if (isFromCurrentState || isAvailableTransition) return 2.5;
    if (isVisitedTransition) return 2.5;
    return 2;
  };

  // Determine opacity based on runtime state
  const getOpacity = () => {
    if (isDisabledTransition) return 0.4;
    return 1;
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
  const strokeColor = getStrokeColor();

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        className={clsx(
          'xsw-edge-path',
          transitionType,
          selected && 'selected',
          // Runtime state classes
          isFromCurrentState && 'xsw-edge-from-current',
          isAvailableTransition && 'xsw-edge-available',
          isVisitedTransition && 'xsw-edge-visited',
          isDisabledTransition && 'xsw-edge-disabled'
        )}
        style={{
          strokeDasharray: getStrokeDasharray(),
          stroke: strokeColor,
          strokeWidth: getStrokeWidth(),
          opacity: getOpacity(),
        }}
      />
      {labelText && (
        <EdgeLabelRenderer>
          <div
            className={clsx(
              'xsw-edge-label',
              isAvailableTransition && 'xsw-edge-label-available',
              isDisabledTransition && 'xsw-edge-label-disabled'
            )}
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
              opacity: getOpacity(),
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
