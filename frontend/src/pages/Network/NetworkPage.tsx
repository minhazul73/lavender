import React from 'react';
import { Globe } from 'lucide-react';

export const NetworkPage: React.FC = () => {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <Globe size={18} color="var(--accent)" /> Network Interfaces & Tools
        </span>
        <span className="badge badge-lavender">Phase 3</span>
      </div>
      <p>IP addresses, WiFi scanning, DNS lookups, and ping latency tests.</p>
    </div>
  );
};
