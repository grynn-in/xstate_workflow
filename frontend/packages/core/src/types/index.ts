// XState Node Types
export type XStateNodeType =
  | 'atomic'
  | 'compound'
  | 'parallel'
  | 'history'
  | 'final';

// Domain-Specific Node Types
export type DomainNodeType =
  | 'start'
  | 'threshold_gate'
  | 'classification_branch'
  | 'approval'
  | 'auto_action'
  | 'end';

export type HistoryType = 'shallow' | 'deep';

// XState Transition Types
export type XStateTransitionType = 'event' | 'delayed' | 'always';

// Guard Configuration
export interface SimpleGuardConfig {
  type: 'simple';
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte' | 'in' | 'contains' | 'is_set' | 'is_not_set';
  value?: unknown;
}

export interface CompoundGuardConfig {
  type: 'compound';
  operator: 'and' | 'or';
  conditions: GuardConfig[];
}

export interface PythonGuardConfig {
  type: 'python';
  name: string;
  description?: string;
}

export type GuardConfig = SimpleGuardConfig | CompoundGuardConfig | PythonGuardConfig;

// Action Configuration
export interface ActionConfig {
  name: string;
  type: 'entry' | 'exit' | 'transition';
  category: 'builtin' | 'python' | 'webhook';
  description?: string;
  params?: Record<string, unknown>;
}

// Trigger Configuration
export interface ButtonTriggerConfig {
  enabled: boolean;
  label: string;
  style: 'primary' | 'secondary' | 'danger' | 'success';
  allowedRoles: string[];
}

export interface AutoTriggerConfig {
  enabled: boolean;
  event: 'on_update' | 'after_insert' | 'on_submit' | 'on_cancel';
  condition?: GuardConfig;
  fireEvent: string;
}

export interface DelayedTriggerConfig {
  enabled: boolean;
  delay: number;
  unit: 'seconds' | 'minutes' | 'hours' | 'days';
  reminderDelay?: number;
  reminderUnit?: 'seconds' | 'minutes' | 'hours' | 'days';
}

export interface TriggerConfig {
  button?: ButtonTriggerConfig;
  auto?: AutoTriggerConfig;
  delayed?: DelayedTriggerConfig;
}

// Workflow Builder Node Data
export interface WorkflowNodeData {
  label: string;
  xstateType: XStateNodeType;
  description?: string;
  isInitial?: boolean;
  entryActions?: string[];
  exitActions?: string[];
  // For compound/parallel states
  children?: string[];
  initialChild?: string;
  // For history states
  historyType?: HistoryType;
  // For invoke services
  invokeConfig?: {
    src: string;
    onDone?: string;
    onError?: string;
  };
  // Metadata for visual styling
  color?: string;
  // Index signature for React Flow compatibility
  [key: string]: unknown;
}

// Workflow Builder Edge Data
export interface WorkflowEdgeData {
  event?: string;
  transitionType: XStateTransitionType;
  delay?: number;
  delayUnit?: 'ms' | 'seconds' | 'minutes' | 'hours';
  guard?: GuardConfig;
  actions?: string[];
  description?: string;
  trigger?: TriggerConfig;
  // Index signature for React Flow compatibility
  [key: string]: unknown;
}

// React Flow Node/Edge with our data
export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: WorkflowNodeData;
  parentId?: string;
  extent?: 'parent';
  measured?: { width: number; height: number };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  data: WorkflowEdgeData;
  label?: string;
  animated?: boolean;
}

// Complete Workflow Configuration
export interface WorkflowBuilderConfig {
  id: string;
  name: string;
  description?: string;
  attachedDoctype?: string;
  version: number;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  context?: Record<string, unknown>;
  metadata?: {
    createdAt?: string;
    updatedAt?: string;
    author?: string;
  };
}

// XState v5 JSON Format Types
export interface XStateTransition {
  target?: string;
  guard?: string;
  actions?: string[];
}

export interface XStateStateConfig {
  type?: 'final' | 'parallel' | 'history';
  initial?: string;
  states?: Record<string, XStateStateConfig>;
  on?: Record<string, XStateTransition | XStateTransition[] | string>;
  entry?: string[];
  exit?: string[];
  always?: XStateTransition[];
  after?: Record<string, XStateTransition | string>;
  invoke?: XStateInvokeConfig | XStateInvokeConfig[];
  history?: HistoryType;
  meta?: Record<string, unknown>;
}

export interface XStateInvokeConfig {
  id?: string;
  src: string;
  onDone?: XStateTransition | string;
  onError?: XStateTransition | string;
}

export interface XStateMachineConfig {
  id: string;
  version?: string;
  initial: string;
  context?: Record<string, unknown>;
  states: Record<string, XStateStateConfig>;
  types?: {
    events?: Record<string, unknown>;
    context?: Record<string, unknown>;
  };
}

// Frappe DocType Field (for guard builder)
export interface FrappeField {
  fieldname: string;
  fieldtype: string;
  label: string;
  options?: string;
  reqd?: boolean;
}

export interface FrappeDocType {
  name: string;
  fields: FrappeField[];
}

// Color theme constants
export const STATE_COLORS: Record<XStateNodeType | 'initial', string> = {
  initial: '#28a745',
  atomic: '#4d65ff',
  compound: '#7c3aed',
  parallel: '#f59e0b',
  history: '#6b7280',
  final: '#dc3545',
} as const;

export const BADGE_COLORS = {
  guard: '#fbbf24',
  action: '#22d3ee',
  selected: '#2490ef',
} as const;

// =============================================================================
// DOMAIN-SPECIFIC NODE TYPES
// =============================================================================

// Assignment Resolver Configuration
export type ResolverType =
  | 'role'
  | 'static_user'
  | 'document_field'
  | 'linked_doc_field'
  | 'hierarchy_walk'
  | 'delegation_matrix'
  | 'cost_center_manager'
  | 'department_head'
  | 'reporting_manager';

export interface RoleResolverConfig {
  type: 'role';
  role: string;
  strategy?: 'all' | 'round_robin' | 'least_loaded';
}

export interface StaticUserResolverConfig {
  type: 'static_user';
  user_id: string;
}

export interface DocumentFieldResolverConfig {
  type: 'document_field';
  field_name: string;
}

export interface LinkedDocFieldResolverConfig {
  type: 'linked_doc_field';
  link_field: string;
  user_field: string;
}

export interface HierarchyWalkResolverConfig {
  type: 'hierarchy_walk';
  hierarchy_doctype: string;
  parent_field: string;
  user_field: string;
  start_from: 'owner' | 'document_field' | 'linked_doc';
  start_field?: string;
  level_mode: 'fixed' | 'until_condition' | 'all_up_to';
  levels_up?: number;
  max_levels?: number;
  until_condition?: {
    type: 'authority_covers_amount' | 'has_role' | 'field_equals' | 'is_root';
    [key: string]: unknown;
  };
  skip_levels?: number;
  max_depth?: number;
}

export interface DelegationMatrixResolverConfig {
  type: 'delegation_matrix';
  amount_field?: string;
  category_field?: string;
}

export type ResolverConfig =
  | RoleResolverConfig
  | StaticUserResolverConfig
  | DocumentFieldResolverConfig
  | LinkedDocFieldResolverConfig
  | HierarchyWalkResolverConfig
  | DelegationMatrixResolverConfig
  | { type: 'cost_center_manager' }
  | { type: 'department_head' }
  | { type: 'reporting_manager' };

// Start Node Data
export interface StartNodeData extends WorkflowNodeData {
  domainType: 'start';
}

// Threshold Gate Node Data
export interface ThresholdGateNodeData extends WorkflowNodeData {
  domainType: 'threshold_gate';
  threshold: {
    field: string;
    operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'ne';
    value: number;
  };
  passTarget?: string;
  failTarget?: string;
}

// Classification Branch Node Data
export interface ClassificationBranchNodeData extends WorkflowNodeData {
  domainType: 'classification_branch';
  field: string;
  branches: Array<{
    value: string;
    label?: string;
    target?: string;
  }>;
  defaultTarget?: string;
}

// Approval Node Data
export interface ApprovalNodeData extends WorkflowNodeData {
  domainType: 'approval';
  resolver: ResolverConfig;
  availableActions: string[];
  slaHours?: number;
  priority?: 'Low' | 'Medium' | 'High' | 'Urgent';
  fallbackUser?: string;
  escalation?: {
    enabled: boolean;
    maxLevel?: number;
    type?: 'hierarchy' | 'static' | 'role';
    user?: string;
    role?: string;
  };
}

// Auto Action Types
export type AutoActionType =
  | 'submit_document'
  | 'cancel_document'
  | 'update_field'
  | 'update_status'
  | 'send_notification'
  | 'call_api'
  | 'run_method';

export interface AutoActionNodeData extends WorkflowNodeData {
  domainType: 'auto_action';
  actionType: AutoActionType;
  actionConfig: {
    // update_field
    field?: string;
    value?: unknown;
    // update_status
    status?: string;
    // send_notification
    notification_type?: 'Email' | 'System';
    recipients?: string[];
    subject?: string;
    message?: string;
    // call_api
    url?: string;
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
    headers?: Record<string, string>;
    payload?: Record<string, unknown>;
    // run_method
    methodName?: string;
    args?: Record<string, unknown>;
  };
}

// End Node Data
export interface EndNodeData extends WorkflowNodeData {
  domainType: 'end';
  finalStatus?: string;
}

// Union type for all domain node data
export type DomainNodeData =
  | StartNodeData
  | ThresholdGateNodeData
  | ClassificationBranchNodeData
  | ApprovalNodeData
  | AutoActionNodeData
  | EndNodeData;

// Domain node colors
export const DOMAIN_NODE_COLORS: Record<DomainNodeType, string> = {
  start: '#22c55e',
  threshold_gate: '#f59e0b',
  classification_branch: '#8b5cf6',
  approval: '#3b82f6',
  auto_action: '#06b6d4',
  end: '#ef4444',
} as const;
