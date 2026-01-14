import { useState, useEffect, useCallback } from 'react';
import { listMachines, getDocTypes, type MachineListItem } from '@xstate-workflow/frappe-adapter';
import '@xstate-workflow/core/styles';

/**
 * Format a date string for display
 */
function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Status badge component
 */
function StatusBadge({ isActive }: { isActive: boolean }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 8px',
        borderRadius: '9999px',
        fontSize: '12px',
        fontWeight: 500,
        background: isActive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(107, 114, 128, 0.1)',
        color: isActive ? '#10b981' : '#6b7280',
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: isActive ? '#10b981' : '#9ca3af',
        }}
      />
      {isActive ? 'Active' : 'Inactive'}
    </span>
  );
}

/**
 * Empty state component
 */
function EmptyState({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="xsw-empty-state">
      <div style={{ fontSize: '48px', marginBottom: '16px' }}>
        {hasFilters ? '&#128269;' : '&#128221;'}
      </div>
      <h3>{hasFilters ? 'No workflows match your filters' : 'No workflows yet'}</h3>
      <p>
        {hasFilters
          ? 'Try adjusting your filters or create a new workflow.'
          : 'Create your first workflow to get started.'}
      </p>
      <a href="/xstate-builder" className="xsw-button xsw-button-primary">
        Create New Workflow
      </a>
    </div>
  );
}

/**
 * Workflow list item component
 */
function WorkflowItem({ machine }: { machine: MachineListItem }) {
  return (
    <a
      href={`/xstate-builder/${machine.machine_id}`}
      className="xsw-workflow-item"
    >
      <div className="xsw-workflow-item-main">
        <div className="xsw-workflow-item-title">
          {machine.title || machine.machine_id}
        </div>
        <div className="xsw-workflow-item-meta">
          {machine.attached_doctype && (
            <span className="xsw-workflow-item-doctype">
              {machine.attached_doctype}
            </span>
          )}
          <span className="xsw-workflow-item-version">v{machine.version}</span>
        </div>
      </div>
      <div className="xsw-workflow-item-right">
        <StatusBadge isActive={machine.is_active} />
        <div className="xsw-workflow-item-modified">
          {formatDate(machine.modified)}
        </div>
      </div>
    </a>
  );
}

/**
 * Dashboard Component
 *
 * Displays a list of all workflows with filtering capabilities.
 */
export function Dashboard() {
  const [machines, setMachines] = useState<MachineListItem[]>([]);
  const [doctypes, setDoctypes] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedDoctype, setSelectedDoctype] = useState<string>('');
  const [showInactive, setShowInactive] = useState(false);

  // Load data
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [machinesData, doctypesData] = await Promise.all([
        listMachines(selectedDoctype || undefined, showInactive),
        getDocTypes(),
      ]);

      setMachines(machinesData);
      setDoctypes(doctypesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workflows');
    } finally {
      setIsLoading(false);
    }
  }, [selectedDoctype, showInactive]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Get unique doctypes from machines for filter dropdown
  const attachedDoctypes = Array.from(
    new Set(machines.map((m) => m.attached_doctype).filter(Boolean))
  ).sort() as string[];

  // Use attached doctypes if available, otherwise fall back to all doctypes
  const filterDoctypes = attachedDoctypes.length > 0 ? attachedDoctypes : doctypes.slice(0, 50);

  const hasFilters = selectedDoctype !== '' || showInactive;

  return (
    <div className="xsw-dashboard">
      {/* Header */}
      <div className="xsw-dashboard-header">
        <div className="xsw-dashboard-header-left">
          <h1>Workflow Dashboard</h1>
          <span className="xsw-dashboard-count">
            {machines.length} workflow{machines.length !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="xsw-dashboard-header-right">
          <a href="/xstate-builder" className="xsw-button xsw-button-primary">
            + Create New
          </a>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="xsw-filter-bar">
        <div className="xsw-filter-group">
          <label htmlFor="doctype-filter">DocType:</label>
          <select
            id="doctype-filter"
            value={selectedDoctype}
            onChange={(e) => setSelectedDoctype(e.target.value)}
            className="xsw-select"
          >
            <option value="">All DocTypes</option>
            {filterDoctypes.map((dt) => (
              <option key={dt} value={dt}>
                {dt}
              </option>
            ))}
          </select>
        </div>

        <div className="xsw-filter-group">
          <label className="xsw-checkbox-label">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            Show inactive workflows
          </label>
        </div>

        {hasFilters && (
          <button
            className="xsw-button xsw-button-text"
            onClick={() => {
              setSelectedDoctype('');
              setShowInactive(false);
            }}
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Content */}
      <div className="xsw-dashboard-content">
        {isLoading ? (
          <div className="xsw-loading">
            <div className="xsw-loading-spinner" />
            <p>Loading workflows...</p>
          </div>
        ) : error ? (
          <div className="xsw-error">
            <h3>Error loading workflows</h3>
            <p>{error}</p>
            <button className="xsw-button xsw-button-secondary" onClick={loadData}>
              Retry
            </button>
          </div>
        ) : machines.length === 0 ? (
          <EmptyState hasFilters={hasFilters} />
        ) : (
          <div className="xsw-workflow-list">
            {machines.map((machine) => (
              <WorkflowItem key={machine.machine_id} machine={machine} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
