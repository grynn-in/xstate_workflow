import { memo } from 'react';
import { BaseStateNode, type BaseStateNodeProps } from './BaseStateNode';

function HistoryStateNodeComponent(props: BaseStateNodeProps) {
  return <BaseStateNode {...props} />;
}

export const HistoryStateNode = memo(HistoryStateNodeComponent);
