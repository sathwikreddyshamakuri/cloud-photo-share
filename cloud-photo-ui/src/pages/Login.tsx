import { useState, type FormEvent, ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';

/**
 * Login page — POSTs {email, password} to /auth/login,
 * stores the returned JWT, then routes to /albums.
 */
export default function Login() {
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // handle both inputs with one function
  const handleChange = (e: ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    try {
      const res = await api.post('/login', form);
      localStorage.setItem('jwt', res.data.access_token);
      navigate('/albums');
    } catch {
      setError('Invalid credentials');
    }
  };

  return (
    <div className="grid min-h-screen place-items-center bg-slate-900">
      <form
        onSubmit={submit}
        className="w-80 space-y-4 rounded-2xl bg-white p-8 shadow-xl"
      >
        <h1 className="text-center text-2xl font-semibold">Sign in</h1>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <input
          className="w-full rounded border p-2"
          name="email"
          type="email"
          placeholder="Email"
          value={form.email}
          onChange={handleChange}
          required
        />

        <input
          className="w-full rounded border p-2"
          name="password"
          type="password"
          placeholder="Password"
          value={form.password}
          onChange={handleChange}
          required
        />

        <button
          type="submit"
          className="w-full rounded bg-emerald-600 py-2 font-semibold text-white hover:bg-emerald-500"
        >
          Log in
        </button>
      </form>
    </div>
  );
}
