import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { ThresholdGateNodeData } from '../../../types';

export interface ThresholdGateNodeProps {
  id: string;
  data: ThresholdGateNodeData;
  selected?: boolean;
}

const OPERATOR_LABELS: Record<string, string> = {
  gt: '>',
  gte: '≥',
  lt: '<',
  lte: '≤',
  eq: '=',
  ne: '≠',
};

function ThresholdGateNodeComponent({ data, selected }: ThresholdGateNodeProps) {
  const { label, threshold, checkType, methodCheck } = data;
  const isMethodCheck = checkType === 'method';

  // Build condition text based on check type
  let conditionText: string;
  if (isMethodCheck) {
    conditionText = methodCheck?.method ? `${methodCheck.method}()` : 'No method';
  } else {
    const operatorLabel = threshold ? OPERATOR_LABELS[threshold.operator] || threshold.operator : '';
    conditionText = threshold
      ? `${threshold.field} ${operatorLabel} ${threshold.value}`
      : 'No condition';
  }

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

      {/* Diamond shape container */}
      <div className="xsw-threshold-diamond">
        <div className="xsw-threshold-content">
          {/* Gate icon - different for method vs field */}
          <div className="xsw-threshold-icon">
            {isMethodCheck ? (
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M12 2L2 12l10 10 10-10L12 2zm0 15l-5-5 5-5 5 5-5 5z" />
              </svg>
            )}
          </div>
          <div className="xsw-threshold-label">{label || 'Gate'}</div>
        </div>
      </div>

      {/* Condition display */}
      <div className="xsw-threshold-condition">
        {isMethodCheck && <span style={{ color: '#8b5cf6', marginRight: '4px' }}>fn:</span>}
        {conditionText}
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
