import React, { useState, useRef, useCallback } from "react";
import {
  Upload as UploadIcon,
  Camera,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Layers,
  ShieldAlert,
  Lightbulb,
  RefreshCw,
  X,
  Plus,
  Images,
  ScanLine,
  ClipboardList,
  Package,
  Calendar,
  BadgeCheck,
  DollarSign,
  Bot,
  Cpu,
  Zap,
} from "lucide-react";
import { inspectionApi, API_BASE_URL } from "../api/client";

const MAX_IMAGES = 5;

// Purpose hints shown under each thumbnail slot
const SLOT_HINTS = [
  { label: "Front Label",      icon: Package,       color: "blue"   },
  { label: "Date / Batch",     icon: Calendar,      color: "amber"  },
  { label: "Back Label",       icon: ClipboardList, color: "violet" },
  { label: "FSSAI Sticker",    icon: BadgeCheck,    color: "emerald"},
  { label: "MRP / Side Panel", icon: DollarSign,    color: "rose"   },
];

const COLOR_CLASSES = {
  blue:    { border: "border-blue-400",   bg: "bg-blue-50",   text: "text-blue-700",   ring: "ring-blue-400"   },
  amber:   { border: "border-amber-400",  bg: "bg-amber-50",  text: "text-amber-700",  ring: "ring-amber-400"  },
  violet:  { border: "border-violet-400", bg: "bg-violet-50", text: "text-violet-700", ring: "ring-violet-400" },
  emerald: { border: "border-emerald-400",bg: "bg-emerald-50",text: "text-emerald-700",ring: "ring-emerald-400"},
  rose:    { border: "border-rose-400",   bg: "bg-rose-50",   text: "text-rose-700",   ring: "ring-rose-400"   },
};

const PIPELINE_STAGES = [
  "Upload",
  "Quality Gate",
  "OpenCV + YOLO",
  "OCR Engine",
  "Rule Engine",
];

export default function Upload({ user, onInspectionComplete, onCancel }) {
  const [files, setFiles]               = useState([]); // [{file, preview, slotIdx}]
  const [productName, setProductName]   = useState("");
  const [brand, setBrand]               = useState("");
  const [isFoodProduct, setIsFoodProduct] = useState(true);
  const [aiEngine, setAiEngine]         = useState("gemini"); // "gemini" | "hybrid" | "local"
  const [loading, setLoading]           = useState(false);
  const [progress, setProgress]         = useState(0);
  const [pipelineStage, setPipelineStage] = useState("");
  const [error, setError]               = useState(null);
  const [qualityDiagnostic, setQualityDiagnostic] = useState(null);

  const fileInputRef   = useRef(null);
  const cameraInputRef = useRef(null);
  const addSlotRef     = useRef(null); // which slot triggered the picker

  // ---------------------------------------------------------------------------
  // Sample labels
  // ---------------------------------------------------------------------------
  const sampleLabels = [
    { id: "compliant",     title: "Compliant Biscuit",       subtitle: "Full compliance (100%)", product: "NutriCrunch Almond Cookies", brand: "Suncrest Foods",    food: true,  url: `${API_BASE_URL}/sample_images/compliant_label.png`,     badge: "Pass"        },
    { id: "non_compliant", title: "Non-Compliant Chocolate", subtitle: "Missing taxes & care",    product: "ChocoDelight Premium Bar",   brand: "ChocoDelight",      food: true,  url: `${API_BASE_URL}/sample_images/non_compliant_label.png`, badge: "Fail"        },
    { id: "partial",       title: "Herbal Soap",             subtitle: "Phone only, no email",   product: "Himalayan Herbal Soap",     brand: "AyurVeda Organics", food: false, url: `${API_BASE_URL}/sample_images/partial_label.png`,      badge: "Partial"     },
    { id: "blurry",        title: "Blurry Label Demo",       subtitle: "Pre-OCR rejection test", product: "Blurry Package Sample",     brand: "QuickSnack",        food: true,  url: `${API_BASE_URL}/sample_images/blurry_label.png`,       badge: "Reject Demo" },
    { id: "low_res",       title: "Low-Res Demo",            subtitle: "Resolution gate test",   product: "Low Resolution Sample",     brand: "MiniBrand",         food: false, url: `${API_BASE_URL}/sample_images/low_res_label.png`,      badge: "Low Res"     },
  ];

  // ---------------------------------------------------------------------------
  // File management
  // ---------------------------------------------------------------------------
  const addFiles = useCallback((newFileList, slotIdx = null) => {
    const arr = Array.from(newFileList);
    setFiles(prev => {
      const remaining = MAX_IMAGES - prev.length;
      if (remaining <= 0) return prev;
      const toAdd = arr.slice(0, remaining).map((f, i) => ({
        file: f,
        preview: URL.createObjectURL(f),
        slotIdx: slotIdx !== null ? slotIdx : prev.length + i,
        id: `${Date.now()}_${i}`,
      }));
      return [...prev, ...toAdd];
    });
    setError(null);
    setQualityDiagnostic(null);
  }, []);

  const removeFile = useCallback((id) => {
    setFiles(prev => {
      const entry = prev.find(f => f.id === id);
      if (entry) URL.revokeObjectURL(entry.preview);
      return prev.filter(f => f.id !== id);
    });
  }, []);

  const handleFileInputChange = (e) => {
    if (e.target.files?.length) addFiles(e.target.files);
    e.target.value = "";
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const handleDragOver = (e) => e.preventDefault();

  // Guard for Viewer Role (evaluated after all hooks)
  if (user?.role === "viewer") {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <div className="w-16 h-16 bg-amber-100 text-amber-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-md shadow-amber-500/10">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">Access Restricted • Read-Only Mode</h2>
        <p className="text-slate-500 text-sm mt-2 max-w-md mx-auto">
          Public viewers are not authorized to conduct or upload product inspections under Legal Metrology Rules. You can browse verified compliance audit reports and download certificates.
        </p>
        <button
          onClick={onCancel}
          className="mt-6 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold transition shadow-md shadow-blue-500/20 cursor-pointer"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Sample selection — loads ONE sample into slot 0
  // ---------------------------------------------------------------------------
  const handleSelectSample = async (sample) => {
    try {
      setLoading(true);
      setError(null);
      setQualityDiagnostic(null);
      setPipelineStage("Loading sample image...");
      const response = await fetch(sample.url);
      const blob = await response.blob();
      const sampleFile = new File([blob], `${sample.id}_label.png`, { type: "image/png" });
      setFiles([{
        file: sampleFile,
        preview: URL.createObjectURL(sampleFile),
        slotIdx: 0,
        id: `sample_${Date.now()}`,
      }]);
      setProductName(sample.product);
      setBrand(sample.brand);
      setIsFoodProduct(sample.food);
    } catch {
      setError("Could not load sample image. Please upload a file manually.");
    } finally {
      setLoading(false);
      setPipelineStage("");
    }
  };

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------
  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (files.length === 0) {
      setError("Please add at least one label photo.");
      return;
    }

    setLoading(true);
    setError(null);
    setQualityDiagnostic(null);

    // Animated pipeline progress based on selected engine
    const stages = aiEngine === "gemini" ? [
      { pct: 15, label: "Stage 1/4: Ingesting packaging label photos..." },
      { pct: 35, label: "Stage 2/4: Gemini Multimodal Visual Quality & Surface Audit..." },
      { pct: 70, label: "Stage 3/4: Gemini AI Statutory Field Extraction (Rules 2011)..." },
      { pct: 92, label: "Stage 4/4: Legal Metrology Rule Compliance Scoring..." },
    ] : aiEngine === "hybrid" ? [
      { pct: 12, label: "Stage 1/5: Ingesting packaging photos..." },
      { pct: 30, label: "Stage 2/5: Dual Quality Gate & Gemini Visual Audit..." },
      { pct: 55, label: "Stage 3/5: OpenCV Preprocessing & Multi-Variant Local OCR..." },
      { pct: 75, label: "Stage 4/5: Gemini AI Extraction & Cross-Engine Consensus Fusion..." },
      { pct: 92, label: "Stage 5/5: Legal Metrology Rule Evaluation (Rules 2011)..." },
    ] : [
      { pct: 12, label: "Stage 1/5: Uploading label photos..." },
      { pct: 32, label: "Stage 2/5: Pre-OCR Quality Gate (blur, sharpness, exposure)..." },
      { pct: 54, label: "Stage 3/5: OpenCV + YOLO Text Region Detection & Preprocessing..." },
      { pct: 75, label: "Stage 4/5: Adaptive Multi-Variant OCR + Field Merge across images..." },
      { pct: 92, label: "Stage 5/5: Legal Metrology Rule Engine (Rules, 2011)..." },
    ];
    const delays = [0, 500, 1400, 2600, 4200];
    const timers = stages.map((s, i) =>
      setTimeout(() => { setProgress(s.pct); setPipelineStage(s.label); }, delays[i] || 1000 * i)
    );

    try {
      const formData = new FormData();
      files.forEach(entry => formData.append("images", entry.file));
      formData.append("product_name", productName.trim() || "Packaged Product");
      formData.append("brand",        brand.trim()        || "Unbranded");
      formData.append("is_food_product", isFoodProduct ? "true" : "false");
      formData.append("ai_engine", aiEngine);

      const result = await inspectionApi.upload(formData);

      timers.forEach(clearTimeout);
      setProgress(100);
      setPipelineStage("Verification completed successfully!");

      setTimeout(() => onInspectionComplete(result), 400);
    } catch (err) {
      timers.forEach(clearTimeout);
      setLoading(false);
      setProgress(0);
      setPipelineStage("");

      if (err.response?.status === 422 && err.response?.data?.detail?.code === "IMAGE_QUALITY_VALIDATION_FAILED") {
        setQualityDiagnostic(err.response.data.detail);
      } else {
        const msg =
          err.response?.data?.detail?.message ||
          err.response?.data?.detail ||
          "Failed to process label image. Please check image quality and try again.";
        setError(typeof msg === "string" ? msg : JSON.stringify(msg));
      }
    }
  };

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------
  const slotColor = (idx) => SLOT_HINTS[idx % SLOT_HINTS.length].color;
  const badgeCls = (badge) =>
    badge === "Pass"    ? "bg-emerald-100 text-emerald-800" :
    badge === "Fail"    ? "bg-rose-100 text-rose-800"       :
    badge === "Partial" ? "bg-amber-100 text-amber-800"     :
                          "bg-purple-100 text-purple-800";

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          New Label Compliance Inspection
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload up to <strong>5 photos</strong> of the same product (front label, back, FSSAI sticker, date panel…).
          Fields found in any photo are merged automatically before compliance scoring.
        </p>
      </div>

      {/* Quality rejection card */}
      {qualityDiagnostic && (
        <div className="mb-8 p-6 rounded-2xl bg-rose-50/90 border-2 border-rose-300 shadow-sm space-y-5 animate-in fade-in slide-in-from-top-3 duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-rose-200/80 pb-4">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 bg-rose-100 text-rose-700 rounded-xl"><ShieldAlert className="w-6 h-6" /></div>
              <div>
                <h2 className="text-base font-bold text-rose-950">Pre-OCR Quality Gate: Failed</h2>
                <p className="text-xs text-rose-700">OCR processing halted to prevent inaccurate extractions.</p>
              </div>
            </div>
            <span className="self-start sm:self-auto text-xs font-bold px-3 py-1 bg-rose-200 text-rose-900 rounded-full">Hard Gate Rejection</span>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-bold uppercase tracking-wider text-rose-900">Rejection reasons</p>
            <ul className="space-y-1.5">
              {qualityDiagnostic.rejection_reasons?.map((r, i) => (
                <li key={i} className="flex items-start text-xs text-rose-900 font-medium">
                  <span className="text-rose-500 mr-2 font-bold">•</span><span>{r}</span>
                </li>
              ))}
            </ul>
          </div>

          {qualityDiagnostic.quality_assessment?.metrics && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              {[
                { label: "Sharpness", val: qualityDiagnostic.quality_assessment.metrics.sharpness_laplacian, sub: `Min: ${qualityDiagnostic.quality_assessment.metrics.blur_threshold || 40}` },
                { label: "Resolution", val: `${qualityDiagnostic.quality_assessment.metrics.width}×${qualityDiagnostic.quality_assessment.metrics.height}`, sub: "Min: 300×200 px" },
                { label: "Brightness", val: `${qualityDiagnostic.quality_assessment.metrics.mean_brightness}/255`, sub: "Target: 30–245" },
                { label: "Contrast",   val: qualityDiagnostic.quality_assessment.metrics.contrast_std, sub: "Min: 20.0" },
              ].map(m => (
                <div key={m.label} className="p-3 bg-white/80 rounded-xl border border-rose-200">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{m.label}</p>
                  <p className="text-sm font-extrabold text-slate-800 mt-0.5">{m.val}</p>
                  <p className="text-[10px] text-slate-400">{m.sub}</p>
                </div>
              ))}
            </div>
          )}

          <div className="p-4 bg-white/90 rounded-xl border border-rose-200 space-y-2">
            <div className="flex items-center space-x-1.5 text-blue-900 font-bold text-xs uppercase tracking-wider">
              <Lightbulb className="w-4 h-4 text-amber-500" />
              <span>How to retake a clearer photo</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-700 pt-1">
              {qualityDiagnostic.recommendations?.map((tip, i) => (
                <div key={i} className="flex items-start space-x-2">
                  <span className="font-bold text-blue-600 shrink-0">{i + 1}.</span>
                  <span>{tip}</span>
                </div>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={() => { setFiles([]); setQualityDiagnostic(null); fileInputRef.current?.click(); }}
            className="w-full py-2.5 px-4 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl text-xs shadow transition flex items-center justify-center space-x-2"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retake / Upload Clearer Images</span>
          </button>
        </div>
      )}

      {/* Standard error */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start space-x-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" />
          <div>
            <p className="font-semibold">Inspection Error</p>
            <p className="text-xs text-rose-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Sample test suite */}
      <div className="mb-8 bg-blue-50/60 border border-blue-200/80 rounded-2xl p-5">
        <div className="flex items-center space-x-2 mb-3">
          <Sparkles className="w-4 h-4 text-blue-600" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-blue-900">
            Quick Sample Test Suite
          </h2>
        </div>
        <p className="text-xs text-blue-800/80 mb-4">
          Select a pre-configured label to load it into slot 1 and test the pipeline:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {sampleLabels.map(sample => (
            <button
              key={sample.id}
              type="button"
              onClick={() => handleSelectSample(sample)}
              disabled={loading}
              className="text-left p-3 bg-white rounded-xl border border-blue-200 hover:border-blue-400 hover:shadow-md transition text-slate-800 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-900 line-clamp-1">{sample.title}</span>
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${badgeCls(sample.badge)}`}>
                    {sample.badge}
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 line-clamp-2">{sample.subtitle}</p>
              </div>
              <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-blue-600 font-semibold">
                <span>Select</span><span>→</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">

        {/* ------------------------------------------------------------------ */}
        {/* Multi-image upload zone                                             */}
        {/* ------------------------------------------------------------------ */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Images className="w-3.5 h-3.5 text-slate-500" />
              Label Photos
              <span className="ml-1 text-[10px] font-semibold text-slate-400 normal-case tracking-normal">
                (up to {MAX_IMAGES} photos)
              </span>
            </label>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
              files.length === 0 ? "bg-slate-100 text-slate-500" :
              files.length < MAX_IMAGES ? "bg-blue-100 text-blue-700" :
              "bg-emerald-100 text-emerald-700"
            }`}>
              {files.length} / {MAX_IMAGES}
            </span>
          </div>

          {/* Hidden inputs */}
          <input type="file" ref={fileInputRef}   onChange={handleFileInputChange} accept="image/*" multiple className="hidden" />
          <input type="file" ref={cameraInputRef} onChange={handleFileInputChange} accept="image/*" capture="environment" className="hidden" />

          {/* Thumbnail grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {SLOT_HINTS.map((hint, slotIdx) => {
              const entry = files[slotIdx];
              const colors = COLOR_CLASSES[hint.color];
              const HintIcon = hint.icon;

              if (entry) {
                // Filled slot
                return (
                  <div
                    key={slotIdx}
                    className={`relative group rounded-xl overflow-hidden border-2 ${colors.border} shadow-sm`}
                    style={{ aspectRatio: "3/4" }}
                  >
                    <img
                      src={entry.preview}
                      alt={hint.label}
                      className="w-full h-full object-cover"
                    />
                    {/* Overlay on hover */}
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2 p-2">
                      <button
                        type="button"
                        onClick={() => { addSlotRef.current = slotIdx; fileInputRef.current?.click(); }}
                        className="text-[10px] font-bold text-white bg-white/20 hover:bg-white/30 backdrop-blur-sm px-2 py-1 rounded-lg w-full transition"
                      >
                        Replace
                      </button>
                    </div>
                    {/* Remove button */}
                    <button
                      type="button"
                      onClick={() => removeFile(entry.id)}
                      className="absolute top-1.5 right-1.5 p-0.5 bg-rose-600 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-md"
                    >
                      <X className="w-3 h-3" />
                    </button>
                    {/* Slot label */}
                    <div className={`absolute bottom-0 left-0 right-0 px-2 py-1 ${colors.bg} bg-opacity-90 backdrop-blur-sm`}>
                      <p className={`text-[9px] font-bold truncate ${colors.text}`}>{hint.label}</p>
                    </div>
                    {/* Check badge */}
                    <div className="absolute top-1.5 left-1.5">
                      <CheckCircle2 className="w-4 h-4 text-white drop-shadow" />
                    </div>
                  </div>
                );
              }

              // Empty slot
              const isNextSlot = slotIdx === files.length;
              return (
                <button
                  key={slotIdx}
                  type="button"
                  onClick={() => {
                    addSlotRef.current = slotIdx;
                    fileInputRef.current?.click();
                  }}
                  disabled={loading || slotIdx > files.length}
                  className={`relative rounded-xl border-2 border-dashed transition flex flex-col items-center justify-center gap-2 p-3 text-center
                    ${slotIdx > files.length ? "border-slate-200 bg-slate-50/50 opacity-40 cursor-not-allowed" :
                      isNextSlot ? `${colors.border} ${colors.bg} hover:shadow-md cursor-pointer` :
                      "border-slate-200 bg-slate-50 cursor-pointer hover:border-slate-400"
                    }`}
                  style={{ aspectRatio: "3/4", minHeight: "120px" }}
                >
                  <div className={`p-2 rounded-full ${isNextSlot ? colors.bg : "bg-slate-100"}`}>
                    {isNextSlot ? (
                      <HintIcon className={`w-5 h-5 ${colors.text}`} />
                    ) : (
                      <Plus className="w-5 h-5 text-slate-400" />
                    )}
                  </div>
                  <div>
                    <p className={`text-[10px] font-bold ${isNextSlot ? colors.text : "text-slate-500"}`}>
                      {hint.label}
                    </p>
                    {isNextSlot && (
                      <p className="text-[9px] text-slate-400 mt-0.5">Click to add</p>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Drop zone (visible when no files yet) */}
          {files.length === 0 && (
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => fileInputRef.current?.click()}
              className="mt-4 border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:border-blue-500 hover:bg-blue-50/30 transition cursor-pointer"
            >
              <div className="flex flex-col items-center">
                <div className="p-3 bg-blue-50 text-blue-600 rounded-full mb-3">
                  <UploadIcon className="w-8 h-8" />
                </div>
                <p className="text-sm font-semibold text-slate-700">
                  Drag & drop label photos here or click to browse
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Add up to 5 photos of different label faces — PNG, JPG, JPEG (max 15 MB each)
                </p>
                <div className="mt-4 flex flex-wrap gap-2 justify-center">
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                    className="inline-flex items-center px-3.5 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 shadow-sm"
                  >
                    <UploadIcon className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
                    Browse Photos
                  </button>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); cameraInputRef.current?.click(); }}
                    className="inline-flex items-center px-3.5 py-1.5 border border-blue-300 rounded-lg text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 shadow-sm"
                  >
                    <Camera className="w-3.5 h-3.5 mr-1.5 text-blue-600" />
                    Take Photo
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Add more button (when slots are partially filled) */}
          {files.length > 0 && files.length < MAX_IMAGES && (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="mt-3 w-full py-2 border-2 border-dashed border-blue-300 rounded-xl text-xs font-bold text-blue-700 hover:bg-blue-50 transition flex items-center justify-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Add another photo ({MAX_IMAGES - files.length} remaining)
            </button>
          )}

          {/* Multi-image tip */}
          {files.length >= 2 && (
            <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-2">
              <ScanLine className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <p className="text-xs text-emerald-800">
                <strong>{files.length} photos loaded.</strong> Fields found in any photo will be merged — 
                so FSSAI from the back label and manufacturing date from the side panel both count.
              </p>
            </div>
          )}
        </div>

        {/* Product details */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Product Name</label>
            <input
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="e.g. NutriCrunch Almond Cookies"
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">Brand / Manufacturer</label>
            <input
              type="text"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="e.g. Suncrest Foods"
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>
        </div>

        {/* Vision AI Engine Selection */}
        <div className="p-4 bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-purple-50/70 rounded-2xl border border-blue-200/80 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-blue-600 animate-pulse" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-800">
                Inspection Vision AI Engine
              </span>
            </div>
            <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-700 border border-blue-200">
              Google Gemini Powered
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {[
              {
                id: "gemini",
                title: "Gemini Multimodal AI",
                desc: "High-accuracy vision on foil, curved labels & small print (FSSAI/MRP)",
                badge: "Recommended",
                icon: Bot,
                badgeColor: "bg-blue-600 text-white",
                activeBorder: "border-blue-600 bg-white ring-2 ring-blue-500/20",
              },
              {
                id: "hybrid",
                title: "Hybrid Consensus",
                desc: "Parallel cross-validation: Gemini AI + OpenCV EasyOCR ensemble",
                badge: "Statutory Rigor",
                icon: Zap,
                badgeColor: "bg-purple-600 text-white",
                activeBorder: "border-purple-600 bg-white ring-2 ring-purple-500/20",
              },
              {
                id: "local",
                title: "Local Offline OCR",
                desc: "On-device OpenCV + EasyOCR + Tesseract pipeline",
                badge: "100% Offline",
                icon: Cpu,
                badgeColor: "bg-slate-700 text-white",
                activeBorder: "border-slate-800 bg-white ring-2 ring-slate-500/20",
              },
            ].map((eng) => {
              const Icon = eng.icon;
              const isSelected = aiEngine === eng.id;
              return (
                <button
                  key={eng.id}
                  type="button"
                  onClick={() => setAiEngine(eng.id)}
                  className={`p-3 rounded-xl border text-left transition relative flex flex-col justify-between ${
                    isSelected
                      ? `${eng.activeBorder} shadow-sm`
                      : "border-slate-200/90 bg-white/70 hover:bg-white hover:border-slate-300"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className={`p-1.5 rounded-lg ${isSelected ? "bg-blue-50 text-blue-600" : "bg-slate-100 text-slate-500"}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className={`text-[9px] font-extrabold px-2 py-0.5 rounded-full ${eng.badgeColor}`}>
                        {eng.badge}
                      </span>
                    </div>
                    <p className={`text-xs font-bold ${isSelected ? "text-slate-900" : "text-slate-700"}`}>
                      {eng.title}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1 leading-snug">
                      {eng.desc}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Food toggle */}
        <div className="flex items-center justify-between p-3.5 bg-slate-50 rounded-xl border border-slate-200">
          <div>
            <p className="text-xs font-bold text-slate-800">Food / Edible Commodity Category</p>
            <p className="text-xs text-slate-500">Enforces Rule LM-06 (Mandatory 14-digit FSSAI License Number)</p>
          </div>
          <button
            type="button"
            onClick={() => setIsFoodProduct(!isFoodProduct)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              isFoodProduct ? "bg-blue-600" : "bg-slate-300"
            }`}
          >
            <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200 ease-in-out ${
              isFoodProduct ? "translate-x-5" : "translate-x-0"
            }`} />
          </button>
        </div>

        {/* Progress */}
        {loading && (
          <div className="p-4 bg-blue-50 rounded-xl border border-blue-200 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-900">{pipelineStage}</span>
              <span className="text-xs font-extrabold text-blue-700">{progress}%</span>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="grid grid-cols-4 sm:grid-cols-5 gap-1 pt-1">
              {(aiEngine === "gemini"
                ? ["Upload", "Quality Gate", "Gemini Vision", "AI Extraction", "Rule Engine"]
                : aiEngine === "hybrid"
                ? ["Upload", "Dual Quality", "OpenCV OCR", "Gemini AI", "Consensus"]
                : PIPELINE_STAGES
              ).map((step, idx) => {
                const active = progress >= (idx + 1) * 18;
                return (
                  <div key={step} className="text-center">
                    <p className={`text-[10px] font-semibold ${active ? "text-blue-700" : "text-slate-400"}`}>
                      {step}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || files.length === 0}
          className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-md shadow-blue-500/20 disabled:opacity-50 transition flex items-center justify-center space-x-2"
        >
          <Layers className="w-4 h-4" />
          <span>
            {loading
              ? "Verifying Compliance Pipeline..."
              : files.length > 1
              ? `Execute Compliance Verification (${files.length} Photos)`
              : "Execute Compliance Verification"}
          </span>
        </button>
      </form>
    </div>
  );
}
