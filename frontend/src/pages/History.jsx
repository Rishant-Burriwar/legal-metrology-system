import React, { useEffect, useState } from "react";
import { Search, Filter, Download, ArrowUpRight, ArrowLeft } from "lucide-react";
import StatusBadge from "../components/StatusBadge";
import { inspectionApi } from "../api/client";

export default function History({ onSelectInspection, onBack }) {
  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");

  const fetchInspections = async () => {
    setLoading(true);
    try {
      const filter = statusFilter === "all" ? null : statusFilter;
      const data = await inspectionApi.list(0, 50, filter);
      setInspections(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInspections();
  }, [statusFilter]);

  const filtered = inspections.filter((insp) => {
    const matchSearch =
      insp.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      insp.brand.toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(insp.id).includes(searchTerm);
    return matchSearch;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <button
            onClick={onBack}
            className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 transition mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1" />
            Back to Dashboard
          </button>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Inspection History
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit trail of all verified packaged commodities
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search product or brand..."
              className="pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none w-52"
            />
          </div>

          <div className="flex items-center space-x-1 border border-slate-300 bg-white rounded-lg p-0.5 text-xs font-medium">
            <button
              onClick={() => setStatusFilter("all")}
              className={`px-2.5 py-1 rounded-md ${
                statusFilter === "all" ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setStatusFilter("Compliant")}
              className={`px-2.5 py-1 rounded-md ${
                statusFilter === "Compliant" ? "bg-emerald-600 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              Compliant
            </button>
            <button
              onClick={() => setStatusFilter("Non-Compliant")}
              className={`px-2.5 py-1 rounded-md ${
                statusFilter === "Non-Compliant" ? "bg-rose-600 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              Non-Compliant
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
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
                <th className="py-3 px-4 text-left">Date</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    Loading inspections...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    No matching inspections found.
                  </td>
                </tr>
              ) : (
                filtered.map((insp) => (
                  <tr
                    key={insp.id}
                    className="hover:bg-slate-50/60 transition"
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
                    <td className="py-3 px-4 text-right space-x-2">
                      <button
                        onClick={() => onSelectInspection(insp.id)}
                        className="text-blue-600 hover:text-blue-800 font-semibold"
                      >
                        View
                      </button>
                      <a
                        href={inspectionApi.getPdfUrl(insp.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-slate-500 hover:text-slate-800"
                        title="Download PDF"
                      >
                        <Download className="w-3.5 h-3.5 inline ml-1" />
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
