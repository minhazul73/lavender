import React from 'react';

interface BadgeProps {
  variant?: 'lavender' | 'success' | 'warning' | 'danger' | 'neutral';
  icon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'lavender',
  icon,
  children,
  className = '',
}) => {
  return (
    <span className={`badge badge-${variant} ${className}`}>
      {icon}
      <span>{children}</span>
    </span>
  );
};
