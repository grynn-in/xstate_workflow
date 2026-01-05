import { memo } from 'react';
import { BaseStateNode, type BaseStateNodeProps } from './BaseStateNode';

function CompoundStateNodeComponent(props: BaseStateNodeProps) {
  const { data } = props;

  return (
    <BaseStateNode {...props}>
      <div className="xsw-compound-container">
        {data.initialChild && (
          <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
            Initial: {data.initialChild}
          </div>
        )}
        {/* Child nodes will be rendered by React Flow as nested nodes */}
        <div style={{ fontSize: '11px', color: '#9ca3af', fontStyle: 'italic' }}>
          Drop states here
        </div>
      </div>
    </BaseStateNode>
  );
}

export const CompoundStateNode = memo(CompoundStateNodeComponent);
