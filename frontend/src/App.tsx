import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { AppShell } from './components/layout/AppShell';
import { LoginPage } from './pages/Login/LoginPage';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import { ErrorBoundary } from './components/common/ErrorBoundary';

const OverviewPage = React.lazy(() => import('./pages/Overview/OverviewPage').then(m => ({ default: m.OverviewPage })));
const ServicesPage = React.lazy(() => import('./pages/Services/ServicesPage').then(m => ({ default: m.ServicesPage })));
const ProcessesPage = React.lazy(() => import('./pages/Processes/ProcessesPage').then(m => ({ default: m.ProcessesPage })));
const StoragePage = React.lazy(() => import('./pages/Storage/StoragePage').then(m => ({ default: m.StoragePage })));
const NetworkPage = React.lazy(() => import('./pages/Network/NetworkPage').then(m => ({ default: m.NetworkPage })));
const PackagesPage = React.lazy(() => import('./pages/Packages/PackagesPage').then(m => ({ default: m.PackagesPage })));
const UsersPage = React.lazy(() => import('./pages/Users/UsersPage').then(m => ({ default: m.UsersPage })));
const PowerPage = React.lazy(() => import('./pages/Power/PowerPage').then(m => ({ default: m.PowerPage })));

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
            <p style={{ margin: '0 0 10px' }}>Waiting for response from the FastAPI backend...</p>
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

const DashboardRoutes: React.FC = () => {
  const { requireAuthForHomepage } = useAuth();

  return (
    <Routes>
      {/* Standalone public login route */}
      <Route path="/login" element={<LoginPage />} />

      {/* Dashboard shell */}
      <Route element={<AppShell />}>
        {/* Homepage overview: public by default, locked if requireAuthForHomepage is true */}
        <Route
          path="/"
          element={
            <React.Suspense fallback={<LoadingSpinner size={36} label="Loading..." />}>
              <ErrorBoundary>
                {requireAuthForHomepage ? (
                  <RequireAuth>
                    <OverviewPage />
                  </RequireAuth>
                ) : (
                  <OverviewPage />
                )}
              </ErrorBoundary>
            </React.Suspense>
          }
        />

        {/* Authenticated management pages requiring Linux user session */}
        <Route
          element={
            <RequireAuth>
              <React.Suspense fallback={<LoadingSpinner size={36} label="Loading..." />}>
                <Outlet />
              </React.Suspense>
            </RequireAuth>
          }
        >
          <Route path="/services" element={<ErrorBoundary><ServicesPage /></ErrorBoundary>} />
          <Route path="/processes" element={<ErrorBoundary><ProcessesPage /></ErrorBoundary>} />
          <Route path="/storage" element={<ErrorBoundary><StoragePage /></ErrorBoundary>} />
          <Route path="/network" element={<ErrorBoundary><NetworkPage /></ErrorBoundary>} />
          <Route path="/packages" element={<ErrorBoundary><PackagesPage /></ErrorBoundary>} />
          <Route path="/users" element={<ErrorBoundary><UsersPage /></ErrorBoundary>} />
          <Route path="/power" element={<ErrorBoundary><PowerPage /></ErrorBoundary>} />
        </Route>
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ToastProvider>
          <AuthProvider>
            <DashboardRoutes />
          </AuthProvider>
        </ToastProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
};
