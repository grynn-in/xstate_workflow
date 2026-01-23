/**
 * Layout module for workflow graphs
 *
 * Provides ELK-based auto-layout for React Flow workflows
 */

import { Position } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';

export type LayoutDirection = 'TB' | 'LR' | 'RL' | 'BT';

export interface LayoutOptions {
  /** Layout direction: TB (top-bottom), LR (left-right), RL (right-left), BT (bottom-top) */
  direction: LayoutDirection;
  /** Spacing as [nodeToNode, betweenLayers] */
  spacing: [number, number];
}

export interface LayoutResult<N extends Node = Node, E extends Edge = Edge> {
  nodes: N[];
  edges: E[];
}

export type LayoutAlgorithm = <N extends Node = Node, E extends Edge = Edge>(
  nodes: N[],
  edges: E[],
  options: LayoutOptions
) => Promise<LayoutResult<N, E>>;

/**
 * Get the source handle position based on layout direction
 */
export function getSourceHandlePosition(direction: LayoutDirection): Position {
  switch (direction) {
    case 'TB':
      return Position.Bottom;
    case 'BT':
      return Position.Top;
    case 'LR':
      return Position.Right;
    case 'RL':
      return Position.Left;
    default:
      return Position.Right;
  }
}

/**
 * Get the target handle position based on layout direction
 */
export function getTargetHandlePosition(direction: LayoutDirection): Position {
  switch (direction) {
    case 'TB':
      return Position.Top;
    case 'BT':
      return Position.Bottom;
    case 'LR':
      return Position.Left;
    case 'RL':
      return Position.Right;
    default:
      return Position.Left;
  }
}

export { elkLayout } from './elk';
export { useAutoLayout } from './useAutoLayout';
