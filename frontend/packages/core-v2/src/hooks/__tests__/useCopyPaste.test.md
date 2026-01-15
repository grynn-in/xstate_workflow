# useCopyPaste Hook Test Cases

## Initialization
| Test | Description |
|------|-------------|
| `should initialize with empty clipboard` | Verifies clipboard starts empty with no nodes or edges |
| `should not be able to paste initially` | Confirms `canPaste` is false when nothing has been copied |

## Copy
| Test | Description |
|------|-------------|
| `should copy a single selected node` | Copies one node when one is selected |
| `should copy multiple selected nodes` | Copies all nodes that are currently selected |
| `should copy edges between selected nodes` | Only copies edges where both source AND target nodes are selected |
| `should not copy edges if only one endpoint is selected` | Prevents copying dangling edges (edge with only one endpoint in selection) |
| `should do nothing if no nodes are selected` | No-op when trying to copy with empty selection |
| `should call onCopy callback after copying` | Triggers callback so parent can react (e.g., show toast) |

## Paste
| Test | Description |
|------|-------------|
| `should paste copied nodes with offset position` | Pasted nodes appear 50px right/down from original (configurable) |
| `should generate new IDs for pasted nodes` | Each paste creates unique IDs to avoid conflicts |
| `should update edge references to new node IDs` | Edges are rewired to point to the new node IDs |
| `should do nothing if clipboard is empty` | No-op when paste is called without prior copy |
| `should allow multiple pastes from same copy` | Copy once, paste many times - each with unique IDs |
| `should paste at specified position when provided` | `pasteAt({x, y})` places nodes at exact coordinates |

## Cut
| Test | Description |
|------|-------------|
| `should copy and call onCut callback` | Cut = copy + notify parent to delete originals |
| `should include edges for deletion when cutting` | Parent handles edge cleanup when node is deleted |
| `should do nothing if no nodes are selected` | No-op when trying to cut with empty selection |

## Clipboard State
| Test | Description |
|------|-------------|
| `should update canPaste when clipboard has content` | `canPaste` becomes true after successful copy |
| `should clear clipboard` | `clearClipboard()` empties the clipboard and sets `canPaste` to false |

## Preserving Node Properties
| Test | Description |
|------|-------------|
| `should preserve node data when copying` | Labels, descriptions, and custom data are retained |
| `should NOT preserve isInitial flag when pasting` | Prevents duplicate initial states (only one allowed) |
| `should preserve edge data when copying` | Edge events, guards, and metadata are retained |

## Selection Updates
| Test | Description |
|------|-------------|
| `should handle selection changes` | Copy reflects current selection, not stale selection |

---

## Hook API

```typescript
interface UseCopyPasteOptions {
  nodes: WorkflowNode[];           // All nodes in the workflow
  edges: WorkflowEdge[];           // All edges in the workflow
  selectedNodeIds?: string[];      // Currently selected node IDs
  pasteOffset?: { x: number; y: number };  // Default offset for paste (default: 50, 50)
  onCopy?: (nodes, edges) => void; // Callback after copy
  onPaste?: (nodes, edges) => void;// Callback to add pasted elements
  onCut?: (nodeIds) => void;       // Callback to delete cut elements
}

interface UseCopyPasteReturn {
  copy: () => void;                // Copy selected nodes/edges
  paste: () => void;               // Paste with default offset
  pasteAt: (position) => void;     // Paste at specific coordinates
  cut: () => void;                 // Copy and delete
  clearClipboard: () => void;      // Clear clipboard
  clipboardNodes: WorkflowNode[];  // Nodes in clipboard
  clipboardEdges: WorkflowEdge[];  // Edges in clipboard
  hasClipboardContent: boolean;    // True if clipboard has content
  canPaste: boolean;               // True if paste is possible
}
```
