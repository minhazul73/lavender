import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner: React.FC<{ size?: number; label?: string }> = ({
  size = 28,
  label = 'Loading...',
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
        gap: '12px',
        color: 'var(--text-muted)',
      }}
    >
      <Loader2 size={size} className="animate-spin" color="var(--purple)" />
      {label && <span style={{ fontSize: '0.85rem' }}>{label}</span>}
    </div>
  );
};
