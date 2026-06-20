import { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Eye, EyeOff, KeyRound, ShieldCheck, Sparkles, Terminal } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { isDemo } from "../lib/api";

export default function Auth() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { signIn, isAuthed } = useAuth();
  const [key, setKey] = useState(params.get("key") || "");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // If ?demo=true is on the URL, auto-authenticate.
  useEffect(() => {
    if (isDemo() && !isAuthed) {
      signIn("demo-7c1f2d-a87e9-9fe870");
      navigate("/console", { replace: true });
    }
  }, [signIn, isAuthed, navigate]);

  // If already authed, skip the page.
  useEffect(() => {
    if (isAuthed) navigate("/console", { replace: true });
  }, [isAuthed, navigate]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (key.trim().length < 8) {
      setError("Key must be at least 8 characters.");
      return;
    }
    setLoading(true);
    setTimeout(() => {
      signIn(key);
      navigate("/console");
    }, 600);
  }

  return (
    <div className="min-h-screen bg-bone text-ink flex">
      {/* Left: brand statement */}
      <aside className="hidden lg:flex w-1/2 flex-col justify-between p-12 border-r border-ink bg-ink text-bone">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-bone flex items-center justify-center">
            <span className="font-display text-ink text-lg leading-none -mt-0.5">P</span>
          </div>
          <span className="font-display text-xl">PARALLAX</span>
        </Link>

        <div>
          <div className="eyebrow text-bone/60 mb-5 flex items-center gap-2">
            <span className="w-6 h-px bg-bone" /> Access restricted
          </div>
          <h1 className="font-display text-display-lg text-balance leading-[0.95]">
            Analyst<br />
            <em className="italic text-acid">Console</em>
          </h1>
          <p className="mt-6 max-w-md text-bone/70 leading-relaxed">
            Submit APKs. Watch the case room. Pull evidence bundles.
            The eight agents do the rest.
          </p>
        </div>

        <div className="font-mono text-[10px] uppercase tracking-widest text-bone/40 flex items-center gap-3">
          <span className="live-dot" />
          <span>System online · 8 agents ready</span>
        </div>
      </aside>

      {/* Right: form */}
      <section className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number] }}
          className="w-full max-w-sm"
        >
          <div className="eyebrow mb-3 flex items-center gap-2 lg:hidden">
            <span className="w-6 h-px bg-ink" /> Analyst Console
          </div>
          <h2 className="font-display text-4xl leading-none mb-2">Sign in.</h2>
          <p className="text-ink/60 text-sm mb-8">
            Your API key is the only thing standing between you and 8 agents arguing about malware.
          </p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="eyebrow block mb-2">API Key</label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink/40" strokeWidth={1.6} />
                <input
                  type={show ? "text" : "password"}
                  value={key}
                  onChange={(e) => setKey(e.target.value)}
                  placeholder="pax_live_••••••••••••••••"
                  className="input pl-10 pr-10"
                  autoComplete="off"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShow(!show)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-ink/50 hover:text-ink"
                >
                  {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {error && (
                <p className="mt-2 font-mono text-xs text-oxblood">{error}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full h-12"
            >
              {loading ? (
                <span className="font-mono text-xs uppercase tracking-widest">Authenticating…</span>
              ) : (
                <>
                  Enter the console
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 border-t border-ink/10 pt-5 space-y-2">
            <button
              onClick={() => {
                signIn("demo-7c1f2d-a87e9-9fe870");
                navigate("/console");
              }}
              className="w-full h-11 flex items-center justify-center gap-2 border border-ink hover:bg-ink hover:text-bone transition-colors text-sm"
            >
              <Sparkles className="w-4 h-4" />
              Enter the demo
            </button>
            <p className="font-mono text-[10px] text-ink/50 text-center">
              Demo loads realistic seeded data — no live backend required.
            </p>
          </div>

          <div className="mt-8 grid grid-cols-2 gap-2 font-mono text-[10px] uppercase tracking-widest text-ink/60">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-3 h-3" />
              <span>AES-256 in transit</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Terminal className="w-3 h-3" />
              <span>8 agents standing by</span>
            </div>
          </div>

          <div className="mt-8 font-mono text-[10px] text-ink/40">
            <Link to="/" className="hover:text-ink">← Back to overview</Link>
          </div>
        </motion.div>
      </section>
    </div>
  );
}
