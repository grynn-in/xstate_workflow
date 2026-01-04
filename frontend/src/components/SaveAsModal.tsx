// Save As New Workflow Modal component

import React, { useState, useEffect } from 'react';
import { getDocTypes, showError } from '../utils/api';

interface SaveAsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (machineId: string, title: string, attachedDoctype: string) => void;
  isSaving: boolean;
  defaultMachineId?: string;
}

export default function SaveAsModal({
  isOpen,
  onClose,
  onSave,
  isSaving,
  defaultMachineId = ''
}: SaveAsModalProps) {
  const [machineId, setMachineId] = useState(defaultMachineId);
  const [title, setTitle] = useState('');
  const [attachedDoctype, setAttachedDoctype] = useState('');
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const [isLoadingDocTypes, setIsLoadingDocTypes] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // Load DocTypes on open
  useEffect(() => {
    if (isOpen && docTypes.length === 0) {
      loadDocTypes();
    }
  }, [isOpen]);

  // Update machineId when defaultMachineId changes
  useEffect(() => {
    if (defaultMachineId) {
      setMachineId(defaultMachineId);
      // Generate title from machineId
      setTitle(defaultMachineId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
    }
  }, [defaultMachineId]);

  const loadDocTypes = async () => {
    setIsLoadingDocTypes(true);
    try {
      const types = await getDocTypes();
      setDocTypes(types.sort());
    } catch (error) {
      showError('Failed to load DocTypes');
    } finally {
      setIsLoadingDocTypes(false);
    }
  };

  const handleTitleChange = (value: string) => {
    setTitle(value);
    // Auto-generate machine_id from title
    const id = value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
    setMachineId(id);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!machineId.trim()) {
      showError('Please enter a Machine ID');
      return;
    }
    if (!title.trim()) {
      showError('Please enter a Title');
      return;
    }

    onSave(machineId.trim(), title.trim(), attachedDoctype);
  };

  const filteredDocTypes = docTypes.filter(dt =>
    dt.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: '#1e293b',
          borderRadius: '12px',
          border: '1px solid #334155',
          width: '100%',
          maxWidth: '480px',
          padding: '24px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
        }}
      >
        <h2 style={{ color: 'white', margin: '0 0 20px', fontSize: '18px' }}>
          Save As New Workflow
        </h2>

        <form onSubmit={handleSubmit}>
          {/* Title */}
          <div style={{ marginBottom: '16px' }}>
            <label
              style={{
                display: 'block',
                color: '#94a3b8',
                fontSize: '13px',
                marginBottom: '6px'
              }}
            >
              Workflow Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => handleTitleChange(e.target.value)}
              placeholder="e.g., Sales Order Approval"
              style={{
                width: '100%',
                padding: '10px 12px',
                background: '#0f172a',
                border: '1px solid #475569',
                borderRadius: '6px',
                color: 'white',
                fontSize: '14px',
                boxSizing: 'border-box'
              }}
              autoFocus
            />
          </div>

          {/* Machine ID */}
          <div style={{ marginBottom: '16px' }}>
            <label
              style={{
                display: 'block',
                color: '#94a3b8',
                fontSize: '13px',
                marginBottom: '6px'
              }}
            >
              Machine ID *
            </label>
            <input
              type="text"
              value={machineId}
              onChange={(e) => setMachineId(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
              placeholder="e.g., sales_order_approval"
              style={{
                width: '100%',
                padding: '10px 12px',
                background: '#0f172a',
                border: '1px solid #475569',
                borderRadius: '6px',
                color: 'white',
                fontSize: '14px',
                fontFamily: 'monospace',
                boxSizing: 'border-box'
              }}
            />
            <span style={{ color: '#64748b', fontSize: '11px', marginTop: '4px', display: 'block' }}>
              Unique identifier (lowercase, no spaces)
            </span>
          </div>

          {/* Attached DocType */}
          <div style={{ marginBottom: '24px' }}>
            <label
              style={{
                display: 'block',
                color: '#94a3b8',
                fontSize: '13px',
                marginBottom: '6px'
              }}
            >
              Attach to DocType (optional)
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search DocTypes..."
              style={{
                width: '100%',
                padding: '10px 12px',
                background: '#0f172a',
                border: '1px solid #475569',
                borderRadius: '6px',
                color: 'white',
                fontSize: '14px',
                marginBottom: '8px',
                boxSizing: 'border-box'
              }}
            />
            <div
              style={{
                maxHeight: '150px',
                overflowY: 'auto',
                background: '#0f172a',
                border: '1px solid #475569',
                borderRadius: '6px'
              }}
            >
              {isLoadingDocTypes ? (
                <div style={{ padding: '12px', color: '#64748b', textAlign: 'center' }}>
                  Loading...
                </div>
              ) : (
                <>
                  {/* None option */}
                  <div
                    onClick={() => {
                      setAttachedDoctype('');
                      setSearchTerm('');
                    }}
                    style={{
                      padding: '8px 12px',
                      cursor: 'pointer',
                      background: attachedDoctype === '' ? '#334155' : 'transparent',
                      color: attachedDoctype === '' ? 'white' : '#94a3b8',
                      fontSize: '13px',
                      borderBottom: '1px solid #334155'
                    }}
                  >
                    (None - Generic Workflow)
                  </div>
                  {filteredDocTypes.slice(0, 50).map((dt) => (
                    <div
                      key={dt}
                      onClick={() => {
                        setAttachedDoctype(dt);
                        setSearchTerm('');
                      }}
                      style={{
                        padding: '8px 12px',
                        cursor: 'pointer',
                        background: attachedDoctype === dt ? '#334155' : 'transparent',
                        color: attachedDoctype === dt ? 'white' : '#94a3b8',
                        fontSize: '13px'
                      }}
                      onMouseOver={(e) => {
                        if (attachedDoctype !== dt) {
                          e.currentTarget.style.background = '#1e293b';
                        }
                      }}
                      onMouseOut={(e) => {
                        if (attachedDoctype !== dt) {
                          e.currentTarget.style.background = 'transparent';
                        }
                      }}
                    >
                      {dt}
                    </div>
                  ))}
                  {filteredDocTypes.length > 50 && (
                    <div style={{ padding: '8px 12px', color: '#64748b', fontSize: '12px' }}>
                      ... and {filteredDocTypes.length - 50} more. Type to filter.
                    </div>
                  )}
                </>
              )}
            </div>
            {attachedDoctype && (
              <div
                style={{
                  marginTop: '8px',
                  padding: '6px 10px',
                  background: '#334155',
                  borderRadius: '4px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <span style={{ color: 'white', fontSize: '13px' }}>{attachedDoctype}</span>
                <button
                  type="button"
                  onClick={() => setAttachedDoctype('')}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                    padding: '0',
                    fontSize: '16px',
                    lineHeight: 1
                  }}
                >
                  ×
                </button>
              </div>
            )}
          </div>

          {/* Buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              style={{
                padding: '10px 20px',
                background: 'transparent',
                border: '1px solid #475569',
                borderRadius: '6px',
                color: '#e2e8f0',
                fontSize: '14px',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving || !machineId.trim() || !title.trim()}
              style={{
                padding: '10px 24px',
                background: isSaving ? '#475569' : '#3b82f6',
                border: 'none',
                borderRadius: '6px',
                color: 'white',
                fontSize: '14px',
                fontWeight: 600,
                cursor: isSaving ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {isSaving ? (
                <>
                  <span className="spinner" />
                  Creating...
                </>
              ) : (
                'Create Workflow'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
