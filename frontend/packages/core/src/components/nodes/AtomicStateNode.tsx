import { memo } from 'react';
import { BaseStateNode, type BaseStateNodeProps } from './BaseStateNode';

function AtomicStateNodeComponent(props: BaseStateNodeProps) {
  return <BaseStateNode {...props} />;
}

export const AtomicStateNode = memo(AtomicStateNodeComponent);
