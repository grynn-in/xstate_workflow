import { memo, useId } from 'react';
import {
  BaseEdge,
  getSmoothStepPath,
  type Position,
} from '@xyflow/react';
import { clsx } from 'clsx';
import type { WorkflowEdgeData } from '@xstate-workflow/core';

/**
 * Extended edge data with runtime state properties and animation support
 */
export interface RuntimeEdgeDataV2 extends WorkflowEdgeData {
  /** Edge originates from the current state */
  isFromCurrentState?: boolean;
  /** Edge can be triggered (event is available and enabled) */
  isAvailableTransition?: boolean;
  /** Edge was used in transition history */
  isVisitedTransition?: boolean;
  /** Edge would be available but is blocked by guard */
  isDisabledTransition?: boolean;
  /** Edge is currently animating (transition in progress) */
  isAnimating?: boolean;
  /** Animation progress (0-1) for custom rendering */
  animationProgress?: number;
  /** Sequence number for path highlighting */
  sequenceNumber?: number;
}

export interface TransitionEdgeV2Props {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourcePosition: Position;
  targetPosition: Position;
  data?: RuntimeEdgeDataV2;
  selected?: boolean;
  markerEnd?: string;
}

function TransitionEdgeV2Component({
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
}: TransitionEdgeV2Props) {
  const uniqueId = useId();
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

  // Runtime state props
  const isFromCurrentState = data?.isFromCurrentState;
  const isAvailableTransition = data?.isAvailableTransition;
  const isVisitedTransition = data?.isVisitedTransition;
  const isDisabledTransition = data?.isDisabledTransition;
  const isAnimating = data?.isAnimating;
  const sequenceNumber = data?.sequenceNumber;

  // Determine stroke dash array based on transition type and runtime state
  const getStrokeDasharray = () => {
    // Animating edges get special dash pattern
    if (isAnimating) {
      return '5 5';
    }
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
    if (isAnimating) return '#22c55e'; // Green for animating
    if (selected) return '#2490ef';
    if (isAvailableTransition) return '#3b82f6'; // Blue for available
    if (isVisitedTransition) return '#22c55e'; // Green for visited
    if (isDisabledTransition) return '#9ca3af'; // Light gray for disabled
    return '#374151'; // Default
  };

  // Determine stroke width based on runtime state
  const getStrokeWidth = () => {
    if (isAnimating) return 3;
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

  const strokeColor = getStrokeColor();
  const animationId = `flow-animation-${uniqueId}`;

  return (
    <>
      {/* Glow filter for animating edges */}
      <defs>
        <filter id={`glow-${uniqueId}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Background path (for glow effect on animation) */}
      {isAnimating && (
        <path
          d={edgePath}
          fill="none"
          stroke="#22c55e"
          strokeWidth={6}
          strokeOpacity={0.3}
          filter={`url(#glow-${uniqueId})`}
          className="xsw-edge-glow"
        />
      )}

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
          isDisabledTransition && 'xsw-edge-disabled',
          // V2 animation classes
          isAnimating && 'xsw-edge-animating'
        )}
        style={{
          strokeDasharray: getStrokeDasharray(),
          stroke: strokeColor,
          strokeWidth: getStrokeWidth(),
          opacity: getOpacity(),
        }}
      />

      {/* Animated traveling dot */}
      {isAnimating && (
        <circle
          r={6}
          fill="#22c55e"
          className="xsw-edge-dot xsw-animating"
          filter={`url(#glow-${uniqueId})`}
        >
          <animateMotion
            dur="0.8s"
            repeatCount="1"
            fill="freeze"
            path={edgePath}
            id={animationId}
          />
        </circle>
      )}

      {/* Sequence number badge for path highlighting */}
      {typeof sequenceNumber === 'number' && sequenceNumber > 0 && (
        <g transform={`translate(${labelX - 30}, ${labelY - 10})`}>
          <rect
            x={0}
            y={0}
            width={20}
            height={20}
            rx={10}
            className="xsw-edge-sequence-bg"
            fill="#22c55e"
          />
          <text
            x={10}
            y={14}
            textAnchor="middle"
            className="xsw-edge-sequence"
            fill="white"
            fontSize={11}
            fontWeight={600}
          >
            {sequenceNumber}
          </text>
        </g>
      )}

      {/* Edge labels removed - events shown in source node handles instead */}
    </>
  );
}

export const TransitionEdgeV2 = memo(TransitionEdgeV2Component);
