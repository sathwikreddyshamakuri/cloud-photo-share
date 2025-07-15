import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import LoginPage from './pages/LoginPage'
import AlbumsPage from './pages/Albums'
import AlbumPage from './pages/Album'

export default function App() {
  const token = localStorage.getItem('token')

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={token ? <Navigate to="/albums" replace /> : <LoginPage />}
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
          path="*"
          element={<Navigate to={token ? '/albums' : '/login'} replace />}
        />
      </Routes>
    </BrowserRouter>
  )
}
