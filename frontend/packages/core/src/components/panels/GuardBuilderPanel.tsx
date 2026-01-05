import { memo, useState, useCallback } from 'react';
import type { GuardConfig, SimpleGuardConfig, FrappeField } from '../../types';

export interface GuardBuilderPanelProps {
  guard?: GuardConfig;
  fields?: FrappeField[];
  onGuardChange: (guard: GuardConfig | undefined) => void;
  onClose: () => void;
}

type GuardMode = 'simple' | 'compound' | 'python';

const OPERATORS: Record<string, { label: string; types: string[] }> = {
  eq: { label: '= equals', types: ['Data', 'Link', 'Select', 'Int', 'Float', 'Currency', 'Date', 'Datetime'] },
  ne: { label: '!= not equals', types: ['Data', 'Link', 'Select', 'Int', 'Float', 'Currency', 'Date', 'Datetime'] },
  gt: { label: '> greater than', types: ['Int', 'Float', 'Currency', 'Date', 'Datetime'] },
  lt: { label: '< less than', types: ['Int', 'Float', 'Currency', 'Date', 'Datetime'] },
  gte: { label: '>= greater or equal', types: ['Int', 'Float', 'Currency', 'Date', 'Datetime'] },
  lte: { label: '<= less or equal', types: ['Int', 'Float', 'Currency', 'Date', 'Datetime'] },
  in: { label: 'in list', types: ['Data', 'Link', 'Select'] },
  contains: { label: 'contains', types: ['Data', 'Text', 'Small Text', 'Long Text'] },
  is_set: { label: 'is set', types: ['Data', 'Link', 'Select', 'Int', 'Float', 'Currency', 'Date', 'Datetime', 'Check'] },
  is_not_set: { label: 'is not set', types: ['Data', 'Link', 'Select', 'Int', 'Float', 'Currency', 'Date', 'Datetime', 'Check'] },
};

function getOperatorsForFieldType(fieldtype: string): string[] {
  return Object.entries(OPERATORS)
    .filter(([_, config]) => config.types.includes(fieldtype) || config.types.length === 0)
    .map(([key]) => key);
}

function generatePythonPreview(guard: GuardConfig): string {
  if (guard.type === 'python') {
    return guard.name;
  }

  if (guard.type === 'simple') {
    const { field, operator, value } = guard;
    switch (operator) {
      case 'eq': return `doc.${field} == ${JSON.stringify(value)}`;
      case 'ne': return `doc.${field} != ${JSON.stringify(value)}`;
      case 'gt': return `doc.${field} > ${value}`;
      case 'lt': return `doc.${field} < ${value}`;
      case 'gte': return `doc.${field} >= ${value}`;
      case 'lte': return `doc.${field} <= ${value}`;
      case 'in': return `doc.${field} in ${JSON.stringify(value)}`;
      case 'contains': return `${JSON.stringify(value)} in doc.${field}`;
      case 'is_set': return `doc.${field}`;
      case 'is_not_set': return `not doc.${field}`;
      default: return `doc.${field} ${operator} ${value}`;
    }
  }

  if (guard.type === 'compound') {
    const conditions = guard.conditions.map(c => generatePythonPreview(c));
    const joiner = guard.operator === 'and' ? ' and ' : ' or ';
    return `(${conditions.join(joiner)})`;
  }

  return '';
}

function GuardBuilderPanelComponent({
  guard,
  fields = [],
  onGuardChange,
  onClose,
}: GuardBuilderPanelProps) {
  const [mode, setMode] = useState<GuardMode>(guard?.type || 'simple');

  // Simple guard state
  const [simpleField, setSimpleField] = useState<string>(
    guard?.type === 'simple' ? guard.field : fields[0]?.fieldname || ''
  );
  const [simpleOperator, setSimpleOperator] = useState<SimpleGuardConfig['operator']>(
    guard?.type === 'simple' ? guard.operator : 'eq'
  );
  const [simpleValue, setSimpleValue] = useState<string>(
    guard?.type === 'simple' && guard.value !== undefined ? String(guard.value) : ''
  );

  // Compound guard state
  const [compoundOperator, setCompoundOperator] = useState<'and' | 'or'>(
    guard?.type === 'compound' ? guard.operator : 'and'
  );
  const [conditions, setConditions] = useState<SimpleGuardConfig[]>(
    guard?.type === 'compound'
      ? guard.conditions.filter((c): c is SimpleGuardConfig => c.type === 'simple')
      : []
  );

  // Python guard state
  const [pythonName, setPythonName] = useState<string>(
    guard?.type === 'python' ? guard.name : ''
  );
  const [pythonDescription, setPythonDescription] = useState<string>(
    guard?.type === 'python' ? guard.description || '' : ''
  );

  const selectedField = fields.find(f => f.fieldname === simpleField);
  const availableOperators = selectedField
    ? getOperatorsForFieldType(selectedField.fieldtype)
    : Object.keys(OPERATORS);

  const buildCurrentGuard = useCallback((): GuardConfig | undefined => {
    switch (mode) {
      case 'simple':
        if (!simpleField) return undefined;
        return {
          type: 'simple',
          field: simpleField,
          operator: simpleOperator,
          value: simpleValue || undefined,
        };
      case 'compound':
        if (conditions.length === 0) return undefined;
        return {
          type: 'compound',
          operator: compoundOperator,
          conditions,
        };
      case 'python':
        if (!pythonName) return undefined;
        return {
          type: 'python',
          name: pythonName,
          description: pythonDescription || undefined,
        };
      default:
        return undefined;
    }
  }, [mode, simpleField, simpleOperator, simpleValue, compoundOperator, conditions, pythonName, pythonDescription]);

  const handleSave = useCallback(() => {
    const newGuard = buildCurrentGuard();
    onGuardChange(newGuard);
    onClose();
  }, [buildCurrentGuard, onGuardChange, onClose]);

  const handleClear = useCallback(() => {
    onGuardChange(undefined);
    onClose();
  }, [onGuardChange, onClose]);

  const addCondition = useCallback(() => {
    const newCondition: SimpleGuardConfig = {
      type: 'simple',
      field: fields[0]?.fieldname || '',
      operator: 'eq',
      value: '',
    };
    setConditions([...conditions, newCondition]);
  }, [conditions, fields]);

  const updateCondition = useCallback((index: number, updates: Partial<SimpleGuardConfig>) => {
    const newConditions = [...conditions];
    newConditions[index] = { ...newConditions[index], ...updates };
    setConditions(newConditions);
  }, [conditions]);

  const removeCondition = useCallback((index: number) => {
    setConditions(conditions.filter((_, i) => i !== index));
  }, [conditions]);

  const currentGuard = buildCurrentGuard();
  const preview = currentGuard ? generatePythonPreview(currentGuard) : '';

  return (
    <div className="xsw-guard-builder">
      <div className="xsw-panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>Guard Builder</span>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px' }}
        >
          ×
        </button>
      </div>

      {/* Mode Selector */}
      <div className="xsw-panel-section">
        <div className="xsw-guard-mode-tabs" style={{ display: 'flex', gap: '4px', marginBottom: '12px' }}>
          {(['simple', 'compound', 'python'] as GuardMode[]).map((m) => (
            <button
              key={m}
              className={`xsw-button ${mode === m ? 'xsw-button-primary' : 'xsw-button-secondary'}`}
              style={{ flex: 1, textTransform: 'capitalize' }}
              onClick={() => setMode(m)}
            >
              {m}
            </button>
          ))}
        </div>

        {/* Simple Mode */}
        {mode === 'simple' && (
          <div className="xsw-guard-simple">
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Field
              </label>
              <select
                className="xsw-select"
                value={simpleField}
                onChange={(e) => setSimpleField(e.target.value)}
              >
                <option value="">Select field...</option>
                {fields.map((field) => (
                  <option key={field.fieldname} value={field.fieldname}>
                    {field.label} ({field.fieldtype})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Operator
              </label>
              <select
                className="xsw-select"
                value={simpleOperator}
                onChange={(e) => setSimpleOperator(e.target.value as SimpleGuardConfig['operator'])}
              >
                {availableOperators.map((op) => (
                  <option key={op} value={op}>
                    {OPERATORS[op].label}
                  </option>
                ))}
              </select>
            </div>

            {!['is_set', 'is_not_set'].includes(simpleOperator) && (
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                  Value
                </label>
                <input
                  type="text"
                  className="xsw-input"
                  value={simpleValue}
                  onChange={(e) => setSimpleValue(e.target.value)}
                  placeholder="Enter value..."
                />
              </div>
            )}
          </div>
        )}

        {/* Compound Mode */}
        {mode === 'compound' && (
          <div className="xsw-guard-compound">
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Combine conditions with
              </label>
              <select
                className="xsw-select"
                value={compoundOperator}
                onChange={(e) => setCompoundOperator(e.target.value as 'and' | 'or')}
              >
                <option value="and">AND (all must be true)</option>
                <option value="or">OR (any must be true)</option>
              </select>
            </div>

            {conditions.map((condition, index) => (
              <div
                key={index}
                style={{
                  padding: '8px',
                  background: '#f9fafb',
                  borderRadius: '4px',
                  marginBottom: '8px',
                  position: 'relative'
                }}
              >
                <button
                  onClick={() => removeCondition(index)}
                  style={{
                    position: 'absolute',
                    top: '4px',
                    right: '4px',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#dc3545'
                  }}
                >
                  ×
                </button>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <select
                    className="xsw-select"
                    value={condition.field}
                    onChange={(e) => updateCondition(index, { field: e.target.value })}
                  >
                    {fields.map((field) => (
                      <option key={field.fieldname} value={field.fieldname}>
                        {field.label}
                      </option>
                    ))}
                  </select>
                  <select
                    className="xsw-select"
                    value={condition.operator}
                    onChange={(e) => updateCondition(index, { operator: e.target.value as SimpleGuardConfig['operator'] })}
                  >
                    {Object.entries(OPERATORS).map(([key, config]) => (
                      <option key={key} value={key}>{config.label}</option>
                    ))}
                  </select>
                </div>
                {!['is_set', 'is_not_set'].includes(condition.operator) && (
                  <input
                    type="text"
                    className="xsw-input"
                    style={{ marginTop: '8px' }}
                    value={String(condition.value || '')}
                    onChange={(e) => updateCondition(index, { value: e.target.value })}
                    placeholder="Value..."
                  />
                )}
              </div>
            ))}

            <button
              className="xsw-button xsw-button-secondary"
              style={{ width: '100%' }}
              onClick={addCondition}
            >
              + Add Condition
            </button>
          </div>
        )}

        {/* Python Mode */}
        {mode === 'python' && (
          <div className="xsw-guard-python">
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Guard Function Name
              </label>
              <input
                type="text"
                className="xsw-input"
                value={pythonName}
                onChange={(e) => setPythonName(e.target.value)}
                placeholder="e.g., check_approval_limit"
              />
              <p style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
                Reference a Python function defined in XSM Guard doctype
              </p>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Description (optional)
              </label>
              <textarea
                className="xsw-input"
                rows={2}
                value={pythonDescription}
                onChange={(e) => setPythonDescription(e.target.value)}
                placeholder="What does this guard check?"
                style={{ resize: 'vertical' }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Preview */}
      {preview && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Preview</div>
          <pre style={{
            background: '#1f2937',
            color: '#10b981',
            padding: '8px 12px',
            borderRadius: '4px',
            fontSize: '12px',
            overflow: 'auto',
            margin: 0
          }}>
            {preview}
          </pre>
        </div>
      )}

      {/* Actions */}
      <div className="xsw-panel-section" style={{ display: 'flex', gap: '8px' }}>
        <button
          className="xsw-button xsw-button-secondary"
          style={{ flex: 1 }}
          onClick={handleClear}
        >
          Clear
        </button>
        <button
          className="xsw-button xsw-button-primary"
          style={{ flex: 1 }}
          onClick={handleSave}
          disabled={!currentGuard}
        >
          Save Guard
        </button>
      </div>
    </div>
  );
}

export const GuardBuilderPanel = memo(GuardBuilderPanelComponent);
