// force redeploy
// cloud-photo-ui/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';

import LoginPage           from './pages/LoginPage';
import SignupPage          from './pages/SignupPage';
import ForgotPasswordPage  from './pages/ForgotPassword';
import ResetPasswordPage   from './pages/ResetPassword';
import VerifyEmailPage     from './pages/VerifyEmail';
import AlbumsPage          from './pages/Albums';
import AlbumPage           from './pages/Album';
import ProfilePage         from './pages/ProfilePage';

function Router() {
  const location = useLocation();
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));

  // update when route changes
  useEffect(() => {
    setToken(localStorage.getItem('token'));
  }, [location]);

  // update when we manually dispatch after login/logout
  useEffect(() => {
    const handler = () => setToken(localStorage.getItem('token'));
    window.addEventListener('token-change', handler);
    return () => window.removeEventListener('token-change', handler);
  }, []);

  return (
    <Routes>
      {/* Public auth pages */}
      <Route
        path="/login"
        element={token ? <Navigate to="/albums" replace /> : <LoginPage />}
      />
      <Route
        path="/signup"
        element={token ? <Navigate to="/albums" replace /> : <SignupPage />}
      />
      <Route
        path="/forgot"
        element={token ? <Navigate to="/albums" replace /> : <ForgotPasswordPage />}
      />
      <Route
        path="/reset"
        element={token ? <Navigate to="/albums" replace /> : <ResetPasswordPage />}
      />
      <Route
        path="/verify"
        element={token ? <Navigate to="/albums" replace /> : <VerifyEmailPage />}
      />

      {/* Protected pages */}
      <Route
        path="/albums"
        element={token ? <AlbumsPage /> : <Navigate to="/login" replace />}
      />
      <Route
        path="/albums/:id"
        element={token ? <AlbumPage /> : <Navigate to="/login" replace />}
      />
      <Route
        path="/profile"
        element={token ? <ProfilePage /> : <Navigate to="/login" replace />}
      />

      {/* catch‑all */}
      <Route
        path="*"
        element={<Navigate to={token ? '/albums' : '/login'} replace />}
      />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Router />
    </BrowserRouter>
  );
}
