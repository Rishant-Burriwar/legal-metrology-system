import React, { useState } from "react";
import { Scale, Lock, Mail, Shield, ArrowRight, AlertCircle } from "lucide-react";
import { authApi } from "../api/client";

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!email || !password) {
      setError("Please provide both email and password.");
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
      setError(err.response?.data?.detail || "Authentication failed. Check credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    // Auto submit
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

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center p-3 bg-blue-600 rounded-2xl shadow-lg shadow-blue-500/30 text-white mb-4">
          <Scale className="w-8 h-8" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Legal Metrology Inspection System
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Enforcement Portal • Legal Metrology (Packaged Commodities) Rules, 2011
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-white py-8 px-6 shadow-2xl rounded-2xl border border-slate-100 sm:px-10">
          {error && (
            <div className="mb-5 p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-center space-x-2 text-rose-700 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Official Email
              </label>
              <div className="mt-1 relative rounded-lg shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="inspector@gov.in"
                  required
                  className="block w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Password
              </label>
              <div className="mt-1 relative rounded-lg shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="block w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center items-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition"
            >
              {loading ? "Authenticating..." : "Sign In to Portal"}
              {!loading && <ArrowRight className="ml-2 w-4 h-4" />}
            </button>
          </form>

          {/* Quick Demo Access Buttons for Evaluators */}
          <div className="mt-6 pt-6 border-t border-slate-200">
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider text-center mb-3">
              1-Click Demo Evaluation Accounts
            </p>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin("inspector@gov.in", "inspector123")}
                className="py-2 px-2 text-left bg-slate-50 hover:bg-blue-50 hover:border-blue-300 rounded-xl border border-slate-200 transition group"
              >
                <div className="text-[11px] font-bold text-slate-800 group-hover:text-blue-700">Inspector Sharma</div>
                <div className="text-[10px] text-slate-400 font-mono">Personal Dashboard</div>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("inspector2@gov.in", "inspector123")}
                className="py-2 px-2 text-left bg-slate-50 hover:bg-blue-50 hover:border-blue-300 rounded-xl border border-slate-200 transition group"
              >
                <div className="text-[11px] font-bold text-slate-800 group-hover:text-blue-700">Inspector Priya</div>
                <div className="text-[10px] text-slate-400 font-mono">2nd Field Officer</div>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("admin@gov.in", "admin123")}
                className="py-2 px-2 text-left bg-slate-50 hover:bg-purple-50 hover:border-purple-300 rounded-xl border border-slate-200 transition group"
              >
                <div className="text-[11px] font-bold text-slate-800 group-hover:text-purple-700">Admin Controller</div>
                <div className="text-[10px] text-slate-400 font-mono">Team Monitor + Audits</div>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("viewer@gov.in", "viewer123")}
                className="py-2 px-2 text-left bg-slate-50 hover:bg-amber-50 hover:border-amber-300 rounded-xl border border-slate-200 transition group"
              >
                <div className="text-[11px] font-bold text-slate-800 group-hover:text-amber-700">Public Viewer</div>
                <div className="text-[10px] text-slate-400 font-mono">Read-Only + PDF</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
