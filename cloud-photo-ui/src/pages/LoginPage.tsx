// cloud-photo-ui/src/pages/LoginPage.tsx
import { useState, useEffect, type FormEvent } from 'react';
import { Link, useLocation, useNavigate }      from 'react-router-dom';
import toast                                   from 'react-hot-toast';
import logo                                    from '../assets/nuagevault-logo.png';
import api, { setAuthToken }                   from '../lib/api';

export default function LoginPage() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const flashMsg: string | undefined = (state as any)?.msg;

  /* toast once on first paint */
  useEffect(() => {
    if (flashMsg) toast.success(flashMsg);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* if already authenticated, skip */
  useEffect(() => {
    if (localStorage.getItem('token')) {
      navigate('/albums', { replace: true });
    }
  }, [navigate]);

  /* form state */
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [error,    setError]    = useState<string | null>(null);
  const [loading,  setLoading]  = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      // supports cookie sessions + bearer tokens
      const res = await api.post<{ access_token?: string }>(
        '/login',
        { email, password },
        { withCredentials: true }
      );

      const token = res.data?.access_token;

      // >>> KEY: persist token & set Authorization header for all future requests
      if (token) setAuthToken(token);
      else setAuthToken(undefined); // cookie-only path — clear any stale header

      toast.success('Logged in');
      navigate('/albums', { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-800 p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md bg-white dark:bg-slate-700 rounded-lg shadow-lg overflow-hidden"
      >
        <div className="h-2 bg-indigo-600" />

        <div className="p-8 flex flex-col items-center space-y-6">
          <img src={logo} alt="NuageVault" className="h-16 w-16 rounded shadow-sm" />
          <h2 className="text-2xl font-semibold">Log in</h2>

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
            disabled={loading}
            className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-500 transition disabled:opacity-60"
          >
            {loading ? 'Signing in…' : 'Log In'}
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
