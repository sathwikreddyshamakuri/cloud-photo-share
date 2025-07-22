// cloud-photo-ui/src/pages/LoginPage.tsx
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useLocation, Link } from 'react-router-dom';
import api from '../lib/api';

export default function LoginPage() {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState<string | null>(null);

  const location = useLocation();
  const flashMsg = (location.state as any)?.msg ?? null;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.post('/login', { email, password });
      localStorage.setItem('token', res.data.access_token);

      // make sure the rest of the app notices the new token
      window.dispatchEvent(new Event('token-change'));

      // hard redirect so Router picks up token immediately
      window.location.replace('/albums');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    }
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-100">
      <form onSubmit={onSubmit} className="bg-white p-6 rounded shadow-md w-80">
        <h2 className="text-xl font-semibold mb-4">Login</h2>

        {flashMsg && <p className="text-green-600 mb-2">{flashMsg}</p>}
        {error    && <p className="text-red-500   mb-2">{error}</p>}

        <label className="block mb-2">
          Email
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full border p-2 rounded mt-1"
            required
          />
        </label>

        <label className="block mb-4">
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
          className="w-full bg-blue-500 text-white p-2 rounded hover:bg-blue-600"
        >
          Login
        </button>

        <p className="mt-3 text-sm text-center">
          Need an account?{' '}
          <Link to="/signup" className="text-blue-600 hover:underline">
            Sign up
          </Link>
        </p>
      </form>
    </div>
  );
}
