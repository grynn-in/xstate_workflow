import { memo, useCallback } from 'react';
import type { ThresholdGateNodeData, FrappeField } from '../../../types';

export interface ThresholdGatePanelProps {
  data: ThresholdGateNodeData;
  doctypeFields?: FrappeField[];
  onDataChange: (data: Partial<ThresholdGateNodeData>) => void;
}

const OPERATORS = [
  { value: 'gt', label: '> (Greater than)' },
  { value: 'gte', label: '>= (Greater or equal)' },
  { value: 'lt', label: '< (Less than)' },
  { value: 'lte', label: '<= (Less or equal)' },
  { value: 'eq', label: '= (Equal to)' },
  { value: 'ne', label: '!= (Not equal to)' },
];

function ThresholdGatePanelComponent({
  data,
  doctypeFields = [],
  onDataChange,
}: ThresholdGatePanelProps) {
  const handleThresholdChange = useCallback((updates: Partial<ThresholdGateNodeData['threshold']>) => {
    onDataChange({
      threshold: {
        ...data.threshold,
        field: data.threshold?.field || '',
        operator: data.threshold?.operator || 'gt',
        value: data.threshold?.value || 0,
        ...updates,
      },
    });
  }, [data.threshold, onDataChange]);

  // Numeric fields for threshold comparison
  const numericFields = doctypeFields.filter(f =>
    ['Int', 'Float', 'Currency', 'Percent'].includes(f.fieldtype)
  );

  return (
    <div className="xsw-domain-panel xsw-threshold-panel">
      <div className="xsw-panel-header">Threshold Gate Configuration</div>

      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Condition Field</div>
        <select
          className="xsw-select"
          value={data.threshold?.field || ''}
          onChange={(e) => handleThresholdChange({ field: e.target.value })}
        >
          <option value="">Select field...</option>
          {numericFields.map(field => (
            <option key={field.fieldname} value={field.fieldname}>
              {field.label} ({field.fieldtype})
            </option>
          ))}
        </select>
        <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
          Select a numeric field to compare against the threshold value
        </p>
      </div>

      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Operator</div>
        <select
          className="xsw-select"
          value={data.threshold?.operator || 'gt'}
          onChange={(e) => handleThresholdChange({
            operator: e.target.value as ThresholdGateNodeData['threshold']['operator']
          })}
        >
          {OPERATORS.map(op => (
            <option key={op.value} value={op.value}>{op.label}</option>
          ))}
        </select>
      </div>

      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Threshold Value</div>
        <input
          type="number"
          className="xsw-input"
          value={data.threshold?.value || 0}
          onChange={(e) => handleThresholdChange({ value: parseFloat(e.target.value) })}
        />
      </div>

      {/* Condition Preview */}
      <div className="xsw-panel-section" style={{ marginTop: '16px' }}>
        <div className="xsw-panel-section-title">Condition Preview</div>
        <div
          style={{
            padding: '12px',
            background: '#f3f4f6',
            borderRadius: '6px',
            fontFamily: 'monospace',
            fontSize: '14px',
          }}
        >
          {data.threshold?.field || 'field'}{' '}
          {OPERATORS.find(o => o.value === data.threshold?.operator)?.value || '>'}{' '}
          {data.threshold?.value || 0}
        </div>
      </div>

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Output Configuration */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title" style={{ color: '#22c55e' }}>
          Pass Output
        </div>
        <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
          When condition is TRUE, workflow proceeds via &quot;Pass&quot; output
        </p>
      </div>

      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title" style={{ color: '#ef4444' }}>
          Fail Output
        </div>
        <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
          When condition is FALSE, workflow proceeds via &quot;Fail&quot; output
        </p>
      </div>
    </div>
  );
}

export const ThresholdGatePanel = memo(ThresholdGatePanelComponent);
