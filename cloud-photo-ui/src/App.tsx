import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import Login   from './pages/Login';
import Albums  from './pages/Albums';
import Album   from './pages/Album';
>>>>>>> 2aae70b (chore: clean up gitignore and commit real source changes)

/* ------ Header with Logout -------------------------------------------- */
function Header() {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('jwt');
    navigate('/login');
  };

  return (
    <header className="flex justify-end bg-white p-4 shadow">
      <button
        onClick={handleLogout}
        className="rounded bg-red-500 px-3 py-1 font-medium text-white hover:bg-red-400"
      >
        Logout
      </button>
    </header>
  );
}

/* ------ Main App ------------------------------------------------------- */
function App() {
  const hasToken = !!localStorage.getItem('jwt');

  return (
    <BrowserRouter>
      {/* Show the header only when signed in */}
      {hasToken && <Header />}

      <Routes>
        <Route
          path="/"
          element={
            hasToken ? <Navigate to="/albums" replace /> : <Navigate to="/login" replace />
          }
        />

        <Route path="/login"     element={<Login  />} />
        <Route path="/albums"    element={<Albums />} />
        <Route path="/album/:id" element={<Album  />} />

        {/* Optional catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
