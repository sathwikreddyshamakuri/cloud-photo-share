import { useEffect, useState } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import api  from '../lib/api';
import logo from '../assets/nuagevault-logo.svg';

export default function VerifyEmailPage() {
  const [sp]      = useSearchParams();
  const token     = sp.get('token') ?? '';
  const navigate  = useNavigate();

  const [status, setStatus] = useState<'loading' | 'ok' | 'err'>('loading');
  const [msg,    setMsg]    = useState('');

 
  useEffect(() => {
    if (!token) {
      setStatus('err');
      setMsg('Missing verification token.');
      return;
    }

    api.post('/auth/verify', { token })
       .then(() => {
         setStatus('ok');
         // bounce to login after 1.5 s
         setTimeout(() => {
           navigate('/login', {
             replace: true,
             state  : { msg: 'Email verified. Please log in.' },
           });
         }, 1500);
       })
       .catch(e => {
         setStatus('err');
         setMsg(e.response?.data?.detail || 'Invalid or expired link.');
       });
  }, [token, navigate]);

  
  const heading =
    status === 'loading' ? 'Verifying your email…' :
    status === 'ok'      ? 'Email verified!'       :
                           'Verification failed';

  const headingClass =
    status === 'loading' ? 'text-slate-700' :
    status === 'ok'      ? 'text-green-600' :
                           'text-red-600';

   return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100 space-y-6 p-4">
      {/* logo */}
      <img src={logo} alt="NuageVault" className="h-14 w-auto drop-shadow-sm" />

      {/* heading */}
      <h1 className={`text-2xl font-semibold ${headingClass}`}>{heading}</h1>

      {/* error details */}
      {status === 'err' && (
        <>
          <p className="text-center text-sm text-gray-600 max-w-xs">{msg}</p>
          <Link to="/login" className="text-blue-600 hover:underline">
            Back to login
          </Link>
        </>
      )}
    </div>
  );
}
