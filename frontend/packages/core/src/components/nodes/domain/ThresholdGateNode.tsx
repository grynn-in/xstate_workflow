import { memo, useMemo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { ThresholdGateNodeData, CheckCondition } from '../../../types';

export interface ThresholdGateNodeProps {
  id: string;
  data: ThresholdGateNodeData;
  selected?: boolean;
}

const OPERATOR_LABELS: Record<string, string> = {
  gt: '>',
  gte: '\u2265',  // ≥
  lt: '<',
  lte: '\u2264',  // ≤
  eq: '=',
  ne: '\u2260',  // ≠
  contains: '\u2283',  // ⊃
  not_contains: '\u2285',  // ⊅
  starts_with: '^=',
  ends_with: '$=',
  in: '\u2208',  // ∈
  not_in: '\u2209',  // ∉
  is_set: '\u2260\u2205',  // ≠∅
  is_not_set: '=\u2205',  // =∅
};

// Format a single condition for display
function formatCondition(condition: CheckCondition): string {
  const opLabel = OPERATOR_LABELS[condition.operator] || condition.operator;

  if (condition.operator === 'is_set') {
    return `${condition.field} IS SET`;
  }
  if (condition.operator === 'is_not_set') {
    return `${condition.field} IS EMPTY`;
  }

  const value = condition.value !== undefined ? condition.value : '?';
  return `${condition.field} ${opLabel} ${value}`;
}

function ThresholdGateNodeComponent({ data, selected }: ThresholdGateNodeProps) {
  const { label, threshold, checkType, checkMode, methodCheck, conditions, conditionLogic } = data;

  // Determine effective mode (backward compatibility)
  const effectiveMode = useMemo(() => {
    if (checkMode) return checkMode;
    if (checkType === 'method') return 'method';
    return 'simple';
  }, [checkMode, checkType]);

  // Build condition display based on mode
  const { conditionLines, modeLabel } = useMemo(() => {
    if (effectiveMode === 'method') {
      const methodName = methodCheck?.method || 'method';
      return {
        conditionLines: [`${methodName}()`],
        modeLabel: 'fn',
      };
    }

    if (effectiveMode === 'compound') {
      const conds = conditions || [];
      if (conds.length === 0) {
        return {
          conditionLines: ['No conditions'],
          modeLabel: conditionLogic === 'or' ? 'OR' : 'AND',
        };
      }

      // Show first 2 conditions, then "+N more" if more exist
      const maxDisplay = 2;
      const displayConds = conds.slice(0, maxDisplay);
      const remaining = conds.length - maxDisplay;

      const lines = displayConds
        .filter(c => c.field)
        .map(c => formatCondition(c));

      if (remaining > 0) {
        lines.push(`+${remaining} more`);
      }

      if (lines.length === 0) {
        lines.push('Configure conditions');
      }

      return {
        conditionLines: lines,
        modeLabel: conditionLogic === 'or' ? 'OR' : 'AND',
      };
    }

    // Simple mode
    if (!threshold?.field) {
      return {
        conditionLines: ['No condition'],
        modeLabel: null,
      };
    }

    const operatorLabel = OPERATOR_LABELS[threshold.operator] || threshold.operator;
    return {
      conditionLines: [`${threshold.field} ${operatorLabel} ${threshold.value}`],
      modeLabel: null,
    };
  }, [effectiveMode, threshold, methodCheck, conditions, conditionLogic]);

  return (
    <div
      className={clsx(
        'xsw-domain-node',
        'xsw-threshold-node',
        selected && 'selected'
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="xsw-handle"
      />

      {/* Header with icon and label */}
      <div className="xsw-threshold-header">
        <span className="xsw-threshold-icon">
          {effectiveMode === 'method' ? (
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z" />
            </svg>
          ) : effectiveMode === 'compound' ? (
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M4 6h4v4H4zm0 8h4v4H4zm8-8h4v4h-4zm0 8h4v4h-4zm8-8h4v4h-4zm0 8h4v4h-4z" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M12 2L2 12l10 10 10-10L12 2z" />
            </svg>
          )}
        </span>
        <span className="xsw-threshold-label">{label || 'Gate'}</span>
      </div>

      {/* Condition display */}
      <div className="xsw-threshold-condition-container">
        {modeLabel && (
          <span
            className={clsx(
              'xsw-threshold-mode-badge',
              effectiveMode === 'method' && 'method',
              effectiveMode === 'compound' && 'compound'
            )}
          >
            {modeLabel}
          </span>
        )}
        <div className="xsw-threshold-conditions">
          {conditionLines.map((line, i) => (
            <div key={i} className="xsw-threshold-condition-line">
              {i > 0 && effectiveMode === 'compound' && conditionLines.length > 1 && !line.startsWith('+') && (
                <span className="xsw-condition-logic">{conditionLogic || 'and'}</span>
              )}
              <span className={line.startsWith('+') ? 'xsw-condition-more' : ''}>
                {line}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Pass/Fail handles */}
      <div className="xsw-threshold-outputs">
        <div className="xsw-threshold-output pass">
          <Handle
            type="source"
            position={Position.Bottom}
            id="pass"
            className="xsw-handle xsw-handle-pass"
            style={{ left: '25%' }}
          />
          <span className="xsw-output-label">Pass</span>
        </div>
        <div className="xsw-threshold-output fail">
          <Handle
            type="source"
            position={Position.Bottom}
            id="fail"
            className="xsw-handle xsw-handle-fail"
            style={{ left: '75%' }}
          />
          <span className="xsw-output-label">Fail</span>
        </div>
      </div>
    </div>
  );
}

export const ThresholdGateNode = memo(ThresholdGateNodeComponent);
