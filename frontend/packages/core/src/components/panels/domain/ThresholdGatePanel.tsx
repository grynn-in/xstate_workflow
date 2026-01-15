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
  const checkType = data.checkType || 'field';

  const handleCheckTypeChange = useCallback((newType: 'field' | 'method') => {
    onDataChange({ checkType: newType });
  }, [onDataChange]);

  const handleThresholdChange = useCallback((updates: Partial<NonNullable<ThresholdGateNodeData['threshold']>>) => {
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

  const handleMethodCheckChange = useCallback((updates: Partial<NonNullable<ThresholdGateNodeData['methodCheck']>>) => {
    onDataChange({
      methodCheck: {
        ...data.methodCheck,
        method: data.methodCheck?.method || '',
        ...updates,
      },
    });
  }, [data.methodCheck, onDataChange]);

  // Numeric fields for threshold comparison
  const numericFields = doctypeFields.filter(f =>
    ['Int', 'Float', 'Currency', 'Percent'].includes(f.fieldtype)
  );

  return (
    <div className="xsw-domain-panel xsw-threshold-panel">
      <div className="xsw-panel-header">Threshold Gate Configuration</div>

      {/* Check Type Selection */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title" title="Choose how to evaluate the condition">Check Type</div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <label className="xsw-radio" style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
            <input
              type="radio"
              name="checkType"
              value="field"
              checked={checkType === 'field'}
              onChange={() => handleCheckTypeChange('field')}
            />
            <span>Field Comparison</span>
          </label>
          <label className="xsw-radio" style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
            <input
              type="radio"
              name="checkType"
              value="method"
              checked={checkType === 'method'}
              onChange={() => handleCheckTypeChange('method')}
            />
            <span>Method Call</span>
          </label>
        </div>
      </div>

      {/* Field Comparison Mode */}
      {checkType === 'field' && (
        <>
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title" title="Select a numeric field from the DocType to compare">Condition Field</div>
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
            <div className="xsw-panel-section-title" title="Comparison operator for the condition">Operator</div>
            <select
              className="xsw-select"
              value={data.threshold?.operator || 'gt'}
              onChange={(e) => handleThresholdChange({
                operator: e.target.value as NonNullable<ThresholdGateNodeData['threshold']>['operator']
              })}
            >
              {OPERATORS.map(op => (
                <option key={op.value} value={op.value}>{op.label}</option>
              ))}
            </select>
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title" title="The value to compare the field against">Threshold Value</div>
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
        </>
      )}

      {/* Method Call Mode */}
      {checkType === 'method' && (
        <>
          <div className="xsw-panel-section">
            <div
              className="xsw-panel-section-title"
              title="Document method that returns {passed: bool, details: dict} or just a boolean"
            >
              Method Name
            </div>
            <input
              className="xsw-input"
              placeholder="check_credit_limit"
              value={data.methodCheck?.method || ''}
              onChange={(e) => handleMethodCheckChange({ method: e.target.value })}
            />
            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
              Method on the document that returns a boolean or {'{passed: bool, details: {...}}'}
            </p>
          </div>

          <div className="xsw-panel-section">
            <div
              className="xsw-panel-section-title"
              title="Store the method result in workflow context under this key (optional)"
            >
              Store Result In (optional)
            </div>
            <input
              className="xsw-input"
              placeholder="credit_check_result"
              value={data.methodCheck?.storeResultIn || ''}
              onChange={(e) => handleMethodCheckChange({ storeResultIn: e.target.value })}
            />
            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
              Store detailed results in workflow context for use in subsequent states
            </p>
          </div>

          {/* Method Preview */}
          <div className="xsw-panel-section" style={{ marginTop: '16px' }}>
            <div className="xsw-panel-section-title">Method Call Preview</div>
            <div
              style={{
                padding: '12px',
                background: '#f3f4f6',
                borderRadius: '6px',
                fontFamily: 'monospace',
                fontSize: '14px',
              }}
            >
              doc.{data.methodCheck?.method || 'method_name'}()
            </div>
          </div>

          {/* Example */}
          <div className="xsw-panel-section" style={{ marginTop: '8px' }}>
            <div className="xsw-panel-section-title">Expected Method Format</div>
            <pre
              style={{
                padding: '12px',
                background: '#1e293b',
                color: '#e2e8f0',
                borderRadius: '6px',
                fontSize: '11px',
                overflow: 'auto',
                margin: 0,
              }}
            >
{`def ${data.methodCheck?.method || 'check_condition'}(self):
    # Return dict with details
    return {
        "passed": True,
        "details": {
            "reason": "...",
            "value": 123
        }
    }
    # Or just return bool
    # return True`}
            </pre>
          </div>
        </>
      )}

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Output Configuration */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title" style={{ color: '#22c55e' }}>
          Pass Output
        </div>
        <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
          {checkType === 'method'
            ? 'When method returns passed=True, workflow proceeds via "Pass" output'
            : 'When condition is TRUE, workflow proceeds via "Pass" output'
          }
        </p>
      </div>

      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title" style={{ color: '#ef4444' }}>
          Fail Output
        </div>
        <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
          {checkType === 'method'
            ? 'When method returns passed=False, workflow proceeds via "Fail" output'
            : 'When condition is FALSE, workflow proceeds via "Fail" output'
          }
        </p>
      </div>
    </div>
  );
}

export const ThresholdGatePanel = memo(ThresholdGatePanelComponent);
