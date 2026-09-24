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
import { ErrorBoundary } from './components/common/ErrorBoundary';

const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { session, loading, refreshProfile } = useAuth();
  const location = useLocation();
  const [tookTooLong, setTookTooLong] = React.useState(false);

  React.useEffect(() => {
    if (!loading) {
      setTookTooLong(false);
      return;
    }
    const timer = setTimeout(() => setTookTooLong(true), 6000);
    return () => clearTimeout(timer);
  }, [loading]);

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-base)',
          gap: '16px',
        }}
      >
        <LoadingSpinner size={36} label="Initializing Lavender..." />
        {tookTooLong && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <p style={{ margin: '0 0 10px' }}>Waiting for response from FastAPI backend (port 8080)...</p>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
              <button
                className="btn btn-xs btn-secondary"
                onClick={() => {
                  setTookTooLong(false);
                  refreshProfile();
                }}
              >
                Retry
              </button>
              <button
                className="btn btn-xs btn-primary"
                onClick={() => {
                  window.location.href = `/login?next=${encodeURIComponent(location.pathname)}`;
                }}
              >
                Go to Login
              </button>
            </div>
          </div>
        )}
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
    <ErrorBoundary>
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
    </ErrorBoundary>
  );
};
