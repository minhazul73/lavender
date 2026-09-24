import React from 'react';
import { Users } from 'lucide-react';

export const UsersPage: React.FC = () => {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <Users size={18} color="var(--blue)" /> User & Session Management
        </span>
        <span className="badge badge-lavender">Phase 3</span>
      </div>
      <p>Linux user accounts, groups editing, active TTY sessions, and SSH key management.</p>
    </div>
  );
};
