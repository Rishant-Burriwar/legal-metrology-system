import React from "react";
import { ShieldCheck, AlertOctagon } from "lucide-react";

export default function ScoreGauge({ score = 0 }) {
  const safeScore = Math.max(0, Math.min(100, Math.round(score)));
  const isCompliant = safeScore >= 80;

  const radius = 56;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (safeScore / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative flex items-center justify-center">
        {/* SVG Radial Meter */}
        <svg className="w-36 h-36 transform -rotate-90" viewBox="0 0 140 140">
          <defs>
            <linearGradient id="scoreCompliantGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#059669" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
            <linearGradient id="scoreViolationGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#e11d48" />
              <stop offset="100%" stopColor="#f43f5e" />
            </linearGradient>
          </defs>

          {/* Background Track */}
          <circle
            cx="70"
            cy="70"
            r={radius}
            stroke="#f1f5f9"
            strokeWidth={strokeWidth}
            fill="transparent"
          />

          {/* Subdued Tick Ring */}
          <circle
            cx="70"
            cy="70"
            r={radius + 7}
            stroke="#e2e8f0"
            strokeWidth="1.5"
            strokeDasharray="2 6"
            fill="transparent"
            className="opacity-60"
          />

          {/* Progress Stroke */}
          <circle
            cx="70"
            cy="70"
            r={radius}
            stroke={isCompliant ? "url(#scoreCompliantGrad)" : "url(#scoreViolationGrad)"}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Central Display */}
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className="text-3xl font-display font-extrabold text-slate-900 tracking-tight tabular-nums">
            {safeScore}%
          </span>
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 -mt-0.5">
            Audit Score
          </span>
        </div>
      </div>

      {/* Official Verdict Badge */}
      <div className="mt-3 text-center">
        {isCompliant ? (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-800 border border-emerald-500/25 shadow-2xs">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
            <span>Statutory Compliant</span>
          </div>
        ) : (
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-800 border border-rose-500/25 shadow-2xs">
            <AlertOctagon className="w-3.5 h-3.5 text-rose-700" />
            <span>Non-Compliant Label</span>
          </div>
        )}
      </div>
    </div>
  );
}
