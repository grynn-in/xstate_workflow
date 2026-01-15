import { memo, CSSProperties } from 'react';
import { useViewport } from '@xyflow/react';
import type { HorizontalLine, VerticalLine } from '../hooks/useHelperLines';

/**
 * Props for HelperLines component
 */
export interface HelperLinesProps {
  /** Horizontal alignment lines */
  horizontalLines: HorizontalLine[];
  /** Vertical alignment lines */
  verticalLines: VerticalLine[];
  /** Line color (default: #0041d0) */
  color?: string;
  /** Line width in pixels (default: 1) */
  strokeWidth?: number;
  /** Line dash pattern (default: '5,5') */
  strokeDasharray?: string;
}

/**
 * Component for rendering alignment helper lines in the workflow canvas.
 *
 * Must be rendered inside a ReactFlow component to access viewport.
 * Lines are rendered in flow coordinates and transform with zoom/pan.
 *
 * @example
 * ```tsx
 * <ReactFlow ...>
 *   <HelperLines
 *     horizontalLines={horizontalLines}
 *     verticalLines={verticalLines}
 *   />
 * </ReactFlow>
 * ```
 */
export const HelperLines = memo(function HelperLines({
  horizontalLines,
  verticalLines,
  color = '#0041d0',
  strokeWidth = 1,
  strokeDasharray = '5,5',
}: HelperLinesProps) {
  const { x, y, zoom } = useViewport();

  if (horizontalLines.length === 0 && verticalLines.length === 0) {
    return null;
  }

  // Transform style to apply viewport transformation
  const transformStyle: CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    zIndex: 1000,
    transform: `translate(${x}px, ${y}px) scale(${zoom})`,
    transformOrigin: '0 0',
  };

  return (
    <svg className="xsw-helper-lines" style={transformStyle}>
      {/* Horizontal lines */}
      {horizontalLines.map((line, index) => (
        <line
          key={`h-${line.type}-${index}`}
          x1={line.x1}
          y1={line.y}
          x2={line.x2}
          y2={line.y}
          stroke={color}
          strokeWidth={strokeWidth / zoom}
          strokeDasharray={strokeDasharray}
        />
      ))}

      {/* Vertical lines */}
      {verticalLines.map((line, index) => (
        <line
          key={`v-${line.type}-${index}`}
          x1={line.x}
          y1={line.y1}
          x2={line.x}
          y2={line.y2}
          stroke={color}
          strokeWidth={strokeWidth / zoom}
          strokeDasharray={strokeDasharray}
        />
      ))}
    </svg>
  );
});
