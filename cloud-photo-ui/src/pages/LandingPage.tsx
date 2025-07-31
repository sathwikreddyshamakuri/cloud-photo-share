// src/pages/LandingPage.tsx
import { Link } from 'react-router-dom';

export default function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col justify-between bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100">
      {/* hero */}
      <section className="flex-1 flex flex-col items-center justify-center p-8 text-center">
        {/* logo goes in /public/nuagevault-logo.png (or .svg) */}
        <img
          src="/nuagevault-logo.png"
          alt="NuageVault"
          className="h-20 w-auto mb-6"
        />

        <h1 className="text-4xl font-extrabold mb-4">
          Your private photo cloud
        </h1>
        <p className="max-w-lg mx-auto text-lg mb-8">
          Store, organise and share your memories – securely and effortlessly –
          with <span className="font-semibold">NuageVault</span>.
        </p>

        <div className="space-x-4">
          <Link
            to="/signup"
            className="inline-block rounded bg-blue-600 px-6 py-3 text-white font-medium hover:bg-blue-500"
          >
            Get started
          </Link>
          <Link
            to="/login"
            className="inline-block rounded border border-blue-600 px-6 py-3 text-blue-600 font-medium hover:bg-blue-50 dark:hover:bg-slate-800/40"
          >
            Log in
          </Link>
        </div>
      </section>

      {/* footer */}
      <footer className="py-6 text-center text-sm opacity-70">
        © {new Date().getFullYear()} NuageVault
      </footer>
    </main>
  );
}
