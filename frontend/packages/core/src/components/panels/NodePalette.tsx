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
    description: 'Simple state with no children',
  },
  {
    type: 'compound',
    label: 'Compound',
    icon: '▣',
    description: 'State containing nested states',
  },
  {
    type: 'parallel',
    label: 'Parallel',
    icon: '║',
    description: 'Concurrent state regions',
  },
  {
    type: 'history',
    label: 'History',
    icon: 'Ⓗ',
    description: 'Remember last active state',
  },
  {
    type: 'final',
    label: 'Final',
    icon: '◉',
    description: 'Terminal state',
  },
];

const DOMAIN_PALETTE_ITEMS: PaletteItem[] = [
  {
    type: 'start',
    label: 'Start',
    icon: '▶',
    description: 'Workflow entry point',
  },
  {
    type: 'approval',
    label: 'Approval',
    icon: '👤',
    description: 'Human approval step with assignee resolution',
  },
  {
    type: 'threshold_gate',
    label: 'Threshold Gate',
    icon: '◇',
    description: 'Conditional branch based on numeric comparison',
  },
  {
    type: 'classification_branch',
    label: 'Classification',
    icon: '⬡',
    description: 'Multi-branch based on field value',
  },
  {
    type: 'auto_action',
    label: 'Auto Action',
    icon: '⚡',
    description: 'Automatic document action (submit, update, notify)',
  },
  {
    type: 'end',
    label: 'End',
    icon: '⏹',
    description: 'Workflow completion point',
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
          >
            Domain
          </button>
          <button
            className={`xsw-mode-btn ${mode === 'xstate' ? 'active' : ''}`}
            onClick={() => handleModeChange('xstate')}
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
