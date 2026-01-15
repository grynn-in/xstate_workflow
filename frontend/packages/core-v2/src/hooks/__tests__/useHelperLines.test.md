# useHelperLines Hook Test Cases

## Initialization
| Test | Description |
|------|-------------|
| `should initialize with no helper lines` | Verifies hook starts with empty horizontal and vertical line arrays |

## Horizontal Alignment Detection
| Test | Description |
|------|-------------|
| `should detect top edge alignment` | Shows horizontal line when dragged node's top aligns with another node's top |
| `should detect center horizontal alignment` | Shows horizontal line when vertical centers of nodes align |
| `should detect bottom edge alignment` | Shows horizontal line when dragged node's bottom aligns with another node's bottom |

## Vertical Alignment Detection
| Test | Description |
|------|-------------|
| `should detect left edge alignment` | Shows vertical line when dragged node's left aligns with another node's left |
| `should detect center vertical alignment` | Shows vertical line when horizontal centers of nodes align |
| `should detect right edge alignment` | Shows vertical line when dragged node's right aligns with another node's right |

## Threshold Behavior
| Test | Description |
|------|-------------|
| `should detect alignment within threshold` | Alignment detected when position is within threshold distance (e.g., 8px with threshold 10) |
| `should NOT detect alignment outside threshold` | No alignment when position is beyond threshold distance |
| `should use default threshold of 5 when not specified` | Default threshold is 5 pixels |

## Snapping
| Test | Description |
|------|-------------|
| `should return snapped position when enabled` | Returns exact aligned position when snapping is on |
| `should NOT snap when disabled` | Returns null for snapped position when snapping is off |
| `should snap to both axes independently` | Can snap X and Y independently if both are within threshold |

## Drag End Behavior
| Test | Description |
|------|-------------|
| `should clear helper lines on drag end` | Lines disappear when drag operation ends |
| `should clear snapped position on drag end` | Snapped position resets to null on drag end |

## Multiple Node Alignment
| Test | Description |
|------|-------------|
| `should detect alignment with multiple nodes` | Can align with any node in the workflow, not just one |
| `should not compare node with itself` | Dragging a node doesn't create alignment lines with itself |

## Line Extent Calculation
| Test | Description |
|------|-------------|
| `should calculate horizontal line extent across aligned nodes` | Line spans from leftmost to rightmost aligned node |
| `should calculate vertical line extent across aligned nodes` | Line spans from topmost to bottommost aligned node |

## Edge Cases
| Test | Description |
|------|-------------|
| `should handle nodes without measured dimensions` | Uses default dimensions (150x40) when node.measured is undefined |
| `should not detect lines when disabled` | No lines generated when `enabled: false` |

---

## Hook API

```typescript
interface UseHelperLinesOptions {
  nodes: NodeLike[];              // All nodes with id, position, measured
  threshold?: number;             // Distance for alignment detection (default: 5)
  enableSnapping?: boolean;       // Snap to aligned position (default: false)
  enabled?: boolean;              // Enable/disable feature (default: true)
  defaultNodeWidth?: number;      // Fallback width (default: 150)
  defaultNodeHeight?: number;     // Fallback height (default: 40)
}

interface UseHelperLinesReturn {
  horizontalLines: HorizontalLine[];   // Active horizontal alignment lines
  verticalLines: VerticalLine[];       // Active vertical alignment lines
  hasActiveLines: boolean;             // True if any lines are showing
  snappedPosition: Position | null;    // Snapped position if snapping enabled
  onNodeDrag: (nodeId, position) => void;  // Call during drag
  onNodeDragEnd: () => void;           // Call when drag ends
}

interface HorizontalLine {
  y: number;                      // Y position of line
  x1: number;                     // Start X
  x2: number;                     // End X
  type: 'top' | 'center' | 'bottom';
}

interface VerticalLine {
  x: number;                      // X position of line
  y1: number;                     // Start Y
  y2: number;                     // End Y
  type: 'left' | 'center' | 'right';
}
```

## Visual Example

```
Node A                    Node B (being dragged)
┌─────────┐              ┌─────────┐
│         │              │         │
│         │   ← ← ← ←    │         │  ← Dragging left
│         │              │         │
└─────────┘              └─────────┘
    ↑                        ↑
    └────────────────────────┘
         Vertical line appears when left edges align
```
