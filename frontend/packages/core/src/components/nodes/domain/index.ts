import { StartNode } from './StartNode';
import { EndNode } from './EndNode';
import { ApprovalNode } from './ApprovalNode';
import { ThresholdGateNode } from './ThresholdGateNode';
import { ClassificationBranchNode } from './ClassificationBranchNode';
import { AutoActionNode } from './AutoActionNode';

export { StartNode } from './StartNode';
export { EndNode } from './EndNode';
export { ApprovalNode } from './ApprovalNode';
export { ThresholdGateNode } from './ThresholdGateNode';
export { ClassificationBranchNode } from './ClassificationBranchNode';
export { AutoActionNode } from './AutoActionNode';

// Domain node type mapping for React Flow registration
export const domainNodeTypes = {
  start: StartNode,
  end: EndNode,
  approval: ApprovalNode,
  threshold_gate: ThresholdGateNode,
  classification_branch: ClassificationBranchNode,
  auto_action: AutoActionNode,
} as const;

export type DomainNodeTypeKey = keyof typeof domainNodeTypes;
