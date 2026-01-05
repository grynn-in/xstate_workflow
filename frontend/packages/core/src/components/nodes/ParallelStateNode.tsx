import { memo } from 'react';
import { BaseStateNode, type BaseStateNodeProps } from './BaseStateNode';

function ParallelStateNodeComponent(props: BaseStateNodeProps) {
  return (
    <BaseStateNode {...props}>
      <div className="xsw-parallel-regions">
        <div className="xsw-parallel-region">
          <div className="xsw-region-label">Region A</div>
          <div style={{ fontSize: '11px', color: '#9ca3af', fontStyle: 'italic' }}>
            Drop states here
          </div>
        </div>
        <div className="xsw-parallel-region">
          <div className="xsw-region-label">Region B</div>
          <div style={{ fontSize: '11px', color: '#9ca3af', fontStyle: 'italic' }}>
            Drop states here
          </div>
        </div>
      </div>
    </BaseStateNode>
  );
}

export const ParallelStateNode = memo(ParallelStateNodeComponent);
