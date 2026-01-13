import { AtomicStateNode } from './AtomicStateNode';
import { CompoundStateNode } from './CompoundStateNode';
import { ParallelStateNode } from './ParallelStateNode';
import { HistoryStateNode } from './HistoryStateNode';
import { FinalStateNode } from './FinalStateNode';

// Domain-specific nodes
import { domainNodeTypes } from './domain';

export { BaseStateNode, type BaseStateNodeProps } from './BaseStateNode';
export { AtomicStateNode } from './AtomicStateNode';
export { CompoundStateNode } from './CompoundStateNode';
export { ParallelStateNode } from './ParallelStateNode';
export { HistoryStateNode } from './HistoryStateNode';
export { FinalStateNode } from './FinalStateNode';

// Domain nodes exports
export * from './domain';

// XState node type mapping for React Flow registration
export const nodeTypes = {
  atomic: AtomicStateNode,
  compound: CompoundStateNode,
  parallel: ParallelStateNode,
  history: HistoryStateNode,
  final: FinalStateNode,
} as const;

// Combined node types (XState + Domain)
export const allNodeTypes = {
  ...nodeTypes,
  ...domainNodeTypes,
} as const;

export type NodeTypeKey = keyof typeof nodeTypes;
export type AllNodeTypeKey = keyof typeof allNodeTypes;
