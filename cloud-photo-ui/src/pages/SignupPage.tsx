// cloud-photo-ui/src/pages/SignupPage.tsx
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../lib/api';
import logo from '../assets/nuagevault-logo.svg';

type RegisterResp = {
  user_id: string;
  email_sent: boolean;
  need_verify: boolean;
};

export default function SignupPage() {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState<string | null>(null);
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.post<RegisterResp>('/register', { email, password });

      if (res.data.need_verify) {
        navigate('/login', {
          replace: true,
          state: {
            msg: res.data.email_sent
              ? 'Account created! Check your email to verify your account.'
              : 'Account created, but we could not send a verification email. Try again later.'
          }
        });
      } else {
        // auto-verified (e.g., AUTO_VERIFY_USERS=1)
        navigate('/albums', { replace: true });
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Sign‑up failed');
    }
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-100">
      <form onSubmit={onSubmit} className="bg-white p-6 rounded shadow-md w-80">
        <div className="flex flex-col items-center mb-6">
          <img src={logo} alt="NuageVault" className="h-12 w-auto" />
          <h2 className="text-xl font-semibold mt-2">Login to your vault</h2>
        </div>

        {error && <p className="text-red-500 mb-2">{error}</p>}

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
            minLength={6}
          />
        </label>

        <button
          type="submit"
          className="w-full bg-green-600 text-white p-2 rounded hover:bg-green-700"
        >
          Sign Up
        </button>

        <p className="mt-3 text-sm text-center">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:underline">
            Log in
          </Link>
        </p>
      </form>
    </div>
  );
}
