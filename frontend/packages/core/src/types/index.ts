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
  | 'parallel_approval'
  | 'auto_action'
  | 'agentic'
  | 'rest_fetch'
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

// Action Configuration (for defining available actions)
export interface ActionConfig {
  name: string;
  type: 'entry' | 'exit' | 'transition';
  category: 'builtin' | 'python' | 'webhook';
  description?: string;
  params?: Record<string, unknown>;
}

// Configured Action (for storing actions with their parameter values)
export interface ConfiguredAction {
  name: string;
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
  /** The XState state name (used for position matching on reload) */
  stateName?: string;
  description?: string;
  isInitial?: boolean;
  /** When true, documents can be submitted when workflow reaches this state */
  allowsSubmit?: boolean;
  // Actions can be strings (legacy) or ConfiguredAction objects (with params)
  entryActions?: Array<string | ConfiguredAction>;
  exitActions?: Array<string | ConfiguredAction>;
  // For compound/parallel states
  children?: string[];
  initialChild?: string;
  // For parallel states - region information
  regions?: Array<{
    name: string;
    label?: string;
    initial?: string;
    childStates?: string[];
  }>;
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
  // Dynamic handles - outgoing events from this node
  outgoingEvents?: string[];
  // Index signature for React Flow compatibility
  [key: string]: unknown;
}

// Workflow Builder Edge Data
export interface WorkflowEdgeData {
  event?: string;
  transitionType: XStateTransitionType;
  delay?: number;
  delayUnit?: 'ms' | 'seconds' | 'minutes' | 'hours' | 'days';
  businessHoursOnly?: boolean; // Only count working hours (Mon-Fri, 9 AM - 6 PM)
  guard?: GuardConfig;
  actions?: string[];
  description?: string;
  trigger?: TriggerConfig;
  pathOffset?: number; // Manual offset for edge path positioning
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
  // Handle connections for multi-handle nodes
  sourceHandle?: string;
  targetHandle?: string;
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

// Event-based colors for handles and edges
export const EVENT_COLORS: Record<string, string> = {
  approve: '#22c55e',    // Green
  approved: '#22c55e',   // Green
  reject: '#ef4444',     // Red
  rejected: '#ef4444',   // Red
  submit: '#3b82f6',     // Blue
  submitted: '#3b82f6',  // Blue
  cancel: '#f59e0b',     // Orange
  cancelled: '#f59e0b',  // Orange
  escalate: '#8b5cf6',   // Purple
  escalated: '#8b5cf6',  // Purple
  pass: '#22c55e',       // Green
  fail: '#ef4444',       // Red
  success: '#22c55e',    // Green
  failure: '#ef4444',    // Red
  error: '#ef4444',      // Red
  default: '#6b7280',    // Gray
} as const;

/**
 * Get color for an event name based on keywords
 */
export function getEventColor(event?: string): string {
  if (!event) return EVENT_COLORS.default;

  const lowerEvent = event.toLowerCase();

  // Check exact matches first
  if (EVENT_COLORS[lowerEvent]) {
    return EVENT_COLORS[lowerEvent];
  }

  // Check for keyword matches
  if (lowerEvent.includes('approve')) return EVENT_COLORS.approve;
  if (lowerEvent.includes('reject')) return EVENT_COLORS.reject;
  if (lowerEvent.includes('submit')) return EVENT_COLORS.submit;
  if (lowerEvent.includes('cancel')) return EVENT_COLORS.cancel;
  if (lowerEvent.includes('escalat')) return EVENT_COLORS.escalate;
  if (lowerEvent.includes('pass')) return EVENT_COLORS.pass;
  if (lowerEvent.includes('fail')) return EVENT_COLORS.fail;
  if (lowerEvent.includes('success')) return EVENT_COLORS.success;
  if (lowerEvent.includes('error')) return EVENT_COLORS.error;

  return EVENT_COLORS.default;
}

// =============================================================================
// DOMAIN-SPECIFIC NODE TYPES
// =============================================================================

// Supported operators for threshold gate conditions (matches backend evaluate_operator)
export type CheckOperator =
  | 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'ne'  // Comparison
  | 'contains' | 'not_contains' | 'starts_with' | 'ends_with'  // String
  | 'in' | 'not_in'  // List
  | 'is_set' | 'is_not_set';  // Null checks

// Single condition for compound threshold gate
export interface CheckCondition {
  id: string;
  field: string;
  fieldType?: string;  // For UI hints (e.g., 'Int', 'Data', 'Select')
  operator: CheckOperator;
  value?: string | number | boolean;
}

// Operators available by field type category
export const OPERATORS_BY_TYPE: Record<string, CheckOperator[]> = {
  numeric: ['gt', 'gte', 'lt', 'lte', 'eq', 'ne', 'is_set', 'is_not_set'],
  text: ['eq', 'ne', 'contains', 'not_contains', 'starts_with', 'ends_with', 'is_set', 'is_not_set'],
  select: ['eq', 'ne', 'in', 'not_in', 'is_set', 'is_not_set'],
  check: ['eq', 'is_set'],
  date: ['gt', 'gte', 'lt', 'lte', 'eq', 'ne', 'is_set', 'is_not_set'],
  link: ['eq', 'ne', 'is_set', 'is_not_set'],
};

// Map Frappe fieldtype to type category
export const FIELD_TYPE_CATEGORIES: Record<string, string> = {
  // Numeric
  Int: 'numeric',
  Float: 'numeric',
  Currency: 'numeric',
  Percent: 'numeric',
  // Text
  Data: 'text',
  'Small Text': 'text',
  Text: 'text',
  'Text Editor': 'text',
  'Long Text': 'text',
  // Select
  Select: 'select',
  // Check (boolean)
  Check: 'check',
  // Date
  Date: 'date',
  Datetime: 'date',
  Time: 'date',
  // Link
  Link: 'link',
  // Default to text for unknown
};

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

  // Check mode: simple (single condition), compound (multiple with AND/OR), method
  checkMode?: 'simple' | 'compound' | 'method';  // Default: 'simple'

  // Legacy field (maps to checkMode) - backward compatibility
  checkType?: 'field' | 'method';

  // Simple mode - single field comparison (backward compatible with old threshold)
  threshold?: {
    field: string;
    operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'ne';
    value: number;
  };

  // Compound mode - multiple conditions with AND/OR logic
  conditions?: CheckCondition[];
  conditionLogic?: 'and' | 'or';  // How to combine conditions (default: 'and')

  // Method-based check
  methodCheck?: {
    method: string;           // e.g., "check_credit_limit"
    storeResultIn?: string;   // context key to store details
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

// Parallel Approval Approver Configuration
export interface ParallelApprover {
  id: string;
  label: string;
  resolver: ResolverConfig;
  required: boolean;
}

// Parallel Approval Node Data
export interface ParallelApprovalNodeData extends WorkflowNodeData {
  domainType: 'parallel_approval';
  approvers: ParallelApprover[];
  completionRule: 'all_required' | 'any_one' | 'quorum';
  quorumCount?: number;  // For 'quorum' rule: how many must approve
  onReject: 'reject_all' | 'continue_others';
  slaHours?: number;
  priority?: 'Low' | 'Medium' | 'High' | 'Urgent';
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

// =============================================================================
// AGENTIC NODE TYPES
// =============================================================================

// Tool configuration for agentic nodes
export interface ToolConfig {
  name: string;
  enabled: boolean;
}

// Allowed method configuration with role-based access
export interface AllowedMethod {
  method: string;
  allowed_roles?: string[];
}

// Decision route for decision-based transitions
export interface DecisionRoute {
  condition: string;
}

// Custom agent event for custom_events transition mode
export interface CustomAgentEvent {
  name: string;
  description?: string;
}

// Data input configuration for pre-loading data
export interface DataInputConfig {
  // Which fields from current document
  documentFields?: string[];
  // Linked documents to fetch
  linkedDocuments?: LinkedDocumentConfig[];
  // Context variables from workflow
  contextVariables?: string[];
}

// Linked document configuration
export interface LinkedDocumentConfig {
  linkField: string;
  fields: string[];
}

// MCP server selection for agentic nodes
export interface MCPServerConfig {
  connectionName: string;
  enabled: boolean;
}

// REST endpoint configuration for agentic nodes
export interface RestEndpointConfig {
  name: string;
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  authType: 'none' | 'api_key' | 'basic' | 'bearer';
  authCredential?: string;
  headers?: Record<string, string>;
  body?: string;
  description: string;
  timeout?: number;
}

// Agentic Node Data
export interface AgenticNodeData extends WorkflowNodeData {
  domainType: 'agentic';
  // Agent configuration
  agentType?: 'react' | 'tool_executor' | 'plan_execute' | 'custom';
  systemPrompt?: string;
  model?: string;
  // Tools
  enabledTools?: ToolConfig[];
  frappeAccess?: 'none' | 'read_only' | 'full_crud';
  allowedMethods?: AllowedMethod[];
  // Data input configuration
  dataInput?: DataInputConfig;
  // MCP server connections
  enabledMcps?: MCPServerConfig[];
  // REST endpoint tools
  restEndpoints?: RestEndpointConfig[];
  // Transition configuration
  transitionMode?: 'simple' | 'decision' | 'custom_events' | 'all';
  decisionRoutes?: DecisionRoute[];
  customEvents?: CustomAgentEvent[];
  // Execution settings
  maxIterations?: number;
  timeoutSeconds?: number;
  retryOnFailure?: boolean;
  maxRetries?: number;
}

// =============================================================================
// REST FETCH NODE TYPES
// =============================================================================

// REST Fetch Node Data - fetches data before transitioning
export interface RestFetchNodeData extends WorkflowNodeData {
  domainType: 'rest_fetch';
  // Request configuration
  url: string;
  method: 'GET' | 'POST' | 'PUT';
  authType: 'none' | 'api_key' | 'basic' | 'bearer';
  authCredential?: string;
  headers?: Record<string, string>;
  body?: string;
  // Response handling
  saveResponseTo: string;  // Context variable name
  // Transitions
  onSuccess: string;       // Event to trigger on success
  onError: string;         // Event to trigger on error
  // Timeout
  timeoutSeconds?: number;
}

// Union type for all domain node data
export type DomainNodeData =
  | StartNodeData
  | ThresholdGateNodeData
  | ClassificationBranchNodeData
  | ApprovalNodeData
  | ParallelApprovalNodeData
  | AutoActionNodeData
  | AgenticNodeData
  | RestFetchNodeData
  | EndNodeData;

// Domain node colors
export const DOMAIN_NODE_COLORS: Record<DomainNodeType, string> = {
  start: '#22c55e',
  threshold_gate: '#f59e0b',
  classification_branch: '#8b5cf6',
  approval: '#3b82f6',
  parallel_approval: '#6366f1',  // Indigo for parallel approval
  auto_action: '#06b6d4',
  agentic: '#ec4899',           // Pink for AI agent
  rest_fetch: '#14b8a6',        // Teal for REST fetch
  end: '#ef4444',
} as const;
