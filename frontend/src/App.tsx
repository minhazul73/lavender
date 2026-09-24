import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { AppShell } from './components/layout/AppShell';
import { LoginPage } from './pages/Login/LoginPage';
import { OverviewPage } from './pages/Overview/OverviewPage';
import { ServicesPage } from './pages/Services/ServicesPage';
import { ProcessesPage } from './pages/Processes/ProcessesPage';
import { StoragePage } from './pages/Storage/StoragePage';
import { NetworkPage } from './pages/Network/NetworkPage';
import { PackagesPage } from './pages/Packages/PackagesPage';
import { UsersPage } from './pages/Users/UsersPage';
import { PowerPage } from './pages/Power/PowerPage';
import { LoadingSpinner } from './components/common/LoadingSpinner';

const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { session, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-base)',
        }}
      >
        <LoadingSpinner size={36} label="Initializing Lavender..." />
      </div>
    );
  }

  if (!session) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <Routes>
            {/* Standalone public login route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Authenticated dashboard shell */}
            <Route
              element={
                <RequireAuth>
                  <AppShell />
                </RequireAuth>
              }
            >
              <Route path="/" element={<OverviewPage />} />
              <Route path="/services" element={<ServicesPage />} />
              <Route path="/processes" element={<ProcessesPage />} />
              <Route path="/storage" element={<StoragePage />} />
              <Route path="/network" element={<NetworkPage />} />
              <Route path="/packages" element={<PackagesPage />} />
              <Route path="/users" element={<UsersPage />} />
              <Route path="/power" element={<PowerPage />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
};
