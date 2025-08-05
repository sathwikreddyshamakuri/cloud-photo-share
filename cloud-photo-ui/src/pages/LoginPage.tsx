// cloud-photo-ui/src/pages/LoginPage.tsx
import { useState } from 'react';
import type { FormEvent } from 'react';
import logo from '../assets/nuagevault-logo.png';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import api from '../lib/api';

export default function LoginPage() {
  const navigate   = useNavigate();
  const loc        = useLocation();
  const flashMsg: string | undefined = (loc.state as any)?.msg;

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [error,    setError]    = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    try {
      /* ---- hit API ---- */
      const { data } = await api.post<{ access_token: string }>('/login', {
        email,
        password,
      });

      /* ---- store token & notify app ---- */
      localStorage.setItem('token', data.access_token);
      window.dispatchEvent(new Event('token-change'));

      /* ---- go to main app ---- */
      navigate('/albums', { replace: true });
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

        {/* body */}
        <div className="p-8 flex flex-col items-center space-y-6">
          <img
            alt="NuageVault"
            className="h-16 w-16 rounded shadow-sm"
          />

          <h2 className="text-2xl font-semibold text-center">
            Login to your vault
          </h2>

          {flashMsg && (
            <p className="w-full text-sm text-green-600 bg-green-50 border border-green-200 rounded p-2">
              {flashMsg}
            </p>
          )}
          {error && (
            <p className="w-full text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
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
         {/* logo */}
          <img
            src={logo}
            alt="NuageVault"
           className="h-16 w-16 rounded shadow-sm"
          />
          <button
            type="submit"
            className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-500 transition"
          >
            Login
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
