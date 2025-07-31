// cloud-photo-ui/src/App.tsx
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
} from 'react-router-dom';
import { useEffect, useState, Fragment } from 'react';
import { Toaster } from 'react-hot-toast';

/* ── public-auth pages ── */
import LandingPage        from './pages/LandingPage';
import LoginPage          from './pages/LoginPage';
import SignupPage         from './pages/SignupPage';
import ForgotPasswordPage from './pages/ForgotPassword';
import ResetPasswordPage  from './pages/ResetPassword';
import VerifyEmailPage    from './pages/VerifyEmail';

/* ── private pages ── */
import WelcomePage  from './pages/WelcomePage';
import Dashboard    from './pages/Dashboard';
import AlbumsPage   from './pages/Albums';
import AlbumPage    from './pages/Album';
import ProfilePage  from './pages/ProfilePage';

function Router() {
  const location          = useLocation();
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('token')
  );

  /* refresh token when route changes */
  useEffect(() => {
    setToken(localStorage.getItem('token'));
  }, [location]);

  /* listen for manual “token-change” events (logout, login, etc.) */
  useEffect(() => {
    const handler = () => setToken(localStorage.getItem('token'));
    window.addEventListener('token-change', handler);
    return () => window.removeEventListener('token-change', handler);
  }, []);

  return (
    <Fragment>
      <Routes>
        {/* ───── public routes ───── */}
        <Route
          path="/"
          element={token ? <Navigate to="/albums" replace /> : <LandingPage />}
        />
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
          element={
            token ? <Navigate to="/albums" replace /> : <ForgotPasswordPage />
          }
        />
        <Route
          path="/reset"
          element={token ? <Navigate to="/albums" replace /> : <ResetPasswordPage />}
        />
        <Route
          path="/verify"
          element={token ? <Navigate to="/albums" replace /> : <VerifyEmailPage />}
        />

        {/* ───── private routes ───── */}
        <Route
          path="/welcome"
          element={token ? <WelcomePage /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/dashboard"
          element={token ? <Dashboard /> : <Navigate to="/login" replace />}
        />
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

        {/* fallback */}
        <Route
          path="*"
          element={<Navigate to={token ? '/albums' : '/login'} replace />}
        />
      </Routes>

      {/* global toast notifications */}
      <Toaster position="bottom-center" />
    </Fragment>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Router />
    </BrowserRouter>
  );
}
