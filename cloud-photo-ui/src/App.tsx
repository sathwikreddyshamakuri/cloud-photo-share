// src/App.tsx
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
} from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Toaster } from 'react-hot-toast';


import LandingPage        from './pages/LandingPage';
import LoginPage          from './pages/LoginPage';
import SignupPage         from './pages/SignupPage';
import ForgotPasswordPage from './pages/ForgotPassword';
import ResetPasswordPage  from './pages/ResetPassword';
import VerifyEmailPage    from './pages/VerifyEmail';


import WelcomePage  from './pages/WelcomePage';
import Dashboard    from './pages/Dashboard';
import AlbumsPage   from './pages/Albums';
import AlbumPage    from './pages/Album';
import ProfilePage  from './pages/ProfilePage';



function Router() {
  const location          = useLocation();
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));


  useEffect(() => setToken(localStorage.getItem('token')), [location]);


  useEffect(() => {
    const h = () => setToken(localStorage.getItem('token'));
    window.addEventListener('token-change', h);
    return () => window.removeEventListener('token-change', h);
  }, []);

  return (
    <>
      <Routes>
        {/* public */}
        <Route path="/"        element={token ? <Navigate to="/albums" replace /> : <LandingPage        />} />
        <Route path="/login"   element={token ? <Navigate to="/albums" replace /> : <LoginPage          />} />
        <Route path="/signup"  element={token ? <Navigate to="/albums" replace /> : <SignupPage         />} />
        <Route path="/forgot"  element={token ? <Navigate to="/albums" replace /> : <ForgotPasswordPage />} />
        <Route path="/reset"   element={token ? <Navigate to="/albums" replace /> : <ResetPasswordPage  />} />
        <Route path="/verify"  element={token ? <Navigate to="/albums" replace /> : <VerifyEmailPage    />} />

        {/* private */}
        <Route path="/welcome"    element={token ? <WelcomePage />  : <Navigate to="/login" replace />} />
        <Route path="/dashboard"  element={token ? <Dashboard   />  : <Navigate to="/login" replace />} />
        <Route path="/albums"     element={token ? <AlbumsPage  />  : <Navigate to="/login" replace />} />
        <Route path="/albums/:id" element={token ? <AlbumPage   />  : <Navigate to="/login" replace />} />
        <Route path="/profile"    element={token ? <ProfilePage />  : <Navigate to="/login" replace />} />

        {/* fallback → always land on landing page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <Toaster position="bottom-center" />
    </>
  );
}

/* root */
export default function App() {
  return (
    <BrowserRouter>
      <Router />
    </BrowserRouter>
  );
}
