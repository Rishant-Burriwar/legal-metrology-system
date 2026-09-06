import React from "react";

export default function ScoreGauge({ score }) {
  const isCompliant = score >= 80;
  const strokeColor = isCompliant ? "#10b981" : "#f43f5e";
  const bgColor = isCompliant ? "#ecfdf5" : "#fff1f2";

  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative flex items-center justify-center">
        <svg className="w-36 h-36 transform -rotate-90" viewBox="0 0 140 140">
          <circle
            cx="70"
            cy="70"
            r={radius}
            className="text-slate-100"
            strokeWidth="12"
            stroke="currentColor"
            fill="transparent"
          />
          <circle
            cx="70"
            cy="70"
            r={radius}
            stroke={strokeColor}
            strokeWidth="12"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          <span className="text-3xl font-extrabold text-slate-800">{Math.round(score)}%</span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Score</span>
        </div>
      </div>
      <div className="mt-3 text-center">
        <span
          className={`inline-block px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
            isCompliant ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
          }`}
        >
          {isCompliant ? "Fully Compliant" : "Non-Compliant"}
        </span>
      </div>
    </div>
  );
}
