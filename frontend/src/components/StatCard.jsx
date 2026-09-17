import React from "react";

export default function StatCard({ title, value, subtitle, icon: Icon, color = "blue" }) {
  const colorSchemes = {
    blue: {
      iconBg: "bg-blue-500/10 text-blue-700 border-blue-500/20",
      accentBar: "bg-blue-600",
      pill: "bg-blue-50 text-blue-700",
    },
    emerald: {
      iconBg: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
      accentBar: "bg-emerald-600",
      pill: "bg-emerald-50 text-emerald-700",
    },
    rose: {
      iconBg: "bg-rose-500/10 text-rose-700 border-rose-500/20",
      accentBar: "bg-rose-600",
      pill: "bg-rose-50 text-rose-700",
    },
    purple: {
      iconBg: "bg-purple-500/10 text-purple-700 border-purple-500/20",
      accentBar: "bg-purple-600",
      pill: "bg-purple-50 text-purple-700",
    },
  };

  const scheme = colorSchemes[color] || colorSchemes.blue;

  return (
    <div className="relative overflow-hidden bg-white rounded-xl p-5 border border-slate-200/85 shadow-card hover:shadow-card-hover transition-all duration-200 group">
      {/* Subtle top indicator accent line */}
      <div className={`absolute top-0 left-0 right-0 h-[2.5px] ${scheme.accentBar} opacity-80 group-hover:opacity-100 transition`} />

      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            {title}
          </p>
          <div className="flex items-baseline space-x-2">
            <h3 className="text-2xl sm:text-3xl font-display font-bold text-slate-900 tracking-tight tabular-nums">
              {value}
            </h3>
          </div>
          {subtitle && (
            <p className="text-xs text-slate-500 font-medium pt-0.5 leading-snug">
              {subtitle}
            </p>
          )}
        </div>

        {Icon && (
          <div className={`p-2.5 rounded-xl border ${scheme.iconBg} shrink-0 transition-transform duration-200 group-hover:scale-105`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
    </div>
  );
}
