import { TransitionEdge } from './TransitionEdge';

export { TransitionEdge, type TransitionEdgeProps } from './TransitionEdge';

// Edge type mapping for React Flow registration
export const edgeTypes = {
  transition: TransitionEdge,
} as const;

export type EdgeTypeKey = keyof typeof edgeTypes;
