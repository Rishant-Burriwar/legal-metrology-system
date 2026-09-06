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
  Layers
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
  Cell, 
  PieChart, 
  Pie 
} from "recharts";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";
import { dashboardApi, inspectionApi } from "../api/client";

export default function Dashboard({ onSelectInspection, onNewInspection }) {
  const [stats, setStats] = useState(null);
  const [recentList, setRecentList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, listData] = await Promise.all([
        dashboardApi.getStats(),
        inspectionApi.list(0, 10),
      ]);
      setStats(statsData);
      setRecentList(listData);
    } catch (err) {
      setError("Failed to load dashboard data. Check backend connectivity.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4"];

  const violationChartData = stats?.violations_by_type?.map((v) => ({
    name: v.rule_code,
    rule: v.description,
    fails: v.fail_count,
    passes: v.pass_count,
  })) || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header & Quick Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Legal Metrology Compliance Overview
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Real-time enforcement analytics under Legal Metrology (Packaged Commodities) Rules, 2011
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={fetchData}
            title="Refresh Data"
            className="p-2 border border-slate-200 rounded-xl bg-white text-slate-600 hover:bg-slate-50 transition shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-600" : ""}`} />
          </button>
          <button
            onClick={onNewInspection}
            className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs sm:text-sm font-bold rounded-xl shadow-md shadow-blue-500/20 transition"
          >
            <PlusCircle className="w-4 h-4 mr-1.5" />
            New Inspection
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
          {error}
        </div>
      )}

      {/* 4 Key Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Inspections"
          value={stats?.total_inspections ?? 0}
          subtitle="Packaged commodities audited"
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
          subtitle="Statutory pass percentage"
          icon={TrendingUp}
          color="purple"
        />
      </div>

      {/* Recharts Visualizations Grid */}
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
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-800">
              Recent Label Inspections
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Click any row to open full statutory compliance report</p>
          </div>
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
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {recentList.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    No inspections recorded yet. Click "New Inspection" to start.
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
                    <td className="py-3 px-4 text-right">
                      <span className="inline-flex items-center text-blue-600 font-semibold hover:underline">
                        Report <ArrowUpRight className="w-3.5 h-3.5 ml-0.5" />
                      </span>
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
