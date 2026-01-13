import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { EndNodeData } from '../../../types';

export interface EndNodeProps {
  id: string;
  data: EndNodeData;
  selected?: boolean;
}

function EndNodeComponent({ data, selected }: EndNodeProps) {
  return (
    <div
      className={clsx(
        'xsw-domain-node',
        'xsw-end-node',
        selected && 'selected'
      )}
    >
      {/* Input Handle only */}
      <Handle
        type="target"
        position={Position.Top}
        className="xsw-handle"
      />

      {/* Double circle (stop icon) */}
      <div className="xsw-end-circle">
        <div className="xsw-end-inner-circle" />
      </div>

      {/* Label */}
      <div className="xsw-domain-label">{data.label || 'End'}</div>

      {/* Final status badge */}
      {data.finalStatus && (
        <div className="xsw-status-badge">{data.finalStatus}</div>
      )}
    </div>
  );
}

export const EndNode = memo(EndNodeComponent);
