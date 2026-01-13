import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { ClassificationBranchNodeData } from '../../../types';

export interface ClassificationBranchNodeProps {
  id: string;
  data: ClassificationBranchNodeData;
  selected?: boolean;
}

function ClassificationBranchNodeComponent({ data, selected }: ClassificationBranchNodeProps) {
  const { label, field, branches, defaultTarget } = data;

  return (
    <div
      className={clsx(
        'xsw-domain-node',
        'xsw-classification-node',
        selected && 'selected'
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="xsw-handle"
      />

      {/* Hexagon shape header */}
      <div className="xsw-classification-header">
        <div className="xsw-classification-icon">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M12 2L4 7v10l8 5 8-5V7l-8-5zm0 2.18l5.5 3.43v6.78L12 17.82l-5.5-3.43V7.61L12 4.18z" />
          </svg>
        </div>
        <span className="xsw-classification-label">{label || 'Branch'}</span>
      </div>

      {/* Field being classified */}
      <div className="xsw-classification-field">
        <span className="xsw-field-label">Field:</span>
        <span className="xsw-field-value">{field || 'Not set'}</span>
      </div>

      {/* Separator */}
      <div className="xsw-node-separator" />

      {/* Branch list */}
      <div className="xsw-classification-branches">
        {branches && branches.length > 0 ? (
          branches.map((branch, index) => (
            <div key={branch.value || index} className="xsw-branch-item">
              <span className="xsw-branch-value">{branch.label || branch.value}</span>
              <Handle
                type="source"
                position={Position.Right}
                id={`branch-${branch.value}`}
                className="xsw-handle xsw-handle-branch"
                style={{ top: `${30 + index * 24}px` }}
              />
            </div>
          ))
        ) : (
          <div className="xsw-no-branches">No branches defined</div>
        )}

        {/* Default output */}
        {defaultTarget && (
          <div className="xsw-branch-item default">
            <span className="xsw-branch-value">Default</span>
            <Handle
              type="source"
              position={Position.Right}
              id="default"
              className="xsw-handle xsw-handle-default"
              style={{ top: `${30 + (branches?.length || 0) * 24}px` }}
            />
          </div>
        )}
      </div>

      {/* Bottom output for linear flow */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="xsw-handle"
      />
    </div>
  );
}

export const ClassificationBranchNode = memo(ClassificationBranchNodeComponent);
