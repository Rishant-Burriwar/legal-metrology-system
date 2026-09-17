import React, { useState, useEffect } from "react";
import Navbar from "./components/Navbar";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Report from "./pages/Report";
import History from "./pages/History";
import { inspectionApi } from "./api/client";
import { RefreshCw } from "lucide-react";

export default function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [currentInspection, setCurrentInspection] = useState(null);
  const [loadingInspection, setLoadingInspection] = useState(false);

  useEffect(() => {
    const savedUser = localStorage.getItem("lm_user");
    const token = localStorage.getItem("lm_token");
    if (savedUser && token) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.removeItem("lm_user");
        localStorage.removeItem("lm_token");
      }
    }

    const handleForceLogout = () => {
      setUser(null);
      setCurrentInspection(null);
      setActiveTab("dashboard");
    };

    window.addEventListener("lm:logout", handleForceLogout);
    return () => window.removeEventListener("lm:logout", handleForceLogout);
  }, []);

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setActiveTab("dashboard");
  };

  const handleLogout = () => {
    localStorage.removeItem("lm_token");
    localStorage.removeItem("lm_user");
    setUser(null);
    setCurrentInspection(null);
    setActiveTab("dashboard");
  };

  const handleSelectInspection = async (inspectionId) => {
    setLoadingInspection(true);
    try {
      const data = await inspectionApi.getById(inspectionId);
      setCurrentInspection(data);
      setActiveTab("report");
    } catch (err) {
      console.error("Failed to load inspection details:", err);
    } finally {
      setLoadingInspection(false);
    }
  };

  const handleInspectionComplete = (inspectionData) => {
    setCurrentInspection(inspectionData);
    setActiveTab("report");
  };

  if (!user) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900 bg-security-grid">
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          if (tab !== "report") {
            setCurrentInspection(null);
          }
        }}
        user={user}
        onLogout={handleLogout}
      />

      <main className="flex-1">
        {loadingInspection && (
          <div className="flex flex-col justify-center items-center py-28 space-y-3">
            <div className="p-3 bg-white rounded-2xl shadow-card border border-slate-200 flex items-center justify-center">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
            </div>
            <p className="text-xs font-semibold text-slate-500 font-mono">Loading statutory record details...</p>
          </div>
        )}

        {!loadingInspection && activeTab === "dashboard" && (
          <Dashboard
            user={user}
            onSelectInspection={handleSelectInspection}
            onNewInspection={() => setActiveTab("upload")}
          />
        )}

        {!loadingInspection && activeTab === "upload" && (
          <Upload
            user={user}
            onInspectionComplete={handleInspectionComplete}
            onCancel={() => setActiveTab("dashboard")}
          />
        )}

        {!loadingInspection && activeTab === "report" && (
          <Report
            user={user}
            inspection={currentInspection}
            onBack={() => setActiveTab("dashboard")}
            onNewInspection={() => {
              setCurrentInspection(null);
              setActiveTab("upload");
            }}
          />
        )}

        {!loadingInspection && activeTab === "history" && (
          <History
            user={user}
            onSelectInspection={handleSelectInspection}
            onBack={() => setActiveTab("dashboard")}
          />
        )}
      </main>

      {/* Official Government Footer */}
      <footer className="border-t border-slate-200/90 bg-white py-6 text-slate-500 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2">
            <div className="w-5 h-5 rounded bg-blue-600 text-white flex items-center justify-center font-bold text-[10px]">
              LM
            </div>
            <span className="font-semibold text-slate-700">
              Directorate of Legal Metrology, Department of Consumer Affairs, Government of India
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-mono text-center sm:text-right">
            Enforcing Legal Metrology (Packaged Commodities) Rules, 2011 • Official National Portal
          </p>
        </div>
      </footer>
    </div>
  );
}
