// Types for XState Workflow Builder

import type { Node, Edge } from '@xyflow/react';

// State types supported by XState
export type StateType = 'initial' | 'atomic' | 'compound' | 'parallel' | 'final' | 'history';

// Custom node data
export interface StateNodeData {
  label: string;
  stateType: StateType;
  entryActions: string[];
  exitActions: string[];
  description?: string;
  isSelected?: boolean;
  // For compound states
  childStates?: string[];
  // For history states
  historyType?: 'shallow' | 'deep';
}

// Custom edge data
export interface TransitionEdgeData {
  event: string;
  guard?: string;
  actions: string[];
  description?: string;
  isConditional?: boolean;
}

// Typed node and edge
export type StateNode = Node<StateNodeData, 'stateNode'>;
export type TransitionEdge = Edge<TransitionEdgeData>;

// XState machine configuration (subset used by builder)
export interface XStateMachineConfig {
  id: string;
  initial: string;
  context?: Record<string, unknown>;
  states: Record<string, XStateStateConfig>;
  meta?: {
    auto_triggers?: Record<string, Record<string, string>>;
    notifications?: Record<string, unknown[]>;
  };
}

export interface XStateStateConfig {
  type?: 'final' | 'parallel' | 'history';
  initial?: string;
  on?: Record<string, XStateTransition | XStateTransition[]>;
  entry?: string | string[];
  exit?: string | string[];
  states?: Record<string, XStateStateConfig>;
  after?: Record<string, XStateTransition>;
  history?: 'shallow' | 'deep';
}

export type XStateTransition = string | {
  target?: string;
  guard?: string;
  cond?: string;  // Legacy XState v4 format
  actions?: string | string[];
};

// React Flow config for import/export
export interface ReactFlowConfig {
  machineId: string;
  nodes: StateNode[];
  edges: TransitionEdge[];
  context?: Record<string, unknown>;
}

// API responses
export interface SaveMachineResponse {
  success: boolean;
  name: string;
  version: number;
}

export interface MachineListItem {
  machine_id: string;
  title: string;
  version: number;
  attached_doctype: string;
  modified: string;
}

// Guard and Action definitions
export interface GuardDefinition {
  name: string;
  description?: string;
  code?: string;
}

export interface ActionDefinition {
  name: string;
  type: 'entry' | 'exit' | 'transition';
  description?: string;
  code?: string;
}

// Props for components
export interface ToolbarProps {
  onAddState: () => void;
  onSave: () => void;
  onExport: () => void;
  onImport: () => void;
  onAutoLayout: () => void;
  machineId: string;
  machineTitle?: string;
  onMachineIdChange: (id: string) => void;
  isSaving: boolean;
  isNewWorkflow?: boolean;
  hasUnsavedChanges?: boolean;
  onOpenInDesk?: () => void;
  onSaveAs?: () => void;
}

export interface PropertiesPanelProps {
  selectedNode: StateNode | null;
  selectedEdge: TransitionEdge | null;
  onNodeUpdate: (id: string, data: Partial<StateNodeData>) => void;
  onEdgeUpdate: (id: string, data: Partial<TransitionEdgeData>) => void;
  onNodeDelete: (id: string) => void;
  onEdgeDelete: (id: string) => void;
  availableGuards: GuardDefinition[];
  availableActions: ActionDefinition[];
}
