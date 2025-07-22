// cloud-photo-ui/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';

import LoginPage  from './pages/LoginPage';
import AlbumsPage from './pages/Albums';
import AlbumPage  from './pages/Album';
import SignupPage from './pages/SignupPage';
import ProfilePage from './pages/profilepage';

function Router() {
  const location = useLocation();

  // keep token in React state so it updates after login/logout
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));

  // whenever route changes, check if localStorage token changed
  useEffect(() => {
    setToken(localStorage.getItem('token'));
  }, [location]);

  return (
    <Routes>
      <Route
        path="/login"
        element={token ? <Navigate to="/albums" replace /> : <LoginPage />}
      />

      <Route
        path="/signup"
       element={token ? <Navigate to="/albums" replace /> : <SignupPage />}
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
