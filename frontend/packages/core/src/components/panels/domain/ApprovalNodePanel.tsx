import { memo, useState, useCallback, useEffect } from 'react';
import type {
  ApprovalNodeData,
  ResolverConfig,
  FrappeField,
} from '../../../types';

export interface ApprovalNodePanelProps {
  data: ApprovalNodeData;
  doctypeFields?: FrappeField[];
  availableRoles?: string[];
  availableDoctypes?: string[];
  availableUsers?: Array<{ name: string; full_name: string }>;
  onDataChange: (data: Partial<ApprovalNodeData>) => void;
  onFetchDoctypeFields?: (doctype: string) => Promise<FrappeField[]>;
}

function ApprovalNodePanelComponent({
  data,
  doctypeFields = [],
  availableRoles = [],
  availableDoctypes = [],
  availableUsers = [],
  onDataChange,
  onFetchDoctypeFields,
}: ApprovalNodePanelProps) {
  // Fields for the selected hierarchy doctype
  const [hierarchyDoctypeFields, setHierarchyDoctypeFields] = useState<FrappeField[]>([]);

  const handleResolverTypeChange = useCallback((type: ResolverConfig['type']) => {
    // Create default config for each resolver type
    let newResolver: ResolverConfig;

    switch (type) {
      case 'role':
        newResolver = { type: 'role', role: '', strategy: 'all' };
        break;
      case 'static_user':
        newResolver = { type: 'static_user', user_id: '' };
        break;
      case 'document_field':
        newResolver = { type: 'document_field', field_name: '' };
        break;
      case 'linked_doc_field':
        newResolver = { type: 'linked_doc_field', link_field: '', user_field: '' };
        break;
      case 'hierarchy_walk':
        newResolver = {
          type: 'hierarchy_walk',
          hierarchy_doctype: '',
          parent_field: '',
          user_field: '',
          start_from: 'owner',
          level_mode: 'fixed',
          levels_up: 1,
        };
        break;
      case 'delegation_matrix':
        newResolver = { type: 'delegation_matrix' };
        break;
      default:
        newResolver = { type };
        break;
    }

    onDataChange({ resolver: newResolver });
  }, [onDataChange]);

  const handleResolverConfigChange = useCallback((updates: Partial<ResolverConfig>) => {
    if (data.resolver) {
      onDataChange({
        resolver: { ...data.resolver, ...updates } as ResolverConfig,
      });
    }
  }, [data.resolver, onDataChange]);

  const handleActionsChange = useCallback((actions: string[]) => {
    onDataChange({ availableActions: actions });
  }, [onDataChange]);

  const handleAddAction = useCallback(() => {
    const action = prompt('Enter action name (e.g., Approve, Reject, Request Info):');
    if (action && !data.availableActions?.includes(action)) {
      onDataChange({
        availableActions: [...(data.availableActions || []), action],
      });
    }
  }, [data.availableActions, onDataChange]);

  const handleRemoveAction = useCallback((action: string) => {
    onDataChange({
      availableActions: data.availableActions?.filter(a => a !== action) || [],
    });
  }, [data.availableActions, onDataChange]);

  // Extract hierarchy doctype for dependency tracking
  const hierarchyDoctype = data.resolver?.type === 'hierarchy_walk'
    ? (data.resolver as { hierarchy_doctype?: string }).hierarchy_doctype
    : undefined;

  // Fetch fields when hierarchy doctype changes
  useEffect(() => {
    if (hierarchyDoctype && onFetchDoctypeFields) {
      onFetchDoctypeFields(hierarchyDoctype)
        .then(setHierarchyDoctypeFields)
        .catch(() => setHierarchyDoctypeFields([]));
    } else {
      setHierarchyDoctypeFields([]);
    }
  }, [hierarchyDoctype, onFetchDoctypeFields]);

  // User link fields from doctype
  const userLinkFields = doctypeFields.filter(f =>
    f.fieldtype === 'Link' && f.options === 'User'
  );

  // All link fields
  const linkFields = doctypeFields.filter(f => f.fieldtype === 'Link');

  // Fields from hierarchy doctype that link to parent records (self-referential)
  // For hierarchy walk, parent field should link back to the same doctype
  const hierarchyParentFields = hierarchyDoctypeFields.filter(f =>
    f.fieldtype === 'Link' && f.options === hierarchyDoctype
  );

  // All link fields from hierarchy doctype (fallback if no self-referential found)
  const hierarchyLinkFields = hierarchyDoctypeFields.filter(f => f.fieldtype === 'Link');

  // Fields from hierarchy doctype that link to User
  const hierarchyUserFields = hierarchyDoctypeFields.filter(f =>
    f.fieldtype === 'Link' && f.options === 'User'
  );

  // Use self-referential fields for parent, or fall back to all link fields
  const parentFieldOptions = hierarchyParentFields.length > 0 ? hierarchyParentFields : hierarchyLinkFields;

  // Boolean/Check fields from hierarchy doctype (for stop conditions)
  const hierarchyBooleanFields = hierarchyDoctypeFields.filter(f =>
    f.fieldtype === 'Check' || f.fieldtype === 'Data'
  );

  return (
    <div className="xsw-domain-panel xsw-approval-panel">
      <div className="xsw-panel-header">Approval Configuration</div>

      {/* Resolver Selection */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Assignment Resolver</div>
        <select
          className="xsw-select"
          value={data.resolver?.type || ''}
          onChange={(e) => handleResolverTypeChange(e.target.value as ResolverConfig['type'])}
        >
          <option value="">Select resolver type...</option>
          <optgroup label="Simple">
            <option value="role">Role-based</option>
            <option value="static_user">Static User</option>
            <option value="document_field">Document Field</option>
          </optgroup>
          <optgroup label="Linked Document">
            <option value="linked_doc_field">Linked Doc Field</option>
            <option value="cost_center_manager">Cost Center Manager</option>
            <option value="department_head">Department Head</option>
          </optgroup>
          <optgroup label="Hierarchy">
            <option value="hierarchy_walk">Hierarchy Walk</option>
            <option value="reporting_manager">Reporting Manager</option>
          </optgroup>
          <optgroup label="Advanced">
            <option value="delegation_matrix">Delegation Matrix</option>
          </optgroup>
        </select>
      </div>

      {/* Role Resolver Config */}
      {data.resolver?.type === 'role' && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Role</div>
          <select
            className="xsw-select"
            value={(data.resolver as { role: string }).role || ''}
            onChange={(e) => handleResolverConfigChange({ role: e.target.value })}
          >
            <option value="">Select role...</option>
            {availableRoles.map(role => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>

          <div className="xsw-panel-section-title" style={{ marginTop: '12px' }}>Strategy</div>
          <select
            className="xsw-select"
            value={(data.resolver as { strategy?: string }).strategy || 'all'}
            onChange={(e) => handleResolverConfigChange({ strategy: e.target.value })}
          >
            <option value="all">All users with role</option>
            <option value="round_robin">Round Robin</option>
            <option value="least_loaded">Least Loaded</option>
          </select>
        </div>
      )}

      {/* Static User Config */}
      {data.resolver?.type === 'static_user' && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">User</div>
          <select
            className="xsw-select"
            value={(data.resolver as { user_id: string }).user_id || ''}
            onChange={(e) => handleResolverConfigChange({ user_id: e.target.value })}
          >
            <option value="">Select user...</option>
            {availableUsers.map(user => (
              <option key={user.name} value={user.name}>
                {user.full_name || user.name} ({user.name})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Document Field Config */}
      {data.resolver?.type === 'document_field' && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">User Field</div>
          <select
            className="xsw-select"
            value={(data.resolver as { field_name: string }).field_name || ''}
            onChange={(e) => handleResolverConfigChange({ field_name: e.target.value })}
          >
            <option value="">Select field...</option>
            {userLinkFields.map(field => (
              <option key={field.fieldname} value={field.fieldname}>
                {field.label} ({field.fieldname})
              </option>
            ))}
            <option value="owner">Document Owner</option>
          </select>
        </div>
      )}

      {/* Linked Doc Field Config */}
      {data.resolver?.type === 'linked_doc_field' && (
        <div className="xsw-panel-section">
          <div className="xsw-panel-section-title">Link Field</div>
          <select
            className="xsw-select"
            value={(data.resolver as { link_field: string }).link_field || ''}
            onChange={(e) => handleResolverConfigChange({ link_field: e.target.value })}
          >
            <option value="">Select link field...</option>
            {linkFields.map(field => (
              <option key={field.fieldname} value={field.fieldname}>
                {field.label} → {field.options}
              </option>
            ))}
          </select>

          <div className="xsw-panel-section-title" style={{ marginTop: '12px' }}>User Field on Linked Doc</div>
          <input
            type="text"
            className="xsw-input"
            placeholder="e.g., manager, owner, custom_approver"
            value={(data.resolver as { user_field: string }).user_field || ''}
            onChange={(e) => handleResolverConfigChange({ user_field: e.target.value })}
          />
        </div>
      )}

      {/* Hierarchy Walk Config */}
      {data.resolver?.type === 'hierarchy_walk' && (
        <div className="xsw-panel-section">
          {/* Hierarchy Structure Section */}
          <div className="xsw-panel-section-title">Hierarchy Structure</div>
          <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '6px', marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
              Hierarchy DocType
            </label>
            <select
              className="xsw-select"
              value={(data.resolver as { hierarchy_doctype: string }).hierarchy_doctype || ''}
              onChange={(e) => handleResolverConfigChange({ hierarchy_doctype: e.target.value })}
              style={{ marginBottom: '8px' }}
            >
              <option value="">Select doctype...</option>
              {availableDoctypes.map(dt => (
                <option key={dt} value={dt}>{dt}</option>
              ))}
            </select>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                  Parent Field
                </label>
                <select
                  className="xsw-select"
                  value={(data.resolver as { parent_field: string }).parent_field || ''}
                  onChange={(e) => handleResolverConfigChange({ parent_field: e.target.value })}
                  disabled={!parentFieldOptions.length}
                >
                  <option value="">
                    {parentFieldOptions.length ? 'Select...' : 'Select doctype first'}
                  </option>
                  {parentFieldOptions.map(field => (
                    <option key={field.fieldname} value={field.fieldname}>
                      {field.label} → {field.options}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                  User Field
                </label>
                <select
                  className="xsw-select"
                  value={(data.resolver as { user_field: string }).user_field || ''}
                  onChange={(e) => handleResolverConfigChange({ user_field: e.target.value })}
                  disabled={!hierarchyUserFields.length}
                >
                  <option value="">
                    {hierarchyDoctypeFields.length
                      ? (hierarchyUserFields.length ? 'Select...' : 'No User link fields')
                      : 'Select doctype first'}
                  </option>
                  {hierarchyUserFields.map(field => (
                    <option key={field.fieldname} value={field.fieldname}>
                      {field.label} ({field.fieldname})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Walking Configuration Section */}
          <div className="xsw-panel-section-title">Walking Configuration</div>
          <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '6px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
              <div>
                <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                  Start From
                </label>
                <select
                  className="xsw-select"
                  value={(data.resolver as { start_from: string }).start_from || 'owner'}
                  onChange={(e) => handleResolverConfigChange({ start_from: e.target.value })}
                >
                  <option value="owner">Document Owner</option>
                  <option value="document_field">Document Field</option>
                  <option value="linked_doc">Linked Document</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                  Level Mode
                </label>
                <select
                  className="xsw-select"
                  value={(data.resolver as { level_mode: string }).level_mode || 'fixed'}
                  onChange={(e) => handleResolverConfigChange({ level_mode: e.target.value })}
                >
                  <option value="fixed">Fixed Levels</option>
                  <option value="until_condition">Until Condition</option>
                  <option value="all_up_to">All Up To</option>
                </select>
              </div>
            </div>

            {/* Start From: Document Field - show field selector */}
            {(data.resolver as { start_from: string }).start_from === 'document_field' && (
              <div style={{ marginBottom: '8px' }}>
                <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                  Start User Field
                </label>
                <select
                  className="xsw-select"
                  value={(data.resolver as { start_field?: string }).start_field || ''}
                  onChange={(e) => handleResolverConfigChange({ start_field: e.target.value })}
                >
                  <option value="">Select user field...</option>
                  {userLinkFields.map(field => (
                    <option key={field.fieldname} value={field.fieldname}>
                      {field.label} ({field.fieldname})
                    </option>
                  ))}
                  <option value="owner">Document Owner</option>
                </select>
              </div>
            )}

            {/* Start From: Linked Doc - show link field and user field */}
            {(data.resolver as { start_from: string }).start_from === 'linked_doc' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                    Link Field
                  </label>
                  <select
                    className="xsw-select"
                    value={(data.resolver as { start_link_field?: string }).start_link_field || ''}
                    onChange={(e) => handleResolverConfigChange({ start_link_field: e.target.value })}
                  >
                    <option value="">Select link field...</option>
                    {linkFields.map(field => (
                      <option key={field.fieldname} value={field.fieldname}>
                        {field.label} → {field.options}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                    User Field on Linked
                  </label>
                  <input
                    type="text"
                    className="xsw-input"
                    placeholder="e.g., owner, manager"
                    value={(data.resolver as { start_user_field?: string }).start_user_field || ''}
                    onChange={(e) => handleResolverConfigChange({ start_user_field: e.target.value })}
                  />
                </div>
              </div>
            )}

            {/* Level Mode: Fixed - show levels_up */}
            {((data.resolver as { level_mode?: string }).level_mode || 'fixed') === 'fixed' && (
              <div>
                <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                  Levels Up
                </label>
                <input
                  type="number"
                  className="xsw-input"
                  min="1"
                  max="10"
                  value={(data.resolver as { levels_up?: number }).levels_up || 1}
                  onChange={(e) => handleResolverConfigChange({ levels_up: parseInt(e.target.value, 10) })}
                  style={{ width: '80px' }}
                />
              </div>
            )}

            {/* Level Mode: All Up To - show max_levels */}
            {(data.resolver as { level_mode?: string }).level_mode === 'all_up_to' && (
              <div>
                <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                  Max Levels
                </label>
                <input
                  type="number"
                  className="xsw-input"
                  min="1"
                  max="10"
                  value={(data.resolver as { max_levels?: number }).max_levels || 5}
                  onChange={(e) => handleResolverConfigChange({ max_levels: parseInt(e.target.value, 10) })}
                  style={{ width: '80px' }}
                />
              </div>
            )}

            {/* Level Mode: Until Condition - show condition field */}
            {(data.resolver as { level_mode?: string }).level_mode === 'until_condition' && (
              <div>
                <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                  Stop When Field is True
                </label>
                <select
                  className="xsw-select"
                  value={(data.resolver as { stop_condition?: string }).stop_condition || ''}
                  onChange={(e) => handleResolverConfigChange({ stop_condition: e.target.value })}
                  disabled={!hierarchyBooleanFields.length}
                >
                  <option value="">
                    {hierarchyDoctypeFields.length
                      ? (hierarchyBooleanFields.length ? 'Select field...' : 'No Check/Data fields')
                      : 'Select doctype first'}
                  </option>
                  {hierarchyBooleanFields.map(field => (
                    <option key={field.fieldname} value={field.fieldname}>
                      {field.label} ({field.fieldname})
                    </option>
                  ))}
                </select>
                <p style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
                  Walking stops when this field is truthy (e.g., is_top_level = 1)
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Separator */}
      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Available Actions */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Available Actions</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '8px' }}>
          {data.availableActions?.length ? (
            data.availableActions.map((action) => (
              <span
                key={action}
                className="xsw-badge"
                style={{
                  background: action.toLowerCase() === 'approve' ? '#dcfce7' : action.toLowerCase() === 'reject' ? '#fee2e2' : '#e5e7eb',
                  color: action.toLowerCase() === 'approve' ? '#166534' : action.toLowerCase() === 'reject' ? '#991b1b' : '#374151',
                  cursor: 'pointer',
                }}
                onClick={() => handleRemoveAction(action)}
                title="Click to remove"
              >
                {action} ×
              </span>
            ))
          ) : (
            <span style={{ color: '#9ca3af', fontSize: '14px' }}>No actions defined</span>
          )}
        </div>
        <button
          className="xsw-button xsw-button-secondary"
          style={{ width: '100%' }}
          onClick={handleAddAction}
        >
          + Add Action
        </button>
      </div>

      {/* SLA Configuration */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">SLA (Hours)</div>
        <input
          type="number"
          className="xsw-input"
          min="0"
          step="0.5"
          placeholder="Optional - leave empty for no SLA"
          value={data.slaHours || ''}
          onChange={(e) => onDataChange({ slaHours: e.target.value ? parseFloat(e.target.value) : undefined })}
        />
      </div>

      {/* Priority */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Priority</div>
        <select
          className="xsw-select"
          value={data.priority || 'Medium'}
          onChange={(e) => onDataChange({ priority: e.target.value as ApprovalNodeData['priority'] })}
        >
          <option value="Low">Low</option>
          <option value="Medium">Medium</option>
          <option value="High">High</option>
          <option value="Urgent">Urgent</option>
        </select>
      </div>

      {/* Fallback User */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Fallback User</div>
        <input
          type="text"
          className="xsw-input"
          placeholder="User to assign if resolver fails"
          value={data.fallbackUser || ''}
          onChange={(e) => onDataChange({ fallbackUser: e.target.value || undefined })}
        />
      </div>
    </div>
  );
}

export const ApprovalNodePanel = memo(ApprovalNodePanelComponent);
