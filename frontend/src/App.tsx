import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';

// Pages
import LoginPage from './pages/operator/LoginPage';
import DashboardPage from './pages/operator/DashboardPage';
import CheckinPage from './pages/operator/CheckinPage';
import CheckoutPage from './pages/operator/CheckoutPage';
import EventPage from './pages/public/EventPage';
import TokenPage from './pages/public/TokenPage';

// Layout
import OperatorLayout from './components/layout/OperatorLayout';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
}

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/evento/:slug" element={<EventPage />} />
      <Route path="/t/:code" element={<TokenPage />} />
      
      {/* Auth routes */}
      <Route path="/login" element={<LoginPage />} />
      
      {/* Protected operator routes */}
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
      </Route>
      
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;


