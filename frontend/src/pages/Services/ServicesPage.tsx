import React from 'react';
import { Server } from 'lucide-react';

export const ServicesPage: React.FC = () => {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <Server size={18} color="var(--purple)" /> Systemd Services
        </span>
        <span className="badge badge-lavender">Phase 3</span>
      </div>
      <p>Services management and journalctl log viewer.</p>
    </div>
  );
};
