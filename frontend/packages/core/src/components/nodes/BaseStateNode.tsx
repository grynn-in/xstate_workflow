import { memo, type ReactNode } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { WorkflowNodeData } from '../../types';

export interface BaseStateNodeProps {
  id: string;
  data: WorkflowNodeData;
  selected?: boolean;
  children?: ReactNode;
}

function BaseStateNodeComponent({ data, selected, children }: BaseStateNodeProps) {
  const { label, xstateType, isInitial, entryActions, exitActions, description } = data;

  const nodeType = isInitial ? 'initial' : xstateType;
  const entryCount = entryActions?.length || 0;
  const exitCount = exitActions?.length || 0;

  return (
    <div
      className={clsx(
        'xsw-node',
        nodeType,
        selected && 'selected'
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="xsw-handle"
      />

      {/* Node Header */}
      <div className="xsw-node-header">
        <div className={clsx('xsw-node-indicator', nodeType)} />
        <span className="xsw-node-label" title={label}>
          {label}
        </span>
        {xstateType === 'history' && (
          <span className="xsw-history-badge">
            {data.historyType === 'deep' ? 'H*' : 'H'}
          </span>
        )}
      </div>

      {/* Description */}
      {description && (
        <div className="xsw-node-description" style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
          {description}
        </div>
      )}

      {/* Separator */}
      {(entryCount > 0 || exitCount > 0) && <div className="xsw-node-separator" />}

      {/* Action Badges */}
      {(entryCount > 0 || exitCount > 0) && (
        <div className="xsw-node-badges">
          {entryCount > 0 && (
            <span className="xsw-badge xsw-badge-entry">
              entry: {entryCount}
            </span>
          )}
          {exitCount > 0 && (
            <span className="xsw-badge xsw-badge-exit">
              exit: {exitCount}
            </span>
          )}
        </div>
      )}

      {/* Additional content for compound/parallel states */}
      {children}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="xsw-handle"
      />
    </div>
  );
}

export const BaseStateNode = memo(BaseStateNodeComponent);
