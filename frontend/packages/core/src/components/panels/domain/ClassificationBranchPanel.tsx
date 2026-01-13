import { memo, useCallback } from 'react';
import type { ClassificationBranchNodeData, FrappeField } from '../../../types';

export interface ClassificationBranchPanelProps {
  data: ClassificationBranchNodeData;
  doctypeFields?: FrappeField[];
  onDataChange: (data: Partial<ClassificationBranchNodeData>) => void;
}

function ClassificationBranchPanelComponent({
  data,
  doctypeFields = [],
  onDataChange,
}: ClassificationBranchPanelProps) {
  const handleFieldChange = useCallback((field: string) => {
    onDataChange({ field });
  }, [onDataChange]);

  const handleAddBranch = useCallback(() => {
    const value = prompt('Enter branch value (e.g., "High", "Low", "Category A"):');
    if (value && !data.branches?.some(b => b.value === value)) {
      onDataChange({
        branches: [...(data.branches || []), { value, label: value }],
      });
    }
  }, [data.branches, onDataChange]);

  const handleRemoveBranch = useCallback((value: string) => {
    onDataChange({
      branches: data.branches?.filter(b => b.value !== value) || [],
    });
  }, [data.branches, onDataChange]);

  const handleBranchLabelChange = useCallback((value: string, newLabel: string) => {
    onDataChange({
      branches: data.branches?.map(b =>
        b.value === value ? { ...b, label: newLabel } : b
      ) || [],
    });
  }, [data.branches, onDataChange]);

  // Select/Link fields that can be used for classification
  const classificationFields = doctypeFields.filter(f =>
    ['Select', 'Link', 'Data'].includes(f.fieldtype)
  );

  // Get options if the selected field is a Select
  const selectedField = doctypeFields.find(f => f.fieldname === data.field);
  const selectOptions = selectedField?.fieldtype === 'Select' && selectedField.options
    ? selectedField.options.split('\n').filter(Boolean)
    : [];

  return (
    <div className="xsw-domain-panel xsw-classification-panel">
      <div className="xsw-panel-header">Classification Branch Configuration</div>

      {/* Field Selection */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Classification Field</div>
        <select
          className="xsw-select"
          value={data.field || ''}
          onChange={(e) => handleFieldChange(e.target.value)}
        >
          <option value="">Select field...</option>
          {classificationFields.map(field => (
            <option key={field.fieldname} value={field.fieldname}>
              {field.label} ({field.fieldtype})
            </option>
          ))}
        </select>
        <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
          The workflow will branch based on this field's value
        </p>
      </div>

      {/* Quick add from Select options */}
      {selectOptions.length > 0 && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Quick Add from Field Options</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {selectOptions
              .filter(opt => !data.branches?.some(b => b.value === opt))
              .map(opt => (
                <button
                  key={opt}
                  className="xsw-button xsw-button-secondary"
                  style={{ fontSize: '12px', padding: '4px 8px' }}
                  onClick={() => onDataChange({
                    branches: [...(data.branches || []), { value: opt, label: opt }],
                  })}
                >
                  + {opt}
                </button>
              ))}
          </div>
        </div>
      )}

      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Branches */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Branches</div>
        {data.branches && data.branches.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {data.branches.map((branch, index) => (
              <div
                key={branch.value}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px',
                  background: '#f3f4f6',
                  borderRadius: '6px',
                }}
              >
                <span
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    background: `hsl(${index * 60}, 70%, 50%)`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: '12px',
                    fontWeight: 'bold',
                  }}
                >
                  {index + 1}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, fontSize: '14px' }}>{branch.value}</div>
                  <input
                    type="text"
                    className="xsw-input"
                    style={{ marginTop: '4px', fontSize: '12px' }}
                    placeholder="Display label (optional)"
                    value={branch.label || ''}
                    onChange={(e) => handleBranchLabelChange(branch.value, e.target.value)}
                  />
                </div>
                <button
                  className="xsw-button"
                  style={{
                    background: '#fee2e2',
                    color: '#991b1b',
                    padding: '4px 8px',
                    fontSize: '12px',
                  }}
                  onClick={() => handleRemoveBranch(branch.value)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: '#9ca3af', fontSize: '14px' }}>
            No branches defined. Add branches for each possible value.
          </p>
        )}

        <button
          className="xsw-button xsw-button-secondary"
          style={{ width: '100%', marginTop: '8px' }}
          onClick={handleAddBranch}
        >
          + Add Branch
        </button>
      </div>

      {/* Default Branch */}
      <div className="xsw-panel-section">
        <label className="xsw-checkbox">
          <input
            type="checkbox"
            checked={!!data.defaultTarget}
            onChange={(e) => onDataChange({
              defaultTarget: e.target.checked ? 'default' : undefined,
            })}
          />
          <span>Include default branch for unmatched values</span>
        </label>
      </div>
    </div>
  );
}

export const ClassificationBranchPanel = memo(ClassificationBranchPanelComponent);
