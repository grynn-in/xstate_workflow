/**
 * Auto-layout algorithm for workflow nodes
 *
 * Creates a left-to-right flow layout similar to n8n:
 * - Initial state on the left
 * - States flow left to right based on transition depth
 * - Branching paths spread vertically
 * - Final/terminal states on the right
 */

import type { XStateMachineConfig, XStateStateConfig } from '../types';

interface LayoutConfig {
  nodeWidth: number;
  nodeHeight: number;
  horizontalGap: number;
  verticalGap: number;
  startX: number;
  startY: number;
}

const DEFAULT_CONFIG: LayoutConfig = {
  nodeWidth: 250,
  nodeHeight: 120,
  horizontalGap: 200,  // Much more horizontal space
  verticalGap: 120,    // Much more vertical space
  startX: 50,
  startY: 50,
};

/**
 * Calculate positions for all nodes in a workflow
 */
export function calculateAutoLayout(
  xstate: XStateMachineConfig,
  config: Partial<LayoutConfig> = {}
): Map<string, { x: number; y: number }> {
  const layoutConfig = { ...DEFAULT_CONFIG, ...config };
  const positions = new Map<string, { x: number; y: number }>();

  if (!xstate.states) {
    return positions;
  }

  // Build forward and reverse graphs
  const { forwardGraph, reverseGraph } = buildGraphs(xstate.states);

  // Identify terminal states (final states or states with no outgoing transitions)
  const terminalStates = findTerminalStates(xstate.states, forwardGraph);

  // Calculate levels using modified BFS that respects workflow flow
  const levels = calculateLevels(xstate.states, xstate.initial, forwardGraph, terminalStates);

  // Group nodes by level and sort within each level
  const levelGroups = groupByLevel(levels);

  // Sort nodes within each level to minimize edge crossings
  sortNodesWithinLevels(levelGroups, forwardGraph, reverseGraph);

  // Calculate positions with improved spacing
  calculatePositions(levelGroups, layoutConfig, positions);

  // Handle parallel state children
  handleParallelStates(xstate.states, positions, layoutConfig);

  return positions;
}

/**
 * Build forward and reverse transition graphs
 */
function buildGraphs(
  states: Record<string, XStateStateConfig>
): { forwardGraph: Map<string, Set<string>>; reverseGraph: Map<string, Set<string>> } {
  const forwardGraph = new Map<string, Set<string>>();
  const reverseGraph = new Map<string, Set<string>>();

  // Initialize all states
  for (const stateName of Object.keys(states)) {
    forwardGraph.set(stateName, new Set());
    reverseGraph.set(stateName, new Set());
  }

  for (const [stateName, stateConfig] of Object.entries(states)) {
    const targets = extractAllTargets(stateConfig);

    for (const target of targets) {
      if (target && states[target]) {
        forwardGraph.get(stateName)!.add(target);
        reverseGraph.get(target)!.add(stateName);
      }
    }
  }

  return { forwardGraph, reverseGraph };
}

/**
 * Extract all target states from a state config
 */
function extractAllTargets(stateConfig: XStateStateConfig): string[] {
  const targets: string[] = [];

  // Process "on" transitions
  if (stateConfig.on) {
    for (const transition of Object.values(stateConfig.on)) {
      targets.push(...extractTargets(transition));
    }
  }

  // Process "always" transitions
  if (stateConfig.always) {
    const alwaysArray = Array.isArray(stateConfig.always)
      ? stateConfig.always
      : [stateConfig.always];
    for (const transition of alwaysArray) {
      targets.push(...extractTargets(transition));
    }
  }

  // Process "after" (delayed) transitions
  if (stateConfig.after) {
    for (const transition of Object.values(stateConfig.after)) {
      targets.push(...extractTargets(transition));
    }
  }

  return targets;
}

/**
 * Extract target state names from a transition
 */
function extractTargets(transition: unknown): string[] {
  if (!transition) return [];

  if (typeof transition === 'string') {
    return [transition];
  }

  if (Array.isArray(transition)) {
    return transition.flatMap(t => extractTargets(t));
  }

  if (typeof transition === 'object' && transition !== null) {
    const t = transition as { target?: string };
    if (t.target) {
      return [t.target];
    }
  }

  return [];
}

/**
 * Find terminal states (final states or no outgoing transitions)
 */
function findTerminalStates(
  states: Record<string, XStateStateConfig>,
  forwardGraph: Map<string, Set<string>>
): Set<string> {
  const terminal = new Set<string>();

  for (const [stateName, stateConfig] of Object.entries(states)) {
    const isFinal = stateConfig.type === 'final';
    const hasNoOutgoing = (forwardGraph.get(stateName)?.size || 0) === 0;

    // Also check for common terminal state names
    const isTerminalName = ['approved', 'rejected', 'cancelled', 'completed', 'done', 'end', 'final'].some(
      term => stateName.toLowerCase().includes(term)
    );

    if (isFinal || hasNoOutgoing || isTerminalName) {
      terminal.add(stateName);
    }
  }

  return terminal;
}

/**
 * Calculate the level (column) of each state
 * Uses longest path from initial state to properly space out the workflow
 */
function calculateLevels(
  states: Record<string, XStateStateConfig>,
  initial: string,
  forwardGraph: Map<string, Set<string>>,
  terminalStates: Set<string>
): Map<string, number> {
  const levels = new Map<string, number>();

  // Use DFS to find longest path to each node (for better spacing)
  function dfs(state: string, currentLevel: number, visited: Set<string>) {
    // Update level if this path is longer
    const existingLevel = levels.get(state) ?? -1;
    if (currentLevel > existingLevel) {
      levels.set(state, currentLevel);
    }

    // Prevent infinite loops but allow revisiting at deeper levels
    if (visited.has(state)) {
      return;
    }

    const newVisited = new Set(visited);
    newVisited.add(state);

    const targets = forwardGraph.get(state) || new Set();
    for (const target of targets) {
      if (states[target]) {
        dfs(target, currentLevel + 1, newVisited);
      }
    }
  }

  // Start DFS from initial state
  if (initial && states[initial]) {
    dfs(initial, 0, new Set());
  }

  // Handle unreachable states
  let maxLevel = Math.max(0, ...levels.values());
  for (const stateName of Object.keys(states)) {
    if (!levels.has(stateName)) {
      // Put unreachable states at the end
      levels.set(stateName, ++maxLevel);
    }
  }

  // Push terminal states to the rightmost appropriate column
  const terminalLevel = maxLevel;
  for (const terminal of terminalStates) {
    const currentLevel = levels.get(terminal) || 0;
    // Only move if it would go further right
    if (currentLevel < terminalLevel) {
      levels.set(terminal, terminalLevel);
    }
  }

  return levels;
}

/**
 * Group states by their level
 */
function groupByLevel(levels: Map<string, number>): Map<number, string[]> {
  const groups = new Map<number, string[]>();

  for (const [state, level] of levels.entries()) {
    if (!groups.has(level)) {
      groups.set(level, []);
    }
    groups.get(level)!.push(state);
  }

  return groups;
}

/**
 * Sort nodes within each level to minimize edge crossings
 */
function sortNodesWithinLevels(
  levelGroups: Map<number, string[]>,
  forwardGraph: Map<string, Set<string>>,
  reverseGraph: Map<string, Set<string>>
): void {
  const sortedLevels = Array.from(levelGroups.keys()).sort((a, b) => a - b);

  for (let i = 0; i < sortedLevels.length; i++) {
    const level = sortedLevels[i];
    const nodes = levelGroups.get(level)!;

    if (i === 0) {
      // First level: sort alphabetically
      nodes.sort();
    } else {
      // Subsequent levels: sort by average position of predecessors
      const prevLevel = sortedLevels[i - 1];
      const prevNodes = levelGroups.get(prevLevel) || [];
      const prevPositions = new Map<string, number>();
      prevNodes.forEach((n, idx) => prevPositions.set(n, idx));

      nodes.sort((a, b) => {
        const aPreds = reverseGraph.get(a) || new Set();
        const bPreds = reverseGraph.get(b) || new Set();

        const aAvg = average([...aPreds].map(p => prevPositions.get(p) ?? 0));
        const bAvg = average([...bPreds].map(p => prevPositions.get(p) ?? 0));

        return aAvg - bAvg;
      });
    }
  }
}

/**
 * Calculate average of numbers
 */
function average(nums: number[]): number {
  if (nums.length === 0) return 0;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

/**
 * Calculate actual positions for each node
 */
function calculatePositions(
  levelGroups: Map<number, string[]>,
  config: LayoutConfig,
  positions: Map<string, { x: number; y: number }>
): void {
  // Calculate total height needed
  const maxNodesInLevel = Math.max(...Array.from(levelGroups.values()).map(g => g.length));
  const totalHeight = maxNodesInLevel * config.nodeHeight + (maxNodesInLevel - 1) * config.verticalGap;

  for (const [level, states] of levelGroups.entries()) {
    const x = config.startX + level * (config.nodeWidth + config.horizontalGap);

    // Center this column's nodes vertically
    const columnHeight = states.length * config.nodeHeight + (states.length - 1) * config.verticalGap;
    const startY = config.startY + (totalHeight - columnHeight) / 2;

    for (let i = 0; i < states.length; i++) {
      const y = startY + i * (config.nodeHeight + config.verticalGap);
      positions.set(states[i], { x, y });
    }
  }
}

/**
 * Handle parallel states - position their children within regions
 */
function handleParallelStates(
  states: Record<string, XStateStateConfig>,
  positions: Map<string, { x: number; y: number }>,
  config: LayoutConfig
): void {
  for (const [stateName, stateConfig] of Object.entries(states)) {
    if (stateConfig.type !== 'parallel' || !stateConfig.states) continue;

    const parentPos = positions.get(stateName);
    if (!parentPos) continue;

    const regions = Object.entries(stateConfig.states);
    const regionHeight = 200;

    let regionY = parentPos.y + 60;

    for (const [regionName, regionConfig] of regions) {
      if (!regionConfig.states) continue;

      const childStates = Object.keys(regionConfig.states);
      let childX = parentPos.x + 40;

      for (const childName of childStates) {
        const fullPath = `${stateName}.${regionName}.${childName}`;
        positions.set(fullPath, { x: childX, y: regionY + 40 });
        positions.set(childName, { x: childX, y: regionY + 40 });
        childX += config.nodeWidth + 40;
      }

      regionY += regionHeight;
    }
  }
}

/**
 * Apply layout to an existing workflow config
 */
export function applyAutoLayout(
  xstate: XStateMachineConfig,
  existingPositions?: Map<string, { x: number; y: number }>
): Map<string, { x: number; y: number }> {
  if (existingPositions && existingPositions.size > 0) {
    const stateCount = Object.keys(xstate.states || {}).length;
    const positionedCount = existingPositions.size;

    if (positionedCount >= stateCount * 0.5) {
      return existingPositions;
    }
  }

  return calculateAutoLayout(xstate);
}
