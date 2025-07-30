import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function WelcomePage() {
  const navigate = useNavigate();

  // auto‑forward after 5 s
  useEffect(() => {
    const t = setTimeout(() => navigate('/albums', { replace: true }), 5000);
    return () => clearTimeout(t);
  }, [navigate]);

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-black text-white">
      {/* replace src with any mp4/webm you like – must allow CORS on the host */}
      <video
        src="https://assets.mixkit.co/videos/preview/mixkit-clouds-in-the-sky-12365-large.mp4"
        autoPlay
        muted
        loop
        className="max-h-[60vh] rounded-lg shadow-lg"
      />
      <p className="mt-6 text-xl font-semibold animate-pulse">
        Welcome to Your Private Cloud
      </p>
    </div>
  );
}
