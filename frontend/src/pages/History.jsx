import React, { useEffect, useState } from "react";
import { Search, Filter, Download, ArrowUpRight, ArrowLeft, RefreshCw } from "lucide-react";
import StatusBadge from "../components/StatusBadge";
import { inspectionApi } from "../api/client";

export default function History({ user, onSelectInspection, onBack }) {
  const [inspections, setInspections] = useState([]);
  const [inspectorsList, setInspectorsList] = useState([]);
  const [selectedInspectorId, setSelectedInspectorId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");

  const fetchInspections = async () => {
    setLoading(true);
    try {
      const filter = statusFilter === "all" ? null : statusFilter;
      const data = await inspectionApi.list(0, 50, filter, selectedInspectorId);
      setInspections(data);

      if (user?.role === "admin" && inspectorsList.length === 0) {
        try {
          const team = await inspectionApi.getInspectors();
          setInspectorsList(team);
        } catch (e) {
          console.error("Failed to load inspectors list:", e);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInspections();
  }, [statusFilter, selectedInspectorId]);

  const filtered = inspections.filter((insp) => {
    const matchSearch =
      insp.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      insp.brand.toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(insp.id).includes(searchTerm);
    return matchSearch;
  });

  const isAdmin = user?.role === "admin";
  const isInspector = user?.role === "inspector";
  const isViewer = user?.role === "viewer";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/90 pb-5">
        <div>
          <button
            onClick={onBack}
            className="inline-flex items-center text-xs font-bold text-slate-500 hover:text-slate-800 transition mb-2 group"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1 group-hover:-translate-x-0.5 transition" />
            Back to Dashboard
          </button>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-display font-extrabold text-slate-900 tracking-tight">
              {isInspector && `My Statutory Audit Trail`}
              {isAdmin && `Department Inspection Registry`}
              {isViewer && `Public Compliance Audit Registry`}
            </h1>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
              Audit Logs
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {isInspector && `Chronological inspection record of packaged commodities audited by ${user?.name}`}
            {isAdmin && `Central department audit trail across all registered field officers`}
            {isViewer && `Certified registry of verified packaged commodities with official certificates`}
          </p>
        </div>

        {/* Filter Controls Toolbar */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Admin Inspector Filter */}
          {isAdmin && (
            <div className="flex items-center space-x-1.5 bg-white border border-slate-200/90 rounded-xl px-3 py-1.5 shadow-card text-xs">
              <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="text-slate-500 font-semibold">Officer:</span>
              <select
                value={selectedInspectorId || "all"}
                onChange={(e) => {
                  const val = e.target.value === "all" ? null : Number(e.target.value);
                  setSelectedInspectorId(val);
                }}
                className="bg-transparent font-bold text-slate-800 outline-none cursor-pointer text-xs"
              >
                <option value="all">All Officers</option>
                {inspectorsList.map((insp) => (
                  <option key={insp.id} value={insp.id}>
                    {insp.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Search Box */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search product, brand or #ID..."
              className="pl-9 pr-3 py-2 text-xs bg-white border border-slate-200/90 rounded-xl focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none w-56 shadow-card transition"
            />
          </div>

          {/* Status Segmented Control */}
          <div className="flex items-center space-x-1 border border-slate-200/90 bg-slate-100/90 rounded-xl p-1 text-xs font-semibold shadow-card">
            <button
              onClick={() => setStatusFilter("all")}
              className={`px-3 py-1 rounded-lg transition ${
                statusFilter === "all" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setStatusFilter("Compliant")}
              className={`px-3 py-1 rounded-lg transition ${
                statusFilter === "Compliant" ? "bg-emerald-600 text-white shadow-2xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Compliant
            </button>
            <button
              onClick={() => setStatusFilter("Non-Compliant")}
              className={`px-3 py-1 rounded-lg transition ${
                statusFilter === "Non-Compliant" ? "bg-rose-600 text-white shadow-2xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Non-Compliant
            </button>
          </div>

          <button
            onClick={() => fetchInspections()}
            title="Refresh Audit Records"
            className="p-2 border border-slate-200/90 rounded-xl bg-white text-slate-600 hover:bg-slate-50 transition shadow-card"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-600" : ""}`} />
          </button>
        </div>
      </div>

      {/* Audit Registry Table */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100 text-xs">
            <thead className="bg-slate-50/80 text-slate-500 uppercase font-semibold text-[11px]">
              <tr>
                <th className="py-3.5 px-4 text-left">Record ID</th>
                <th className="py-3.5 px-4 text-left">Commodity Description</th>
                <th className="py-3.5 px-4 text-left">Brand / Entity</th>
                <th className="py-3.5 px-4 text-left">Audit Score</th>
                <th className="py-3.5 px-4 text-left">Verdict</th>
                <th className="py-3.5 px-4 text-left">Auditing Officer</th>
                <th className="py-3.5 px-4 text-left">Audit Date</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <div className="flex items-center justify-center space-x-2">
                      <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                      <span>Loading statutory inspection records...</span>
                    </div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No matching statutory inspection records found.
                  </td>
                </tr>
              ) : (
                filtered.map((insp) => (
                  <tr
                    key={insp.id}
                    onClick={() => onSelectInspection(insp.id)}
                    className="hover:bg-blue-50/30 cursor-pointer transition"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-700">#{insp.id}</td>
                    <td className="py-3.5 px-4 font-semibold text-slate-900 text-sm">{insp.product_name}</td>
                    <td className="py-3.5 px-4 text-slate-600 font-medium">{insp.brand}</td>
                    <td className="py-3.5 px-4 font-bold text-slate-900 tabular-nums">{Math.round(insp.compliance_score)}%</td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={insp.overall_status} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 font-medium">{insp.inspector_name}</td>
                    <td className="py-3.5 px-4 text-slate-500 font-mono">
                      {new Date(insp.created_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => onSelectInspection(insp.id)}
                        className="inline-flex items-center text-blue-600 hover:text-blue-800 font-bold hover:underline"
                      >
                        Inspect <ArrowUpRight className="w-3.5 h-3.5 ml-0.5" />
                      </button>
                      <a
                        href={inspectionApi.getPdfUrl(insp.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg transition"
                        title="Download Statutory Certificate PDF"
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
