// Toolbar component for workflow builder

import React, { useRef } from 'react';
import type { ToolbarProps } from '../types';

export default function Toolbar({
  onAddState,
  onSave,
  onExport,
  onImport,
  onAutoLayout,
  machineId,
  machineTitle,
  onMachineIdChange,
  isSaving,
  isNewWorkflow = false,
  hasUnsavedChanges = false,
  onOpenInDesk,
  onSaveAs
}: ToolbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onImport();
    }
    // Reset input
    e.target.value = '';
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '12px 16px',
        background: 'linear-gradient(to right, #1e293b, #334155)',
        borderBottom: '1px solid #475569',
        flexWrap: 'wrap'
      }}
    >
      {/* Workflow title/status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {isNewWorkflow ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              background: '#0f172a',
              borderRadius: '6px',
              border: '1px dashed #475569'
            }}
          >
            <span style={{ color: '#f59e0b', fontSize: '14px' }}>+</span>
            <span style={{ color: '#94a3b8', fontSize: '13px' }}>New Workflow</span>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                padding: '6px 12px',
                background: '#0f172a',
                borderRadius: '6px',
                border: '1px solid #475569'
              }}
            >
              <span style={{ color: 'white', fontSize: '13px', fontWeight: 500 }}>
                {machineTitle || machineId}
              </span>
              {hasUnsavedChanges && (
                <span style={{ color: '#f59e0b', marginLeft: '6px' }}>*</span>
              )}
            </div>
            {onOpenInDesk && (
              <button
                onClick={onOpenInDesk}
                title="Open in Desk"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '32px',
                  height: '32px',
                  background: 'transparent',
                  border: '1px solid #475569',
                  borderRadius: '6px',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                ↗
              </button>
            )}
          </div>
        )}
      </div>

      {/* Divider */}
      <div style={{ width: '1px', height: '24px', background: '#475569' }} />

      {/* Add state button */}
      <button
        onClick={onAddState}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 14px',
          background: '#10b981',
          border: 'none',
          borderRadius: '6px',
          color: 'white',
          fontSize: '13px',
          fontWeight: 500,
          cursor: 'pointer',
          transition: 'background 0.2s'
        }}
        onMouseOver={(e) => (e.currentTarget.style.background = '#059669')}
        onMouseOut={(e) => (e.currentTarget.style.background = '#10b981')}
      >
        <span>+</span>
        <span>Add State</span>
      </button>

      {/* Auto layout button */}
      <button
        onClick={onAutoLayout}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 14px',
          background: '#6366f1',
          border: 'none',
          borderRadius: '6px',
          color: 'white',
          fontSize: '13px',
          fontWeight: 500,
          cursor: 'pointer',
          transition: 'background 0.2s'
        }}
        onMouseOver={(e) => (e.currentTarget.style.background = '#4f46e5')}
        onMouseOut={(e) => (e.currentTarget.style.background = '#6366f1')}
      >
        <span>⊞</span>
        <span>Auto Layout</span>
      </button>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Import button */}
      <button
        onClick={handleImportClick}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 14px',
          background: 'transparent',
          border: '1px solid #475569',
          borderRadius: '6px',
          color: '#e2e8f0',
          fontSize: '13px',
          fontWeight: 500,
          cursor: 'pointer',
          transition: 'border-color 0.2s'
        }}
        onMouseOver={(e) => (e.currentTarget.style.borderColor = '#6366f1')}
        onMouseOut={(e) => (e.currentTarget.style.borderColor = '#475569')}
      >
        <span>Import</span>
      </button>

      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      {/* Export button */}
      <button
        onClick={onExport}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 14px',
          background: 'transparent',
          border: '1px solid #475569',
          borderRadius: '6px',
          color: '#e2e8f0',
          fontSize: '13px',
          fontWeight: 500,
          cursor: 'pointer',
          transition: 'border-color 0.2s'
        }}
        onMouseOver={(e) => (e.currentTarget.style.borderColor = '#6366f1')}
        onMouseOut={(e) => (e.currentTarget.style.borderColor = '#475569')}
      >
        <span>Export</span>
      </button>

      {/* Save As button (for existing workflows) */}
      {!isNewWorkflow && onSaveAs && (
        <button
          onClick={onSaveAs}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 14px',
            background: 'transparent',
            border: '1px solid #475569',
            borderRadius: '6px',
            color: '#e2e8f0',
            fontSize: '13px',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'border-color 0.2s'
          }}
          onMouseOver={(e) => (e.currentTarget.style.borderColor = '#6366f1')}
          onMouseOut={(e) => (e.currentTarget.style.borderColor = '#475569')}
        >
          <span>Save As</span>
        </button>
      )}

      {/* Save button */}
      <button
        onClick={onSave}
        disabled={isSaving}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 18px',
          background: isSaving ? '#475569' : '#3b82f6',
          border: 'none',
          borderRadius: '6px',
          color: 'white',
          fontSize: '13px',
          fontWeight: 600,
          cursor: isSaving ? 'not-allowed' : 'pointer',
          transition: 'background 0.2s'
        }}
        onMouseOver={(e) => !isSaving && (e.currentTarget.style.background = '#2563eb')}
        onMouseOut={(e) => !isSaving && (e.currentTarget.style.background = '#3b82f6')}
      >
        {isSaving ? (
          <>
            <span className="spinner" />
            <span>Saving...</span>
          </>
        ) : isNewWorkflow ? (
          <>
            <span>+</span>
            <span>Create Workflow</span>
          </>
        ) : (
          <span>Save</span>
        )}
      </button>
    </div>
  );
}
