import React from "react";
import { CheckCircle, XCircle, AlertTriangle, ShieldCheck, ShieldAlert } from "lucide-react";

export default function StatusBadge({ status, type = "status", size = "sm" }) {
  const norm = String(status || "").toLowerCase().trim();

  const sizeClasses = size === "lg" 
    ? "px-3.5 py-1.5 text-sm font-semibold gap-1.5" 
    : "px-2.5 py-1 text-xs font-medium gap-1";

  if (norm === "compliant" || norm === "pass") {
    return (
      <span className={`inline-flex items-center rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 ${sizeClasses}`}>
        {type === "verdict" ? <ShieldCheck className="w-4 h-4 text-emerald-600" /> : <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />}
        {status}
      </span>
    );
  }

  if (norm === "non-compliant" || norm === "fail") {
    return (
      <span className={`inline-flex items-center rounded-full bg-rose-50 text-rose-700 border border-rose-200 ${sizeClasses}`}>
        {type === "verdict" ? <ShieldAlert className="w-4 h-4 text-rose-600" /> : <XCircle className="w-3.5 h-3.5 text-rose-600" />}
        {status}
      </span>
    );
  }

  if (norm === "major") {
    return (
      <span className={`inline-flex items-center rounded-full bg-red-100 text-red-800 border border-red-300 font-semibold ${sizeClasses}`}>
        <AlertTriangle className="w-3 h-3 text-red-600" />
        Major
      </span>
    );
  }

  if (norm === "minor") {
    return (
      <span className={`inline-flex items-center rounded-full bg-amber-50 text-amber-800 border border-amber-200 ${sizeClasses}`}>
        Minor
      </span>
    );
  }

  if (norm === "found") {
    return (
      <span className={`inline-flex items-center rounded-full bg-blue-50 text-blue-700 border border-blue-200 ${sizeClasses}`}>
        Detected
      </span>
    );
  }

  if (norm === "low_confidence") {
    return (
      <span className={`inline-flex items-center rounded-full bg-amber-50 text-amber-700 border border-amber-200 ${sizeClasses}`}>
        Low Confidence
      </span>
    );
  }

  if (norm === "uncertain") {
    return (
      <span className={`inline-flex items-center rounded-full bg-orange-50 text-orange-700 border border-orange-200 font-semibold ${sizeClasses}`}>
        <AlertTriangle className="w-3 h-3 text-orange-600" />
        Uncertain
      </span>
    );
  }

  if (norm === "rejected" || norm === "quality_failed") {
    return (
      <span className={`inline-flex items-center rounded-full bg-rose-100 text-rose-800 border border-rose-300 font-semibold ${sizeClasses}`}>
        <XCircle className="w-3.5 h-3.5 text-rose-600" />
        Pre-OCR Rejected
      </span>
    );
  }

  if (norm === "not_found") {
    return (
      <span className={`inline-flex items-center rounded-full bg-slate-100 text-slate-600 border border-slate-200 ${sizeClasses}`}>
        Missing
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center rounded-full bg-slate-100 text-slate-700 border border-slate-200 ${sizeClasses}`}>
      {status}
    </span>
  );
}
