import React from "react";
import { Scale, LogOut, PlusCircle, LayoutDashboard, History, User } from "lucide-react";

export default function Navbar({ activeTab, setActiveTab, user, onLogout }) {
  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-40 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Title */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab("dashboard")}>
            <div className="bg-blue-600 p-2 rounded-lg text-white shadow-md shadow-blue-500/30">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base sm:text-lg tracking-tight text-white">LegalMetrology</span>
                <span className="bg-blue-500/20 text-blue-300 text-[10px] font-semibold px-2 py-0.5 rounded border border-blue-400/30 uppercase tracking-wider">
                  Rules, 2011
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">Automated Packaged Commodities Verification</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            <button
              onClick={() => setActiveTab("dashboard")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition ${
                activeTab === "dashboard"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </button>

            {/* New Inspection: Allowed for Inspector and Admin, Hidden for Viewer */}
            {user?.role !== "viewer" && (
              <button
                onClick={() => setActiveTab("upload")}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition ${
                  activeTab === "upload"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-slate-800"
                }`}
              >
                <PlusCircle className="w-4 h-4" />
                <span>New Inspection</span>
              </button>
            )}

            <button
              onClick={() => setActiveTab("history")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition ${
                activeTab === "history"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
            >
              <History className="w-4 h-4" />
              <span>History</span>
            </button>
          </nav>

          {/* User Profile & Logout */}
          <div className="flex items-center space-x-3">
            {user && (
              <div className="hidden md:flex items-center space-x-2 border-l border-slate-700/80 pl-3">
                <div className="text-right">
                  <div className="text-xs font-medium text-slate-200">{user.name}</div>
                  {user.role === "admin" && (
                    <span className="inline-block text-[10px] bg-purple-500/20 text-purple-300 border border-purple-400/30 px-2 py-0.2 rounded uppercase font-bold tracking-wider">
                      Admin Supervisor
                    </span>
                  )}
                  {user.role === "inspector" && (
                    <span className="inline-block text-[10px] bg-blue-500/20 text-blue-300 border border-blue-400/30 px-2 py-0.2 rounded uppercase font-bold tracking-wider">
                      Inspector
                    </span>
                  )}
                  {user.role === "viewer" && (
                    <span className="inline-block text-[10px] bg-amber-500/20 text-amber-300 border border-amber-400/30 px-2 py-0.2 rounded uppercase font-bold tracking-wider">
                      Viewer (Read-Only)
                    </span>
                  )}
                </div>
              </div>
            )}
            <button
              onClick={onLogout}
              title="Sign Out"
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
