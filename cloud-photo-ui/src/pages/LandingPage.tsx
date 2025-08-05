// cloud-photo-ui/src/pages/LandingPage.tsx
import { Link } from 'react-router-dom';
import logo     from '../assets/nuagevault-logo.png';   // same file used elsewhere

export default function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-900">
      {/* ───── hero ───── */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-4">
        <img
          src={logo}
          alt="NuageVault"
          className="h-20 w-auto mb-8 drop-shadow-lg"
        />

        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight mb-4">
          Your <span className="text-indigo-600">secure</span> personal cloud
        </h1>

        <p className="max-w-xl mx-auto text-lg text-slate-600 dark:text-slate-300 mb-8">
          NuageVault stores, organises and shares your memories on <em>your</em>
          &nbsp;terms. 100 % private • End-to-end encrypted • Runs on AWS.
        </p>

        <div className="flex flex-wrap justify-center gap-4">
          <Link
            to="/signup"
            className="rounded bg-indigo-600 px-6 py-3 text-white font-medium hover:bg-indigo-500 transition"
          >
            Get started – it’s free
          </Link>
          <Link
            to="/login"
            className="rounded border border-indigo-600 px-6 py-3 text-indigo-600 font-medium hover:bg-indigo-50 dark:hover:bg-slate-800/40 transition"
          >
            Log&nbsp;in
          </Link>
        </div>
      </section>

      {/* ───── tiny features strip (optional) ───── */}
      <section className="bg-white dark:bg-slate-800 py-8 border-t border-slate-200 dark:border-slate-700">
        <div className="max-w-5xl mx-auto grid gap-6 sm:grid-cols-3 px-6 text-center">
          <Feature icon="🔒" title="Zero-knowledge">
            Only <strong>you</strong> can read your photos.
          </Feature>
          <Feature icon="⚡" title="Blazing fast">
            Optimised CloudFront delivery worldwide.
          </Feature>
          <Feature icon="☁️" title="Unlimited storage">
            Pay only for what you actually use.
          </Feature>
        </div>
      </section>

      {/* ───── footer ───── */}
      <footer className="py-6 text-center text-sm text-slate-500 dark:text-slate-400">
        © {new Date().getFullYear()} NuageVault • Made with&nbsp;❤
      </footer>
    </main>
  );
}

function Feature({
  icon,
  title,
  children,
}: {
  icon: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <div className="text-3xl">{icon}</div>
      <h3 className="font-semibold">{title}</h3>
      <p className="text-sm text-slate-600 dark:text-slate-300">{children}</p>
    </div>
  );
}
