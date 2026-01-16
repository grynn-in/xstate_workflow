import { memo, useState, useCallback, useRef, useEffect, type ReactNode } from 'react';

export type PanelPosition = 'left' | 'right';

export interface ResizablePanelProps {
  children: ReactNode;
  position: PanelPosition;
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  collapsedWidth?: number;
  defaultCollapsed?: boolean;
  onWidthChange?: (width: number) => void;
  onCollapsedChange?: (collapsed: boolean) => void;
  className?: string;
}

function ResizablePanelComponent({
  children,
  position,
  defaultWidth = 250,
  minWidth = 150,
  maxWidth = 500,
  collapsedWidth = 0,
  defaultCollapsed = false,
  onWidthChange,
  onCollapsedChange,
  className = '',
}: ResizablePanelProps) {
  const [width, setWidth] = useState(defaultWidth);
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [isResizing, setIsResizing] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  // Handle resize start
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = width;
  }, [width]);

  // Handle resize move
  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = position === 'left'
        ? e.clientX - startXRef.current
        : startXRef.current - e.clientX;

      const newWidth = Math.min(maxWidth, Math.max(minWidth, startWidthRef.current + delta));
      setWidth(newWidth);
      onWidthChange?.(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, position, minWidth, maxWidth, onWidthChange]);

  // Handle collapse toggle
  const toggleCollapse = useCallback(() => {
    const newCollapsed = !isCollapsed;
    setIsCollapsed(newCollapsed);
    onCollapsedChange?.(newCollapsed);
  }, [isCollapsed, onCollapsedChange]);

  // Determine the actual width to use
  const actualWidth = isCollapsed ? collapsedWidth : width;

  return (
    <div
      ref={panelRef}
      className={`xsw-resizable-panel xsw-resizable-panel-${position} ${isCollapsed ? 'collapsed' : ''} ${className}`}
      style={{
        width: actualWidth,
        minWidth: isCollapsed ? collapsedWidth : minWidth,
      }}
    >
      {/* Collapse/Expand Button */}
      <button
        className={`xsw-panel-collapse-btn xsw-panel-collapse-btn-${position}`}
        onClick={toggleCollapse}
        title={isCollapsed ? 'Expand panel' : 'Collapse panel'}
      >
        {position === 'left'
          ? (isCollapsed ? '›' : '‹')
          : (isCollapsed ? '‹' : '›')
        }
      </button>

      {/* Panel Content */}
      {!isCollapsed && (
        <>
          <div className="xsw-resizable-panel-content">
            {children}
          </div>

          {/* Resize Handle */}
          <div
            className={`xsw-resize-handle xsw-resize-handle-${position}`}
            onMouseDown={handleResizeStart}
          />
        </>
      )}

      {/* Collapsed state indicator */}
      {isCollapsed && (
        <div className="xsw-collapsed-indicator" onClick={toggleCollapse}>
          <span className="xsw-collapsed-text">
            {position === 'left' ? 'Nodes' : 'Properties'}
          </span>
        </div>
      )}
    </div>
  );
}

export const ResizablePanel = memo(ResizablePanelComponent);
