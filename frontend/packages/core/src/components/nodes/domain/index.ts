import { StartNode } from './StartNode';
import { EndNode } from './EndNode';
import { ApprovalNode } from './ApprovalNode';
import { ParallelApprovalNode } from './ParallelApprovalNode';
import { ThresholdGateNode } from './ThresholdGateNode';
import { ClassificationBranchNode } from './ClassificationBranchNode';
import { AutoActionNode } from './AutoActionNode';
import { AgenticNode } from './AgenticNode';
import { RestFetchNode } from './RestFetchNode';

export { StartNode } from './StartNode';
export { EndNode } from './EndNode';
export { ApprovalNode } from './ApprovalNode';
export { ParallelApprovalNode } from './ParallelApprovalNode';
export { ThresholdGateNode } from './ThresholdGateNode';
export { ClassificationBranchNode } from './ClassificationBranchNode';
export { AutoActionNode } from './AutoActionNode';
export { AgenticNode } from './AgenticNode';
export { RestFetchNode } from './RestFetchNode';

// Domain node type mapping for React Flow registration
export const domainNodeTypes = {
  start: StartNode,
  end: EndNode,
  approval: ApprovalNode,
  parallel_approval: ParallelApprovalNode,
  threshold_gate: ThresholdGateNode,
  classification_branch: ClassificationBranchNode,
  auto_action: AutoActionNode,
  agentic: AgenticNode,
  rest_fetch: RestFetchNode,
} as const;

export type DomainNodeTypeKey = keyof typeof domainNodeTypes;
