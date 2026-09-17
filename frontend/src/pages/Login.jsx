import React, { useState } from "react";
import { 
  Scale, 
  Lock, 
  Mail, 
  ArrowRight, 
  AlertCircle, 
  ShieldCheck, 
  FileCheck2, 
  Cpu, 
  Award
} from "lucide-react";
import { authApi } from "../api/client";

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!email || !password) {
      setError("Please provide both official email and password.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const data = await authApi.login(email, password);
      localStorage.setItem("lm_token", data.access_token);
      localStorage.setItem("lm_user", JSON.stringify(data.user));
      onLoginSuccess(data.user);
    } catch (err) {
      setError(err.response?.data?.detail || "Authentication failed. Please verify credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await authApi.login(demoEmail, demoPassword);
        localStorage.setItem("lm_token", data.access_token);
        localStorage.setItem("lm_user", JSON.stringify(data.user));
        onLoginSuccess(data.user);
      } catch (err) {
        setError(err.response?.data?.detail || "Quick login failed.");
      } finally {
        setLoading(false);
      }
    }, 100);
  };

  const demoAccounts = [
    {
      name: "Inspector Sharma",
      role: "Field Enforcement Officer",
      email: "inspector@gov.in",
      pass: "inspector123",
      clearance: "Officer Grade I",
      badgeColor: "bg-blue-500/10 text-blue-700 border-blue-500/30",
    },
    {
      name: "Inspector Priya",
      role: "District Inspection Officer",
      email: "inspector2@gov.in",
      pass: "inspector123",
      clearance: "Officer Grade II",
      badgeColor: "bg-blue-500/10 text-blue-700 border-blue-500/30",
    },
    {
      name: "Admin Controller",
      role: "Directorate Supervisor",
      email: "admin@gov.in",
      pass: "admin123",
      clearance: "Full Directorate Oversight",
      badgeColor: "bg-purple-500/10 text-purple-700 border-purple-500/30",
    },
    {
      name: "Public Citizen Viewer",
      role: "Consumer Registry",
      email: "viewer@gov.in",
      pass: "viewer123",
      clearance: "Read-Only Certified Reports",
      badgeColor: "bg-amber-500/10 text-amber-800 border-amber-500/30",
    },
  ];

  return (
    <div className="min-h-screen bg-navy-950 text-slate-100 flex flex-col justify-between selection:bg-blue-600 selection:text-white relative overflow-hidden bg-security-grid-dark">
      {/* Decorative background glow accents */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Governmental Masthead */}
      <header className="border-b border-navy-800/80 bg-navy-900/60 backdrop-blur-sm px-4 sm:px-8 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
              <Scale className="w-4 h-4" />
            </div>
            <div>
              <span className="font-display font-bold text-sm tracking-tight text-white block">
                Directorate of Legal Metrology
              </span>
              <span className="text-[10px] text-slate-400 block -mt-0.5">
                Department of Consumer Affairs, Government of India
              </span>
            </div>
          </div>
          <div className="hidden sm:flex items-center space-x-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-subtle-pulse"></span>
            <span className="text-xs text-slate-300 font-mono">Enforcement Engine Online</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 sm:py-16 flex items-center">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 items-center w-full">
          
          {/* Left Column: Directorate Mandate & Statutory Context */}
          <div className="lg:col-span-7 space-y-8">
            <div className="space-y-3">
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-400/20 text-blue-300 text-xs font-semibold">
                <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
                <span>Statutory Compliance Inspection System</span>
              </div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-display font-extrabold text-white tracking-tight leading-[1.15]">
                Automated Verification for Packaged Commodities
              </h1>
              <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-2xl font-normal">
                National enforcement architecture verifying mandatory label declarations pursuant to the 
                <strong className="text-white font-semibold"> Legal Metrology (Packaged Commodities) Rules, 2011 </strong>
                under the Legal Metrology Act, 2009.
              </p>
            </div>

            {/* Core Verification Pillars */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
              <div className="p-4 rounded-xl bg-navy-900/70 border border-navy-800/80 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-blue-500/15 flex items-center justify-center text-blue-400">
                  <FileCheck2 className="w-4 h-4" />
                </div>
                <h2 className="text-xs font-bold text-white uppercase tracking-wider">
                  Rule 6 Declarations
                </h2>
                <p className="text-xs text-slate-400 leading-normal">
                  Strict audit of MRP, Net Quantity, Mfg Date, Packer Address, and Consumer Care details.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-navy-900/70 border border-navy-800/80 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center text-emerald-400">
                  <Award className="w-4 h-4" />
                </div>
                <h2 className="text-xs font-bold text-white uppercase tracking-wider">
                  FSSAI & Standards
                </h2>
                <p className="text-xs text-slate-400 leading-normal">
                  Statutory 14-digit FSSAI license validation on food packages with country of origin verification.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-navy-900/70 border border-navy-800/80 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-purple-500/15 flex items-center justify-center text-purple-400">
                  <Cpu className="w-4 h-4" />
                </div>
                <h2 className="text-xs font-bold text-white uppercase tracking-wider">
                  Multimodal CV Engine
                </h2>
                <p className="text-xs text-slate-400 leading-normal">
                  Adaptive pre-OCR quality gate, OpenCV deskewing, and Gemini Multimodal Vision AI.
                </p>
              </div>
            </div>

            {/* Regulatory Reference Notice */}
            <div className="p-4 rounded-xl bg-navy-900/40 border border-navy-800/60 flex items-start space-x-3 text-xs text-slate-400">
              <span className="font-mono text-blue-400 font-bold shrink-0">NOTICE:</span>
              <p>
                Authorized personnel only. All audit actions, certificate generations, and OCR typography extractions are cryptographically logged for statutory evidentiary compliance.
              </p>
            </div>
          </div>

          {/* Right Column: Secure Authentication Console */}
          <div className="lg:col-span-5">
            <div className="bg-white text-slate-900 rounded-2xl shadow-elevated border border-slate-200/90 p-6 sm:p-8">
              <div className="border-b border-slate-100 pb-5 mb-5">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-display font-bold text-slate-900 tracking-tight">
                    Officer Authentication
                  </h2>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                    SSL Encrypted
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Enter registered departmental credentials or use 1-click test passcards below.
                </p>
              </div>

              {error && (
                <div className="mb-5 p-3 rounded-xl bg-rose-50 border border-rose-200/90 flex items-start space-x-2.5 text-rose-700 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span className="font-medium leading-relaxed">{error}</span>
                </div>
              )}

              <form className="space-y-4" onSubmit={handleSubmit}>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Official Email ID
                  </label>
                  <div className="relative rounded-lg shadow-2xs">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Mail className="w-4 h-4" />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="officer@gov.in"
                      required
                      className="block w-full pl-9 pr-3 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Access Password
                  </label>
                  <div className="relative rounded-lg shadow-2xs">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Lock className="w-4 h-4" />
                    </div>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="block w-full pl-9 pr-3 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex justify-center items-center py-2.5 px-4 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.99] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 disabled:opacity-50 transition shadow-md shadow-blue-500/20"
                >
                  {loading ? "Authenticating Clearance..." : "Authenticate Session"}
                  {!loading && <ArrowRight className="ml-2 w-4 h-4" />}
                </button>
              </form>

              {/* 1-Click Evaluation Passcards */}
              <div className="mt-6 pt-5 border-t border-slate-100">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    1-Click Evaluation Passcards
                  </p>
                  <span className="text-[10px] text-slate-400">Instant Demo Login</span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  {demoAccounts.map((acc) => (
                    <button
                      key={acc.email}
                      type="button"
                      onClick={() => handleQuickLogin(acc.email, acc.pass)}
                      disabled={loading}
                      className="p-2.5 text-left rounded-xl bg-slate-50 hover:bg-blue-50/50 border border-slate-200/90 hover:border-blue-300 transition group flex flex-col justify-between"
                    >
                      <div>
                        <div className="text-xs font-bold text-slate-800 group-hover:text-blue-700 truncate">
                          {acc.name}
                        </div>
                        <div className="text-[10px] text-slate-500 truncate mt-0.5">
                          {acc.role}
                        </div>
                      </div>
                      <div className="mt-2 pt-1 border-t border-slate-200/60 flex items-center justify-between">
                        <span className="text-[9px] font-mono text-slate-400 truncate">
                          {acc.email}
                        </span>
                        <span className="text-[10px] text-blue-600 opacity-0 group-hover:opacity-100 transition">
                          →
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

            </div>
          </div>

        </div>
      </main>

      {/* Official Government Footer */}
      <footer className="border-t border-navy-800/80 bg-navy-900/80 py-4 px-4 sm:px-8 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>
            Directorate of Legal Metrology • Legal Metrology (Packaged Commodities) Rules, 2011
          </p>
          <p className="text-[11px] text-slate-500 font-mono">
            Security Tier 1 • Automated Statutory Verification Terminal
          </p>
        </div>
      </footer>
    </div>
  );
}
