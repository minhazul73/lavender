import React from 'react';
import { Power } from 'lucide-react';

export const PowerPage: React.FC = () => {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <Power size={18} color="var(--red)" /> Power Controls & Scheduling
        </span>
        <span className="badge badge-lavender">Phase 3</span>
      </div>
      <p>System reboot, shutdown, suspend, CPU governor tuning, and timed power actions.</p>
    </div>
  );
};
