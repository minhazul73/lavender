import React from 'react';
import { Activity } from 'lucide-react';

export const ProcessesPage: React.FC = () => {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <Activity size={18} color="var(--blue)" /> Running Processes
        </span>
        <span className="badge badge-neutral">Phase 3</span>
      </div>
      <p>Realtime process inspector, sorting, and kill controls.</p>
    </div>
  );
};
