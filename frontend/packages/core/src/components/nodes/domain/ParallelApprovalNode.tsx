import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { clsx } from 'clsx';
import type { ParallelApprovalNodeData } from '../../../types';

export interface ParallelApprovalNodeProps {
  id: string;
  data: ParallelApprovalNodeData;
  selected?: boolean;
}

const COMPLETION_RULE_LABELS: Record<string, string> = {
  all_required: 'All Required',
  any_one: 'Any One',
  quorum: 'Quorum',
};

function ParallelApprovalNodeComponent({ data, selected }: ParallelApprovalNodeProps) {
  const { label, approvers = [], completionRule, quorumCount, slaHours, priority, onReject } = data;

  // Get completion rule display text
  const completionText = completionRule === 'quorum'
    ? `${quorumCount || 0} of ${approvers.length}`
    : COMPLETION_RULE_LABELS[completionRule] || completionRule;

  return (
    <div
      className={clsx(
        'xsw-domain-node',
        'xsw-parallel-approval-node',
        selected && 'selected',
        priority && `priority-${priority.toLowerCase()}`
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="xsw-handle"
      />

      {/* Header with parallel icon */}
      <div className="xsw-parallel-approval-header">
        <div className="xsw-parallel-approval-icon">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z" />
          </svg>
        </div>
        <span className="xsw-parallel-approval-label">{label || 'Parallel Approval'}</span>
        {priority && (
          <span className={clsx('xsw-priority-badge', priority.toLowerCase())}>
            {priority}
          </span>
        )}
      </div>

      {/* Separator */}
      <div className="xsw-node-separator" />

      {/* Approvers list */}
      <div className="xsw-parallel-approvers">
        {approvers.length > 0 ? (
          approvers.slice(0, 3).map((approver) => (
            <div
              key={approver.id}
              className={clsx(
                'xsw-approver-slot',
                approver.required && 'required'
              )}
            >
              <span className="xsw-approver-icon">
                {approver.resolver?.type === 'role' ? '👥' : '👤'}
              </span>
              <span className="xsw-approver-label">{approver.label || 'Approver'}</span>
              {approver.required && (
                <span className="xsw-required-badge">*</span>
              )}
            </div>
          ))
        ) : (
          <div className="xsw-no-approvers">No approvers configured</div>
        )}
        {approvers.length > 3 && (
          <div className="xsw-more-approvers">
            +{approvers.length - 3} more
          </div>
        )}
      </div>

      {/* Completion info */}
      <div className="xsw-parallel-info">
        <div className="xsw-info-row">
          <span className="xsw-info-label">Complete:</span>
          <span className="xsw-info-value">{completionText}</span>
        </div>
        {slaHours && (
          <div className="xsw-info-row">
            <span className="xsw-info-label">SLA:</span>
            <span className="xsw-info-value">{slaHours}h</span>
          </div>
        )}
        {onReject && (
          <div className="xsw-info-row">
            <span className="xsw-info-label">On Reject:</span>
            <span className="xsw-info-value">
              {onReject === 'reject_all' ? 'Reject All' : 'Continue'}
            </span>
          </div>
        )}
      </div>

      {/* Output Handles */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="approved"
        className="xsw-handle xsw-handle-approve"
        style={{ left: '30%' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="rejected"
        className="xsw-handle xsw-handle-reject"
        style={{ left: '70%' }}
      />

      {/* Output labels */}
      <div className="xsw-parallel-outputs">
        <span className="xsw-output-label approve">Approved</span>
        <span className="xsw-output-label reject">Rejected</span>
      </div>
    </div>
  );
}

export const ParallelApprovalNode = memo(ParallelApprovalNodeComponent);
