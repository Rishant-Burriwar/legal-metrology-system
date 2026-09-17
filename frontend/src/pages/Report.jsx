import React, { useState } from "react";
import { 
  Download, 
  ArrowLeft, 
  AlertTriangle, 
  FileText, 
  Tag, 
  Layers,
  Sparkles,
  Gauge,
  Activity,
  Repeat,
  ZoomIn,
  ShieldCheck,
  Info,
  CheckCircle2,
  RotateCw,
  Film,
  Video,
  Eye,
  Beaker,
  BookOpen
} from "lucide-react";
import ScoreGauge from "../components/ScoreGauge";
import StatusBadge from "../components/StatusBadge";
import { inspectionApi, API_BASE_URL } from "../api/client";

export default function Report({ user, inspection, onBack, onNewInspection }) {
  // Primary Tabs: "compliance" (Rule 6 Legal Metrology) | "intelligence" (Ingredients & Additives)
  const [activeMainTab, setActiveMainTab] = useState("compliance");
  const [activeOcrTab, setActiveOcrTab]   = useState("validated"); // "validated" | "raw"
  const [showRawOcr, setShowRawOcr]       = useState(false);
  const [selectedAngleIdx, setSelectedAngleIdx] = useState(0);
  const [selectedImageModal, setSelectedImageModal] = useState(null);

  if (!inspection) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center text-slate-500 mx-auto mb-3">
          <FileText className="w-6 h-6" />
        </div>
        <p className="text-slate-600 font-medium">No statutory inspection report currently loaded.</p>
        <button
          onClick={onBack}
          className="mt-4 px-4 py-2 bg-navy-900 text-white rounded-xl text-xs font-bold shadow-xs hover:bg-navy-800 transition cursor-pointer"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  // Multi-image and view handling with comprehensive alias support
  const productImages = inspection.product_images && inspection.product_images.length > 0
    ? inspection.product_images
    : [
        {
          id: 1,
          view: "Front Label (Principal)",
          image_path: inspection.image_path,
          path: inspection.image_path,
          cropped_path: inspection.cropped_image_path,
          crop_path: inspection.cropped_image_path,
        }
      ];

  const currentImage = productImages[selectedAngleIdx] || productImages[0];

  const resolveImageUrl = (item, fallback = "") => {
    if (!item && !fallback) return "";
    const raw = item?.image_path || item?.path || item?.url || fallback || "";
    if (!raw) return "";
    return raw.startsWith("http") ? raw : `${API_BASE_URL}${raw}`;
  };

  const resolveCroppedUrl = (item, fallback = "") => {
    if (!item && !fallback) return "";
    const raw = item?.cropped_path || item?.crop_path || item?.cropped_image_path || item?.image_path || item?.path || fallback || "";
    if (!raw) return "";
    return raw.startsWith("http") ? raw : `${API_BASE_URL}${raw}`;
  };

  const currentOrigUrl = resolveImageUrl(currentImage, inspection.image_path);
  const currentCroppedUrl = resolveCroppedUrl(currentImage, inspection.cropped_image_path || currentOrigUrl);

  const pdfDownloadUrl = inspectionApi.getPdfUrl(inspection.id);

  const isCompliant = inspection.overall_status === "Compliant";
  const violations = inspection.violations || [];
  const extData = inspection.extracted_data || {};
  const geminiAnalysis = inspection.quality_assessment?.gemini_analysis || extData._gemini_analysis;
  const aiEngineUsed = extData._ai_engine || (geminiAnalysis ? "Gemini Multimodal Vision AI" : "Local OpenCV + EasyOCR");

  const passedCount = violations.filter((v) => v.status === "Pass").length;
  const failedCount = violations.filter((v) => v.status === "Fail").length;

  const qualityMetrics = inspection.quality_assessment?.metrics || {};
  const qualityScore = inspection.quality_score ?? 0.0;
  const ocrConf = inspection.ocr_confidence ? Math.round(inspection.ocr_confidence * 100) : 0;
  const retries = inspection.ocr_retry_count ?? 0;

  // Product Intelligence data
  const pi = inspection.product_intelligence || null;
  const additives = pi?.additives || [];
  const allergens = pi?.allergens || [];
  const ingredients = pi?.ingredients || [];
  const riskSummary = pi?.risk_summary || { green: 0, yellow: 0, orange: 0, red: 0 };
  const nutrition = pi?.nutritional_panel || null;

  // Mode metadata
  const inspectionMode = inspection.inspection_mode || "multi_image";
  const panoramaData = inspection.panorama_data || null;
  const videoMeta = inspection.video_metadata || null;

  const jumpToAngle = (viewName) => {
    if (!viewName) return;
    const target = String(viewName).toLowerCase();
    const idx = productImages.findIndex((p) => {
      const v = String(p.view || "").toLowerCase();
      return v.includes(target) || target.includes(v);
    });
    if (idx >= 0) {
      setSelectedAngleIdx(idx);
    }
  };

  const renderFieldValue = (field) => {
    if (!field) return <span className="text-slate-400 font-normal italic">Not Found</span>;
    if (typeof field === "string") return field;

    if (field.status === "not_found") {
      return <span className="text-rose-600 font-semibold italic">Missing Statutory Declaration</span>;
    }

    if (field.status === "low_confidence") {
      return (
        <div className="space-y-1">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Below Verification Threshold
          </span>
          <p className="text-[11px] text-amber-700 font-medium">
            OCR clarity insufficient to guarantee statutory precision. Value withheld.
          </p>
        </div>
      );
    }

    return (
      <div className="flex items-center flex-wrap gap-2">
        <span className="font-bold text-slate-900">{field.value || <span className="text-slate-400 italic">Not Detected</span>}</span>
        {field.source_view && (
          <button
            type="button"
            onClick={() => jumpToAngle(field.source_view)}
            title={`View evidence on ${field.source_view}`}
            className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 transition cursor-pointer flex items-center gap-1"
          >
            <span>Verified on:</span>
            <span>{field.source_view}</span>
          </button>
        )}
      </div>
    );
  };

  const isViewer = user?.role === "viewer";

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Breadcrumb & Action Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200/90">
        <button
          onClick={onBack}
          className="inline-flex items-center text-xs font-bold text-slate-600 hover:text-slate-900 transition group cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5 group-hover:-translate-x-0.5 transition" />
          Back to Dashboard
        </button>

        <div className="flex items-center space-x-2.5">
          {!isViewer && (
            <button
              onClick={onNewInspection}
              className="px-3.5 py-1.5 border border-slate-200 rounded-xl text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 transition shadow-2xs cursor-pointer"
            >
              New Inspection
            </button>
          )}
          <a
            href={pdfDownloadUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-display font-bold shadow-md shadow-blue-500/20 active:scale-[0.98] transition cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 mr-1.5" />
            Download 7-Section Statutory PDF
          </a>
        </div>
      </div>

      {/* Official Certificate Summary Banner */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-6 sm:p-8 shadow-card relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-3 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                AUDIT RECORD #{String(inspection.id).padStart(4, "0")}
              </span>
              <StatusBadge status={inspection.overall_status} type="verdict" size="lg" />
              
              {/* Inspection Mode Badge */}
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-800 border border-slate-200">
                {inspectionMode === "video" ? (
                  <>
                    <Film className="w-3 h-3 mr-1 text-cyan-600" />
                    Video Inspection
                  </>
                ) : inspectionMode === "panorama" ? (
                  <>
                    <RotateCw className="w-3 h-3 mr-1 text-indigo-600" />
                    360° Cylindrical Panorama
                  </>
                ) : (
                  <>
                    <Layers className="w-3 h-3 mr-1 text-blue-600" />
                    Multi-Angle ({productImages.length} Faces)
                  </>
                )}
              </span>

              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
                <Sparkles className="w-3 h-3 mr-1 text-blue-600" />
                {aiEngineUsed}
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-display font-black text-slate-900 tracking-tight">
              {inspection.product_name}
            </h1>

            <div className="flex flex-wrap gap-y-2 gap-x-5 text-xs text-slate-500">
              <div>
                <span className="font-semibold text-slate-700">Brand / Entity:</span>{" "}
                <span className="font-bold text-slate-900">{inspection.brand}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-700">Audit Timestamp:</span>{" "}
                <span className="font-mono text-slate-600">{new Date(inspection.created_at).toLocaleString()}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-700">Rules Satisfied:</span>{" "}
                <span className="font-bold text-slate-900">{passedCount} of {violations.length} Mandatory Declarations</span>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed pt-1 max-w-2xl">
              {isCompliant
                ? "All mandatory statutory declarations mandated under Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011 have been successfully detected, validated across packaging faces, and confirmed compliant."
                : `Statutory deficiency detected: ${failedCount} mandatory declaration requirement(s) failed statutory verification criteria. Evidentiary report generated.`}
            </p>
          </div>

          <div className="shrink-0 w-full md:w-auto border-t md:border-t-0 md:border-l border-slate-100 pt-4 md:pt-0 md:pl-8 flex justify-center">
            <ScoreGauge score={inspection.compliance_score} />
          </div>
        </div>
      </div>

      {/* Multi-Angle Coverage Telemetry Banner */}
      {productImages.length > 1 && (
        <div className="p-5 bg-gradient-to-r from-blue-950 via-navy-900 to-slate-900 text-white rounded-2xl border border-blue-800/80 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-4 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex items-start space-x-3.5">
            <div className="p-2.5 bg-blue-600/30 text-blue-300 border border-blue-500/40 rounded-xl shrink-0 mt-0.5">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-500/30 text-blue-200 border border-blue-400/40">
                  MULTI-VIEW FUSION
                </span>
                <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{productImages.length} Packaging Facets Analyzed & Synthesized</span>
                </span>
              </div>
              <p className="text-sm font-display font-bold text-white mt-1">
                Unified Statutory Declarations Derived Across All Package Angles
              </p>
              <p className="text-xs text-blue-200/80 mt-0.5">
                Declarations, ingredients and marks were cross-verified across {productImages.map(p => p.view || 'Angle').join(' + ')}.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {productImages.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setSelectedAngleIdx(idx)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer border ${
                  selectedAngleIdx === idx
                    ? "bg-blue-600 text-white border-blue-400 shadow-sm ring-2 ring-blue-400/30"
                    : "bg-white/10 text-slate-200 border-white/10 hover:bg-white/20"
                }`}
              >
                <span>Angle {idx + 1}:</span>
                <span className="truncate max-w-[110px]">{p.view || `Facet ${idx + 1}`}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Mode-Specific Telemetry Banners */}
      {videoMeta && (
        <div className="p-4 bg-cyan-50/80 rounded-2xl border border-cyan-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-cyan-950">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-cyan-600 text-white rounded-xl">
              <Video className="w-4 h-4" />
            </div>
            <div>
              <p className="font-bold">Continuous Video Inspection Intake</p>
              <p className="text-cyan-800">
                Duration: {videoMeta.duration_sec?.toFixed(1)}s • Total Frames: {videoMeta.total_frames} • Blur Rejected: {videoMeta.blur_rejected_frames || 0}
              </p>
            </div>
          </div>
          <span className="font-mono font-bold px-3 py-1 bg-white text-cyan-900 rounded-full border border-cyan-200 shadow-2xs self-start sm:self-auto">
            {videoMeta.selected_keyframes || productImages.length} High-Precision Keyframes Analyzed
          </span>
        </div>
      )}

      {panoramaData && (
        <div className="p-4 bg-indigo-50/80 rounded-2xl border border-indigo-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-indigo-950">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-indigo-600 text-white rounded-xl">
              <RotateCw className="w-4 h-4" />
            </div>
            <div>
              <p className="font-bold">360° Cylindrical Panorama Unwrap</p>
              <p className="text-indigo-800">
                Status: <strong className="capitalize">{panoramaData.status}</strong> • Stitch Confidence: {Math.round((panoramaData.stitch_confidence || 0.85) * 100)}% • Source Angles: {panoramaData.source_images_count || productImages.length}
              </p>
            </div>
          </div>
          {panoramaData.panorama_image_path && (
            <button
              type="button"
              onClick={() => setSelectedImageModal(`${API_BASE_URL}${panoramaData.panorama_image_path}`)}
              className="text-xs font-bold text-indigo-700 hover:text-indigo-900 bg-white px-3 py-1 rounded-xl border border-indigo-200 shadow-2xs flex items-center space-x-1 cursor-pointer"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Inspect Unwrapped Surface</span>
            </button>
          )}
        </div>
      )}

      {/* TWO PRIMARY TABS */}
      <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
        <button
          type="button"
          onClick={() => setActiveMainTab("compliance")}
          className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-display font-bold text-xs transition cursor-pointer ${
            activeMainTab === "compliance"
              ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
              : "bg-white text-slate-700 hover:bg-slate-100 border border-slate-200"
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Packaging Compliance (Rule 6 Audit)</span>
          <span className={`ml-1 text-[10px] px-1.5 py-0.2 rounded-full ${
            activeMainTab === "compliance" ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600"
          }`}>
            {passedCount}/{violations.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveMainTab("intelligence")}
          className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl font-display font-bold text-xs transition cursor-pointer ${
            activeMainTab === "intelligence"
              ? "bg-purple-600 text-white shadow-md shadow-purple-500/20"
              : "bg-white text-slate-700 hover:bg-slate-100 border border-slate-200"
          }`}
        >
          <Beaker className="w-4 h-4" />
          <span>Product Intelligence (Ingredients & Additives)</span>
          {additives.length > 0 && (
            <span className={`ml-1 text-[10px] px-1.5 py-0.2 rounded-full ${
              activeMainTab === "intelligence" ? "bg-white/20 text-white" : "bg-purple-100 text-purple-800"
            }`}>
              {additives.length} Additives
            </span>
          )}
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: PACKAGING COMPLIANCE (RULE 6 LEGAL METROLOGY)                      */}
      {/* ========================================================================= */}
      {activeMainTab === "compliance" && (
        <div className="space-y-6">
          {/* Diagnostics Telemetry Row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-white rounded-xl border border-slate-200/90 shadow-card flex items-start space-x-3">
              <div className="p-2.5 bg-blue-500/10 text-blue-700 border border-blue-500/20 rounded-xl shrink-0">
                <Gauge className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Surface Quality</span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">
                    {qualityScore >= 80 ? "Crisp" : qualityScore >= 60 ? "Good" : "Acceptable"}
                  </span>
                </div>
                <p className="text-xl font-display font-extrabold text-slate-900 mt-1 tabular-nums">
                  {qualityScore.toFixed(1)} <span className="text-xs text-slate-400 font-semibold font-sans">/ 100</span>
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
                  Laplacian: {qualityMetrics.sharpness_laplacian ?? "N/A"}
                </p>
              </div>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200/90 shadow-card flex items-start space-x-3">
              <div className="p-2.5 bg-emerald-500/10 text-emerald-700 border border-emerald-500/20 rounded-xl shrink-0">
                <Activity className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">OCR Confidence</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${ocrConf >= 75 ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                    {ocrConf >= 75 ? "High Precision" : "Moderate"}
                  </span>
                </div>
                <p className="text-xl font-display font-extrabold text-slate-900 mt-1 tabular-nums">
                  {ocrConf}% <span className="text-xs text-slate-400 font-semibold font-sans">Consensus</span>
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Disambiguated typography stream
                </p>
              </div>
            </div>

            <div className="p-4 bg-white rounded-xl border border-slate-200/90 shadow-card flex items-start space-x-3">
              <div className="p-2.5 bg-purple-500/10 text-purple-700 border border-purple-500/20 rounded-xl shrink-0">
                <Repeat className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Multi-Pass Stage</span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">
                    {retries > 0 ? "Adaptive Retry" : "Single Pass"}
                  </span>
                </div>
                <p className="text-xl font-display font-extrabold text-slate-900 mt-1 tabular-nums">
                  {retries === 0 ? "1 Pass" : `${retries + 1} Passes`}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {retries > 0 ? `${retries} retry stage(s) executed` : "Target confidence satisfied in Pass 1"}
                </p>
              </div>
            </div>
          </div>

          {/* Gemini AI Multimodal Packaging Visual Analysis Card */}
          {geminiAnalysis && (
            <div className="bg-gradient-to-r from-blue-50/80 via-slate-50 to-indigo-50/60 rounded-2xl border border-blue-200/80 p-5 sm:p-6 shadow-card space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-blue-200/60 pb-3">
                <div className="flex items-center space-x-2.5">
                  <div className="p-2 bg-blue-600 text-white rounded-xl shadow-xs">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h2 className="text-sm font-display font-bold text-slate-900">
                      Multimodal Packaging & Substrate Analysis
                    </h2>
                    <p className="text-xs text-slate-500">
                      Computer Vision audit of label curvature, specular reflection & visual clarity
                    </p>
                  </div>
                </div>
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-white text-blue-900 border border-blue-200 shadow-2xs font-mono">
                  Legibility: {geminiAnalysis.legibility_score ?? 95}/100 ({geminiAnalysis.visual_clarity || "Good"})
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-white/90 rounded-xl border border-blue-100 shadow-2xs">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Packaging Type</p>
                  <p className="text-xs font-bold text-slate-800 mt-0.5 capitalize truncate">
                    {geminiAnalysis.packaging_type || "Packaged Commodity"}
                  </p>
                </div>
                <div className="p-3 bg-white/90 rounded-xl border border-blue-100 shadow-2xs">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Surface Glare</p>
                  <p className="text-xs font-bold text-slate-800 mt-0.5 truncate">
                    {geminiAnalysis.glare_detected ? `Detected (${geminiAnalysis.glare_severity || 'Mild'})` : "None (Balanced)"}
                  </p>
                </div>
                <div className="p-3 bg-white/90 rounded-xl border border-blue-100 shadow-2xs">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Curvature</p>
                  <p className="text-xs font-bold text-slate-800 mt-0.5 truncate">
                    {geminiAnalysis.surface_curvature || "Flat"}
                  </p>
                </div>
                <div className="p-3 bg-white/90 rounded-xl border border-blue-100 shadow-2xs">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Recommended CV</p>
                  <p className="text-xs font-bold text-blue-700 mt-0.5 truncate">
                    {geminiAnalysis.recommended_opencv_variant || "Variant A (Balanced)"}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Multi-Angle Switcher & Computer Vision Rectification Dock */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-card space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <Layers className="w-4 h-4 text-blue-600" />
                <h2 className="text-xs font-display font-bold uppercase tracking-wider text-slate-800">
                  Packaging Angle Visual Inspector & OpenCV Rectification
                </h2>
              </div>
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <ZoomIn className="w-3 h-3" /> Click preview to enlarge
              </span>
            </div>

            {/* Angle Selector Tabs if more than 1 image */}
            {productImages.length > 1 && (
              <div className="flex flex-wrap items-center gap-2">
                {productImages.map((img, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSelectedAngleIdx(idx)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer ${
                      selectedAngleIdx === idx
                        ? "bg-navy-900 text-white shadow-xs"
                        : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                    }`}
                  >
                    <span>Angle {idx + 1}:</span>
                    <span className="truncate max-w-[120px]">{img.view || `Facet ${idx + 1}`}</span>
                  </button>
                ))}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              {/* Original Angle Input */}
              <div className="border border-slate-200 rounded-xl p-3 bg-slate-50/50">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700 mb-2">
                  <span>{currentImage?.view || `Angle ${selectedAngleIdx + 1}`} (Raw Capture)</span>
                  <span className="text-[10px] font-mono text-slate-400">
                    {qualityMetrics.width ? `${qualityMetrics.width}×${qualityMetrics.height} px` : "Ingest"}
                  </span>
                </div>
                <div
                  className="h-56 bg-slate-950 rounded-lg overflow-hidden border border-slate-200 flex items-center justify-center cursor-pointer group"
                  onClick={() => setSelectedImageModal(currentOrigUrl)}
                >
                  <img
                    src={currentOrigUrl}
                    alt="Packaging Angle Scan"
                    className="max-h-full max-w-full object-contain group-hover:scale-105 transition duration-200"
                  />
                </div>
              </div>

              {/* OpenCV Rectified */}
              <div className="border border-blue-200 rounded-xl p-3 bg-blue-50/30">
                <div className="flex items-center justify-between text-xs font-semibold text-blue-900 mb-2">
                  <span>OpenCV Cropped & Deskewed Label Region</span>
                  <span className="text-[10px] font-mono bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-bold">
                    Contour Detected
                  </span>
                </div>
                <div
                  className="h-56 bg-slate-950 rounded-lg overflow-hidden border border-blue-200 flex items-center justify-center cursor-pointer group"
                  onClick={() => setSelectedImageModal(currentCroppedUrl)}
                >
                  <img
                    src={currentCroppedUrl}
                    alt="Cropped Rectified Label"
                    className="max-h-full max-w-full object-contain group-hover:scale-105 transition duration-200"
                  />
                </div>
              </div>
            </div>

            {/* Statutory Declarations Discovered on Current Angle */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
              <div className="flex items-center space-x-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Statutory Findings on {currentImage?.view || `Angle ${selectedAngleIdx + 1}`}:
                </span>
                <span className="text-xs font-bold text-slate-900">
                  {violations.filter(v => {
                    const sv = String(v.source_view || "").toLowerCase();
                    const cv = String(currentImage?.view || "").toLowerCase();
                    return sv && cv && (sv.includes(cv) || cv.includes(sv));
                  }).length} Evidence Anchor(s) Linked
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {violations.filter(v => {
                  const sv = String(v.source_view || "").toLowerCase();
                  const cv = String(currentImage?.view || "").toLowerCase();
                  return sv && cv && (sv.includes(cv) || cv.includes(sv));
                }).map((v, i) => (
                  <span
                    key={i}
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                      v.status === "Pass"
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : "bg-rose-50 text-rose-800 border-rose-200"
                    }`}
                  >
                    <span>{v.rule_code}</span>
                    <span className="opacity-70 font-sans font-normal">• {v.description?.slice(0, 24)}...</span>
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Evidence-Linked Mandatory Declarations Checklist Table */}
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-card overflow-hidden">
            <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-display font-bold uppercase tracking-wider text-slate-800">
                  Legal Metrology (Packaged Commodities) Rules, 2011 Checklist
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Rule-by-rule statutory compliance breakdown with source panel evidence linking
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200">
                  {passedCount} Verified
                </span>
                {failedCount > 0 && (
                  <span className="text-xs font-bold px-2.5 py-1 rounded-md bg-rose-50 text-rose-800 border border-rose-200">
                    {failedCount} Violations
                  </span>
                )}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-100 text-xs">
                <thead className="bg-slate-50/80 text-slate-500 uppercase font-semibold text-[11px]">
                  <tr>
                    <th className="py-3 px-4 text-left">Statutory Code</th>
                    <th className="py-3 px-4 text-left">Requirement</th>
                    <th className="py-3 px-4 text-left">Verdict</th>
                    <th className="py-3 px-4 text-left">Source Panel</th>
                    <th className="py-3 px-4 text-left">Detected vs Statutory Condition</th>
                    <th className="py-3 px-4 text-left">Severity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {violations.map((v, idx) => (
                    <tr key={idx} className={v.status === "Fail" ? "bg-rose-50/30" : "hover:bg-slate-50/50 transition"}>
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-800 whitespace-nowrap">{v.rule_code}</td>
                      <td className="py-3.5 px-4 font-semibold text-slate-800 max-w-xs">{v.description}</td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <StatusBadge status={v.status} />
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        {v.source_view ? (
                          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                            {v.source_view}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic text-[11px]">All Panels</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-slate-700">
                        {v.detected_value ? (
                          <div>
                            <span className="font-semibold text-slate-900">Found:</span>{" "}
                            <span className="font-mono text-slate-800">{v.detected_value}</span>
                            {v.expected_condition && (
                              <div className="text-[11px] text-rose-700 mt-0.5">
                                <span className="font-semibold">Expected:</span> {v.expected_condition}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-500">{v.description}</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <StatusBadge status={v.severity} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Structured Field Extractions Grid */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-card space-y-4">
            <div className="flex items-center space-x-2">
              <Tag className="w-4 h-4 text-blue-600" />
              <h2 className="text-xs font-display font-bold uppercase tracking-wider text-slate-800">
                Structured Declarations Extractions (NLP & Field Validation)
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Net Quantity */}
              <div className="p-4 rounded-xl border border-slate-200/90 bg-slate-50/40 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-600">Net Quantity (Standard Metric Unit)</span>
                  <StatusBadge status={extData.net_quantity?.status || "not_found"} />
                </div>
                <div className="text-sm font-bold text-slate-900 mt-1">
                  {renderFieldValue(extData.net_quantity)}
                </div>
              </div>

              {/* MRP */}
              <div className="p-4 rounded-xl border border-slate-200/90 bg-slate-50/40 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-600">Maximum Retail Price (MRP incl. of all taxes)</span>
                  <StatusBadge status={extData.mrp?.status || "not_found"} />
                </div>
                <div className="text-sm font-bold text-slate-900 mt-1">
                  {renderFieldValue(extData.mrp)}
                </div>
              </div>

              {/* Mfg Date */}
              <div className="p-4 rounded-xl border border-slate-200/90 bg-slate-50/40 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-600">Date of Manufacture / Packing</span>
                  <StatusBadge status={extData.manufacture_date?.status || "not_found"} />
                </div>
                <div className="text-sm font-bold text-slate-900 mt-1">
                  {renderFieldValue(extData.manufacture_date)}
                </div>
              </div>

              {/* Customer Care */}
              <div className="p-4 rounded-xl border border-slate-200/90 bg-slate-50/40 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-600">Consumer Care Details (Tel / Email / Address)</span>
                  <StatusBadge status={extData.customer_care?.status || "not_found"} />
                </div>
                <div className="text-sm font-bold text-slate-900 mt-1">
                  {renderFieldValue(extData.customer_care)}
                </div>
              </div>

              {/* FSSAI */}
              <div className="p-4 rounded-xl border border-slate-200/90 bg-slate-50/40 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-600">FSSAI 14-Digit Registration</span>
                  <StatusBadge status={extData.fssai_license?.status || "not_found"} />
                </div>
                <div className="text-sm font-bold text-slate-900 mt-1 font-mono">
                  {renderFieldValue(extData.fssai_license)}
                </div>
              </div>

              {/* Country of Origin */}
              <div className="p-4 rounded-xl border border-slate-200/90 bg-slate-50/40 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-600">Country of Origin</span>
                  <StatusBadge status={extData.country_of_origin?.status || "not_found"} />
                </div>
                <div className="text-sm font-bold text-slate-900 mt-1">
                  {renderFieldValue(extData.country_of_origin)}
                </div>
              </div>

              {/* Manufacturer Details */}
              <div className="md:col-span-2 p-4 rounded-xl border border-slate-200/90 bg-slate-50/40 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-600">Manufacturer / Packer Identity & Address</span>
                  <StatusBadge status={extData.manufacturer_details?.status || "not_found"} />
                </div>
                <div className="text-sm font-bold text-slate-900 mt-1">
                  {renderFieldValue(extData.manufacturer_details)}
                </div>
              </div>
            </div>
          </div>

          {/* OCR Typography Stream Inspector */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-card space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 text-blue-600" />
                <h2 className="text-xs font-display font-bold uppercase tracking-wider text-slate-800">
                  OCR Typography Stream Inspector
                </h2>
              </div>

              <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl">
                <button
                  type="button"
                  onClick={() => {
                    setActiveOcrTab("validated");
                    setShowRawOcr(true);
                  }}
                  className={`px-3 py-1 text-xs font-bold rounded-lg transition cursor-pointer ${
                    activeOcrTab === "validated" && showRawOcr
                      ? "bg-white text-blue-700 shadow-2xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  Validated & Disambiguated
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveOcrTab("raw");
                    setShowRawOcr(true);
                  }}
                  className={`px-3 py-1 text-xs font-bold rounded-lg transition cursor-pointer ${
                    activeOcrTab === "raw" && showRawOcr
                      ? "bg-white text-blue-700 shadow-2xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  Raw Engine Output
                </button>
                <button
                  type="button"
                  onClick={() => setShowRawOcr(!showRawOcr)}
                  className="px-2.5 py-1 text-xs text-slate-500 hover:text-slate-800 font-semibold cursor-pointer"
                >
                  {showRawOcr ? "Collapse ▲" : "Inspect ▼"}
                </button>
              </div>
            </div>

            {showRawOcr && (
              <div className="p-4 rounded-xl bg-navy-950 text-slate-200 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto border border-navy-800">
                {activeOcrTab === "validated"
                  ? (inspection.validated_ocr_text || inspection.raw_ocr_text || "No text extracted by OCR engine.")
                  : (inspection.raw_ocr_text || "No raw text extracted by OCR engine.")}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: PRODUCT INTELLIGENCE (INGREDIENTS & ADDITIVES)                      */}
      {/* ========================================================================= */}
      {activeMainTab === "intelligence" && (
        <div className="space-y-6">
          {!pi || (!pi.ingredients_found && additives.length === 0) ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center space-y-3 shadow-card">
              <div className="w-12 h-12 rounded-2xl bg-purple-50 text-purple-600 border border-purple-200 flex items-center justify-center mx-auto">
                <Beaker className="w-6 h-6" />
              </div>
              <h3 className="text-base font-display font-bold text-slate-900">
                No Ingredients or Additives Declaration Detected
              </h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
                This package may be a non-food commodity or the ingredients panel was not included in the uploaded angles. Upload the side or rear ingredients panel to activate INS additive decoding and allergen alerts.
              </p>
            </div>
          ) : (
            <>
              {/* Product Intelligence Header & Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
                {/* Total Ingredients */}
                <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-card">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Ingredients Count</span>
                  <p className="text-2xl font-display font-black text-slate-900 mt-1 tabular-nums">
                    {pi.total_ingredients_count || ingredients.length}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Parsed statutory components</p>
                </div>

                {/* Decoded Additives */}
                <div className="p-4 bg-white rounded-2xl border border-purple-200 bg-purple-50/20 shadow-card">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700">Decoded Additives</span>
                  <p className="text-2xl font-display font-black text-purple-950 mt-1 tabular-nums">
                    {additives.length}
                  </p>
                  <p className="text-[11px] text-purple-700 mt-0.5">INS codes cross-referenced</p>
                </div>

                {/* Flagged Allergens */}
                <div className="p-4 bg-white rounded-2xl border border-amber-200 bg-amber-50/20 shadow-card">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800">Allergen Warnings</span>
                  <p className="text-2xl font-display font-black text-amber-950 mt-1 tabular-nums">
                    {allergens.length}
                  </p>
                  <p className="text-[11px] text-amber-800 mt-0.5">Mandatory statutory flags</p>
                </div>

                {/* Evidence Confidence */}
                <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-card">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Evidence Confidence</span>
                  <p className="text-2xl font-display font-black text-slate-900 mt-1 tabular-nums">
                    {Math.round((pi.evidence_confidence || 0.9) * 100)}%
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Codex & FSSAI benchmark</p>
                </div>
              </div>

              {/* Additive Risk Summary Dial Bar */}
              <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-card space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-display font-bold uppercase tracking-wider text-slate-800">
                    Additive Risk Level Distribution (FSSAI / Codex Scientific Evidence)
                  </span>
                  <span className="text-[11px] font-mono text-slate-500">
                    {additives.length} Total Identified Additives
                  </span>
                </div>

                <div className="flex items-center space-x-2 pt-1">
                  <div className="flex-1 flex h-3 rounded-full overflow-hidden bg-slate-100">
                    {riskSummary.green > 0 && (
                      <div
                        style={{ width: `${(riskSummary.green / additives.length) * 100}%` }}
                        className="bg-emerald-500"
                        title={`Green (Low Concern): ${riskSummary.green}`}
                      />
                    )}
                    {riskSummary.yellow > 0 && (
                      <div
                        style={{ width: `${(riskSummary.yellow / additives.length) * 100}%` }}
                        className="bg-amber-400"
                        title={`Yellow (Context / ADI): ${riskSummary.yellow}`}
                      />
                    )}
                    {riskSummary.orange > 0 && (
                      <div
                        style={{ width: `${(riskSummary.orange / additives.length) * 100}%` }}
                        className="bg-orange-500"
                        title={`Orange (Cautionary): ${riskSummary.orange}`}
                      />
                    )}
                    {riskSummary.red > 0 && (
                      <div
                        style={{ width: `${(riskSummary.red / additives.length) * 100}%` }}
                        className="bg-rose-600"
                        title={`Red (High Concern / Strict Limits): ${riskSummary.red}`}
                      />
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-xs pt-1">
                  <span className="flex items-center gap-1.5 text-emerald-800">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    <strong>{riskSummary.green}</strong> Generally Permitted / Safe
                  </span>
                  <span className="flex items-center gap-1.5 text-amber-800">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                    <strong>{riskSummary.yellow}</strong> Quantity / Sensitivity Sensitive
                  </span>
                  <span className="flex items-center gap-1.5 text-orange-800">
                    <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
                    <strong>{riskSummary.orange}</strong> Cautionary / ADI Monitoring
                  </span>
                  {riskSummary.red > 0 && (
                    <span className="flex items-center gap-1.5 text-rose-800">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-600" />
                      <strong>{riskSummary.red}</strong> Strictly Regulated / Banned
                    </span>
                  )}
                </div>
              </div>

              {/* Allergen Alerts Banner */}
              {allergens.length > 0 && (
                <div className="p-5 bg-amber-50/90 rounded-2xl border-2 border-amber-200/90 shadow-card space-y-3">
                  <div className="flex items-center space-x-2 text-amber-950 font-display font-bold text-sm">
                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                    <span>Statutory Allergen Advisories Detected</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 pt-1">
                    {allergens.map((alg, i) => (
                      <div
                        key={i}
                        className="p-3 bg-white/90 rounded-xl border border-amber-200/80 flex items-start justify-between gap-2"
                      >
                        <div>
                          <div className="flex items-center space-x-1.5">
                            <span className="text-xs font-bold text-slate-900">{alg.name}</span>
                            <span className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded uppercase ${
                              alg.type === "explicit"
                                ? "bg-amber-200 text-amber-900"
                                : alg.type === "precautionary"
                                ? "bg-slate-200 text-slate-700"
                                : "bg-purple-100 text-purple-800"
                            }`}>
                              {alg.type}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-600 mt-1 leading-snug">
                            {alg.advisory}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Decoded Additive Knowledge Base Cards */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Beaker className="w-4 h-4 text-purple-600" />
                    <h2 className="text-xs font-display font-bold uppercase tracking-wider text-slate-800">
                      Decoded INS Food Additives & Scientific Evaluations
                    </h2>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">
                    FSSAI & Codex STAN 192-1995 Evidence Base
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {additives.map((add, idx) => {
                    const isGreen = add.risk_level === "green";
                    const isYellow = add.risk_level === "yellow";
                    const isOrange = add.risk_level === "orange";

                    const badgeStyle = isGreen
                      ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                      : isYellow
                      ? "bg-amber-100 text-amber-800 border-amber-300"
                      : isOrange
                      ? "bg-orange-100 text-orange-800 border-orange-300"
                      : "bg-rose-100 text-rose-800 border-rose-300";

                    const cardBorder = isGreen
                      ? "border-emerald-200 bg-emerald-50/10"
                      : isYellow
                      ? "border-amber-200 bg-amber-50/10"
                      : isOrange
                      ? "border-orange-300 bg-orange-50/20"
                      : "border-rose-300 bg-rose-50/20";

                    return (
                      <div
                        key={idx}
                        className={`p-5 rounded-2xl border shadow-card space-y-3 transition ${cardBorder}`}
                      >
                        <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-2.5">
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="font-mono font-bold text-sm text-slate-950">{add.identifier}</span>
                              <span className="text-xs font-bold text-slate-800">— {add.common_name}</span>
                            </div>
                            <p className="text-[11px] text-purple-700 font-semibold mt-0.5">{add.function}</p>
                          </div>

                          <span className={`text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border ${badgeStyle}`}>
                            {isGreen ? "🟢 Low Concern" : isYellow ? "🟡 Context / ADI" : isOrange ? "🟠 Cautionary" : "🔴 Strict Limits"}
                          </span>
                        </div>

                        <div className="space-y-2 text-xs text-slate-700">
                          <div>
                            <span className="font-bold text-slate-900">Functional Purpose:</span>{" "}
                            <span>{add.purpose}</span>
                          </div>
                          <div>
                            <span className="font-bold text-slate-900">Typical Commodity Use:</span>{" "}
                            <span>{add.typical_use}</span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px] space-y-1">
                            <p>
                              <strong className="text-slate-900">Regulatory Status:</strong>{" "}
                              <span className="text-slate-700">{add.regulatory_status}</span>
                            </p>
                            <p>
                              <strong className="text-slate-900">Health & Dietary Context:</strong>{" "}
                              <span className="text-slate-700">{add.concerns}</span>
                            </p>
                          </div>
                        </div>

                        {add.sources?.length > 0 && (
                          <div className="pt-1 flex items-center gap-1 text-[10px] text-slate-400 font-mono">
                            <BookOpen className="w-3 h-3 text-slate-400" />
                            <span className="truncate">{add.sources[0]}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Complete Ingredients Composition List */}
              <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-card space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-display font-bold uppercase tracking-wider text-slate-800">
                    Statutory Ingredient Panel Declaration Breakdown
                  </h3>
                  <span className="text-[10px] font-mono text-slate-400">Order of Predominance</span>
                </div>

                {pi.raw_ingredient_text && (
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs font-mono text-slate-800 leading-relaxed">
                    <strong>Raw Declaration:</strong> {pi.raw_ingredient_text}
                  </div>
                )}

                <div className="flex flex-wrap gap-2 pt-1">
                  {ingredients.map((ing, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center px-2.5 py-1 rounded-xl text-xs bg-slate-100 text-slate-800 border border-slate-200"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-500 mr-1.5" />
                      <strong className="mr-1">{ing.name}</strong>
                      {ing.percentage && <span className="text-slate-500 font-mono">({ing.percentage})</span>}
                    </span>
                  ))}
                </div>
              </div>

              {/* Nutritional Panel Audit (if detected) */}
              {nutrition && (
                <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-card space-y-3">
                  <h3 className="text-xs font-display font-bold uppercase tracking-wider text-slate-800">
                    Nutritional Information Audit (Per 100g / Serving)
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5 text-center">
                    {[
                      { label: "Energy", val: nutrition.calories_kcal ? `${nutrition.calories_kcal} kcal` : "N/A" },
                      { label: "Protein", val: nutrition.protein_g ? `${nutrition.protein_g} g` : "N/A" },
                      { label: "Carbs", val: nutrition.carbohydrates_g ? `${nutrition.carbohydrates_g} g` : "N/A" },
                      { label: "Added Sugar", val: nutrition.sugars_g ? `${nutrition.sugars_g} g` : "N/A" },
                      { label: "Total Fat", val: nutrition.total_fat_g ? `${nutrition.total_fat_g} g` : "N/A" },
                      { label: "Sat Fat", val: nutrition.saturated_fat_g ? `${nutrition.saturated_fat_g} g` : "N/A" },
                      { label: "Sodium", val: nutrition.sodium_mg ? `${nutrition.sodium_mg} mg` : "N/A" },
                    ].map((nut) => (
                      <div key={nut.label} className="p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                        <p className="text-[10px] font-bold uppercase text-slate-500">{nut.label}</p>
                        <p className="text-xs font-bold text-slate-900 mt-0.5">{nut.val}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Scientific & Statutory Disclaimer */}
              <div className="p-4 rounded-xl bg-slate-100 border border-slate-200 text-xs text-slate-600 flex items-start space-x-2.5">
                <Info className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  <strong>Regulatory Advisory Notice:</strong> {pi.disclaimer}
                </p>
              </div>
            </>
          )}
        </div>
      )}

      {/* Fullscreen Image Modal */}
      {selectedImageModal && (
        <div
          className="fixed inset-0 z-50 bg-navy-950/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setSelectedImageModal(null)}
        >
          <div className="max-w-4xl max-h-[90vh] bg-white rounded-2xl overflow-hidden p-2 shadow-2xl border border-slate-200">
            <img
              src={selectedImageModal}
              alt="Enlarged packaging inspect view"
              className="max-h-[85vh] max-w-full object-contain rounded-xl"
            />
          </div>
        </div>
      )}
    </div>
  );
}
