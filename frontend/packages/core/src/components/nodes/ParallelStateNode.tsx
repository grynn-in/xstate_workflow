import { memo, useState } from 'react';
import { BaseStateNode, type BaseStateNodeProps } from './BaseStateNode';

function ParallelStateNodeComponent(props: BaseStateNodeProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { regions } = props.data;

  // Default regions if none defined
  const displayRegions = regions && regions.length > 0
    ? regions
    : [
        { name: 'region_a', label: 'Region A', childStates: [] },
        { name: 'region_b', label: 'Region B', childStates: [] },
      ];

  const totalStates = displayRegions.reduce(
    (sum, r) => sum + (r.childStates?.length || 0),
    0
  );

  return (
    <BaseStateNode {...props}>
      {/* Collapsible header */}
      <div
        className="xsw-parallel-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
        style={{ cursor: 'pointer', userSelect: 'none' }}
      >
        <span className="xsw-parallel-toggle-icon">
          {isExpanded ? '▼' : '▶'}
        </span>
        <span className="xsw-parallel-toggle-label">
          {displayRegions.length} regions, {totalStates} states
        </span>
      </div>

      {/* Expanded regions */}
      {isExpanded && (
        <div className="xsw-parallel-regions">
          {displayRegions.map((region) => (
            <div key={region.name} className="xsw-parallel-region">
              <div className="xsw-region-label">
                {region.label || region.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </div>
              {region.childStates && region.childStates.length > 0 ? (
                <div style={{ fontSize: '11px', color: '#6b7280' }}>
                  {region.childStates.length} state{region.childStates.length !== 1 ? 's' : ''}
                  {region.initial && (
                    <span style={{ marginLeft: '4px', color: '#22c55e' }}>
                      (→{region.initial})
                    </span>
                  )}
                </div>
              ) : (
                <div style={{ fontSize: '11px', color: '#9ca3af', fontStyle: 'italic' }}>
                  Empty region
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </BaseStateNode>
  );
}

export const ParallelStateNode = memo(ParallelStateNodeComponent);
