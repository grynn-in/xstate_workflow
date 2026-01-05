import { useEffect, useState, useCallback } from 'react';
import { getMachineState, triggerEvent } from '@xstate-workflow/frappe-adapter';

interface AvailableEvent {
  event: string;
  target: string | null;
  enabled: boolean;
  guards: string[];
  actions: string[];
  trigger?: {
    button?: {
      enabled: boolean;
      label: string;
      style: 'primary' | 'secondary' | 'success' | 'danger';
      allowedRoles: string[];
    };
  };
}

interface WorkflowState {
  has_workflow: boolean;
  current_state?: string;
  available_events?: AvailableEvent[];
}

interface WorkflowActionButtonsProps {
  doctype: string;
  docname: string;
  onTransition?: (event: string, result: unknown) => void;
}

const BUTTON_STYLES: Record<string, { bg: string; border: string; color: string; hover: string }> = {
  primary: {
    bg: '#2490ef',
    border: '#2490ef',
    color: '#ffffff',
    hover: '#1a73e8',
  },
  secondary: {
    bg: '#f4f5f6',
    border: '#d1d5db',
    color: '#374151',
    hover: '#e5e7eb',
  },
  success: {
    bg: '#10b981',
    border: '#10b981',
    color: '#ffffff',
    hover: '#059669',
  },
  danger: {
    bg: '#ef4444',
    border: '#ef4444',
    color: '#ffffff',
    hover: '#dc2626',
  },
};

export function WorkflowActionButtons({
  doctype,
  docname,
  onTransition,
}: WorkflowActionButtonsProps) {
  const [state, setState] = useState<WorkflowState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingEvent, setPendingEvent] = useState<string | null>(null);

  const loadState = useCallback(async () => {
    try {
      setIsLoading(true);
      const result = await getMachineState(doctype, docname);
      setState(result);
    } catch (err) {
      console.error('Failed to load workflow state:', err);
    } finally {
      setIsLoading(false);
    }
  }, [doctype, docname]);

  useEffect(() => {
    loadState();

    // Subscribe to realtime updates
    if (typeof frappe !== 'undefined' && frappe.realtime) {
      const handler = (data: { doctype: string; docname: string }) => {
        if (data.doctype === doctype && data.docname === docname) {
          loadState();
        }
      };

      frappe.realtime.on('workflow_transition', handler);
      return () => {
        frappe.realtime.off('workflow_transition', handler);
      };
    }
  }, [doctype, docname, loadState]);

  const handleTriggerEvent = useCallback(async (event: string) => {
    try {
      setPendingEvent(event);
      const result = await triggerEvent(doctype, docname, event);

      if (result.success) {
        // Show success message
        if (typeof frappe !== 'undefined' && frappe.show_alert) {
          frappe.show_alert({
            message: `Workflow transitioned to: ${result.new_state}`,
            indicator: 'green',
          });
        }

        // Reload state
        await loadState();

        // Callback
        onTransition?.(event, result);
      } else {
        // Show error
        if (typeof frappe !== 'undefined' && frappe.show_alert) {
          frappe.show_alert({
            message: result.error || 'Transition failed',
            indicator: 'red',
          });
        }
      }
    } catch (err) {
      console.error('Transition error:', err);
      if (typeof frappe !== 'undefined' && frappe.show_alert) {
        frappe.show_alert({
          message: err instanceof Error ? err.message : 'Transition failed',
          indicator: 'red',
        });
      }
    } finally {
      setPendingEvent(null);
    }
  }, [doctype, docname, loadState, onTransition]);

  // Check if user has permission for a button
  const hasPermission = useCallback((allowedRoles: string[]): boolean => {
    if (!allowedRoles || allowedRoles.length === 0) {
      return true; // No restrictions
    }

    if (typeof frappe !== 'undefined' && frappe.user_roles) {
      return allowedRoles.some(role => frappe.user_roles.includes(role));
    }

    return true; // Allow if we can't check
  }, []);

  if (isLoading) {
    return null;
  }

  if (!state?.has_workflow || !state.available_events) {
    return null;
  }

  // Filter to events that have button triggers enabled
  const buttonEvents = state.available_events.filter(evt => {
    if (!evt.enabled) return false;

    // Check if trigger config exists and button is enabled
    const trigger = evt.trigger?.button;
    if (trigger && trigger.enabled) {
      return hasPermission(trigger.allowedRoles);
    }

    // Fall back to showing all enabled events as buttons
    return true;
  });

  if (buttonEvents.length === 0) {
    return null;
  }

  return (
    <div className="xsw-action-buttons" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
      {buttonEvents.map((evt) => {
        const trigger = evt.trigger?.button;
        const styleKey = trigger?.style || 'secondary';
        const style = BUTTON_STYLES[styleKey];
        const label = trigger?.label || evt.event.replace(/_/g, ' ');
        const isPending = pendingEvent === evt.event;

        return (
          <button
            key={evt.event}
            className={`btn btn-${styleKey} btn-sm xsw-action-btn`}
            onClick={() => handleTriggerEvent(evt.event)}
            disabled={isPending}
            style={{
              backgroundColor: style.bg,
              borderColor: style.border,
              color: style.color,
              padding: '6px 12px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 500,
              cursor: isPending ? 'wait' : 'pointer',
              opacity: isPending ? 0.7 : 1,
              transition: 'all 0.15s ease',
            }}
            title={evt.target ? `Transition to: ${evt.target}` : undefined}
          >
            {isPending ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className="xsw-spinner" style={{
                  width: '12px',
                  height: '12px',
                  border: '2px solid currentColor',
                  borderTopColor: 'transparent',
                  borderRadius: '50%',
                  animation: 'xsw-spin 0.8s linear infinite',
                }} />
                Processing...
              </span>
            ) : (
              label
            )}
          </button>
        );
      })}

      {/* CSS for spinner animation */}
      <style>{`
        @keyframes xsw-spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// Declare frappe global
declare const frappe: {
  realtime: {
    on: (event: string, handler: (data: unknown) => void) => void;
    off: (event: string, handler: (data: unknown) => void) => void;
  };
  show_alert: (options: { message: string; indicator: string }) => void;
  user_roles: string[];
};
