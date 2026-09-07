import React, { useState, useEffect } from "react";
import Navbar from "./components/Navbar";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Report from "./pages/Report";
import History from "./pages/History";
import { inspectionApi } from "./api/client";

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
    <div className="min-h-screen bg-slate-50 flex flex-col">
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
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
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

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        <p>
          Directorate of Legal Metrology, Department of Consumer Affairs • Legal Metrology (Packaged Commodities) Rules, 2011 Compliance System
        </p>
      </footer>
    </div>
  );
}
