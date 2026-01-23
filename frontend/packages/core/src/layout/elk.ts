/**
 * ELK-based layout algorithm for workflow graphs
 *
 * Uses ELKjs layered algorithm which is designed for directed graphs
 * like state machines and workflows.
 */

import Elk from 'elkjs/lib/elk.bundled.js';
import type { Node, Edge } from '@xyflow/react';
import type { LayoutOptions, LayoutResult, LayoutDirection } from './index';

const elk = new Elk();

// Default node dimensions if not measured
const DEFAULT_WIDTH = 250;
const DEFAULT_HEIGHT = 120;

/**
 * Convert layout direction to ELK direction
 */
function getElkDirection(direction: LayoutDirection): string {
  switch (direction) {
    case 'TB':
      return 'DOWN';
    case 'BT':
      return 'UP';
    case 'LR':
      return 'RIGHT';
    case 'RL':
      return 'LEFT';
    default:
      return 'RIGHT';
  }
}

/**
 * Apply ELK layout to React Flow nodes and edges
 */
export async function elkLayout<N extends Node = Node, E extends Edge = Edge>(
  nodes: N[],
  edges: E[],
  options: LayoutOptions
): Promise<LayoutResult<N, E>> {
  const [nodeNodeSpacing, layerSpacing] = options.spacing;

  const graph = {
    id: 'elk-root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': getElkDirection(options.direction),
      'elk.spacing.nodeNode': String(nodeNodeSpacing),
      'elk.layered.spacing.nodeNodeBetweenLayers': String(layerSpacing),
      // Additional options for better workflow layout
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
      'elk.edgeRouting': 'SPLINES',
    },
    children: nodes.map((node) => ({
      id: node.id,
      width: node.measured?.width ?? node.width ?? DEFAULT_WIDTH,
      height: node.measured?.height ?? node.height ?? DEFAULT_HEIGHT,
    })),
    edges: edges.map((edge) => ({
      id: edge.id,
      sources: [edge.source],
      targets: [edge.target],
    })),
  };

  const root = await elk.layout(graph);

  // Create a map for quick lookup of positioned nodes
  const layoutMap = new Map<string, { x: number; y: number }>();
  for (const child of root.children ?? []) {
    if (child.x !== undefined && child.y !== undefined) {
      layoutMap.set(child.id, { x: child.x, y: child.y });
    }
  }

  // Apply positions to nodes
  const layoutNodes = nodes.map((node) => {
    const position = layoutMap.get(node.id);
    if (position) {
      return {
        ...node,
        position: { x: position.x, y: position.y },
      };
    }
    return node;
  });

  return {
    nodes: layoutNodes as N[],
    edges,
  };
}
