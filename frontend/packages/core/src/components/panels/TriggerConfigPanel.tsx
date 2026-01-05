import { memo, useState, useCallback } from 'react';
import type { TriggerConfig, ButtonTriggerConfig, AutoTriggerConfig, DelayedTriggerConfig } from '../../types';

export interface TriggerConfigPanelProps {
  trigger?: TriggerConfig;
  eventName?: string;
  availableRoles?: string[];
  onTriggerChange: (trigger: TriggerConfig | undefined) => void;
  onClose: () => void;
}

const BUTTON_STYLES = [
  { value: 'primary', label: 'Primary (Blue)' },
  { value: 'secondary', label: 'Secondary (Gray)' },
  { value: 'success', label: 'Success (Green)' },
  { value: 'danger', label: 'Danger (Red)' },
];

const AUTO_EVENTS = [
  { value: 'on_update', label: 'On Update (when document is saved)' },
  { value: 'after_insert', label: 'After Insert (when document is created)' },
  { value: 'on_submit', label: 'On Submit (when document is submitted)' },
  { value: 'on_cancel', label: 'On Cancel (when document is cancelled)' },
];

const DELAY_UNITS = [
  { value: 'seconds', label: 'Seconds' },
  { value: 'minutes', label: 'Minutes' },
  { value: 'hours', label: 'Hours' },
  { value: 'days', label: 'Days' },
];

function TriggerConfigPanelComponent({
  trigger,
  eventName = 'EVENT',
  availableRoles = ['System Manager', 'Administrator'],
  onTriggerChange,
  onClose,
}: TriggerConfigPanelProps) {
  // Button trigger state
  const [buttonEnabled, setButtonEnabled] = useState(trigger?.button?.enabled || false);
  const [buttonLabel, setButtonLabel] = useState(trigger?.button?.label || eventName);
  const [buttonStyle, setButtonStyle] = useState<ButtonTriggerConfig['style']>(
    trigger?.button?.style || 'primary'
  );
  const [buttonRoles, setButtonRoles] = useState<string[]>(
    trigger?.button?.allowedRoles || []
  );

  // Auto trigger state
  const [autoEnabled, setAutoEnabled] = useState(trigger?.auto?.enabled || false);
  const [autoEvent, setAutoEvent] = useState<AutoTriggerConfig['event']>(
    trigger?.auto?.event || 'on_update'
  );
  const [autoFireEvent, setAutoFireEvent] = useState(trigger?.auto?.fireEvent || eventName);

  // Delayed trigger state
  const [delayedEnabled, setDelayedEnabled] = useState(trigger?.delayed?.enabled || false);
  const [delayValue, setDelayValue] = useState(trigger?.delayed?.delay || 0);
  const [delayUnit, setDelayUnit] = useState<DelayedTriggerConfig['unit']>(
    trigger?.delayed?.unit || 'hours'
  );
  const [reminderEnabled, setReminderEnabled] = useState(!!trigger?.delayed?.reminderDelay);
  const [reminderDelay, setReminderDelay] = useState(trigger?.delayed?.reminderDelay || 0);
  const [reminderUnit, setReminderUnit] = useState<DelayedTriggerConfig['unit']>(
    trigger?.delayed?.reminderUnit || 'hours'
  );

  const toggleRole = useCallback((role: string) => {
    if (buttonRoles.includes(role)) {
      setButtonRoles(buttonRoles.filter(r => r !== role));
    } else {
      setButtonRoles([...buttonRoles, role]);
    }
  }, [buttonRoles]);

  const buildTriggerConfig = useCallback((): TriggerConfig | undefined => {
    const config: TriggerConfig = {};

    if (buttonEnabled) {
      config.button = {
        enabled: true,
        label: buttonLabel,
        style: buttonStyle,
        allowedRoles: buttonRoles,
      };
    }

    if (autoEnabled) {
      config.auto = {
        enabled: true,
        event: autoEvent,
        fireEvent: autoFireEvent,
      };
    }

    if (delayedEnabled && delayValue > 0) {
      config.delayed = {
        enabled: true,
        delay: delayValue,
        unit: delayUnit,
        ...(reminderEnabled && reminderDelay > 0 && {
          reminderDelay,
          reminderUnit,
        }),
      };
    }

    // Return undefined if nothing is enabled
    if (!config.button && !config.auto && !config.delayed) {
      return undefined;
    }

    return config;
  }, [
    buttonEnabled, buttonLabel, buttonStyle, buttonRoles,
    autoEnabled, autoEvent, autoFireEvent,
    delayedEnabled, delayValue, delayUnit,
    reminderEnabled, reminderDelay, reminderUnit
  ]);

  const handleSave = useCallback(() => {
    const config = buildTriggerConfig();
    onTriggerChange(config);
    onClose();
  }, [buildTriggerConfig, onTriggerChange, onClose]);

  return (
    <div className="xsw-trigger-config">
      <div className="xsw-panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>Trigger Configuration</span>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px' }}
        >
          ×
        </button>
      </div>

      {/* Form Button Trigger */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Form Button</div>
        <label className="xsw-checkbox" style={{ marginBottom: '12px' }}>
          <input
            type="checkbox"
            checked={buttonEnabled}
            onChange={(e) => setButtonEnabled(e.target.checked)}
          />
          <span>Show as form button</span>
        </label>

        {buttonEnabled && (
          <div style={{ paddingLeft: '24px' }}>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Button Label
              </label>
              <input
                type="text"
                className="xsw-input"
                value={buttonLabel}
                onChange={(e) => setButtonLabel(e.target.value)}
                placeholder="e.g., Approve, Submit, Reject"
              />
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Button Style
              </label>
              <select
                className="xsw-select"
                value={buttonStyle}
                onChange={(e) => setButtonStyle(e.target.value as ButtonTriggerConfig['style'])}
              >
                {BUTTON_STYLES.map((style) => (
                  <option key={style.value} value={style.value}>
                    {style.label}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Allowed Roles
              </label>
              <div style={{ maxHeight: '120px', overflow: 'auto', border: '1px solid #e5e7eb', borderRadius: '4px', padding: '8px' }}>
                {availableRoles.map((role) => (
                  <label key={role} className="xsw-checkbox" style={{ display: 'block', marginBottom: '4px' }}>
                    <input
                      type="checkbox"
                      checked={buttonRoles.includes(role)}
                      onChange={() => toggleRole(role)}
                    />
                    <span>{role}</span>
                  </label>
                ))}
              </div>
              <p style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
                Leave empty to allow all users
              </p>
            </div>

            {/* Preview */}
            <div style={{ marginTop: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Preview
              </label>
              <button
                className={`xsw-button xsw-button-${buttonStyle}`}
                style={{ cursor: 'default' }}
              >
                {buttonLabel || 'Button'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Auto Trigger */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Auto Trigger</div>
        <label className="xsw-checkbox" style={{ marginBottom: '12px' }}>
          <input
            type="checkbox"
            checked={autoEnabled}
            onChange={(e) => setAutoEnabled(e.target.checked)}
          />
          <span>Trigger automatically on document event</span>
        </label>

        {autoEnabled && (
          <div style={{ paddingLeft: '24px' }}>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Document Event
              </label>
              <select
                className="xsw-select"
                value={autoEvent}
                onChange={(e) => setAutoEvent(e.target.value as AutoTriggerConfig['event'])}
              >
                {AUTO_EVENTS.map((event) => (
                  <option key={event.value} value={event.value}>
                    {event.label}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Fire Event
              </label>
              <input
                type="text"
                className="xsw-input"
                value={autoFireEvent}
                onChange={(e) => setAutoFireEvent(e.target.value)}
                placeholder="e.g., SUBMIT, APPROVE"
              />
              <p style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
                The workflow event to trigger when document event fires
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Delayed Trigger */}
      <div className="xsw-panel-section">
        <div className="xsw-panel-section-title">Scheduled/Delayed</div>
        <label className="xsw-checkbox" style={{ marginBottom: '12px' }}>
          <input
            type="checkbox"
            checked={delayedEnabled}
            onChange={(e) => setDelayedEnabled(e.target.checked)}
          />
          <span>Auto-transition after delay (XState "after")</span>
        </label>

        {delayedEnabled && (
          <div style={{ paddingLeft: '24px' }}>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                Delay
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="number"
                  className="xsw-input"
                  style={{ flex: 1 }}
                  value={delayValue}
                  onChange={(e) => setDelayValue(parseInt(e.target.value, 10) || 0)}
                  min={0}
                />
                <select
                  className="xsw-select"
                  style={{ width: '120px' }}
                  value={delayUnit}
                  onChange={(e) => setDelayUnit(e.target.value as DelayedTriggerConfig['unit'])}
                >
                  {DELAY_UNITS.map((unit) => (
                    <option key={unit.value} value={unit.value}>
                      {unit.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <label className="xsw-checkbox" style={{ marginBottom: '12px' }}>
              <input
                type="checkbox"
                checked={reminderEnabled}
                onChange={(e) => setReminderEnabled(e.target.checked)}
              />
              <span>Send reminder before transition</span>
            </label>

            {reminderEnabled && (
              <div style={{ marginBottom: '12px', paddingLeft: '24px' }}>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#6b7280' }}>
                  Reminder Time (before transition)
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="number"
                    className="xsw-input"
                    style={{ flex: 1 }}
                    value={reminderDelay}
                    onChange={(e) => setReminderDelay(parseInt(e.target.value, 10) || 0)}
                    min={0}
                  />
                  <select
                    className="xsw-select"
                    style={{ width: '120px' }}
                    value={reminderUnit}
                    onChange={(e) => setReminderUnit(e.target.value as DelayedTriggerConfig['unit'])}
                  >
                    {DELAY_UNITS.map((unit) => (
                      <option key={unit.value} value={unit.value}>
                        {unit.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Save */}
      <div className="xsw-panel-section" style={{ display: 'flex', gap: '8px' }}>
        <button
          className="xsw-button xsw-button-secondary"
          style={{ flex: 1 }}
          onClick={onClose}
        >
          Cancel
        </button>
        <button
          className="xsw-button xsw-button-primary"
          style={{ flex: 1 }}
          onClick={handleSave}
        >
          Save Trigger
        </button>
      </div>
    </div>
  );
}

export const TriggerConfigPanel = memo(TriggerConfigPanelComponent);
