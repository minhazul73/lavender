import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { ElevationModal } from '../common/ElevationModal';

const ROUTE_TITLES: Record<string, string> = {
  '/': 'System Overview',
  '/services': 'Systemd Services',
  '/processes': 'Running Processes',
  '/storage': 'Storage & Filesystems',
  '/network': 'Network Interfaces',
  '/packages': 'Package Management',
  '/users': 'User Management',
  '/power': 'Power & Performance',
};

export const AppShell: React.FC = () => {
  const location = useLocation();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Determine current page title
  const currentTitle = ROUTE_TITLES[location.pathname] || 'Lavender Dashboard';

  return (
    <div
      className="dashboard-shell"
      style={{
        display: 'flex',
        minHeight: '100vh',
        width: '100%',
        backgroundColor: 'var(--bg-base)',
      }}
    >
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0,
          overflowX: 'hidden',
        }}
      >
        <Topbar
          title={currentTitle}
          onToggleSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)}
        />

        <main
          className="dashboard-content"
          style={{
            flex: 1,
            padding: '24px',
            maxWidth: '1600px',
            width: '100%',
            margin: '0 auto',
          }}
        >
          <Outlet />
        </main>
      </div>

      {/* Global Elevation Modal */}
      <ElevationModal />
    </div>
  );
};
