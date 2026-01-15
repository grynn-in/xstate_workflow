import { memo, useCallback } from 'react';
import type {
  ParallelApprovalNodeData,
  ParallelApprover,
  ResolverConfig,
  FrappeField,
} from '../../../types';

export interface ParallelApprovalPanelProps {
  data: ParallelApprovalNodeData;
  doctypeFields?: FrappeField[];
  availableRoles?: string[];
  onDataChange: (data: Partial<ParallelApprovalNodeData>) => void;
}

function ParallelApprovalPanelComponent({
  data,
  doctypeFields = [],
  availableRoles = [],
  onDataChange,
}: ParallelApprovalPanelProps) {
  // User link fields from doctype
  const userLinkFields = doctypeFields.filter(f =>
    f.fieldtype === 'Link' && f.options === 'User'
  );

  const handleAddApprover = useCallback(() => {
    const newApprover: ParallelApprover = {
      id: `approver_${Date.now()}`,
      label: `Approver ${(data.approvers?.length || 0) + 1}`,
      resolver: { type: 'role', role: '' },
      required: true,
    };
    onDataChange({
      approvers: [...(data.approvers || []), newApprover],
    });
  }, [data.approvers, onDataChange]);

  const handleRemoveApprover = useCallback((id: string) => {
    onDataChange({
      approvers: data.approvers?.filter(a => a.id !== id) || [],
    });
  }, [data.approvers, onDataChange]);

  const handleApproverChange = useCallback((id: string, updates: Partial<ParallelApprover>) => {
    onDataChange({
      approvers: data.approvers?.map(a =>
        a.id === id ? { ...a, ...updates } : a
      ) || [],
    });
  }, [data.approvers, onDataChange]);

  const handleResolverTypeChange = useCallback((approverId: string, type: ResolverConfig['type']) => {
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
        newResolver = { type: 'hierarchy_walk', hierarchy_doctype: '', parent_field: '', user_field: '', start_from: 'owner', level_mode: 'fixed' };
        break;
      case 'delegation_matrix':
        newResolver = { type: 'delegation_matrix' };
        break;
      case 'cost_center_manager':
        newResolver = { type: 'cost_center_manager' };
        break;
      case 'department_head':
        newResolver = { type: 'department_head' };
        break;
      case 'reporting_manager':
        newResolver = { type: 'reporting_manager' };
        break;
    }
    handleApproverChange(approverId, { resolver: newResolver });
  }, [handleApproverChange]);

  const handleResolverConfigChange = useCallback((approverId: string, updates: Partial<ResolverConfig>) => {
    const approver = data.approvers?.find(a => a.id === approverId);
    if (approver) {
      handleApproverChange(approverId, {
        resolver: { ...approver.resolver, ...updates } as ResolverConfig,
      });
    }
  }, [data.approvers, handleApproverChange]);

  return (
    <div className="xsw-domain-panel xsw-parallel-approval-panel">
      <div className="xsw-panel-header">Parallel Approval Configuration</div>

      {/* Approvers List */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Approvers</div>

        {data.approvers?.length ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {data.approvers.map((approver, index) => (
              <div
                key={approver.id}
                style={{
                  padding: '12px',
                  background: '#f8fafc',
                  borderRadius: '6px',
                  border: '1px solid #e2e8f0',
                }}
              >
                {/* Approver Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ fontWeight: 600, color: '#374151' }}>#{index + 1}</span>
                  <input
                    type="text"
                    className="xsw-input"
                    style={{ flex: 1 }}
                    placeholder="Approver label"
                    value={approver.label}
                    onChange={(e) => handleApproverChange(approver.id, { label: e.target.value })}
                  />
                  <button
                    className="xsw-button xsw-button-secondary"
                    style={{ padding: '4px 8px', minWidth: 'auto' }}
                    onClick={() => handleRemoveApprover(approver.id)}
                    title="Remove approver"
                  >
                    ×
                  </button>
                </div>

                {/* Required Toggle */}
                <label className="xsw-checkbox" style={{ marginBottom: '8px' }}>
                  <input
                    type="checkbox"
                    checked={approver.required}
                    onChange={(e) => handleApproverChange(approver.id, { required: e.target.checked })}
                  />
                  <span>Required approver</span>
                </label>

                {/* Resolver Type */}
                <div style={{ marginBottom: '8px' }}>
                  <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                    Resolver Type
                  </label>
                  <select
                    className="xsw-select"
                    value={approver.resolver?.type || ''}
                    onChange={(e) => handleResolverTypeChange(approver.id, e.target.value as ResolverConfig['type'])}
                  >
                    <option value="">Select...</option>
                    <option value="role">Role-based</option>
                    <option value="static_user">Static User</option>
                    <option value="document_field">Document Field</option>
                    <option value="reporting_manager">Reporting Manager</option>
                    <option value="department_head">Department Head</option>
                  </select>
                </div>

                {/* Resolver Config */}
                {approver.resolver?.type === 'role' && (
                  <div>
                    <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                      Role
                    </label>
                    <select
                      className="xsw-select"
                      value={(approver.resolver as { role: string }).role || ''}
                      onChange={(e) => handleResolverConfigChange(approver.id, { role: e.target.value })}
                    >
                      <option value="">Select role...</option>
                      {availableRoles.map(role => (
                        <option key={role} value={role}>{role}</option>
                      ))}
                    </select>
                  </div>
                )}

                {approver.resolver?.type === 'static_user' && (
                  <div>
                    <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                      User ID
                    </label>
                    <input
                      type="text"
                      className="xsw-input"
                      placeholder="user@example.com"
                      value={(approver.resolver as { user_id: string }).user_id || ''}
                      onChange={(e) => handleResolverConfigChange(approver.id, { user_id: e.target.value })}
                    />
                  </div>
                )}

                {approver.resolver?.type === 'document_field' && (
                  <div>
                    <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
                      User Field
                    </label>
                    <select
                      className="xsw-select"
                      value={(approver.resolver as { field_name: string }).field_name || ''}
                      onChange={(e) => handleResolverConfigChange(approver.id, { field_name: e.target.value })}
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
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: '#9ca3af', fontSize: '14px', textAlign: 'center', padding: '16px' }}>
            No approvers configured
          </div>
        )}

        <button
          className="xsw-button xsw-button-secondary"
          style={{ width: '100%', marginTop: '12px' }}
          onClick={handleAddApprover}
        >
          + Add Approver
        </button>
      </div>

      {/* Separator */}
      <div className="xsw-node-separator" style={{ margin: '16px 0' }} />

      {/* Completion Rule */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Completion Rule</div>
        <select
          className="xsw-select"
          value={data.completionRule || 'all_required'}
          onChange={(e) => onDataChange({ completionRule: e.target.value as ParallelApprovalNodeData['completionRule'] })}
        >
          <option value="all_required">All required must approve</option>
          <option value="any_one">Any one can approve</option>
          <option value="quorum">Quorum (N of M)</option>
        </select>

        {data.completionRule === 'quorum' && (
          <div style={{ marginTop: '8px' }}>
            <label style={{ fontSize: '12px', color: '#6b7280', display: 'block', marginBottom: '4px' }}>
              Required approvals
            </label>
            <input
              type="number"
              className="xsw-input"
              min="1"
              max={data.approvers?.length || 1}
              value={data.quorumCount || 1}
              onChange={(e) => onDataChange({ quorumCount: parseInt(e.target.value, 10) })}
            />
            <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
              {data.quorumCount || 1} of {data.approvers?.length || 0} must approve
            </div>
          </div>
        )}
      </div>

      {/* On Reject Behavior */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">On Rejection</div>
        <select
          className="xsw-select"
          value={data.onReject || 'reject_all'}
          onChange={(e) => onDataChange({ onReject: e.target.value as ParallelApprovalNodeData['onReject'] })}
        >
          <option value="reject_all">Reject entire workflow</option>
          <option value="continue_others">Continue with remaining approvers</option>
        </select>
        <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
          {data.onReject === 'reject_all'
            ? 'If any approver rejects, the entire approval fails immediately'
            : 'Other approvers can continue even if one rejects'
          }
        </div>
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
          onChange={(e) => onDataChange({ priority: e.target.value as ParallelApprovalNodeData['priority'] })}
        >
          <option value="Low">Low</option>
          <option value="Medium">Medium</option>
          <option value="High">High</option>
          <option value="Urgent">Urgent</option>
        </select>
      </div>
    </div>
  );
}

export const ParallelApprovalPanel = memo(ParallelApprovalPanelComponent);
