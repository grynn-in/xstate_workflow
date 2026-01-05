import { AtomicStateNode } from './AtomicStateNode';
import { CompoundStateNode } from './CompoundStateNode';
import { ParallelStateNode } from './ParallelStateNode';
import { HistoryStateNode } from './HistoryStateNode';
import { FinalStateNode } from './FinalStateNode';

export { BaseStateNode, type BaseStateNodeProps } from './BaseStateNode';
export { AtomicStateNode } from './AtomicStateNode';
export { CompoundStateNode } from './CompoundStateNode';
export { ParallelStateNode } from './ParallelStateNode';
export { HistoryStateNode } from './HistoryStateNode';
export { FinalStateNode } from './FinalStateNode';

// Node type mapping for React Flow registration
export const nodeTypes = {
  atomic: AtomicStateNode,
  compound: CompoundStateNode,
  parallel: ParallelStateNode,
  history: HistoryStateNode,
  final: FinalStateNode,
} as const;

export type NodeTypeKey = keyof typeof nodeTypes;
