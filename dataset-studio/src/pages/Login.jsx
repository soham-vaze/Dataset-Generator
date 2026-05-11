import { useState } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";
import AnimatedBackground from "../components/AnimatedBackground";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, delay: i * 0.08, ease: [0.25, 0.46, 0.45, 0.94] },
  }),
};

const logoIcon = (
  <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 2L2 7l10 5 10-5-10-5z" />
    <path d="M2 17l10 5 10-5" opacity="0.5" />
    <path d="M2 12l10 5 10-5" opacity="0.7" />
  </svg>
);

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [focused, setFocused] = useState(null);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    try {
      const res = await axios.post("http://localhost:8000/login", formData);
      login(res.data.access_token);
      navigate("/");
    } catch (err) {
      setError("Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex overflow-hidden">
      <AnimatedBackground variant="login" />

      {/* Ambient light blobs */}
      <div className="fixed inset-0 z-[1] pointer-events-none overflow-hidden">
        <div className="absolute -top-[30%] -left-[15%] w-[700px] h-[700px] rounded-full bg-primary/[0.04] blur-[120px] animate-float" />
        <div className="absolute -bottom-[20%] -right-[10%] w-[600px] h-[600px] rounded-full bg-blue-500/[0.03] blur-[100px] animate-float" style={{ animationDelay: "-3s" }} />
        <div className="absolute top-[40%] left-[60%] w-[400px] h-[400px] rounded-full bg-cyan-500/[0.02] blur-[80px] animate-float" style={{ animationDelay: "-5s" }} />
      </div>

      {/* Left branding panel */}
      <div className="hidden lg:flex lg:w-[52%] relative z-10 flex-col justify-between p-14 xl:p-16">
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="flex items-center gap-3"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary via-primary-700 to-blue-500 flex items-center justify-center shadow-glow">
            {logoIcon}
          </div>
          <span className="text-lg font-bold text-zinc-100 tracking-tight">Dataset Studio</span>
        </motion.div>

        <div className="max-w-xl">
          <motion.h1
            initial="hidden"
            animate="visible"
            className="text-[3.4rem] xl:text-[3.8rem] font-extrabold leading-[1.08] tracking-[-0.03em]"
          >
            <motion.span variants={fadeUp} custom={1} className="block text-gradient">
              Generate
            </motion.span>
            <motion.span variants={fadeUp} custom={2} className="block text-zinc-100">
              Production-Ready
            </motion.span>
            <motion.span variants={fadeUp} custom={3} className="block text-zinc-100">
              AI Datasets
            </motion.span>
            <motion.span variants={fadeUp} custom={4} className="block text-gradient-blue">
              in Minutes
            </motion.span>
          </motion.h1>

          <motion.p
            variants={fadeUp}
            custom={5}
            initial="hidden"
            animate="visible"
            className="text-zinc-400 text-[17px] leading-relaxed max-w-md mt-7"
          >
            The intelligent platform for creating high-quality synthetic datasets.
            SFT, NL-SQL, RAG-QA, Classification, Code, and Multilingual — all in one place.
          </motion.p>

          {/* Stats */}
          <motion.div
            initial="hidden"
            animate="visible"
            className="flex gap-4 mt-12"
          >
            {[
              { value: "6", label: "Dataset Types", gradient: "text-gradient" },
              { value: "50+", label: "Languages", gradient: "text-gradient-blue" },
              { value: "∞", label: "Possibilities", gradient: "text-gradient-emerald" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                variants={fadeUp}
                custom={7 + i}
                className="group relative rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm px-6 py-4 hover:border-white/[0.1] hover:bg-white/[0.035] transition-all duration-500"
              >
                <div className={`text-2xl font-bold ${stat.gradient}`}>{stat.value}</div>
                <div className="text-[11px] text-zinc-500 font-medium mt-1.5 tracking-wide">{stat.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.8 }}
          className="flex items-center gap-3"
        >
          <div className="flex -space-x-1.5">
            {["bg-primary-500", "bg-blue-500", "bg-cyan-500"].map((c, i) => (
              <div key={i} className={`w-2 h-2 rounded-full ${c} ring-2 ring-dark`} />
            ))}
          </div>
          <p className="text-xs text-zinc-600">
            Powered by Local LLMs · Built for AI Engineers
          </p>
        </motion.div>
      </div>

      {/* Right login panel */}
      <div className="flex-1 flex items-center justify-center relative z-10 p-6 lg:p-12">
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="w-full max-w-[420px]"
        >
          <div className="glass-card p-8 md:p-10 relative overflow-hidden">
            {/* Subtle top accent */}
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

            {/* Mobile logo */}
            <div className="flex items-center gap-3 mb-8 lg:hidden">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary via-primary-700 to-blue-500 flex items-center justify-center shadow-glow">
                {logoIcon}
              </div>
              <span className="text-base font-bold text-zinc-100">Dataset Studio</span>
            </div>

            <div className="mb-8">
              <h2 className="text-2xl font-bold text-zinc-100 tracking-[-0.02em]">Welcome back</h2>
              <p className="text-sm text-zinc-500 mt-2">Sign in to your account to continue</p>
            </div>

            <form onSubmit={handleLogin} className="space-y-5">
              {/* Email field */}
              <div className="space-y-2">
                <label className="block text-[11px] font-semibold text-zinc-500 tracking-[0.08em] uppercase">
                  Email
                </label>
                <div className={`relative rounded-xl transition-all duration-300 ${focused === "email" ? "ring-1 ring-primary/30" : ""}`}>
                  <input
                    type="email"
                    placeholder="you@example.com"
                    className="glass-input w-full"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onFocus={() => setFocused("email")}
                    onBlur={() => setFocused(null)}
                    required
                  />
                </div>
              </div>

              {/* Password field */}
              <div className="space-y-2">
                <label className="block text-[11px] font-semibold text-zinc-500 tracking-[0.08em] uppercase">
                  Password
                </label>
                <div className={`relative rounded-xl transition-all duration-300 ${focused === "password" ? "ring-1 ring-primary/30" : ""}`}>
                  <input
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    className="glass-input w-full pr-11"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => setFocused("password")}
                    onBlur={() => setFocused(null)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors duration-200"
                  >
                    {showPassword ? (
                      <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                      </svg>
                    ) : (
                      <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Error */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -8, height: 0 }}
                    animate={{ opacity: 1, y: 0, height: "auto" }}
                    exit={{ opacity: 0, y: -8, height: 0 }}
                    className="text-sm text-red-400 bg-red-500/[0.08] border border-red-500/20 rounded-xl px-4 py-3 flex items-center gap-2"
                  >
                    <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                    </svg>
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2.5 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <svg className="w-4 h-4 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                    </svg>
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="mt-8 flex items-center gap-4">
              <div className="flex-1 h-px bg-gradient-to-r from-transparent to-white/[0.06]" />
              <span className="text-[11px] text-zinc-600 uppercase tracking-widest">or</span>
              <div className="flex-1 h-px bg-gradient-to-l from-transparent to-white/[0.06]" />
            </div>

            <div className="mt-6 text-center">
              <p className="text-sm text-zinc-500">
                Don't have an account?{" "}
                <Link
                  to="/register"
                  className="text-primary-400 hover:text-primary-300 font-medium transition-colors duration-200"
                >
                  Create one
                </Link>
              </p>
            </div>
          </div>

          {/* Bottom glow */}
          <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 w-3/4 h-16 bg-primary/[0.06] blur-[40px] rounded-full pointer-events-none" />
        </motion.div>
      </div>
    </div>
  );
}
