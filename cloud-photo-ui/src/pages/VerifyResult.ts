// cloud-photo-ui/src/pages/VerifyResult.tsx
import { useSearchParams, Link } from "react-router-dom";

export default function VerifyResult() {
  const [sp] = useSearchParams();
  const status = sp.get("status") ?? "unknown";

  const map: Record<string, { title: string; msg: string }> = {
    ok:       { title: "Email verified ✓", msg: "You're all set. Please sign in." },
    already:  { title: "Already verified", msg: "You can sign in now." },
    expired:  { title: "Link expired", msg: "Request a new verification email from your profile." },
    invalid:  { title: "Invalid link", msg: "Please request a fresh verification email." },
    notfound: { title: "Account not found", msg: "Please sign up again or contact support." },
    unknown:  { title: "Something went wrong", msg: "Please try again." },
  };

  const view = map[status];

  return (
    <div className="max-w-md mx-auto mt-20 p-6 rounded-2xl shadow">
      <h1 className="text-2xl font-semibold mb-2">{view.title}</h1>
      <p className="mb-6">{view.msg}</p>
      <Link to="/login" className="inline-block px-4 py-2 rounded-xl bg-black text-white">Go to Login</Link>
    </div>
  );
}
