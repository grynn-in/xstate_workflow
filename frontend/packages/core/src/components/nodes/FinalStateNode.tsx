import { memo } from 'react';
import { BaseStateNode, type BaseStateNodeProps } from './BaseStateNode';

function FinalStateNodeComponent(props: BaseStateNodeProps) {
  return <BaseStateNode {...props} />;
}

export const FinalStateNode = memo(FinalStateNodeComponent);
