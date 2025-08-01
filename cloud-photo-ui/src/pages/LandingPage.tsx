// cloud-photo-ui/src/pages/LoginPage.tsx
import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import logo from '../assets/nuagevault-logo.png';   // ✔ bundled path

export default function LoginPage() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const flashMsg: string | undefined = (state as any)?.msg;

  // ── redirect authenticated users straight to /albums ──
  if (localStorage.getItem('token')) {
    navigate('/albums', { replace: true });
  }

  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    try {
      await api.post('/login', { email, password });
      // login OK → show intro splash, then albums
      navigate('/welcome', { replace: true });
      window.dispatchEvent(new Event('token-change'));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-800 p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md bg-white dark:bg-slate-700 rounded-lg shadow-lg overflow-hidden"
      >
        {/* top accent bar */}
        <div className="h-2 bg-indigo-600" />

        <div className="p-8 flex flex-col items-center space-y-6">
          <img src={logo} alt="NuageVault" className="h-16 w-16 rounded" />

          <h2 className="text-2xl font-semibold text-center">Log in</h2>

          {flashMsg && (
            <p className="w-full text-sm text-green-700 bg-green-50 border border-green-200 rounded p-2">
              {flashMsg}
            </p>
          )}
          {error && (
            <p className="w-full text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
              {error}
            </p>
          )}

          <label className="w-full space-y-1">
            <span className="text-sm">Email</span>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              className="w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </label>

          <label className="w-full space-y-1">
            <span className="text-sm">Password</span>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </label>

          <button
            type="submit"
            className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-500 transition"
          >
            Log In
          </button>

          <div className="flex justify-between w-full text-sm">
            <Link to="/forgot" className="text-blue-600 hover:underline">
              Forgot password?
            </Link>
            <span>
              Need an account?{' '}
              <Link to="/signup" className="text-blue-600 hover:underline">
                Sign up
              </Link>
            </span>
          </div>
        </div>
      </form>
    </main>
  );
}
