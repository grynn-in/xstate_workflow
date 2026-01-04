// Auto-layout using Dagre

import dagre from 'dagre';
import type { Node, Edge } from '@xyflow/react';

const NODE_WIDTH = 180;
const NODE_HEIGHT = 60;

export function getLayoutedElements<T extends Record<string, unknown>, U extends Record<string, unknown>>(
  nodes: Node<T>[],
  edges: Edge<U>[],
  direction: 'LR' | 'TB' = 'LR'
): { nodes: Node<T>[]; edges: Edge<U>[] } {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 80,
    ranksep: 100,
    marginx: 50,
    marginy: 50
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2
      },
      targetPosition: isHorizontal ? 'left' : 'top',
      sourcePosition: isHorizontal ? 'right' : 'bottom'
    } as Node<T>;
  });

  return { nodes: layoutedNodes, edges };
}

export function getInitialNodePosition(existingNodes: Node[]): { x: number; y: number } {
  if (existingNodes.length === 0) {
    return { x: 100, y: 100 };
  }

  // Find the rightmost node and place new one to its right
  const maxX = Math.max(...existingNodes.map((n) => n.position.x));
  const avgY = existingNodes.reduce((sum, n) => sum + n.position.y, 0) / existingNodes.length;

  return {
    x: maxX + NODE_WIDTH + 100,
    y: avgY
  };
}
