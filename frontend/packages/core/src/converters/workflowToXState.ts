import type {
  WorkflowBuilderConfig,
  WorkflowNode,
  WorkflowEdge,
  XStateMachineConfig,
  XStateStateConfig,
  XStateTransition,
  GuardConfig,
  DomainNodeType,
  ApprovalNodeData,
  ParallelApprovalNodeData,
  ThresholdGateNodeData,
  ClassificationBranchNodeData,
  AutoActionNodeData,
  EndNodeData,
} from '../types';

// Domain node types that need special handling
const DOMAIN_NODE_TYPES: DomainNodeType[] = [
  'start',
  'threshold_gate',
  'classification_branch',
  'approval',
  'parallel_approval',
  'auto_action',
  'agentic',
  'rest_fetch',
  'end',
];

/**
 * Converts a WorkflowBuilder configuration to XState v5 JSON format
 */
export function workflowToXState(config: WorkflowBuilderConfig): XStateMachineConfig {
  const { id, nodes, edges, context } = config;

  // Find the initial state
  const initialNode = nodes.find((n) => n.data.isInitial);
  if (!initialNode) {
    throw new Error('No initial state found in workflow');
  }

  // Build the states object
  const states: Record<string, XStateStateConfig> = {};

  // Process top-level nodes (nodes without parentId)
  const topLevelNodes = nodes.filter((n) => !n.parentId);

  for (const node of topLevelNodes) {
    states[node.data.label] = buildStateConfig(node, nodes, edges);
  }

  return {
    id,
    version: String(config.version),
    initial: initialNode.data.label,
    context: context || {},
    states,
  };
}

/**
 * Checks if a node is a domain-specific node
 */
function isDomainNode(node: WorkflowNode): boolean {
  const domainType = (node.data as { domainType?: DomainNodeType }).domainType;
  return domainType !== undefined && DOMAIN_NODE_TYPES.includes(domainType);
}

/**
 * Builds an XState state configuration from a workflow node
 */
function buildStateConfig(
  node: WorkflowNode,
  allNodes: WorkflowNode[],
  allEdges: WorkflowEdge[]
): XStateStateConfig {
  const config: XStateStateConfig = {};
  const { data } = node;

  // Handle domain-specific nodes
  if (isDomainNode(node)) {
    return buildDomainNodeConfig(node, allNodes, allEdges);
  }

  // Set state type for special states
  if (data.xstateType === 'final') {
    config.type = 'final';
  } else if (data.xstateType === 'parallel') {
    config.type = 'parallel';
  } else if (data.xstateType === 'history') {
    config.type = 'history';
    config.history = data.historyType || 'shallow';
  }

  // Add entry/exit actions
  if (data.entryActions?.length) {
    config.entry = data.entryActions;
  }
  if (data.exitActions?.length) {
    config.exit = data.exitActions;
  }

  // Handle compound states (nested states)
  if (data.xstateType === 'compound' || data.xstateType === 'parallel') {
    const childNodes = allNodes.filter((n) => n.parentId === node.id);
    if (childNodes.length > 0) {
      config.states = {};
      for (const child of childNodes) {
        config.states[child.data.label] = buildStateConfig(child, allNodes, allEdges);
      }

      // Set initial child for compound states
      if (data.xstateType === 'compound' && data.initialChild) {
        config.initial = data.initialChild;
      }
    }
  }

  // Handle invoke configuration
  if (data.invokeConfig) {
    config.invoke = {
      src: data.invokeConfig.src,
      ...(data.invokeConfig.onDone && { onDone: data.invokeConfig.onDone }),
      ...(data.invokeConfig.onError && { onError: data.invokeConfig.onError }),
    };
  }

  // Build transitions from edges
  const outgoingEdges = allEdges.filter((e) => e.source === node.id);

  // Group edges by type
  const eventEdges = outgoingEdges.filter((e) => e.data.transitionType === 'event');
  const delayedEdges = outgoingEdges.filter((e) => e.data.transitionType === 'delayed');
  const alwaysEdges = outgoingEdges.filter((e) => e.data.transitionType === 'always');

  // Process event transitions
  if (eventEdges.length > 0) {
    config.on = {};

    // Group by event name (for conditional transitions)
    const eventGroups = new Map<string, WorkflowEdge[]>();
    for (const edge of eventEdges) {
      const eventName = edge.data.event || 'UNKNOWN';
      if (!eventGroups.has(eventName)) {
        eventGroups.set(eventName, []);
      }
      eventGroups.get(eventName)!.push(edge);
    }

    for (const [eventName, groupEdges] of eventGroups) {
      if (groupEdges.length === 1) {
        config.on[eventName] = buildTransition(groupEdges[0], allNodes);
      } else {
        // Multiple transitions for same event = conditional
        // Map to XStateTransition[] - convert strings to objects
        config.on[eventName] = groupEdges.map((e) => {
          const transition = buildTransition(e, allNodes);
          return typeof transition === 'string'
            ? { target: transition }
            : transition;
        });
      }
    }
  }

  // Process delayed transitions
  if (delayedEdges.length > 0) {
    config.after = {};
    for (const edge of delayedEdges) {
      const delay = calculateDelayMs(edge.data.delay || 0, edge.data.delayUnit);
      config.after[delay] = buildTransition(edge, allNodes);
    }
  }

  // Process always transitions
  if (alwaysEdges.length > 0) {
    config.always = alwaysEdges.map((e) => {
      const transition = buildTransition(e, allNodes);
      // Always transitions should always be objects, not strings
      return typeof transition === 'string'
        ? { target: transition }
        : transition;
    });
  }

  return config;
}

/**
 * Builds an XState transition from a workflow edge
 */
function buildTransition(edge: WorkflowEdge, allNodes: WorkflowNode[]): XStateTransition | string {
  const targetNode = allNodes.find((n) => n.id === edge.target);
  const targetLabel = targetNode?.data.label || edge.target;

  const { data } = edge;
  const hasGuard = !!data.guard;
  const hasActions = (data.actions?.length || 0) > 0;

  // Simple transition (just target)
  if (!hasGuard && !hasActions) {
    return targetLabel;
  }

  // Complex transition
  const transition: XStateTransition = {
    target: targetLabel,
  };

  if (hasGuard) {
    transition.guard = guardConfigToString(data.guard!);
  }

  if (hasActions) {
    transition.actions = data.actions;
  }

  return transition;
}

/**
 * Converts a GuardConfig to a guard name string
 */
function guardConfigToString(guard: GuardConfig): string {
  switch (guard.type) {
    case 'python':
      return guard.name;
    case 'simple':
      // Generate a guard name based on the condition
      return `check_${guard.field}_${guard.operator}`;
    case 'compound':
      // Generate a combined guard name
      return `combined_guard_${guard.operator}`;
    default:
      return 'unknown_guard';
  }
}

/**
 * Converts delay value and unit to milliseconds
 */
function calculateDelayMs(delay: number, unit?: string): number {
  switch (unit) {
    case 'seconds':
      return delay * 1000;
    case 'minutes':
      return delay * 60 * 1000;
    case 'hours':
      return delay * 60 * 60 * 1000;
    case 'days':
      return delay * 24 * 60 * 60 * 1000;
    default: // 'ms' or undefined
      return delay;
  }
}

/**
 * Builds XState configuration for domain-specific nodes
 */
function buildDomainNodeConfig(
  node: WorkflowNode,
  allNodes: WorkflowNode[],
  allEdges: WorkflowEdge[]
): XStateStateConfig {
  const domainType = (node.data as { domainType: DomainNodeType }).domainType;
  const config: XStateStateConfig = {};

  // Store domain node configuration in meta
  config.meta = {
    domain_node: {
      type: domainType,
      ...extractDomainNodeMeta(node),
    },
  };

  switch (domainType) {
    case 'start':
      // Start node is just an entry point with an outgoing transition
      return buildStartNodeConfig(node, allNodes, allEdges);

    case 'end':
      // End node is a final state
      return buildEndNodeConfig(node);

    case 'approval':
      // Approval node creates a task and waits for action
      return buildApprovalNodeConfig(node, allNodes, allEdges);

    case 'parallel_approval':
      // Parallel approval has multiple concurrent approvers
      return buildParallelApprovalConfig(node, allNodes, allEdges);

    case 'threshold_gate':
      // Threshold gate has conditional always transitions
      return buildThresholdGateConfig(node, allNodes, allEdges);

    case 'classification_branch':
      // Classification branch has multiple guarded transitions
      return buildClassificationBranchConfig(node, allNodes, allEdges);

    case 'auto_action':
      // Auto action runs entry action and transitions immediately
      return buildAutoActionConfig(node, allNodes, allEdges);

    default:
      return config;
  }
}

/**
 * Extract domain-specific metadata from node data
 */
function extractDomainNodeMeta(node: WorkflowNode): Record<string, unknown> {
  const domainType = (node.data as { domainType: DomainNodeType }).domainType;

  switch (domainType) {
    case 'approval': {
      const approvalData = node.data as ApprovalNodeData;
      return {
        resolver: approvalData.resolver,
        available_actions: approvalData.availableActions,
        sla_hours: approvalData.slaHours,
        priority: approvalData.priority,
        fallback_user: approvalData.fallbackUser,
        escalation: approvalData.escalation,
        label: approvalData.label,
      };
    }

    case 'parallel_approval': {
      const parallelData = node.data as ParallelApprovalNodeData;
      return {
        approvers: parallelData.approvers,
        completion_rule: parallelData.completionRule,
        quorum_count: parallelData.quorumCount,
        on_reject: parallelData.onReject,
        sla_hours: parallelData.slaHours,
        priority: parallelData.priority,
        label: parallelData.label,
      };
    }

    case 'threshold_gate': {
      const gateData = node.data as ThresholdGateNodeData;
      return {
        threshold: gateData.threshold,
        label: gateData.label,
      };
    }

    case 'classification_branch': {
      const branchData = node.data as ClassificationBranchNodeData;
      return {
        field: branchData.field,
        branches: branchData.branches,
        default_target: branchData.defaultTarget,
        label: branchData.label,
      };
    }

    case 'auto_action': {
      const actionData = node.data as AutoActionNodeData;
      return {
        action_type: actionData.actionType,
        action_config: actionData.actionConfig,
        label: actionData.label,
      };
    }

    case 'end': {
      const endData = node.data as EndNodeData;
      return {
        final_status: endData.finalStatus,
        label: endData.label,
      };
    }

    default:
      return { label: node.data.label };
  }
}

function buildStartNodeConfig(
  node: WorkflowNode,
  allNodes: WorkflowNode[],
  allEdges: WorkflowEdge[]
): XStateStateConfig {
  const config: XStateStateConfig = {
    meta: {
      domain_node: { type: 'start', label: node.data.label },
    },
  };

  // Start nodes immediately transition to the next state
  const outgoingEdges = allEdges.filter((e) => e.source === node.id);
  if (outgoingEdges.length > 0) {
    const targetNode = allNodes.find((n) => n.id === outgoingEdges[0].target);
    if (targetNode) {
      config.always = [{ target: targetNode.data.label }];
    }
  }

  return config;
}

function buildEndNodeConfig(node: WorkflowNode): XStateStateConfig {
  const endData = node.data as EndNodeData;
  return {
    type: 'final',
    meta: {
      domain_node: {
        type: 'end',
        final_status: endData.finalStatus,
        label: endData.label,
      },
    },
    // Add entry action to update status if configured
    ...(endData.finalStatus && {
      entry: ['update_status'],
    }),
  };
}

function buildApprovalNodeConfig(
  node: WorkflowNode,
  allNodes: WorkflowNode[],
  allEdges: WorkflowEdge[]
): XStateStateConfig {
  const approvalData = node.data as ApprovalNodeData;
  const config: XStateStateConfig = {
    meta: {
      domain_node: {
        type: 'approval',
        resolver: approvalData.resolver,
        available_actions: approvalData.availableActions || ['Approve', 'Reject'],
        sla_hours: approvalData.slaHours,
        priority: approvalData.priority,
        fallback_user: approvalData.fallbackUser,
        escalation: approvalData.escalation,
        label: approvalData.label,
      },
    },
    // Entry action creates the approval task
    entry: ['create_approval_task'],
    // Exit action cleans up
    exit: ['cancel_approval_tasks'],
    on: {},
  };

  // Create transitions for each available action
  const outgoingEdges = allEdges.filter((e) => e.source === node.id);
  const actions = approvalData.availableActions || ['Approve', 'Reject'];

  for (const action of actions) {
    // Find edge for this action (by handle id or default mapping)
    const actionLower = action.toLowerCase();
    const matchingEdge = outgoingEdges.find((e) => {
      const handleId = (e as { sourceHandle?: string }).sourceHandle;
      return handleId === actionLower || handleId === action;
    }) || outgoingEdges[actions.indexOf(action)];

    if (matchingEdge) {
      const targetNode = allNodes.find((n) => n.id === matchingEdge.target);
      if (targetNode) {
        config.on![action.toUpperCase()] = { target: targetNode.data.label };
      }
    }
  }

  return config;
}

function buildParallelApprovalConfig(
  node: WorkflowNode,
  allNodes: WorkflowNode[],
  allEdges: WorkflowEdge[]
): XStateStateConfig {
  const parallelData = node.data as ParallelApprovalNodeData;

  // Build regions for each approver - this creates a parallel state
  const regions: Record<string, XStateStateConfig> = {};

  for (const approver of parallelData.approvers || []) {
    regions[approver.id] = {
      initial: 'pending',
      states: {
        pending: {
          entry: ['create_approval_task'],
          on: {
            [`APPROVE_${approver.id}`]: 'approved',
            [`REJECT_${approver.id}`]: 'rejected',
          },
          meta: {
            approver_config: approver,
          },
        },
        approved: { type: 'final' },
        rejected: { type: 'final' },
      },
    };
  }

  const config: XStateStateConfig = {
    type: 'parallel',
    states: regions,
    meta: {
      domain_node: {
        type: 'parallel_approval',
        approvers: parallelData.approvers,
        completion_rule: parallelData.completionRule,
        quorum_count: parallelData.quorumCount,
        on_reject: parallelData.onReject,
        sla_hours: parallelData.slaHours,
        priority: parallelData.priority,
        label: parallelData.label,
      },
    },
    on: {},
  };

  // Find outgoing edges for approved/rejected outcomes
  const outgoingEdges = allEdges.filter((e) => e.source === node.id);
  const approvedEdge = outgoingEdges.find((e) => (e as { sourceHandle?: string }).sourceHandle === 'approved');
  const rejectedEdge = outgoingEdges.find((e) => (e as { sourceHandle?: string }).sourceHandle === 'rejected');

  // Add transitions for overall approval/rejection
  if (approvedEdge) {
    const approvedTarget = allNodes.find((n) => n.id === approvedEdge.target);
    if (approvedTarget) {
      // All required approvers approved - check completion rule
      config.on!['PARALLEL_APPROVED'] = { target: approvedTarget.data.label };
    }
  }

  if (rejectedEdge) {
    const rejectedTarget = allNodes.find((n) => n.id === rejectedEdge.target);
    if (rejectedTarget) {
      config.on!['PARALLEL_REJECTED'] = { target: rejectedTarget.data.label };
    }
  }

  return config;
}

function buildThresholdGateConfig(
  node: WorkflowNode,
  allNodes: WorkflowNode[],
  allEdges: WorkflowEdge[]
): XStateStateConfig {
  const gateData = node.data as ThresholdGateNodeData;
  const isMethodCheck = gateData.checkType === 'method';

  // Build meta based on check type
  const domainNodeMeta: Record<string, unknown> = {
    type: 'threshold_gate',
    checkType: gateData.checkType || 'field',
    label: gateData.label,
  };

  if (isMethodCheck) {
    domainNodeMeta.methodCheck = gateData.methodCheck;
  } else {
    domainNodeMeta.threshold = gateData.threshold;
  }

  const config: XStateStateConfig = {
    meta: {
      domain_node: domainNodeMeta,
    },
    always: [],
  };

  // Find pass and fail edges
  const outgoingEdges = allEdges.filter((e) => e.source === node.id);
  const passEdge = outgoingEdges.find((e) => (e as { sourceHandle?: string }).sourceHandle === 'pass');
  const failEdge = outgoingEdges.find((e) => (e as { sourceHandle?: string }).sourceHandle === 'fail');

  // Build guard name based on check type
  let guardName: string;
  if (isMethodCheck) {
    guardName = gateData.methodCheck?.method
      ? `method_check_${gateData.methodCheck.method}`
      : 'method_check';
  } else {
    guardName = gateData.threshold
      ? `threshold_${gateData.threshold.field}_${gateData.threshold.operator}_${gateData.threshold.value}`
      : 'threshold_check';
  }

  if (passEdge) {
    const passTarget = allNodes.find((n) => n.id === passEdge.target);
    if (passTarget) {
      config.always!.push({
        target: passTarget.data.label,
        guard: guardName,
      });
    }
  }

  if (failEdge) {
    const failTarget = allNodes.find((n) => n.id === failEdge.target);
    if (failTarget) {
      // Fail transition (no guard - default when pass guard fails)
      config.always!.push({
        target: failTarget.data.label,
      });
    }
  }

  return config;
}

function buildClassificationBranchConfig(
  node: WorkflowNode,
  allNodes: WorkflowNode[],
  allEdges: WorkflowEdge[]
): XStateStateConfig {
  const branchData = node.data as ClassificationBranchNodeData;
  const config: XStateStateConfig = {
    meta: {
      domain_node: {
        type: 'classification_branch',
        field: branchData.field,
        branches: branchData.branches,
        label: branchData.label,
      },
    },
    always: [],
  };

  const outgoingEdges = allEdges.filter((e) => e.source === node.id);

  // Build guarded transitions for each branch
  for (const branch of branchData.branches || []) {
    const branchEdge = outgoingEdges.find((e) =>
      (e as { sourceHandle?: string }).sourceHandle === `branch-${branch.value}`
    );

    if (branchEdge) {
      const targetNode = allNodes.find((n) => n.id === branchEdge.target);
      if (targetNode) {
        config.always!.push({
          target: targetNode.data.label,
          guard: `classification_${branchData.field}_eq_${branch.value}`,
        });
      }
    }
  }

  // Default branch
  if (branchData.defaultTarget) {
    const defaultEdge = outgoingEdges.find((e) =>
      (e as { sourceHandle?: string }).sourceHandle === 'default'
    );
    if (defaultEdge) {
      const targetNode = allNodes.find((n) => n.id === defaultEdge.target);
      if (targetNode) {
        config.always!.push({
          target: targetNode.data.label,
        });
      }
    }
  }

  return config;
}

function buildAutoActionConfig(
  node: WorkflowNode,
  allNodes: WorkflowNode[],
  allEdges: WorkflowEdge[]
): XStateStateConfig {
  const actionData = node.data as AutoActionNodeData;
  const config: XStateStateConfig = {
    meta: {
      domain_node: {
        type: 'auto_action',
        action_type: actionData.actionType,
        action_config: actionData.actionConfig,
        label: actionData.label,
      },
    },
    // Entry action executes the configured action
    entry: [actionData.actionType || 'log'],
  };

  // Auto actions immediately transition to next state
  const outgoingEdges = allEdges.filter((e) => e.source === node.id);
  if (outgoingEdges.length > 0) {
    const targetNode = allNodes.find((n) => n.id === outgoingEdges[0].target);
    if (targetNode) {
      config.always = [{ target: targetNode.data.label }];
    }
  }

  return config;
}
