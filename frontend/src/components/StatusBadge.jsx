import React from "react";
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck, ShieldAlert, AlertCircle, MinusCircle } from "lucide-react";

export default function StatusBadge({ status, type = "status", size = "sm" }) {
  const norm = String(status || "").toLowerCase().trim();

  const isLg = size === "lg";
  const baseClasses = isLg
    ? "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold tracking-tight shadow-xs transition"
    : "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-medium tracking-tight shadow-2xs transition";

  if (norm === "compliant" || norm === "pass") {
    return (
      <span className={`${baseClasses} bg-emerald-500/10 text-emerald-800 border border-emerald-500/25`}>
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-600"></span>
        </span>
        {type === "verdict" ? (
          <ShieldCheck className={isLg ? "w-4 h-4 text-emerald-700" : "w-3 h-3 text-emerald-700"} />
        ) : (
          <CheckCircle2 className={isLg ? "w-3.5 h-3.5 text-emerald-700" : "w-3 h-3 text-emerald-700"} />
        )}
        <span className="font-semibold">{status || "Compliant"}</span>
      </span>
    );
  }

  if (norm === "non-compliant" || norm === "fail") {
    return (
      <span className={`${baseClasses} bg-rose-500/10 text-rose-800 border border-rose-500/25`}>
        <span className="h-1.5 w-1.5 rounded-full bg-rose-600"></span>
        {type === "verdict" ? (
          <ShieldAlert className={isLg ? "w-4 h-4 text-rose-700" : "w-3 h-3 text-rose-700"} />
        ) : (
          <XCircle className={isLg ? "w-3.5 h-3.5 text-rose-700" : "w-3 h-3 text-rose-700"} />
        )}
        <span className="font-semibold">{status || "Non-Compliant"}</span>
      </span>
    );
  }

  if (norm === "major") {
    return (
      <span className={`${baseClasses} bg-rose-500/15 text-rose-900 border border-rose-600/30 font-bold`}>
        <AlertTriangle className={isLg ? "w-3.5 h-3.5 text-rose-700" : "w-3 h-3 text-rose-700"} />
        <span>Major Violation</span>
      </span>
    );
  }

  if (norm === "minor") {
    return (
      <span className={`${baseClasses} bg-amber-500/10 text-amber-900 border border-amber-500/25`}>
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500"></span>
        <span>Minor Deviation</span>
      </span>
    );
  }

  if (norm === "found" || norm === "detected") {
    return (
      <span className={`${baseClasses} bg-blue-500/10 text-blue-800 border border-blue-500/20`}>
        <span className="h-1.5 w-1.5 rounded-full bg-blue-600"></span>
        <span>Verified</span>
      </span>
    );
  }

  if (norm === "low_confidence") {
    return (
      <span className={`${baseClasses} bg-amber-500/10 text-amber-800 border border-amber-500/30`}>
        <AlertCircle className={isLg ? "w-3.5 h-3.5 text-amber-600" : "w-3 h-3 text-amber-600"} />
        <span>Low Confidence</span>
      </span>
    );
  }

  if (norm === "uncertain") {
    return (
      <span className={`${baseClasses} bg-amber-500/10 text-amber-900 border border-amber-500/30 font-semibold`}>
        <AlertTriangle className={isLg ? "w-3.5 h-3.5 text-amber-600" : "w-3 h-3 text-amber-600"} />
        <span>Uncertain</span>
      </span>
    );
  }

  if (norm === "rejected" || norm === "quality_failed") {
    return (
      <span className={`${baseClasses} bg-rose-500/15 text-rose-900 border border-rose-500/30 font-semibold`}>
        <XCircle className={isLg ? "w-3.5 h-3.5 text-rose-700" : "w-3 h-3 text-rose-700"} />
        <span>Pre-OCR Rejected</span>
      </span>
    );
  }

  if (norm === "not_found" || norm === "missing") {
    return (
      <span className={`${baseClasses} bg-slate-100 text-slate-600 border border-slate-200/90`}>
        <MinusCircle className={isLg ? "w-3.5 h-3.5 text-slate-400" : "w-3 h-3 text-slate-400"} />
        <span>Missing Declaration</span>
      </span>
    );
  }

  return (
    <span className={`${baseClasses} bg-slate-100 text-slate-700 border border-slate-200`}>
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400"></span>
      <span>{status}</span>
    </span>
  );
}
