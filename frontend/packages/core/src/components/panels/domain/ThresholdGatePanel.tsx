import { memo, useCallback, useMemo } from 'react';
import type {
  ThresholdGateNodeData,
  FrappeField,
  CheckCondition,
  CheckOperator,
} from '../../../types';
import { OPERATORS_BY_TYPE, FIELD_TYPE_CATEGORIES } from '../../../types';

export interface ThresholdGatePanelProps {
  data: ThresholdGateNodeData;
  doctypeFields?: FrappeField[];
  onDataChange: (data: Partial<ThresholdGateNodeData>) => void;
}

// Operator labels for display
const OPERATOR_LABELS: Record<CheckOperator, string> = {
  gt: '> (Greater than)',
  gte: '>= (Greater or equal)',
  lt: '< (Less than)',
  lte: '<= (Less or equal)',
  eq: '= (Equals)',
  ne: '!= (Not equal)',
  contains: 'Contains',
  not_contains: 'Does not contain',
  starts_with: 'Starts with',
  ends_with: 'Ends with',
  in: 'In list',
  not_in: 'Not in list',
  is_set: 'Is set (not empty)',
  is_not_set: 'Is not set (empty)',
};

// Simple mode operators (numeric only)
const SIMPLE_OPERATORS: Array<{ value: string; label: string }> = [
  { value: 'gt', label: '> (Greater than)' },
  { value: 'gte', label: '>= (Greater or equal)' },
  { value: 'lt', label: '< (Less than)' },
  { value: 'lte', label: '<= (Less or equal)' },
  { value: 'eq', label: '= (Equal to)' },
  { value: 'ne', label: '!= (Not equal to)' },
];

// Generate unique ID for conditions
function generateConditionId(): string {
  return `cond_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Get field type category
function getFieldCategory(fieldtype: string): string {
  return FIELD_TYPE_CATEGORIES[fieldtype] || 'text';
}

// Get operators for a field type
function getOperatorsForField(fieldtype: string): CheckOperator[] {
  const category = getFieldCategory(fieldtype);
  return OPERATORS_BY_TYPE[category] || OPERATORS_BY_TYPE.text;
}

function ThresholdGatePanelComponent({
  data,
  doctypeFields = [],
  onDataChange,
}: ThresholdGatePanelProps) {
  // Determine effective check mode (handle backward compatibility)
  const effectiveMode = useMemo(() => {
    if (data.checkMode) return data.checkMode;
    // Legacy: checkType === 'method' maps to 'method'
    if (data.checkType === 'method') return 'method';
    // Legacy: checkType === 'field' or undefined with threshold maps to 'simple'
    return 'simple';
  }, [data.checkMode, data.checkType]);

  // Handle mode change
  const handleModeChange = useCallback((newMode: 'simple' | 'compound' | 'method') => {
    onDataChange({
      checkMode: newMode,
      // Clear legacy field when explicitly setting mode
      checkType: undefined,
    });
  }, [onDataChange]);

  // Simple mode handlers
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

  // Compound mode handlers
  const handleConditionLogicChange = useCallback((logic: 'and' | 'or') => {
    onDataChange({ conditionLogic: logic });
  }, [onDataChange]);

  const handleAddCondition = useCallback(() => {
    const newCondition: CheckCondition = {
      id: generateConditionId(),
      field: '',
      operator: 'eq',
      value: '',
    };
    onDataChange({
      conditions: [...(data.conditions || []), newCondition],
    });
  }, [data.conditions, onDataChange]);

  const handleRemoveCondition = useCallback((conditionId: string) => {
    onDataChange({
      conditions: (data.conditions || []).filter(c => c.id !== conditionId),
    });
  }, [data.conditions, onDataChange]);

  const handleConditionChange = useCallback((conditionId: string, updates: Partial<CheckCondition>) => {
    onDataChange({
      conditions: (data.conditions || []).map(c =>
        c.id === conditionId ? { ...c, ...updates } : c
      ),
    });
  }, [data.conditions, onDataChange]);

  // Method mode handlers
  const handleMethodCheckChange = useCallback((updates: Partial<NonNullable<ThresholdGateNodeData['methodCheck']>>) => {
    onDataChange({
      methodCheck: {
        ...data.methodCheck,
        method: data.methodCheck?.method || '',
        ...updates,
      },
    });
  }, [data.methodCheck, onDataChange]);

  // Filter fields by type
  const numericFields = useMemo(() =>
    doctypeFields.filter(f => ['Int', 'Float', 'Currency', 'Percent'].includes(f.fieldtype)),
    [doctypeFields]
  );

  // All fields for compound mode
  const allFields = useMemo(() =>
    doctypeFields.filter(f =>
      !['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Button', 'Table'].includes(f.fieldtype)
    ),
    [doctypeFields]
  );

  // Build condition preview text
  const conditionPreview = useMemo(() => {
    if (effectiveMode === 'simple') {
      if (!data.threshold?.field) return 'No condition configured';
      const op = SIMPLE_OPERATORS.find(o => o.value === data.threshold?.operator)?.value || '>';
      return `${data.threshold.field} ${op} ${data.threshold.value}`;
    }

    if (effectiveMode === 'compound') {
      const conditions = data.conditions || [];
      if (conditions.length === 0) return 'No conditions configured';

      const logic = data.conditionLogic || 'and';
      const parts = conditions
        .filter(c => c.field)
        .map(c => {
          const opLabel = c.operator === 'is_set' ? 'IS SET'
            : c.operator === 'is_not_set' ? 'IS NOT SET'
            : `${OPERATOR_LABELS[c.operator]?.split(' ')[0] || c.operator} ${c.value ?? ''}`;
          return `${c.field} ${opLabel}`;
        });

      if (parts.length === 0) return 'No conditions configured';
      return parts.length === 1 ? parts[0] : `(${parts.join(` ${logic.toUpperCase()} `)})`;
    }

    if (effectiveMode === 'method') {
      return data.methodCheck?.method
        ? `doc.${data.methodCheck.method}()`
        : 'No method configured';
    }

    return 'Unknown mode';
  }, [effectiveMode, data.threshold, data.conditions, data.conditionLogic, data.methodCheck]);

  return (
    <div className="xsw-domain-panel xsw-threshold-panel">
      <div className="xsw-panel-header">Threshold Gate Configuration</div>

      {/* Mode Selection Tabs */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title" title="Choose how to evaluate the condition">
          Check Mode
        </div>
        <div className="xsw-mode-tabs">
          <button
            className={`xsw-mode-tab ${effectiveMode === 'simple' ? 'active' : ''}`}
            onClick={() => handleModeChange('simple')}
          >
            Simple
          </button>
          <button
            className={`xsw-mode-tab ${effectiveMode === 'compound' ? 'active' : ''}`}
            onClick={() => handleModeChange('compound')}
          >
            Multiple
          </button>
          <button
            className={`xsw-mode-tab ${effectiveMode === 'method' ? 'active' : ''}`}
            onClick={() => handleModeChange('method')}
          >
            Method
          </button>
        </div>
      </div>

      {/* ========== SIMPLE MODE ========== */}
      {effectiveMode === 'simple' && (
        <>
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title" title="Select a numeric field to compare">
              Condition Field
            </div>
            {doctypeFields.length === 0 ? (
              <p style={{ fontSize: '12px', color: '#f59e0b', marginTop: '4px', padding: '8px', background: '#fef3c7', borderRadius: '4px' }}>
                First select a DocType from the dropdown in the <strong>top toolbar</strong> to see available fields
              </p>
            ) : numericFields.length === 0 ? (
              <p style={{ fontSize: '12px', color: '#f59e0b', marginTop: '4px', padding: '8px', background: '#fef3c7', borderRadius: '4px' }}>
                No numeric fields found in this DocType. Use <strong>Multiple</strong> mode for text/other fields, or <strong>Method</strong> mode.
              </p>
            ) : (
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
            )}
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Operator</div>
            <select
              className="xsw-select"
              value={data.threshold?.operator || 'gt'}
              onChange={(e) => handleThresholdChange({
                operator: e.target.value as NonNullable<ThresholdGateNodeData['threshold']>['operator']
              })}
            >
              {SIMPLE_OPERATORS.map(op => (
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
        </>
      )}

      {/* ========== COMPOUND MODE ========== */}
      {effectiveMode === 'compound' && (
        <>
          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Condition Logic</div>
            <div className="xsw-logic-toggle">
              <label className="xsw-radio-option">
                <input
                  type="radio"
                  name="conditionLogic"
                  value="and"
                  checked={(data.conditionLogic || 'and') === 'and'}
                  onChange={() => handleConditionLogicChange('and')}
                />
                <span>ALL must match (AND)</span>
              </label>
              <label className="xsw-radio-option">
                <input
                  type="radio"
                  name="conditionLogic"
                  value="or"
                  checked={data.conditionLogic === 'or'}
                  onChange={() => handleConditionLogicChange('or')}
                />
                <span>ANY must match (OR)</span>
              </label>
            </div>
          </div>

          <div className="xsw-panel-section">
            <div className="xsw-panel-section-title">Conditions</div>

            {doctypeFields.length === 0 ? (
              <p style={{ fontSize: '12px', color: '#f59e0b', marginTop: '4px', padding: '8px', background: '#fef3c7', borderRadius: '4px' }}>
                First select a DocType from the dropdown in the <strong>top toolbar</strong> to see available fields
              </p>
            ) : (
              <>
                <div className="xsw-conditions-list">
                  {(data.conditions || []).map((condition, index) => (
                    <ConditionRow
                      key={condition.id}
                      condition={condition}
                      index={index}
                      fields={allFields}
                      onChange={(updates) => handleConditionChange(condition.id, updates)}
                      onRemove={() => handleRemoveCondition(condition.id)}
                    />
                  ))}
                </div>

                <button
                  className="xsw-button xsw-button-secondary xsw-add-condition-btn"
                  onClick={handleAddCondition}
                  style={{ marginTop: '8px', width: '100%' }}
                >
                  + Add Condition
                </button>

                {(data.conditions || []).length === 0 && (
                  <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px', textAlign: 'center' }}>
                    Add conditions to evaluate. All/Any must pass for the gate to allow passage.
                  </p>
                )}
              </>
            )}
          </div>
        </>
      )}

      {/* ========== METHOD MODE ========== */}
      {effectiveMode === 'method' && (
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

          {/* Method Example */}
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

      {/* Condition Preview */}
      <div className="xsw-panel-section" style={{ marginTop: '16px' }}>
        <div className="xsw-panel-section-title">Preview</div>
        <div
          style={{
            padding: '12px',
            background: '#f3f4f6',
            borderRadius: '6px',
            fontFamily: 'monospace',
            fontSize: '13px',
            wordBreak: 'break-word',
          }}
        >
          {conditionPreview}
        </div>
      </div>

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Output Configuration */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title" style={{ color: '#22c55e' }}>
          Pass Output
        </div>
        <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
          {effectiveMode === 'method'
            ? 'When method returns passed=True, workflow proceeds via "Pass" output'
            : effectiveMode === 'compound'
            ? `When ${data.conditionLogic === 'or' ? 'ANY' : 'ALL'} conditions are TRUE, workflow proceeds via "Pass" output`
            : 'When condition is TRUE, workflow proceeds via "Pass" output'
          }
        </p>
      </div>

      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title" style={{ color: '#ef4444' }}>
          Fail Output
        </div>
        <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px' }}>
          {effectiveMode === 'method'
            ? 'When method returns passed=False, workflow proceeds via "Fail" output'
            : effectiveMode === 'compound'
            ? `When ${data.conditionLogic === 'or' ? 'NONE' : 'ANY'} conditions are FALSE, workflow proceeds via "Fail" output`
            : 'When condition is FALSE, workflow proceeds via "Fail" output'
          }
        </p>
      </div>
    </div>
  );
}

// Condition Row Component
interface ConditionRowProps {
  condition: CheckCondition;
  index: number;
  fields: FrappeField[];
  onChange: (updates: Partial<CheckCondition>) => void;
  onRemove: () => void;
}

function ConditionRow({ condition, index, fields, onChange, onRemove }: ConditionRowProps) {
  // Get field info
  const selectedField = fields.find(f => f.fieldname === condition.field);
  const fieldtype = selectedField?.fieldtype || 'Data';
  const operators = getOperatorsForField(fieldtype);

  // Check if current operator needs a value
  const needsValue = condition.operator !== 'is_set' && condition.operator !== 'is_not_set';

  // Handle field change - reset operator if needed
  const handleFieldChange = (fieldname: string) => {
    const field = fields.find(f => f.fieldname === fieldname);
    const newFieldtype = field?.fieldtype || 'Data';
    const availableOps = getOperatorsForField(newFieldtype);

    // If current operator is not valid for new field type, reset to first available
    const newOperator = availableOps.includes(condition.operator)
      ? condition.operator
      : availableOps[0];

    onChange({
      field: fieldname,
      fieldType: newFieldtype,
      operator: newOperator,
    });
  };

  return (
    <div className="xsw-condition-row">
      <div className="xsw-condition-row-header">
        <span className="xsw-condition-number">{index + 1}</span>
        <button
          className="xsw-condition-remove"
          onClick={onRemove}
          title="Remove condition"
        >
          &times;
        </button>
      </div>

      <div className="xsw-condition-fields">
        {/* Field Selection */}
        <select
          className="xsw-select xsw-condition-field"
          value={condition.field || ''}
          onChange={(e) => handleFieldChange(e.target.value)}
        >
          <option value="">Select field...</option>
          {fields.map(field => (
            <option key={field.fieldname} value={field.fieldname}>
              {field.label}
            </option>
          ))}
        </select>

        {/* Operator Selection */}
        <select
          className="xsw-select xsw-condition-operator"
          value={condition.operator || 'eq'}
          onChange={(e) => onChange({ operator: e.target.value as CheckOperator })}
        >
          {operators.map(op => (
            <option key={op} value={op}>{OPERATOR_LABELS[op]}</option>
          ))}
        </select>

        {/* Value Input */}
        {needsValue && (
          <input
            className="xsw-input xsw-condition-value"
            placeholder="Value"
            value={condition.value !== undefined ? String(condition.value) : ''}
            onChange={(e) => {
              // Try to parse as number if it looks like one
              const val = e.target.value;
              const numVal = parseFloat(val);
              onChange({
                value: !isNaN(numVal) && val === String(numVal) ? numVal : val
              });
            }}
          />
        )}
      </div>
    </div>
  );
}

export const ThresholdGatePanel = memo(ThresholdGatePanelComponent);
