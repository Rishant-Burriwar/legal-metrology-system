import React, { useEffect, useState } from "react";
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  FileText, 
  ArrowUpRight, 
  PlusCircle, 
  RefreshCw, 
  TrendingUp, 
  BarChart3,
  Layers,
  Users,
  Eye,
  Download,
  Filter,
  ShieldCheck,
  Calendar,
  Check
} from "lucide-react";
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  BarChart, 
  Bar, 
  Cell
} from "recharts";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";
import { dashboardApi, inspectionApi } from "../api/client";

export default function Dashboard({ user, onSelectInspection, onNewInspection }) {
  const [stats, setStats] = useState(null);
  const [recentList, setRecentList] = useState([]);
  const [inspectorsList, setInspectorsList] = useState([]);
  const [selectedInspectorId, setSelectedInspectorId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async (inspectorId = selectedInspectorId) => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, listData] = await Promise.all([
        dashboardApi.getStats(inspectorId),
        inspectionApi.list(0, 10, null, inspectorId),
      ]);
      setStats(statsData);
      setRecentList(listData);

      if (user?.role === "admin" && inspectorsList.length === 0) {
        try {
          const team = await inspectionApi.getInspectors();
          setInspectorsList(team);
        } catch (e) {
          console.error("Failed to load inspectors list:", e);
        }
      }
    } catch (err) {
      setError("Failed to load dashboard data. Check backend connectivity.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(selectedInspectorId);
  }, [selectedInspectorId]);

  const handleInspectorSelect = (id) => {
    setSelectedInspectorId((prev) => (prev === id ? null : id));
  };

  const violationChartData = stats?.violations_by_type?.map((v) => ({
    name: v.rule_code,
    rule: v.description,
    fails: v.fail_count,
    passes: v.pass_count,
  })) || [];

  const isViewer = user?.role === "viewer";
  const isAdmin = user?.role === "admin";
  const isInspector = user?.role === "inspector";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Role-Specific Banner for Viewer */}
      {isViewer && (
        <div className="p-4 rounded-2xl bg-amber-50/90 border border-amber-200 flex items-start space-x-3 text-amber-900 shadow-sm">
          <div className="p-2 bg-amber-100 rounded-xl text-amber-700 shrink-0 mt-0.5">
            <Eye className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-sm text-amber-950">
                Public Verification Portal (Read-Only Mode)
              </span>
              <span className="bg-amber-200/80 text-amber-900 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">
                Certificate Registry
              </span>
            </div>
            <p className="text-xs text-amber-800 mt-1 leading-relaxed">
              You are logged in as a <strong>Public Viewer</strong>. You have full access to inspect statutory compliance histories, view Rule LM-01–LM-07 evaluations, and download verified PDF certificates. Creating new product inspections is restricted to enforcement officers.
            </p>
          </div>
        </div>
      )}

      {/* Header & Role Context */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              {isAdmin && "Admin Command Center • Legal Metrology Directorate"}
              {isInspector && `Inspector Workspace • ${user?.name || "Officer"}`}
              {isViewer && "Legal Metrology Compliance Overview"}
            </h1>
            {isAdmin && (
              <span className="bg-purple-100 text-purple-800 border border-purple-200 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                Full Oversight
              </span>
            )}
            {isInspector && (
              <span className="bg-blue-100 text-blue-800 border border-blue-200 text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                Personal Audits
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            {isAdmin && "Department-wide enforcement analytics, inspector team performance & product audit execution"}
            {isInspector && "Track your assigned packaged commodity audits, compliance rates, and statutory rule records"}
            {isViewer && "Real-time compliance analytics under Legal Metrology (Packaged Commodities) Rules, 2011"}
          </p>
        </div>

        {/* Controls & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Admin Inspector Filter Dropdown */}
          {isAdmin && (
            <div className="flex items-center space-x-2 bg-white border border-slate-200 rounded-xl px-3 py-1.5 shadow-sm text-xs">
              <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="font-semibold text-slate-500 whitespace-nowrap">Filter by Inspector:</span>
              <select
                value={selectedInspectorId || "all"}
                onChange={(e) => {
                  const val = e.target.value === "all" ? null : Number(e.target.value);
                  setSelectedInspectorId(val);
                }}
                className="bg-transparent font-bold text-slate-800 outline-none cursor-pointer text-xs"
              >
                <option value="all">All Inspectors (Global Department)</option>
                {inspectorsList.map((insp) => (
                  <option key={insp.id} value={insp.id}>
                    {insp.name} ({insp.role})
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={() => fetchData(selectedInspectorId)}
            title="Refresh Data"
            className="p-2 border border-slate-200 rounded-xl bg-white text-slate-600 hover:bg-slate-50 transition shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-600" : ""}`} />
          </button>

          {/* New Inspection Button: Visible for Inspector and Admin, Hidden for Viewer */}
          {!isViewer && (
            <button
              onClick={onNewInspection}
              className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs sm:text-sm font-bold rounded-xl shadow-md shadow-blue-500/20 transition"
            >
              <PlusCircle className="w-4 h-4 mr-1.5" />
              New Inspection
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
          {error}
        </div>
      )}

      {/* Filter Active Alert for Admin */}
      {isAdmin && selectedInspectorId && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-between text-xs text-blue-800">
          <div className="flex items-center space-x-2">
            <span className="font-bold">Filtered View Active:</span>
            <span>
              Showing metrics for <strong>{stats?.inspector_name || `Inspector #${selectedInspectorId}`}</strong>
            </span>
          </div>
          <button
            onClick={() => setSelectedInspectorId(null)}
            className="font-bold text-blue-700 hover:text-blue-900 underline ml-3 cursor-pointer"
          >
            Reset to Department-wide
          </button>
        </div>
      )}

      {/* 4 Key Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title={isInspector ? "My Audited Labels" : "Total Inspections"}
          value={stats?.total_inspections ?? 0}
          subtitle={isInspector ? "Conducted by you" : "Packaged commodities audited"}
          icon={Layers}
          color="blue"
        />
        <StatCard
          title="Compliant Labels"
          value={stats?.compliant_count ?? 0}
          subtitle="Satisfied mandatory declarations"
          icon={CheckCircle}
          color="emerald"
        />
        <StatCard
          title="Non-Compliant Labels"
          value={stats?.non_compliant_count ?? 0}
          subtitle="Statutory violations flagged"
          icon={XCircle}
          color="rose"
        />
        <StatCard
          title="Compliance Rate"
          value={`${stats?.compliance_rate ?? 0}%`}
          subtitle={isInspector ? "Your audit pass rate" : "Department pass percentage"}
          icon={TrendingUp}
          color="purple"
        />
      </div>

      {/* Admin Inspector Team Progress Tracker Section */}
      {isAdmin && stats?.inspectors_progress && stats.inspectors_progress.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-purple-100 text-purple-700 rounded-xl">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-800">
                  Inspector Team Progress & Performance Monitor
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Real-time activity, audit volume, and compliance scores across all field officers
                </p>
              </div>
            </div>
            <span className="text-[11px] font-semibold bg-slate-100 text-slate-600 px-2.5 py-1 rounded-lg">
              {stats.inspectors_progress.length} Officers Registered
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50 text-slate-600 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-4 text-left">Inspector</th>
                  <th className="py-3 px-4 text-left">Role</th>
                  <th className="py-3 px-4 text-center">Total Audited</th>
                  <th className="py-3 px-4 text-center">Compliant</th>
                  <th className="py-3 px-4 text-center">Non-Compliant</th>
                  <th className="py-3 px-4 text-left">Compliance Rate</th>
                  <th className="py-3 px-4 text-center">Avg Score</th>
                  <th className="py-3 px-4 text-left">Last Active</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {stats.inspectors_progress.map((officer) => {
                  const isSelected = selectedInspectorId === officer.id;
                  return (
                    <tr
                      key={officer.id}
                      className={`hover:bg-purple-50/40 transition ${
                        isSelected ? "bg-purple-50/70 font-semibold" : ""
                      }`}
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2.5">
                          <div className="w-7 h-7 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-xs uppercase shadow-sm">
                            {officer.name.charAt(0)}
                          </div>
                          <div>
                            <div className="font-semibold text-slate-900">{officer.name}</div>
                            <div className="text-[11px] text-slate-400 font-mono">{officer.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                            officer.role === "admin"
                              ? "bg-purple-100 text-purple-700 border border-purple-200"
                              : "bg-blue-100 text-blue-700 border border-blue-200"
                          }`}
                        >
                          {officer.role}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center font-bold text-slate-800 text-sm">
                        {officer.total_inspections}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {officer.compliant_count}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                          {officer.non_compliant_count}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="w-32">
                          <div className="flex items-center justify-between text-[11px] mb-1">
                            <span className="font-bold text-slate-700">{officer.compliance_rate}%</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-emerald-500 h-1.5 rounded-full transition-all"
                              style={{ width: `${Math.min(100, officer.compliance_rate)}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center font-bold text-slate-700">
                        {officer.avg_score}%
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {officer.last_inspection_at
                          ? new Date(officer.last_inspection_at).toLocaleDateString(undefined, {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "No audits yet"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleInspectorSelect(officer.id)}
                          className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                            isSelected
                              ? "bg-purple-600 text-white shadow-sm"
                              : "bg-slate-100 text-slate-700 hover:bg-purple-100 hover:text-purple-800"
                          }`}
                        >
                          {isSelected ? "Active Filter" : "Focus Audits"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Visualizations Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Compliance Trend Line Chart */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Compliance Score Trend
              </h2>
              <p className="text-[11px] text-slate-400">Score (%) across verified product packages</p>
            </div>
            <span className="text-[10px] bg-slate-100 px-2 py-0.5 rounded font-semibold text-slate-600">
              Recent Inspections
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats?.recent_trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="label" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" domain={[0, 100]} fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "none",
                    borderRadius: "8px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                  formatter={(val, name, item) => [`${val}% Score`, item.payload.product]}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#2563eb"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: "#2563eb" }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Violations by Rule Bar Chart */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Rule Violations Distribution
              </h2>
              <p className="text-[11px] text-slate-400">Fail counts across mandatory declarations (LM-01 to LM-07)</p>
            </div>
            <span className="text-[10px] bg-rose-50 text-rose-700 px-2 py-0.5 rounded font-semibold border border-rose-200">
              Violations
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={violationChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "none",
                    borderRadius: "8px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                  formatter={(val, name, item) => [`${val} Failures`, item.payload.rule]}
                />
                <Bar dataKey="fails" fill="#ef4444" radius={[4, 4, 0, 0]}>
                  {violationChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fails > 0 ? "#ef4444" : "#cbd5e1"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Inspections Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-800">
              {isInspector ? "My Recent Label Inspections" : "Recent Label Inspections"}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Click any row to open statutory compliance report or download official PDF
            </p>
          </div>
          {isViewer && (
            <span className="text-[11px] text-slate-500 font-medium bg-slate-100 px-3 py-1 rounded-lg">
              Official Certificates Available for Download
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-600 uppercase font-semibold">
              <tr>
                <th className="py-3 px-4 text-left">ID</th>
                <th className="py-3 px-4 text-left">Product Name</th>
                <th className="py-3 px-4 text-left">Brand</th>
                <th className="py-3 px-4 text-left">Compliance Score</th>
                <th className="py-3 px-4 text-left">Status</th>
                <th className="py-3 px-4 text-left">Inspector</th>
                <th className="py-3 px-4 text-left">Inspection Date</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {recentList.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    No inspections recorded yet. {!isViewer && "Click \"New Inspection\" to start."}
                  </td>
                </tr>
              ) : (
                recentList.map((insp) => (
                  <tr
                    key={insp.id}
                    onClick={() => onSelectInspection(insp.id)}
                    className="hover:bg-blue-50/40 cursor-pointer transition"
                  >
                    <td className="py-3 px-4 font-mono font-bold text-slate-700">#{insp.id}</td>
                    <td className="py-3 px-4 font-semibold text-slate-900">{insp.product_name}</td>
                    <td className="py-3 px-4 text-slate-600">{insp.brand}</td>
                    <td className="py-3 px-4 font-bold text-slate-800">{Math.round(insp.compliance_score)}%</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={insp.overall_status} size="sm" />
                    </td>
                    <td className="py-3 px-4 text-slate-500">{insp.inspector_name}</td>
                    <td className="py-3 px-4 text-slate-500">
                      {new Date(insp.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right space-x-2" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => onSelectInspection(insp.id)}
                        className="inline-flex items-center text-blue-600 font-semibold hover:underline"
                      >
                        Report <ArrowUpRight className="w-3.5 h-3.5 ml-0.5" />
                      </button>
                      <a
                        href={inspectionApi.getPdfUrl(insp.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center p-1 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 rounded transition"
                        title="Download PDF Report"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
