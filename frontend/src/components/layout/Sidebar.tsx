import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Server,
  Activity,
  HardDrive,
  Globe,
  Package,
  Users,
  Power,
  ChevronLeft,
  ChevronRight,
  Cpu,
  LucideIcon,
} from 'lucide-react';
import { api } from '../../api/client';
import { SystemInfo } from '../../api/types';

interface NavItemDef {
  path: string;
  name: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItemDef[] = [
  { path: '/', name: 'Overview', icon: LayoutDashboard },
  { path: '/services', name: 'Services', icon: Server },
  { path: '/processes', name: 'Processes', icon: Activity },
  { path: '/storage', name: 'Storage', icon: HardDrive },
  { path: '/network', name: 'Network', icon: Globe },
  { path: '/packages', name: 'Packages', icon: Package },
  { path: '/users', name: 'Users', icon: Users },
  { path: '/power', name: 'Power', icon: Power },
];

export const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('lavender_sidebar_collapsed') === 'true';
  });

  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);

  useEffect(() => {
    localStorage.setItem('lavender_sidebar_collapsed', String(collapsed));
  }, [collapsed]);

  useEffect(() => {
    api.get<SystemInfo>('/api/device/info')
      .then((data) => setSystemInfo(data))
      .catch(() => {});
  }, []);

  const toggleCollapse = () => setCollapsed((prev) => !prev);

  return (
    <aside
      className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''}`}
      style={{
        width: collapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)',
        minWidth: collapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)',
        height: '100vh',
        position: 'sticky',
        top: 0,
        display: 'flex',
        flexDirection: 'column',
        background: 'rgba(6, 15, 30, 0.95)',
        backdropFilter: 'blur(16px)',
        borderRight: '1px solid var(--border)',
        transition: 'width 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        overflow: 'hidden',
        zIndex: 60,
      }}
    >
      {/* Sidebar Header */}
      <div
        className="sidebar-header"
        style={{
          height: 'var(--topbar-height)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          padding: collapsed ? '0' : '0 16px',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        {!collapsed && (
          <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'var(--grad-lavender)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                boxShadow: '0 2px 8px var(--lavender-glow)',
                flexShrink: 0,
              }}
            >
              <Cpu size={18} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <h1
                style={{
                  fontSize: '1.05rem',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                  margin: 0,
                  letterSpacing: '-0.01em',
                }}
              >
                Lavender
              </h1>
              <span
                style={{
                  fontSize: '0.72rem',
                  color: 'var(--text-muted)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: '140px',
                }}
                title={systemInfo?.model || 'Linux Device'}
              >
                {systemInfo?.model || 'Linux Dashboard'}
              </span>
            </div>
          </div>
        )}

        {/* Collapse toggle button */}
        <button
          type="button"
          onClick={toggleCollapse}
          className="btn btn-ghost btn-icon"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          style={{ color: 'var(--text-secondary)', padding: '6px' }}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Navigation Links */}
      <nav
        style={{
          flex: 1,
          padding: '16px 10px',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          overflowY: 'auto',
        }}
      >
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              title={collapsed ? item.name : undefined}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'active' : ''}`
              }
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: collapsed ? '10px 0' : '10px 14px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                borderRadius: 'var(--radius-md)',
                color: isActive ? '#ffffff' : 'var(--text-secondary)',
                background: isActive
                  ? 'linear-gradient(90deg, rgba(124, 58, 237, 0.28) 0%, rgba(124, 58, 237, 0.1) 100%)'
                  : 'transparent',
                borderLeft: isActive ? '3px solid var(--purple)' : '3px solid transparent',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.88rem',
                textDecoration: 'none',
                transition: 'var(--transition)',
              })}
            >
              <Icon size={18} />
              {!collapsed && <span>{item.name}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Sidebar Footer */}
      <div
        className="sidebar-footer"
        style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: collapsed ? 'center' : 'flex-start',
          gap: '4px',
          fontSize: '0.72rem',
          color: 'var(--text-muted)',
        }}
      >
        <span
          className="badge badge-lavender"
          style={{ fontSize: '0.7rem', padding: '2px 6px' }}
        >
          v0.4.0
        </span>
        {!collapsed && systemInfo?.os_name && (
          <span
            style={{
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              maxWidth: '200px',
            }}
            title={systemInfo.os_pretty || systemInfo.os_name}
          >
            {systemInfo.os_name}
          </span>
        )}
      </div>
    </aside>
  );
};
