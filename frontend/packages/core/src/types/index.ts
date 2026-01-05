// XState Node Types
export type XStateNodeType =
  | 'atomic'
  | 'compound'
  | 'parallel'
  | 'history'
  | 'final';

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
