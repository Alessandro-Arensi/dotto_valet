import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';

import LoginPage from './pages/operator/LoginPage';
import DashboardPage from './pages/operator/DashboardPage';
import CheckinPage from './pages/operator/CheckinPage';
import CheckoutPage from './pages/operator/CheckoutPage';
import EventPage from './pages/public/EventPage';
import TokenPage from './pages/public/TokenPage';
import AdminEventsPage from './pages/admin/AdminEventsPage';
import AdminRacksPage from './pages/admin/AdminRacksPage';
import AdminOperatorsPage from './pages/admin/AdminOperatorsPage';

import OperatorLayout from './components/layout/OperatorLayout';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { isAuthenticated, operator } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requireAdmin && !operator?.is_admin) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

function App() {
  return (
    <Routes>
      <Route path="/evento/:slug" element={<EventPage defaultTab="reserve" />} />
      <Route path="/evento/:slug/walkin" element={<EventPage defaultTab="walkin" />} />
      <Route path="/t/:code" element={<TokenPage />} />

      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <OperatorLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="checkin" element={<CheckinPage />} />
        <Route path="checkout" element={<CheckoutPage />} />
        <Route
          path="admin/events"
          element={
            <ProtectedRoute requireAdmin>
              <AdminEventsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="admin/events/:eventId/racks"
          element={
            <ProtectedRoute requireAdmin>
              <AdminRacksPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="admin/operators"
          element={
            <ProtectedRoute requireAdmin>
              <AdminOperatorsPage />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
