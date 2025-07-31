// cloud-photo-ui/src/pages/SignupPage.tsx
import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../lib/api';

type RegisterResp = {
  user_id:     string;
  email_sent:  boolean;
  need_verify: boolean;
};

export default function SignupPage() {
  const navigate = useNavigate();

  /* redirect if already logged-in */
  useEffect(() => {
    if (localStorage.getItem('token')) {
      navigate('/albums', { replace: true });
    }
  }, [navigate]);

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [error,    setError]    = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    try {
      const { data } = await api.post<RegisterResp>('/register', { email, password });

      if (data.need_verify) {
        navigate('/login', {
          replace: true,
          state: {
            msg: data.email_sent
              ? 'Account created! Check your email to verify your account.'
              : 'Account created, but we could not send a verification email. Try again later.',
          },
        });
      } else {
        /* AUTO_VERIFY_USERS=1 path */
        navigate('/albums', { replace: true });
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Sign-up failed');
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4">
      {/* brand header */}
      <div className="flex flex-col items-center mb-6">
        {/* logo lives in /public so it’s served at the root */}
        <img src="/nuagevault-logo.png" alt="NuageVault" className="h-12 w-auto" />
        <h2 className="text-xl font-semibold mt-2">Create your vault account</h2>
      </div>

      <form onSubmit={onSubmit} className="bg-white p-6 rounded shadow-md w-80">
        {error && <p className="text-red-500 mb-3">{error}</p>}

        <label className="block mb-3">
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
