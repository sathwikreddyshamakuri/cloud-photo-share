import { useSearchParams, Link, useNavigate } from "react-router-dom";
import { useEffect, useMemo } from "react";

// Use Vite URL import to avoid PNG typings
const logoUrl = new URL("../assets/nuagevault-logo.png", import.meta.url).href;

export default function VerifyResultPage() {
  const [sp] = useSearchParams();
  const status = (sp.get("status") || "").toLowerCase();
  const navigate = useNavigate();

  const meta = useMemo(() => {
    switch (status) {
      case "ok":
        return { title: "Email verified!", desc: "Your email is now verified. You can log in to your vault.", tone: "ok" as const };
      case "already":
        return { title: "Already verified", desc: "Your email was already verified. You can log in.", tone: "ok" as const };
      case "expired":
        return { title: "Link expired", desc: "Your verification link expired. Request a new one from the login page.", tone: "warn" as const };
      case "invalid":
        return { title: "Invalid link", desc: "This verification link is not valid. Please request a new one.", tone: "err" as const };
      case "notfound":
        return { title: "Account not found", desc: "We couldn’t find an account for that email. Try signing up.", tone: "err" as const };
      default:
        return { title: "Verification status", desc: "We could not determine your verification status.", tone: "warn" as const };
    }
  }, [status]);

  useEffect(() => {
    if (meta.tone === "ok") {
      const id = setTimeout(() => navigate("/login", { replace: true }), 1600);
      return () => clearTimeout(id);
    }
  }, [meta.tone, navigate]);

  const toneClass =
    meta.tone === "ok" ? "text-green-600" :
    meta.tone === "warn" ? "text-amber-600" : "text-red-600";

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-100 p-6 space-y-6">
      <img src={logoUrl} alt="NuageVault" className="h-14 w-auto drop-shadow-sm" />
      <h1 className={`text-2xl font-semibold ${toneClass}`}>{meta.title}</h1>
      <p className="text-center text-sm text-gray-700 max-w-sm">{meta.desc}</p>
      <div className="space-x-4">
        <Link className="text-blue-600 hover:underline" to="/login">Go to login</Link>
        <Link className="text-blue-600 hover:underline" to="/signup">Sign up</Link>
      </div>
    </div>
  );
}