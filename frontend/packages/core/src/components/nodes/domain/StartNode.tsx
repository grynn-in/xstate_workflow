import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { StartNodeData } from '../../../types';

export interface StartNodeProps {
  id: string;
  data: StartNodeData;
  selected?: boolean;
}

function StartNodeComponent({ data, selected }: StartNodeProps) {
  return (
    <div
      className={clsx(
        'xsw-domain-node',
        'xsw-start-node',
        selected && 'selected'
      )}
    >
      {/* Circle with play icon */}
      <div className="xsw-start-circle">
        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
          <path d="M8 5v14l11-7z" />
        </svg>
      </div>

      {/* Label */}
      <div className="xsw-domain-label">{data.label || 'Start'}</div>

      {/* Output Handle only */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="xsw-handle"
      />
    </div>
  );
}

export const StartNode = memo(StartNodeComponent);
