// cloud-photo-ui/src/pages/ResetPasswordPage.tsx
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import logo from '../assets/nuagevault-logo.png';

export default function ResetPasswordPage() {
  const [sp] = useSearchParams();
  const token = sp.get('token') ?? '';
  const emailParam = sp.get('email') ?? '';       // 👈 read email from URL
  const email = emailParam.toLowerCase();         // 👈 normalize casing
  const navigate = useNavigate();

  const [pwd, setPwd] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErr(null);

    if (!token || !emailParam) {
      setErr(!token ? 'Missing token.' : 'Missing email address.');
      return;
    }
    if (pwd.length < 8) { setErr('Password must be at least 8 characters.'); return; }

    try {
      setBusy(true);
      // ✅ correct endpoint + include email
      await api.post('/auth/reset-password', {
        email,
        token,
        new_password: pwd,
      });
      setMsg('Password updated. Redirecting to login…');
      setTimeout(() => navigate('/login', { replace: true }), 1200);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to reset (link may be expired).');
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Missing token</p>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
      <form onSubmit={submit} className="bg-white p-6 rounded shadow-md w-80 space-y-3">
        <div className="flex flex-col items-center mb-2">
          <img src={logo} alt="NuageVault" className="h-12 w-auto" />
          <h2 className="text-xl font-semibold mt-2">Reset your password</h2>
          {emailParam && (
            <p className="text-xs text-gray-600 break-all">for <span className="font-mono">{emailParam}</span></p>
          )}
        </div>

        {msg && <p className="text-green-600 text-sm">{msg}</p>}
        {err && <p className="text-red-600 text-sm">{err}</p>}

        <label className="block">
          <span className="text-sm">New password</span>
          <input
            type="password"
            className="w-full border p-2 rounded mt-1"
            value={pwd}
            onChange={e => setPwd(e.target.value)}
            required
            minLength={8}
          />
        </label>

        <button
          className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700 disabled:opacity-60"
          disabled={busy}
        >
          {busy ? 'Updating…' : 'Update'}
        </button>

        <p className="text-center text-sm mt-3">
          <Link to="/login" className="text-blue-600 hover:underline">Back to login</Link>
        </p>
      </form>
    </div>
  );
}
