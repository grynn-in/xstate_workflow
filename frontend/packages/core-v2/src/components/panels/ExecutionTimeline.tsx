import { memo, useCallback } from 'react';
import type { TimelineEntry } from '../../hooks/useExecutionTimeline';

/**
 * Props for ExecutionTimeline component
 */
export interface ExecutionTimelineProps {
  /** Timeline entries to display */
  entries: TimelineEntry[];
  /** Currently selected entry index */
  selectedIndex: number | null;
  /** Whether playback is at start */
  isAtStart: boolean;
  /** Whether playback is at end */
  isAtEnd: boolean;
  /** Callback when entry is clicked */
  onSelectEntry: (index: number) => void;
  /** Callback to go to previous entry */
  onPrevious: () => void;
  /** Callback to go to next entry */
  onNext: () => void;
  /** Callback to clear selection (go to current) */
  onClearSelection: () => void;
  /** Whether can go to previous */
  canGoPrevious: boolean;
  /** Whether can go to next */
  canGoNext: boolean;
}

/**
 * Format duration in human-readable form
 */
function formatDuration(ms: number | null): string {
  if (ms === null) return 'current';

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}d ${hours % 24}h`;
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
}

/**
 * Timeline marker component for a single entry
 */
const TimelineMarker = memo(function TimelineMarker({
  entry,
  isSelected,
  onClick,
}: {
  entry: TimelineEntry;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <div
      className={`xsw-timeline-marker ${isSelected ? 'xsw-timeline-marker-selected' : ''}`}
      style={{ left: `${entry.positionPercent}%` }}
      onClick={onClick}
      title={`${entry.event}: ${entry.fromState} → ${entry.toState}\n${entry.formattedTime}${entry.user ? `\nBy: ${entry.user}` : ''}`}
    >
      <div className="xsw-timeline-marker-dot" />
      <div className="xsw-timeline-marker-label">
        {entry.index + 1}
      </div>
    </div>
  );
});

/**
 * Entry detail card shown when an entry is selected
 */
const EntryDetail = memo(function EntryDetail({
  entry,
}: {
  entry: TimelineEntry;
}) {
  return (
    <div className="xsw-timeline-detail">
      <div className="xsw-timeline-detail-header">
        <span className="xsw-timeline-detail-event">{entry.event}</span>
        <span className="xsw-timeline-detail-time">{entry.formattedTime}</span>
      </div>
      <div className="xsw-timeline-detail-transition">
        <span className="xsw-timeline-detail-state">{entry.fromState}</span>
        <span className="xsw-timeline-detail-arrow">→</span>
        <span className="xsw-timeline-detail-state">{entry.toState}</span>
      </div>
      {entry.user && (
        <div className="xsw-timeline-detail-user">
          By: {entry.user}
        </div>
      )}
      {entry.durationMs !== null && (
        <div className="xsw-timeline-detail-duration">
          Duration in state: {formatDuration(entry.durationMs)}
        </div>
      )}
    </div>
  );
});

/**
 * Execution Timeline component for visualizing workflow transition history.
 *
 * Features:
 * - Horizontal timeline with markers for each transition
 * - Click markers to "time travel" and see workflow at that point
 * - Navigation buttons (previous/next/current)
 * - Entry detail card showing transition info
 *
 * @example
 * ```tsx
 * const timeline = useExecutionTimeline({ transitionLog, currentState });
 *
 * <ExecutionTimeline
 *   entries={timeline.entries}
 *   selectedIndex={timeline.selectedIndex}
 *   isAtStart={timeline.isAtStart}
 *   isAtEnd={timeline.isAtEnd}
 *   onSelectEntry={timeline.selectEntry}
 *   onPrevious={timeline.previousEntry}
 *   onNext={timeline.nextEntry}
 *   onClearSelection={timeline.clearSelection}
 *   canGoPrevious={timeline.canGoPrevious}
 *   canGoNext={timeline.canGoNext}
 * />
 * ```
 */
export const ExecutionTimeline = memo(function ExecutionTimeline({
  entries,
  selectedIndex,
  isAtStart,
  isAtEnd,
  onSelectEntry,
  onPrevious,
  onNext,
  onClearSelection,
  canGoPrevious,
  canGoNext,
}: ExecutionTimelineProps) {
  const handleMarkerClick = useCallback(
    (index: number) => {
      onSelectEntry(index);
    },
    [onSelectEntry]
  );

  if (entries.length === 0) {
    return (
      <div className="xsw-timeline xsw-timeline-empty">
        <div className="xsw-timeline-empty-message">
          No transitions yet
        </div>
      </div>
    );
  }

  const selectedEntry = selectedIndex !== null ? entries[selectedIndex] : null;

  return (
    <div className="xsw-timeline">
      {/* Timeline header */}
      <div className="xsw-timeline-header">
        <span className="xsw-timeline-title">Transition Timeline</span>
        <span className="xsw-timeline-count">
          {entries.length} transition{entries.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Timeline track */}
      <div className="xsw-timeline-track-container">
        <div className="xsw-timeline-track">
          <div className="xsw-timeline-track-line" />
          {entries.map((entry) => (
            <TimelineMarker
              key={entry.index}
              entry={entry}
              isSelected={entry.index === selectedIndex}
              onClick={() => handleMarkerClick(entry.index)}
            />
          ))}
        </div>
      </div>

      {/* Navigation controls */}
      <div className="xsw-timeline-controls">
        <button
          className="xsw-timeline-btn"
          onClick={onPrevious}
          disabled={!canGoPrevious}
          title="Previous transition"
        >
          &#x25C0;
        </button>
        <button
          className="xsw-timeline-btn"
          onClick={onClearSelection}
          disabled={selectedIndex === null}
          title="Go to current state"
        >
          &#x25CF;
        </button>
        <button
          className="xsw-timeline-btn"
          onClick={onNext}
          disabled={!canGoNext}
          title="Next transition"
        >
          &#x25B6;
        </button>
        {selectedIndex !== null && (
          <span className="xsw-timeline-position">
            Step {selectedIndex + 1} of {entries.length}
          </span>
        )}
      </div>

      {/* Selected entry detail */}
      {selectedEntry && <EntryDetail entry={selectedEntry} />}
    </div>
  );
});
