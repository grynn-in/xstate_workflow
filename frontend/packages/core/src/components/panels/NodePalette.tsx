import { memo, useCallback, type DragEvent } from 'react';
import type { XStateNodeType } from '../../types';
import { STATE_COLORS } from '../../types';

export interface NodePaletteProps {
  onAddNode?: (type: XStateNodeType, position: { x: number; y: number }) => void;
}

interface PaletteItem {
  type: XStateNodeType;
  label: string;
  icon: string;
  description: string;
}

const PALETTE_ITEMS: PaletteItem[] = [
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

function NodePaletteComponent({ onAddNode }: NodePaletteProps) {
  const onDragStart = useCallback(
    (event: DragEvent<HTMLDivElement>, type: XStateNodeType) => {
      event.dataTransfer.setData('application/xstate-node-type', type);
      event.dataTransfer.effectAllowed = 'move';
    },
    []
  );

  const handleClick = useCallback(
    (type: XStateNodeType) => {
      // Add at default position when clicked
      onAddNode?.(type, { x: 250 + Math.random() * 100, y: 150 + Math.random() * 100 });
    },
    [onAddNode]
  );

  return (
    <div className="xsw-palette">
      <div className="xsw-palette-section">
        <div className="xsw-palette-title">States</div>
        {PALETTE_ITEMS.map((item) => (
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
              style={{ color: STATE_COLORS[item.type] }}
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
          <p style={{ marginBottom: '8px' }}>
            Drag nodes to the canvas or click to add.
          </p>
          <p style={{ marginBottom: '8px' }}>
            Connect states by dragging from one handle to another.
          </p>
          <p>
            Use compound states to create nested workflows.
          </p>
        </div>
      </div>
    </div>
  );
}

export const NodePalette = memo(NodePaletteComponent);
