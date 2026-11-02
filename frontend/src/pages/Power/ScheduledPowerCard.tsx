import React, { useState } from 'react';
import { Clock, AlertTriangle } from 'lucide-react';

export interface ScheduledPowerState {
  scheduled: boolean;
  action?: string;
  target_time?: string;
  minutes?: number;
  details?: string | null;
}

export interface ScheduledPowerCardProps {
  scheduledState?: ScheduledPowerState | null;
  onSchedule: (action: 'reboot' | 'poweroff', minutes: number, message?: string) => Promise<void> | void;
  onCancelScheduled: () => Promise<void> | void;
  actionPending: boolean;
}

export const ScheduledPowerCard: React.FC<ScheduledPowerCardProps> = ({
  scheduledState,
  onSchedule,
  onCancelScheduled,
  actionPending,
}) => {
  const [schedAction, setSchedAction] = useState<'reboot' | 'poweroff'>('reboot');
  const [schedMinutes, setSchedMinutes] = useState<number>(15);
  const [schedMessage, setSchedMessage] = useState<string>('Scheduled from Lavender dashboard');

  return (
    <div className="card">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Clock size={20} color="var(--purple)" />
          <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>
            Scheduled Power Actions
          </h3>
        </div>
        {scheduledState?.scheduled ? (
          <span className="badge badge-warning">Pending Action</span>
        ) : (
          <span className="badge">No Actions</span>
        )}
      </div>

      {/* Pending schedule status banner */}
      {scheduledState?.scheduled ? (
        <div
          style={{
            padding: '14px 18px',
            borderRadius: 'var(--radius)',
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
            marginBottom: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertTriangle size={18} color="#f59e0b" />
            <span style={{ fontSize: '0.9rem', color: '#f59e0b', fontWeight: 600 }}>
              {scheduledState.details || 'A timed power action is currently pending'}
            </span>
          </div>
          <button
            className="btn btn-danger"
            onClick={onCancelScheduled}
            style={{ fontSize: '0.85rem', padding: '6px 12px' }}
          >
            Cancel Scheduled Action
          </button>
        </div>
      ) : (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 'var(--radius)',
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border)',
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <Clock size={16} />
          <span>No pending reboot or shutdown operations are currently scheduled.</span>
        </div>
      )}

      {/* Quick Timers */}
      <div style={{ marginBottom: '20px' }}>
        <div
          style={{
            fontSize: '0.85rem',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            marginBottom: '10px',
          }}
        >
          Quick Scheduling Presets:
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          <button
            className="btn btn-secondary"
            disabled={actionPending}
            onClick={() => onSchedule('reboot', 5)}
            style={{ fontSize: '0.85rem' }}
          >
            Reboot in 5m
          </button>
          <button
            className="btn btn-secondary"
            disabled={actionPending}
            onClick={() => onSchedule('reboot', 15)}
            style={{ fontSize: '0.85rem' }}
          >
            Reboot in 15m
          </button>
          <button
            className="btn btn-secondary"
            disabled={actionPending}
            onClick={() => onSchedule('reboot', 30)}
            style={{ fontSize: '0.85rem' }}
          >
            Reboot in 30m
          </button>
          <button
            className="btn btn-secondary"
            disabled={actionPending}
            onClick={() => onSchedule('reboot', 60)}
            style={{ fontSize: '0.85rem' }}
          >
            Reboot in 1h
          </button>
          <button
            className="btn btn-secondary"
            disabled={actionPending}
            onClick={() => onSchedule('poweroff', 15)}
            style={{ fontSize: '0.85rem' }}
          >
            Power Off in 15m
          </button>
        </div>
      </div>

      {/* Custom Schedule Form */}
      <div
        style={{
          padding: '16px',
          borderRadius: 'var(--radius)',
          background: 'rgba(255, 255, 255, 0.015)',
          border: '1px solid var(--border)',
        }}
      >
        <div
          style={{
            fontSize: '0.85rem',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            marginBottom: '12px',
          }}
        >
          Custom Timed Action:
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSchedule(schedAction, schedMinutes, schedMessage);
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <select
            className="input"
            value={schedAction}
            onChange={(e) => setSchedAction(e.target.value as 'reboot' | 'poweroff')}
            style={{ width: '130px', padding: '6px 10px', fontSize: '0.85rem' }}
          >
            <option value="reboot">Reboot</option>
            <option value="poweroff">Power Off</option>
          </select>

          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>in</span>

          <input
            type="number"
            className="input"
            min={1}
            max={1440}
            value={schedMinutes}
            onChange={(e) => setSchedMinutes(parseInt(e.target.value, 10) || 1)}
            style={{ width: '90px', padding: '6px 10px', fontSize: '0.85rem' }}
            required
          />

          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>minutes</span>

          <input
            type="text"
            className="input"
            placeholder="Broadcast message (optional)"
            value={schedMessage}
            onChange={(e) => setSchedMessage(e.target.value)}
            style={{ flex: '1 1 200px', padding: '6px 10px', fontSize: '0.85rem' }}
          />

          <button
            type="submit"
            className="btn btn-primary"
            disabled={actionPending}
            style={{ padding: '7px 18px', fontSize: '0.85rem' }}
          >
            {actionPending ? 'Scheduling...' : 'Schedule'}
          </button>
        </form>
      </div>
    </div>
  );
};

