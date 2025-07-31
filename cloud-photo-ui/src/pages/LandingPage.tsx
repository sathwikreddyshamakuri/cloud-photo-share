// src/pages/LoginPage.tsx
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import api   from '../lib/api';

interface LoginResp {
  access_token: string;
}

export default function LoginPage() {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState<string | null>(null);

  const navigate  = useNavigate();
  const location  = useLocation();                 // so we can read flash-msg
  const flashMsg  = location.state?.msg as string | undefined;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    try {
      const { data } = await api.post<LoginResp>('/login', { email, password });

      /* 1️⃣  persist token */
      localStorage.setItem('token', data.access_token);

      /* 2️⃣  notify router right away */
      window.dispatchEvent(new Event('token-change'));

      /* 3️⃣  redirect */
      navigate('/welcome', { replace: true });     // or '/albums'
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Bad credentials');
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4">
      {/* logo / brand */}
      <img src="/nuagevault-logo.png" alt="NuageVault" className="h-14 w-auto mb-6" />

      {/* optional flash message (e.g. “Email verified, please login”) */}
      {flashMsg && (
        <p className="mb-4 px-4 py-2 bg-green-100 text-green-700 rounded">
          {flashMsg}
        </p>
      )}

      <form onSubmit={onSubmit} className="bg-white shadow rounded p-6 w-full max-w-sm space-y-4">
        <h2 className="text-xl font-semibold text-center">Log in</h2>

        {error && <p className="text-red-500">{error}</p>}

        <label className="block">
          Email
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full border p-2 rounded mt-1"
            required
          />
        </label>

        <label className="block">
          Password
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full border p-2 rounded mt-1"
            required
          />
        </label>

        <button
          type="submit"
          className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-500"
        >
          Log In
        </button>

        <div className="flex justify-between text-sm mt-2">
          <Link to="/forgot" className="text-blue-600 hover:underline">
            Forgot password?
          </Link>
          <Link to="/signup" className="text-blue-600 hover:underline">
            Sign up
          </Link>
        </div>
      </form>
    </div>
  );
}
