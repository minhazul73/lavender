import React from 'react';
import { HardDrive } from 'lucide-react';

export const StoragePage: React.FC = () => {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <HardDrive size={18} color="var(--accent)" /> Disks & Storage
        </span>
        <span className="badge badge-lavender">Phase 3</span>
      </div>
      <p>Partition visualizer, mount details, and unmounting operations.</p>
    </div>
  );
};
