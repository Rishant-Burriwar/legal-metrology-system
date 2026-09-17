import React from "react";
import { 
  Scale, 
  LogOut, 
  PlusCircle, 
  LayoutDashboard, 
  History, 
  FileText
} from "lucide-react";

export default function Navbar({ activeTab, setActiveTab, user, onLogout }) {
  const isViewer = user?.role === "viewer";
  const isAdmin = user?.role === "admin";
  const isInspector = user?.role === "inspector";

  return (
    <header className="sticky top-0 z-40 bg-navy-950 text-white border-b border-navy-800 shadow-md">
      {/* Top Official Government Banner Ribbon */}
      <div className="bg-navy-900/90 border-b border-navy-800/80 px-4 sm:px-6 lg:px-8 py-1">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-[11px] text-slate-300 font-medium">
          <div className="flex items-center space-x-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-subtle-pulse"></span>
            <span className="font-semibold text-slate-200">Directorate of Legal Metrology</span>
            <span className="hidden sm:inline text-slate-500">•</span>
            <span className="hidden sm:inline text-slate-400">Department of Consumer Affairs, Govt. of India</span>
          </div>
          <div className="flex items-center space-x-3 text-[11px]">
            <span className="hidden md:inline text-slate-400">Statutory Framework:</span>
            <span className="font-mono bg-navy-800 text-blue-300 px-2 py-0.5 rounded border border-navy-700 font-semibold">
              Rules, 2011 (Sec. 6)
            </span>
          </div>
        </div>
      </div>

      {/* Main Command Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Identity */}
          <div 
            className="flex items-center space-x-3 cursor-pointer select-none group" 
            onClick={() => setActiveTab("dashboard")}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-navy-800 p-0.5 shadow-md flex items-center justify-center border border-blue-400/30">
              <div className="w-full h-full bg-navy-950 rounded-[10px] flex items-center justify-center">
                <Scale className="w-5 h-5 text-blue-400 group-hover:text-blue-300 transition" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-display font-bold text-base sm:text-lg tracking-tight text-white">
                  LegalMetrology
                </span>
                <span className="text-[10px] font-mono uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-400/30">
                  PCR-2011
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block leading-none mt-0.5">
                Packaged Commodity Verification Terminal
              </p>
            </div>
          </div>

          {/* Navigation Controls */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            {isViewer ? (
              <button
                onClick={() => setActiveTab("dashboard")}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition ${
                  activeTab === "dashboard"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-navy-900"
                }`}
              >
                <FileText className="w-4 h-4 text-blue-300" />
                <span>Download Reports</span>
              </button>
            ) : (
              <>
                <button
                  onClick={() => setActiveTab("dashboard")}
                  className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition ${
                    activeTab === "dashboard"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-slate-300 hover:text-white hover:bg-navy-900"
                  }`}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  <span>Dashboard</span>
                </button>

                <button
                  onClick={() => setActiveTab("upload")}
                  className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition ${
                    activeTab === "upload"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-slate-300 hover:text-white hover:bg-navy-900"
                  }`}
                >
                  <PlusCircle className="w-4 h-4 text-emerald-400" />
                  <span>New Inspection</span>
                </button>

                <button
                  onClick={() => setActiveTab("history")}
                  className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition ${
                    activeTab === "history"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-slate-300 hover:text-white hover:bg-navy-900"
                  }`}
                >
                  <History className="w-4 h-4" />
                  <span>Audit Trail</span>
                </button>
              </>
            )}
          </nav>

          {/* User Status Badge & Logout */}
          <div className="flex items-center space-x-3">
            {user && (
              <div className="flex items-center space-x-2.5 border-l border-navy-800 pl-3 sm:pl-4">
                <div className="hidden sm:block text-right">
                  <div className="text-xs font-bold text-slate-200 tracking-tight leading-tight">
                    {user.name}
                  </div>
                  <div className="flex items-center justify-end space-x-1 mt-0.5">
                    {isAdmin && (
                      <span className="inline-flex items-center text-[10px] bg-purple-500/15 text-purple-300 border border-purple-400/30 px-2 py-0.2 rounded font-semibold tracking-wide uppercase">
                        Admin Controller
                      </span>
                    )}
                    {isInspector && (
                      <span className="inline-flex items-center text-[10px] bg-blue-500/15 text-blue-300 border border-blue-400/30 px-2 py-0.2 rounded font-semibold tracking-wide uppercase">
                        Field Inspector
                      </span>
                    )}
                    {isViewer && (
                      <span className="inline-flex items-center text-[10px] bg-amber-500/15 text-amber-300 border border-amber-400/30 px-2 py-0.2 rounded font-semibold tracking-wide uppercase">
                        Public Portal
                      </span>
                    )}
                  </div>
                </div>

                <button
                  onClick={onLogout}
                  title="Sign Out of Session"
                  className="p-2 text-slate-400 hover:text-rose-400 hover:bg-navy-900 rounded-lg transition border border-transparent hover:border-navy-700"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
