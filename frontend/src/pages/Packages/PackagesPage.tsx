import React from 'react';
import { Package } from 'lucide-react';

export const PackagesPage: React.FC = () => {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <Package size={18} color="var(--purple)" /> Package Management
        </span>
        <span className="badge badge-lavender">Phase 3</span>
      </div>
      <p>Multi-backend package search, upgrades, and installations.</p>
    </div>
  );
};
