import { memo, useCallback, useState, type DragEvent } from 'react';
import type { XStateNodeType, DomainNodeType } from '../../types';
import { STATE_COLORS, DOMAIN_NODE_COLORS } from '../../types';

export type PaletteMode = 'xstate' | 'domain';

export interface NodePaletteProps {
  mode?: PaletteMode;
  onModeChange?: (mode: PaletteMode) => void;
  onAddNode?: (type: XStateNodeType | DomainNodeType, position: { x: number; y: number }) => void;
}

interface PaletteItem {
  type: XStateNodeType | DomainNodeType;
  label: string;
  icon: string;
  description: string;
}

const XSTATE_PALETTE_ITEMS: PaletteItem[] = [
  {
    type: 'atomic',
    label: 'State',
    icon: '○',
    description: 'A basic workflow state. Documents move between states via transitions. Click or drag to add.',
  },
  {
    type: 'compound',
    label: 'Compound',
    icon: '▣',
    description: 'A parent state containing nested child states. Useful for grouping related states together.',
  },
  {
    type: 'parallel',
    label: 'Parallel',
    icon: '║',
    description: 'Multiple state regions that run simultaneously. All regions are active at the same time.',
  },
  {
    type: 'history',
    label: 'History',
    icon: 'Ⓗ',
    description: 'Remembers and returns to the previously active state. Use inside compound states.',
  },
  {
    type: 'final',
    label: 'Final',
    icon: '◉',
    description: 'An end state that marks the workflow as complete. No outgoing transitions allowed.',
  },
];

const DOMAIN_PALETTE_ITEMS: PaletteItem[] = [
  {
    type: 'start',
    label: 'Start',
    icon: '▶',
    description: 'The entry point where all workflows begin. Every workflow needs exactly one Start node.',
  },
  {
    type: 'approval',
    label: 'Approval',
    icon: '👤',
    description: 'A state requiring human approval. Creates tasks assigned to users/roles. Configure assignees in properties.',
  },
  {
    type: 'threshold_gate',
    label: 'Threshold Gate',
    icon: '◇',
    description: 'Branch based on a numeric comparison (e.g., amount > 10000). Routes to different paths based on value.',
  },
  {
    type: 'classification_branch',
    label: 'Classification',
    icon: '⬡',
    description: 'Branch based on a field value (e.g., type == "Urgent"). Creates multiple outgoing paths.',
  },
  {
    type: 'auto_action',
    label: 'Auto Action',
    icon: '⚡',
    description: 'Automatically executes actions: update fields, send emails, submit documents, call APIs.',
  },
  {
    type: 'end',
    label: 'End',
    icon: '⏹',
    description: 'The completion point of the workflow. Documents reaching this state are considered done.',
  },
];

function NodePaletteComponent({ mode: controlledMode, onModeChange, onAddNode }: NodePaletteProps) {
  const [internalMode, setInternalMode] = useState<PaletteMode>('domain');
  const mode = controlledMode ?? internalMode;

  const handleModeChange = useCallback((newMode: PaletteMode) => {
    if (onModeChange) {
      onModeChange(newMode);
    } else {
      setInternalMode(newMode);
    }
  }, [onModeChange]);

  const onDragStart = useCallback(
    (event: DragEvent<HTMLDivElement>, type: XStateNodeType | DomainNodeType) => {
      event.dataTransfer.setData('application/xstate-node-type', type);
      event.dataTransfer.effectAllowed = 'move';
    },
    []
  );

  const handleClick = useCallback(
    (type: XStateNodeType | DomainNodeType) => {
      onAddNode?.(type, { x: 250 + Math.random() * 100, y: 150 + Math.random() * 100 });
    },
    [onAddNode]
  );

  const items = mode === 'xstate' ? XSTATE_PALETTE_ITEMS : DOMAIN_PALETTE_ITEMS;
  const colors = mode === 'xstate' ? STATE_COLORS : DOMAIN_NODE_COLORS;

  return (
    <div className="xsw-palette">
      {/* Mode Toggle */}
      <div className="xsw-palette-section">
        <div className="xsw-palette-mode-toggle">
          <button
            className={`xsw-mode-btn ${mode === 'domain' ? 'active' : ''}`}
            onClick={() => handleModeChange('domain')}
            title="High-level workflow nodes: Approvals, Auto Actions, Gates. Recommended for most users."
          >
            Domain
          </button>
          <button
            className={`xsw-mode-btn ${mode === 'xstate' ? 'active' : ''}`}
            onClick={() => handleModeChange('xstate')}
            title="Low-level XState primitives: Atomic, Compound, Parallel, History, Final. For advanced users."
          >
            XState
          </button>
        </div>
      </div>

      <div className="xsw-palette-section">
        <div className="xsw-palette-title">
          {mode === 'xstate' ? 'States' : 'Workflow Nodes'}
        </div>
        {items.map((item) => (
          <div
            key={item.type}
            className="xsw-palette-item"
            draggable
            onDragStart={(e) => onDragStart(e, item.type)}
            onClick={() => handleClick(item.type)}
            title={item.description}
          >
            <span
              className="xsw-palette-icon"
              style={{ color: colors[item.type as keyof typeof colors] || '#6b7280' }}
            >
              {item.icon}
            </span>
            <span>{item.label}</span>
          </div>
        ))}
      </div>

      <div className="xsw-palette-section">
        <div className="xsw-palette-title">Tips</div>
        <div style={{ fontSize: '12px', color: '#6b7280', lineHeight: 1.5 }}>
          {mode === 'domain' ? (
            <>
              <p style={{ marginBottom: '8px' }}>
                Start with a <strong>Start</strong> node and end with an <strong>End</strong> node.
              </p>
              <p style={{ marginBottom: '8px' }}>
                Use <strong>Approval</strong> nodes for human decision points.
              </p>
              <p>
                <strong>Gates</strong> and <strong>Branches</strong> create conditional paths.
              </p>
            </>
          ) : (
            <>
              <p style={{ marginBottom: '8px' }}>
                Drag nodes to the canvas or click to add.
              </p>
              <p style={{ marginBottom: '8px' }}>
                Connect states by dragging from one handle to another.
              </p>
              <p>
                Use compound states to create nested workflows.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export const NodePalette = memo(NodePaletteComponent);
