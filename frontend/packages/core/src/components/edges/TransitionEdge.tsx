import { memo, useCallback, useState } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  useReactFlow,
  useViewport,
  getSmoothStepPath,
  type Position,
} from '@xyflow/react';
import { clsx } from 'clsx';
import type { WorkflowEdgeData } from '../../types';
import { getEventColor } from '../../types';

export type EdgePathType = 'bezier' | 'smoothstep';

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
  /** Custom control point for edge path (user-draggable) */
  controlPoint?: { x: number; y: number };
  /** Edge path type: bezier (default, draggable) or smoothstep (orthogonal) */
  edgePathType?: EdgePathType;
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

/**
 * Create a quadratic bezier path with a control point
 */
function getQuadraticPath(
  sourceX: number,
  sourceY: number,
  targetX: number,
  targetY: number,
  controlX: number,
  controlY: number
): string {
  return `M ${sourceX} ${sourceY} Q ${controlX} ${controlY} ${targetX} ${targetY}`;
}

/**
 * Calculate default control point (midpoint with offset)
 */
function getDefaultControlPoint(
  sourceX: number,
  sourceY: number,
  targetX: number,
  targetY: number,
  offset: number = 0
): { x: number; y: number } {
  const midX = (sourceX + targetX) / 2;
  const midY = (sourceY + targetY) / 2;

  // Calculate perpendicular offset
  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;

  // Perpendicular direction (normalized)
  const perpX = -dy / len;
  const perpY = dx / len;

  // Add offset perpendicular to the line
  // Also add some natural curvature based on distance
  const naturalCurve = Math.min(50, len * 0.1);
  const totalOffset = offset * 30 + (offset !== 0 ? 0 : naturalCurve);

  return {
    x: midX + perpX * totalOffset,
    y: midY + perpY * totalOffset,
  };
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
  const { setEdges } = useReactFlow();
  const { zoom } = useViewport();
  const [isDragging, setIsDragging] = useState(false);

  // Edge path type: bezier (default) or smoothstep
  const edgePathType = data?.edgePathType ?? 'bezier';

  // Use custom pathOffset if provided
  const offset = data?.pathOffset ?? 0;

  // Get control point - use saved one or calculate default (for bezier)
  const defaultControl = getDefaultControlPoint(sourceX, sourceY, targetX, targetY, offset);
  const controlPoint = data?.controlPoint || defaultControl;

  // Create the path based on edge type
  let edgePath: string;
  let labelX: number;
  let labelY: number;

  if (edgePathType === 'smoothstep') {
    // Use React Flow's built-in smoothstep path
    const [path, labelXPos, labelYPos] = getSmoothStepPath({
      sourceX,
      sourceY,
      sourcePosition,
      targetX,
      targetY,
      targetPosition,
      borderRadius: 8,
    });
    edgePath = path;
    labelX = labelXPos;
    labelY = labelYPos;
  } else {
    // Use custom quadratic bezier path (default)
    edgePath = getQuadraticPath(
      sourceX,
      sourceY,
      targetX,
      targetY,
      controlPoint.x,
      controlPoint.y
    );
    // Label position (at the control point)
    labelX = controlPoint.x;
    labelY = controlPoint.y;
  }

  const transitionType = data?.transitionType || 'event';

  // Runtime state props
  const isFromCurrentState = data?.isFromCurrentState;
  const isAvailableTransition = data?.isAvailableTransition;
  const isVisitedTransition = data?.isVisitedTransition;
  const isDisabledTransition = data?.isDisabledTransition;

  // Handle control point drag
  const handleControlPointDrag = useCallback(
    (event: React.MouseEvent) => {
      event.stopPropagation();
      setIsDragging(true);

      const startX = event.clientX;
      const startY = event.clientY;
      const startControlX = controlPoint.x;
      const startControlY = controlPoint.y;
      // Capture zoom at drag start to ensure consistent movement
      const currentZoom = zoom;

      const handleMouseMove = (moveEvent: MouseEvent) => {
        // Convert screen delta to flow coordinates by dividing by zoom
        const deltaX = (moveEvent.clientX - startX) / currentZoom;
        const deltaY = (moveEvent.clientY - startY) / currentZoom;

        setEdges((edges) =>
          edges.map((edge) => {
            if (edge.id === id) {
              return {
                ...edge,
                data: {
                  ...edge.data,
                  controlPoint: {
                    x: startControlX + deltaX,
                    y: startControlY + deltaY,
                  },
                },
              };
            }
            return edge;
          })
        );
      };

      const handleMouseUp = () => {
        setIsDragging(false);
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [id, controlPoint, setEdges, zoom]
  );

  // Reset control point to default
  const handleResetControlPoint = useCallback(
    (event: React.MouseEvent) => {
      event.stopPropagation();
      setEdges((edges) =>
        edges.map((edge) => {
          if (edge.id === id) {
            return {
              ...edge,
              data: {
                ...edge.data,
                controlPoint: undefined, // Remove custom control point
              },
            };
          }
          return edge;
        })
      );
    },
    [id, setEdges]
  );

  // Determine stroke dash array based on transition type
  const getStrokeDasharray = () => {
    if (isAvailableTransition) return '8, 4';
    switch (transitionType) {
      case 'delayed':
        return '5, 5';
      case 'always':
        return '2, 2';
      default:
        return undefined;
    }
  };

  // Determine stroke color - uses event-based coloring when not in special state
  const getStrokeColor = () => {
    if (selected) return '#2490ef';
    if (isAvailableTransition) return '#3b82f6';
    if (isVisitedTransition) return '#6b7280';
    if (isDisabledTransition) return '#9ca3af';
    // Use event-based color for regular transitions
    if (transitionType === 'event' && data?.event) {
      return getEventColor(data.event);
    }
    return '#374151';
  };

  // Determine stroke width
  const getStrokeWidth = () => {
    if (selected) return 3;
    if (isFromCurrentState || isAvailableTransition) return 2.5;
    if (isVisitedTransition) return 2.5;
    return 2;
  };

  // Determine opacity
  const getOpacity = () => {
    if (isDisabledTransition) return 0.4;
    return 1;
  };

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

      {/* Draggable control point - only show when edge is selected and using bezier path */}
      {selected && edgePathType === 'bezier' && (
        <EdgeLabelRenderer>
          <div
            className="xsw-edge-control-point"
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${controlPoint.x}px, ${controlPoint.y}px)`,
              pointerEvents: 'all',
              cursor: isDragging ? 'grabbing' : 'grab',
            }}
            onMouseDown={handleControlPointDrag}
            onDoubleClick={handleResetControlPoint}
            title="Drag to adjust curve. Double-click to reset."
          >
            <div className="xsw-control-point-inner" />
          </div>
        </EdgeLabelRenderer>
      )}

      {/* Edge labels removed - events shown in source node handles instead */}
    </>
  );
}

export const TransitionEdge = memo(TransitionEdgeComponent);
