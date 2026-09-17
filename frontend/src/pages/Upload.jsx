import React, { useState, useRef, useCallback } from "react";
import {
  Upload as UploadIcon,
  Camera,
  AlertCircle,
  Sparkles,
  Layers,
  ShieldAlert,
  Lightbulb,
  RefreshCw,
  X,
  Images,
  ClipboardList,
  Package,
  Calendar,
  BadgeCheck,
  DollarSign,
  Bot,
  Cpu,
  Zap,
  Check,
  Sliders,
  Video,
  Film,
  RotateCw,
  Play,
  FileCheck,
  Plus
} from "lucide-react";
import { inspectionApi, API_BASE_URL } from "../api/client";

const MAX_IMAGES = 5;

// Purpose hints shown under each thumbnail slot
const SLOT_HINTS = [
  { label: "Front Label (Principal)",  sub: "Brand, Net Qty & Name",  icon: Package       },
  { label: "Back Panel (Declarations)",sub: "Packer, Mfg & Helpline",  icon: ClipboardList },
  { label: "Side / Ingredients Panel", sub: "Additives & Allergens",   icon: Layers        },
  { label: "Date & Batch Panel",       sub: "Mfg / Packing Month",     icon: Calendar      },
  { label: "MRP / Price Panel",        sub: "Incl. of all taxes",      icon: DollarSign    },
];

const PIPELINE_STAGES = [
  "Intake Verification",
  "Pre-OCR Quality Gate",
  "OpenCV Rectification",
  "Typography OCR",
  "Statutory Rule Audit",
];

export default function Upload({ user, onInspectionComplete, onCancel }) {
  // Intake mode: "multi_image" | "panorama" | "video"
  const [intakeMode, setIntakeMode]       = useState("multi_image");
  const [files, setFiles]                 = useState([]); // [{file, preview, slotIdx, id, view}]
  const [videoFile, setVideoFile]         = useState(null);
  const [videoPreview, setVideoPreview]   = useState(null);
  const [productName, setProductName]     = useState("");
  const [brand, setBrand]                 = useState("");
  const [isFoodProduct, setIsFoodProduct] = useState(true);
  const [aiEngine, setAiEngine]           = useState("gemini"); // "gemini" | "hybrid" | "local"
  const [stitchPanorama, setStitchPanorama] = useState(false);
  const [loading, setLoading]             = useState(false);
  const [progress, setProgress]           = useState(0);
  const [pipelineStage, setPipelineStage] = useState("");
  const [error, setError]                 = useState(null);
  const [qualityDiagnostic, setQualityDiagnostic] = useState(null);

  const fileInputRef   = useRef(null);
  const videoInputRef  = useRef(null);
  const cameraInputRef = useRef(null);
  const addSlotRef     = useRef(null);

  // ---------------------------------------------------------------------------
  // Pre-configured Reference Packaging Samples & SIH Benchmarks
  // ---------------------------------------------------------------------------
  const benchmarkSuites = [
    {
      id: "multi_compliant",
      title: "Multi-Angle Biscuit (100% Compliant)",
      subtitle: "Front (Qty/MRP) + Back (Packer/Lic) + Side (Ingredients & Additives)",
      mode: "multi_image",
      product: "NutriCrunch Almond Cookies",
      brand: "Suncrest Foods",
      food: true,
      badge: "Rule 6 Verified (100%)",
      badgeType: "pass",
      images: [
        { name: "nutricrunch_front.png", view: "Front Label (Principal)", slot: 0 },
        { name: "nutricrunch_back.png",  view: "Back Panel (Declarations)", slot: 1 },
        { name: "nutricrunch_side.png",  view: "Side / Ingredients Panel", slot: 2 },
      ],
    },
    {
      id: "multi_deficiencies",
      title: "Multi-Angle Choco Bar (Violations Flagged)",
      subtitle: "Missing taxes clause, missing care, missing FSSAI + synthetic dyes",
      mode: "multi_image",
      product: "ChocoDelight Dark Truffle",
      brand: "ChocoDelight",
      food: true,
      badge: "Deficiencies Flagged",
      badgeType: "fail",
      images: [
        { name: "chocobar_front.png", view: "Front Label (Principal)", slot: 0 },
        { name: "chocobar_back.png",  view: "Back Panel (Declarations)", slot: 1 },
      ],
    },
    {
      id: "panorama_bottle",
      title: "360° Cylindrical Bottle Unwrap",
      subtitle: "3 sequential overlapping scans stitched into 360° cylindrical unwrap",
      mode: "panorama",
      product: "Aero Drink Electrolyte Citrus",
      brand: "Aero Beverage Corp.",
      food: true,
      badge: "360° Cylindrical Stitch",
      badgeType: "pan",
      images: [
        { name: "cylinder_p1.png", view: "Cylinder Sector 1", slot: 0 },
        { name: "cylinder_p2.png", view: "Cylinder Sector 2", slot: 1 },
        { name: "cylinder_p3.png", view: "Cylinder Sector 3", slot: 2 },
      ],
    },
    {
      id: "video_demo",
      title: "Handheld Video Package Inspection",
      subtitle: "Continuous video clip with blur-filtered keyframe extraction",
      mode: "video",
      product: "Handheld Video Package Inspection",
      brand: "Suncrest Foods",
      food: true,
      badge: "Continuous Video Keyframing",
      badgeType: "video",
      videoUrl: `${API_BASE_URL}/sample_images/sample_inspection_video.mp4`,
    },
    {
      id: "blurry_reject",
      title: "Blurry Quality Gate Hard Reject",
      subtitle: "Sharpness below statutory threshold (Laplacian < 40)",
      mode: "multi_image",
      product: "Blurry Sample",
      brand: "QuickSnack",
      food: true,
      badge: "Hard Gate Rejection",
      badgeType: "reject",
      images: [
        { name: "blurry_label.png", view: "Front Label", slot: 0 }
      ]
    },
  ];

  // ---------------------------------------------------------------------------
  // File management (Handles specific slot clicks, multi-file intake & drops)
  // ---------------------------------------------------------------------------
  const addFiles = useCallback((newFileList, slotIdx = null) => {
    const arr = Array.from(newFileList);
    if (!arr.length) return;

    setFiles((prev) => {
      const updated = [...prev];

      if (slotIdx !== null && slotIdx !== undefined && slotIdx >= 0) {
        // User clicked a specific slot: populate starting from this slot
        arr.forEach((file, i) => {
          const targetSlot = slotIdx + i;
          if (targetSlot < MAX_IMAGES) {
            const slotHint = SLOT_HINTS[targetSlot];
            const existingIdx = updated.findIndex((f) => f.slotIdx === targetSlot);
            if (existingIdx >= 0) {
              try { URL.revokeObjectURL(updated[existingIdx].preview); } catch (_) {}
              updated.splice(existingIdx, 1);
            }
            updated.push({
              file: file,
              preview: URL.createObjectURL(file),
              slotIdx: targetSlot,
              id: `${Date.now()}_slot_${targetSlot}_${i}_${Math.random().toString(36).slice(2, 7)}`,
              view: slotHint ? slotHint.label : `Angle ${targetSlot + 1}`,
            });
          }
        });
      } else {
        // General drop or multi-file browse: populate open slots sequentially
        arr.forEach((file, i) => {
          const takenSlots = new Set(updated.map((f) => f.slotIdx));
          let targetSlot = -1;
          for (let s = 0; s < MAX_IMAGES; s++) {
            if (!takenSlots.has(s)) {
              targetSlot = s;
              break;
            }
          }
          if (targetSlot === -1 && updated.length < MAX_IMAGES) {
            targetSlot = updated.length;
          }
          if (targetSlot >= 0 && targetSlot < MAX_IMAGES) {
            const slotHint = SLOT_HINTS[targetSlot];
            updated.push({
              file: file,
              preview: URL.createObjectURL(file),
              slotIdx: targetSlot,
              id: `${Date.now()}_slot_${targetSlot}_${i}_${Math.random().toString(36).slice(2, 7)}`,
              view: slotHint ? slotHint.label : `Angle ${targetSlot + 1}`,
            });
          }
        });
      }

      updated.sort((a, b) => a.slotIdx - b.slotIdx);
      return updated.slice(0, MAX_IMAGES);
    });
    setError(null);
    setQualityDiagnostic(null);
  }, []);

  const removeFile = useCallback((id) => {
    setFiles((prev) => {
      const entry = prev.find((f) => f.id === id);
      if (entry) {
        try { URL.revokeObjectURL(entry.preview); } catch (_) {}
      }
      return prev.filter((f) => f.id !== id);
    });
  }, []);

  const handleFileInputChange = (e) => {
    if (e.target.files?.length) {
      addFiles(e.target.files, addSlotRef.current);
    }
    addSlotRef.current = null;
    e.target.value = "";
  };

  const handleVideoInputChange = (e) => {
    if (e.target.files?.length) {
      const file = e.target.files[0];
      setVideoFile(file);
      if (videoPreview) {
        try { URL.revokeObjectURL(videoPreview); } catch (_) {}
      }
      setVideoPreview(URL.createObjectURL(file));
      setError(null);
    }
    e.target.value = "";
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    if (intakeMode === "video") {
      if (e.dataTransfer.files?.length) {
        const file = e.dataTransfer.files[0];
        setVideoFile(file);
        setVideoPreview(URL.createObjectURL(file));
      }
    } else {
      if (e.dataTransfer.files?.length) {
        addFiles(e.dataTransfer.files, addSlotRef.current);
        addSlotRef.current = null;
      }
    }
  }, [intakeMode, addFiles]);

  const handleDragOver = (e) => e.preventDefault();

  // Guard for Viewer Role
  if (user?.role === "viewer") {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <div className="w-16 h-16 bg-amber-500/10 text-amber-700 border border-amber-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-sm">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-display font-bold text-slate-900">
          Inspection Mode Restricted • Read-Only Clearance
        </h2>
        <p className="text-slate-500 text-xs sm:text-sm mt-2 max-w-md mx-auto leading-relaxed">
          Public accounts do not possess statutory field inspection authority under Rule 6. You can browse verified audit records and download official certified reports.
        </p>
        <button
          onClick={onCancel}
          className="mt-6 px-5 py-2.5 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-bold transition shadow-md cursor-pointer"
        >
          Return to Public Registry
        </button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Load SIH Benchmark Harness Sample
  // ---------------------------------------------------------------------------
  const handleSelectBenchmark = async (suite) => {
    try {
      setLoading(true);
      setError(null);
      setQualityDiagnostic(null);
      setIntakeMode(suite.mode);
      setProductName(suite.product);
      setBrand(suite.brand);
      setIsFoodProduct(suite.food);

      if (suite.mode === "video") {
        setPipelineStage("Loading benchmark video sample...");
        const response = await fetch(suite.videoUrl);
        const blob = await response.blob();
        const vFile = new File([blob], "sample_inspection_video.mp4", { type: "video/mp4" });
        setVideoFile(vFile);
        if (videoPreview) {
          try { URL.revokeObjectURL(videoPreview); } catch (_) {}
        }
        setVideoPreview(URL.createObjectURL(vFile));
        setFiles([]);
      } else {
        setPipelineStage("Loading multi-angle packaging images...");
        const loadedFiles = [];
        for (let i = 0; i < suite.images.length; i++) {
          const item = suite.images[i];
          const imgUrl = `${API_BASE_URL}/sample_images/${item.name}`;
          const res = await fetch(imgUrl);
          const blob = await res.blob();
          const f = new File([blob], item.name, { type: "image/png" });
          loadedFiles.push({
            file: f,
            preview: URL.createObjectURL(f),
            slotIdx: item.slot,
            id: `benchmark_${Date.now()}_${i}`,
            view: item.view,
          });
        }
        setFiles(loadedFiles);
        setVideoFile(null);
        if (videoPreview) {
          try { URL.revokeObjectURL(videoPreview); } catch (_) {}
          setVideoPreview(null);
        }
        if (suite.mode === "panorama") {
          setStitchPanorama(true);
        }
      }
    } catch {
      setError("Could not load benchmark sample. Please upload packaging photos manually.");
    } finally {
      setLoading(false);
      setPipelineStage("");
    }
  };

  // ---------------------------------------------------------------------------
  // Submit inspection pipeline (Routes to Multi-Image, Panorama, or Video)
  // ---------------------------------------------------------------------------
  const handleSubmit = async (e) => {
    e?.preventDefault();

    if (intakeMode === "video") {
      if (!videoFile) {
        setError("Please select or record a video of the packaged commodity.");
        return;
      }
    } else {
      if (files.length === 0) {
        setError("Please capture or upload at least one packaging face photo.");
        return;
      }
    }

    setLoading(true);
    setError(null);
    setQualityDiagnostic(null);

    const stages = intakeMode === "video" ? [
      { pct: 15, label: "Stage 1/5: Ingesting high-definition video inspection stream..." },
      { pct: 35, label: "Stage 2/5: Temporal sampling & Laplacian blur rejection..." },
      { pct: 55, label: "Stage 3/5: Histogram duplicate rejection & viewpoint estimation..." },
      { pct: 75, label: "Stage 4/5: Multi-view statutory OCR & Product Intelligence extraction..." },
      { pct: 92, label: "Stage 5/5: Legal Metrology Rule Evaluation (Rules 2011)..." },
    ] : intakeMode === "panorama" ? [
      { pct: 15, label: "Stage 1/5: Loading overlapping package angle captures..." },
      { pct: 35, label: "Stage 2/5: OpenCV ORB feature extraction & cylindrical unwrap stitching..." },
      { pct: 55, label: "Stage 3/5: Unwrapped surface text extraction & multi-panel fusion..." },
      { pct: 75, label: "Stage 4/5: Additives, allergens & nutritional intelligence audit..." },
      { pct: 92, label: "Stage 5/5: Generating 7-Section Statutory Compliance Report..." },
    ] : aiEngine === "gemini" ? [
      { pct: 15, label: "Stage 1/4: Ingesting packaging label photos & view metadata..." },
      { pct: 35, label: "Stage 2/4: Gemini Multimodal Visual Quality & Surface Audit..." },
      { pct: 70, label: "Stage 3/4: Gemini AI Statutory Field Extraction & Additive Decoding..." },
      { pct: 92, label: "Stage 4/4: Legal Metrology Rule Compliance Scoring & Evidence Linking..." },
    ] : [
      { pct: 12, label: "Stage 1/5: Ingesting packaging photos..." },
      { pct: 30, label: "Stage 2/5: Dual Quality Gate & OpenCV Preprocessing..." },
      { pct: 55, label: "Stage 3/5: Multi-Variant OCR & Structured Field Merge..." },
      { pct: 75, label: "Stage 4/5: Product Intelligence: INS Additive & Allergen Detection..." },
      { pct: 92, label: "Stage 5/5: Legal Metrology Rule Engine (Rules 2011)..." },
    ];

    const delays = [0, 600, 1500, 2800, 4400];
    const timers = stages.map((s, i) =>
      setTimeout(() => { setProgress(s.pct); setPipelineStage(s.label); }, delays[i] || 1000 * i)
    );

    try {
      let result;

      if (intakeMode === "video") {
        const formData = new FormData();
        formData.append("video", videoFile);
        formData.append("product_name", productName.trim() || "Video Inspected Package");
        formData.append("brand", brand.trim() || "Unbranded");
        formData.append("category", isFoodProduct ? "food" : "general");
        formData.append("sample_rate", "1.5");
        formData.append("max_frames", "8");
        result = await inspectionApi.uploadVideo(formData);
      } else if (intakeMode === "panorama") {
        const formData = new FormData();
        files.forEach((entry) => formData.append("images", entry.file));
        formData.append("product_name", productName.trim() || "Cylindrical Package");
        formData.append("brand", brand.trim() || "Unbranded");
        formData.append("category", isFoodProduct ? "food" : "general");
        result = await inspectionApi.uploadPanorama(formData);
      } else {
        const formData = new FormData();
        files.forEach((entry) => {
          formData.append("images", entry.file);
        });
        const viewsList = files.map((f, idx) => f.view || SLOT_HINTS[idx]?.label || `Angle ${idx + 1}`);
        formData.append("views", JSON.stringify(viewsList));
        formData.append("product_name", productName.trim() || "Packaged Product");
        formData.append("brand", brand.trim() || "Unbranded");
        formData.append("is_food_product", isFoodProduct ? "true" : "false");
        formData.append("ai_engine", aiEngine);
        if (stitchPanorama) {
          formData.append("stitch_panorama", "true");
        }
        result = await inspectionApi.upload(formData);
      }

      timers.forEach(clearTimeout);
      setProgress(100);
      setPipelineStage("Inspection completed successfully!");

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
          "Failed to process inspection. Please verify input data and try again.";
        setError(typeof msg === "string" ? msg : JSON.stringify(msg));
      }
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200/90 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-display font-extrabold text-slate-900 tracking-tight">
              Packaging Compliance Intake Studio
            </h1>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
              Form LM-01 Intake
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Statutory AI audit supporting <strong>Multi-Angle Photos</strong>, <strong>360° Cylindrical Panorama</strong>, and <strong>Continuous Video</strong> with Product Intelligence decoding.
          </p>
        </div>
        <div className="flex items-center space-x-2 self-start sm:self-auto">
          <button
            type="button"
            onClick={onCancel}
            className="px-3.5 py-1.5 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 transition cursor-pointer"
          >
            Cancel
          </button>
        </div>
      </div>

      {/* Hard Gate Quality Rejection Card */}
      {qualityDiagnostic && (
        <div className="p-6 rounded-2xl bg-rose-50/90 border-2 border-rose-300 shadow-card space-y-5 animate-in fade-in slide-in-from-top-3 duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-rose-200/80 pb-4">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-rose-600 text-white rounded-xl shadow-xs">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-base font-display font-bold text-rose-950">
                  Pre-OCR Quality Gate: Rejection Triggered
                </h2>
                <p className="text-xs text-rose-700">
                  Image legibility failed statutory threshold. OCR processing halted to prevent evidentiary inaccuracies.
                </p>
              </div>
            </div>
            <span className="self-start sm:self-auto text-xs font-mono font-bold px-3 py-1 bg-rose-200 text-rose-900 rounded-full">
              Hard Gate Lock
            </span>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-bold uppercase tracking-wider text-rose-900">
              Rejection Findings
            </p>
            <ul className="space-y-1.5">
              {qualityDiagnostic.rejection_reasons?.map((r, i) => (
                <li key={i} className="flex items-start text-xs text-rose-900 font-medium">
                  <span className="text-rose-500 mr-2 font-bold">•</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>

          {qualityDiagnostic.quality_assessment?.metrics && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              {[
                { label: "Laplacian Sharpness", val: qualityDiagnostic.quality_assessment.metrics.sharpness_laplacian, sub: `Min: ${qualityDiagnostic.quality_assessment.metrics.blur_threshold || 40}` },
                { label: "Resolution", val: `${qualityDiagnostic.quality_assessment.metrics.width}×${qualityDiagnostic.quality_assessment.metrics.height}`, sub: "Min: 300×200 px" },
                { label: "Brightness", val: `${qualityDiagnostic.quality_assessment.metrics.mean_brightness}/255`, sub: "Target: 30–245" },
                { label: "Contrast Variance", val: qualityDiagnostic.quality_assessment.metrics.contrast_std, sub: "Min: 20.0" },
              ].map((m) => (
                <div key={m.label} className="p-3 bg-white/90 rounded-xl border border-rose-200/90 shadow-2xs">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{m.label}</p>
                  <p className="text-sm font-display font-black text-slate-900 mt-0.5 tabular-nums">{m.val}</p>
                  <p className="text-[10px] text-slate-400 font-mono">{m.sub}</p>
                </div>
              ))}
            </div>
          )}

          <div className="p-4 bg-white/90 rounded-xl border border-rose-200/90 space-y-2">
            <div className="flex items-center space-x-1.5 text-blue-900 font-bold text-xs uppercase tracking-wider">
              <Lightbulb className="w-4 h-4 text-amber-500" />
              <span>Guidelines for Retaking Packaging Photo</span>
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
            className="w-full py-2.5 px-4 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl text-xs shadow-sm transition flex items-center justify-center space-x-2 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retake or Upload Higher-Resolution Photos</span>
          </button>
        </div>
      )}

      {/* Standard Error Notice */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start space-x-3 text-rose-800 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
          <div>
            <p className="font-bold">Inspection Intake Notice</p>
            <p className="text-rose-700 mt-0.5 leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* Quick Reference Statutory Benchmark Harness (SIH Judge 1-Click Demo) */}
      <div className="bg-slate-900 text-white rounded-2xl p-5 shadow-card border border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <h2 className="text-xs font-display font-bold uppercase tracking-wider text-slate-200">
              SIH Statutory Benchmark Harness • 1-Click Evaluation
            </h2>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-900/60 text-blue-300 border border-blue-700/50">
            Judge Demo Mode
          </span>
        </div>
        <p className="text-xs text-slate-400 mb-4">
          Click any pre-configured statutory benchmark below to automatically load multi-angle, panorama, or video inspection sets:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {benchmarkSuites.map((sample) => (
            <button
              key={sample.id}
              type="button"
              onClick={() => handleSelectBenchmark(sample)}
              disabled={loading}
              className="text-left p-3.5 bg-slate-800/80 hover:bg-slate-800 rounded-xl border border-slate-700/80 hover:border-blue-500/50 transition flex flex-col justify-between group cursor-pointer"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-100 line-clamp-1 group-hover:text-blue-300 transition">
                    {sample.title}
                  </span>
                </div>
                <span className={`inline-block text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                  sample.badgeType === "pass" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" :
                  sample.badgeType === "fail" ? "bg-rose-500/20 text-rose-300 border border-rose-500/30" :
                  sample.badgeType === "pan" ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30" :
                  sample.badgeType === "video" ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30" :
                  "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                }`}>
                  {sample.badge}
                </span>
                <p className="text-[10px] text-slate-400 mt-2 line-clamp-2">
                  {sample.subtitle}
                </p>
              </div>
              <div className="mt-3 pt-2 border-t border-slate-700/60 flex items-center justify-between text-[10px] text-blue-400 font-semibold">
                <span>Load Suite</span>
                <span className="group-hover:translate-x-0.5 transition">→</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Intake Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200/90 p-6 sm:p-8 shadow-card space-y-8">
        
        {/* Intake Mode Switcher */}
        <div>
          <label className="text-xs font-display font-bold text-slate-800 uppercase tracking-wider block mb-2.5">
            Select Packaging Intake Modality
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              {
                id: "multi_image",
                title: "Multi-Angle Packaging Dock",
                desc: "1–5 statutory face photos (Front, Back, Side, Mfg, MRP) fused into single unified declaration session.",
                icon: Images,
              },
              {
                id: "panorama",
                title: "360° Cylindrical / Box Panorama",
                desc: "Sequential overlapping photos stitched into unwrapped cylindrical plane for curved bottles & jars.",
                icon: RotateCw,
              },
              {
                id: "video",
                title: "Continuous Video Inspection",
                desc: "Handheld package rotation video with automated blur-gating, duplicate rejection & keyframe extraction.",
                icon: Film,
              },
            ].map((m) => {
              const Icon = m.icon;
              const isSel = intakeMode === m.id;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => {
                    setIntakeMode(m.id);
                    setError(null);
                  }}
                  className={`p-4 rounded-xl border text-left transition relative flex flex-col justify-between cursor-pointer ${
                    isSel
                      ? "border-blue-600 bg-blue-50/20 ring-2 ring-blue-500/20 shadow-xs"
                      : "border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300"
                  }`}
                >
                  <div>
                    <div className="flex items-center space-x-2 mb-2">
                      <div className={`p-2 rounded-xl ${isSel ? "bg-navy-900 text-white" : "bg-slate-100 text-slate-600"}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className={`text-xs font-display font-bold ${isSel ? "text-slate-950" : "text-slate-800"}`}>
                        {m.title}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 leading-snug">
                      {m.desc}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Hidden Inputs */}
        <input type="file" ref={fileInputRef} onChange={handleFileInputChange} accept="image/*" multiple className="hidden" />
        <input type="file" ref={cameraInputRef} onChange={handleFileInputChange} accept="image/*" capture="environment" className="hidden" />
        <input type="file" ref={videoInputRef} onChange={handleVideoInputChange} accept="video/mp4,video/quicktime,video/webm" className="hidden" />

        {/* MODALITY 1: Multi-Angle Intake Dock */}
        {intakeMode === "multi_image" && (
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className="space-y-4"
          >
            {/* Intake Header with Active Status & Global Actions */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 p-4 rounded-2xl border border-slate-200">
              <div>
                <label className="text-xs font-display font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Images className="w-4 h-4 text-blue-600" />
                  Packaging Angle Intake Dock (1–5 Facets)
                </label>
                <p className="text-xs text-slate-500 mt-0.5">
                  Upload up to 5 label facets. Declarations, ingredients & FSSAI across all panels are cross-referenced & deduplicated.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className={`text-xs font-mono font-bold px-3 py-1 rounded-full border ${
                  files.length === 0 ? "bg-white text-slate-600 border-slate-200" :
                  files.length < MAX_IMAGES ? "bg-blue-50 text-blue-800 border-blue-200" :
                  "bg-emerald-50 text-emerald-800 border-emerald-200"
                }`}>
                  {files.length} / {MAX_IMAGES} Angles Loaded
                </span>

                <button
                  type="button"
                  onClick={() => {
                    addSlotRef.current = null;
                    fileInputRef.current?.click();
                  }}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-xs transition flex items-center gap-1.5 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Upload Multiple Photos</span>
                </button>

                {files.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setFiles([])}
                    className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition cursor-pointer font-semibold"
                  >
                    Clear All
                  </button>
                )}
              </div>
            </div>

            {/* Prominent Dropzone Banner when 0 or few files are loaded */}
            {files.length === 0 && (
              <div
                onClick={() => {
                  addSlotRef.current = null;
                  fileInputRef.current?.click();
                }}
                className="border-2 border-dashed border-blue-300 hover:border-blue-500 rounded-2xl p-6 text-center bg-blue-50/20 hover:bg-blue-50/40 transition cursor-pointer group"
              >
                <div className="flex flex-col items-center justify-center">
                  <div className="p-3 bg-blue-500/10 text-blue-700 border border-blue-500/20 rounded-2xl mb-2 group-hover:scale-105 transition">
                    <Images className="w-6 h-6" />
                  </div>
                  <p className="text-xs sm:text-sm font-display font-bold text-slate-800">
                    Drag & Drop 2 to 5 packaging photos here, or click to browse
                  </p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Select multiple files at once (Ctrl+Click in file dialog) to populate Front, Back & Side panels automatically.
                  </p>
                </div>
              </div>
            )}

            {/* 5-Slot Intake Dock Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5 pt-1">
              {SLOT_HINTS.map((hint, slotIdx) => {
                const entry = files.find((f) => f.slotIdx === slotIdx);
                const HintIcon = hint.icon;

                if (entry) {
                  return (
                    <div
                      key={slotIdx}
                      className="relative group rounded-xl overflow-hidden border-2 border-blue-500 shadow-sm bg-slate-900"
                      style={{ aspectRatio: "3/4" }}
                    >
                      <img
                        src={entry.preview}
                        alt={hint.label}
                        className="w-full h-full object-cover"
                      />
                      
                      {/* Hover Overlay */}
                      <div className="absolute inset-0 bg-slate-950/70 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2 p-2 backdrop-blur-xs">
                        <button
                          type="button"
                          onClick={() => { addSlotRef.current = slotIdx; fileInputRef.current?.click(); }}
                          className="text-[10px] font-bold text-white bg-white/20 hover:bg-white/30 px-2.5 py-1.5 rounded-lg w-full transition cursor-pointer"
                        >
                          Replace Angle
                        </button>
                        <button
                          type="button"
                          onClick={() => removeFile(entry.id)}
                          className="text-[10px] font-bold text-rose-300 hover:text-rose-100 bg-rose-600/60 hover:bg-rose-600 px-2.5 py-1.5 rounded-lg w-full transition cursor-pointer"
                        >
                          Remove
                        </button>
                      </div>

                      {/* Remove Action Button */}
                      <button
                        type="button"
                        onClick={() => removeFile(entry.id)}
                        className="absolute top-1.5 right-1.5 p-1 bg-rose-600 hover:bg-rose-700 text-white rounded-full opacity-0 group-hover:opacity-100 transition shadow-md cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>

                      {/* Verified Status Badge */}
                      <div className="absolute top-1.5 left-1.5">
                        <span className="px-1.5 py-0.5 rounded-md bg-emerald-600 text-white text-[9px] font-bold flex items-center gap-1 shadow-xs">
                          <Check className="w-2.5 h-2.5" />
                          <span>Angle {slotIdx + 1}</span>
                        </span>
                      </div>

                      {/* Slot Label Footer */}
                      <div className="absolute bottom-0 left-0 right-0 px-2.5 py-1.5 bg-navy-950/90 backdrop-blur-xs border-t border-slate-700/50">
                        <p className="text-[10px] font-bold text-white truncate">{entry.view || hint.label}</p>
                        <p className="text-[9px] text-slate-400 truncate">{hint.sub}</p>
                      </div>
                    </div>
                  );
                }

                // Empty Slot — Clickable at any time
                return (
                  <button
                    key={slotIdx}
                    type="button"
                    onClick={() => {
                      addSlotRef.current = slotIdx;
                      fileInputRef.current?.click();
                    }}
                    disabled={loading}
                    className="relative rounded-xl border border-dashed border-slate-300 hover:border-blue-500 bg-slate-50/70 hover:bg-blue-50/30 transition flex flex-col items-center justify-center gap-2 p-3 text-center cursor-pointer group"
                    style={{ aspectRatio: "3/4", minHeight: "130px" }}
                  >
                    <div className="p-2.5 rounded-xl bg-slate-200 group-hover:bg-blue-600 group-hover:text-white text-slate-600 transition shadow-2xs">
                      <HintIcon className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-slate-700 group-hover:text-blue-900 transition">
                        {hint.label}
                      </p>
                      <p className="text-[9px] text-slate-400 mt-0.5 line-clamp-1">
                        + Add {hint.sub}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Optional Panorama Stitching Checkbox in Multi-Image */}
            <div className="mt-2 flex items-center space-x-2 text-xs text-slate-700">
              <input
                type="checkbox"
                id="stitch_pan_check"
                checked={stitchPanorama}
                onChange={(e) => setStitchPanorama(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="stitch_pan_check" className="font-semibold cursor-pointer">
                Also attempt OpenCV 360° Cylindrical Panorama stitch across these angle captures
              </label>
            </div>
          </div>
        )}

        {/* MODALITY 2: 360° Panorama Mode */}
        {intakeMode === "panorama" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-xs font-display font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <RotateCw className="w-4 h-4 text-indigo-600" />
                  360° Cylindrical / Box Panorama Stitcher
                </label>
                <p className="text-xs text-slate-500 mt-0.5">
                  Upload 2 to 6 sequential overlapping photos (min 50% overlap). OpenCV matches feature anchors to unwrap the complete continuous surface.
                </p>
              </div>
              <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200">
                {files.length} Overlapping Photos
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {files.map((entry, idx) => (
                <div
                  key={entry.id}
                  className="relative group rounded-xl overflow-hidden border border-slate-300 shadow-2xs bg-slate-900 aspect-4/3"
                >
                  <img src={entry.preview} alt={`Sector ${idx + 1}`} className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => removeFile(entry.id)}
                    className="absolute top-1.5 right-1.5 p-1 bg-rose-600 text-white rounded-full opacity-0 group-hover:opacity-100 transition shadow-md cursor-pointer"
                  >
                    <X className="w-3 h-3" />
                  </button>
                  <div className="absolute bottom-0 left-0 right-0 px-2 py-1 bg-navy-950/80 text-[10px] text-white font-mono">
                    Sector {idx + 1}
                  </div>
                </div>
              ))}

              {files.length < 6 && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="rounded-xl border-2 border-dashed border-indigo-300 hover:border-indigo-500 bg-indigo-50/30 hover:bg-indigo-50/60 transition flex flex-col items-center justify-center p-4 text-center cursor-pointer aspect-4/3"
                >
                  <RotateCw className="w-5 h-5 text-indigo-600 mb-1" />
                  <span className="text-xs font-bold text-indigo-900">+ Add Overlapping Sector</span>
                  <span className="text-[10px] text-indigo-600">Overlap min. 50%</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* MODALITY 3: Continuous Video Mode */}
        {intakeMode === "video" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-xs font-display font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Film className="w-4 h-4 text-cyan-600" />
                  Continuous Video Inspection & Keyframe Extractor
                </label>
                <p className="text-xs text-slate-500 mt-0.5">
                  Record or upload a 3–15 second video slowly rotating the packaged commodity. OpenCV filters blur, rejects duplicate angles, and extracts sharp keyframes.
                </p>
              </div>
              <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-full bg-cyan-50 text-cyan-800 border border-cyan-200">
                1.5 FPS Auto-Sampling
              </span>
            </div>

            {videoPreview ? (
              <div className="relative rounded-2xl overflow-hidden border border-slate-300 bg-slate-950 max-w-lg mx-auto shadow-md">
                <video src={videoPreview} controls className="w-full max-h-64 object-contain" />
                <div className="p-3 bg-navy-950 flex items-center justify-between text-xs text-slate-300 border-t border-slate-800">
                  <div className="flex items-center space-x-2">
                    <Video className="w-4 h-4 text-cyan-400" />
                    <span className="truncate max-w-xs">{videoFile?.name || "Recorded Video Stream"}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setVideoFile(null);
                      setVideoPreview(null);
                    }}
                    className="text-rose-400 hover:text-rose-300 font-semibold cursor-pointer"
                  >
                    Remove Video
                  </button>
                </div>
              </div>
            ) : (
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onClick={() => videoInputRef.current?.click()}
                className="border-2 border-dashed border-cyan-300 hover:border-cyan-500 rounded-2xl p-8 text-center bg-cyan-50/20 hover:bg-cyan-50/40 transition cursor-pointer"
              >
                <div className="flex flex-col items-center">
                  <div className="p-3 bg-cyan-500/10 text-cyan-700 border border-cyan-500/20 rounded-2xl mb-3">
                    <Video className="w-7 h-7" />
                  </div>
                  <p className="text-sm font-display font-bold text-slate-800">
                    Drag & Drop packaging video here or click to browse
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Supports MP4, MOV, WEBM (3 to 15 seconds, up to 100 MB)
                  </p>
                  <div className="mt-4 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); videoInputRef.current?.click(); }}
                      className="px-4 py-2 bg-white border border-cyan-300 hover:bg-cyan-50 text-cyan-800 rounded-xl text-xs font-bold shadow-2xs transition cursor-pointer"
                    >
                      Select Video File
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Commodity Identification Details */}
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <h2 className="text-xs font-display font-bold text-slate-800 uppercase tracking-wider">
              Commodity Identification Details
            </h2>
            <span className="text-[10px] text-slate-400">(Optional - auto-detected by OCR if blank)</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Product Name / Commodity Description
              </label>
              <input
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="e.g. NutriCrunch Almond Cookies"
                className="w-full px-3.5 py-2.5 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Brand / Packer Entity
              </label>
              <input
                type="text"
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                placeholder="e.g. Suncrest Foods Ltd."
                className="w-full px-3.5 py-2.5 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-600 focus:border-blue-600 outline-none transition"
              />
            </div>
          </div>
        </div>

        {/* Vision AI Engine Selection */}
        {intakeMode === "multi_image" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-blue-600" />
                <span className="text-xs font-display font-bold uppercase tracking-wider text-slate-800">
                  Inspection Inference Architecture
                </span>
              </div>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                Statutory Engine Selection
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                {
                  id: "gemini",
                  title: "Gemini Multimodal Vision AI",
                  desc: "High-precision multimodal parsing on reflective foil, curvature & miniature typography.",
                  badge: "Recommended",
                  icon: Bot,
                  badgeStyle: "bg-blue-600 text-white",
                  activeBorder: "border-blue-600 bg-blue-50/20 ring-2 ring-blue-500/20",
                },
                {
                  id: "hybrid",
                  title: "Hybrid Consensus Ensemble",
                  desc: "Parallel consensus fusion combining Gemini AI with local OpenCV EasyOCR pipelines.",
                  badge: "Statutory Rigor",
                  icon: Zap,
                  badgeStyle: "bg-purple-700 text-white",
                  activeBorder: "border-purple-600 bg-purple-50/20 ring-2 ring-purple-500/20",
                },
                {
                  id: "local",
                  title: "Air-Gapped Offline OCR",
                  desc: "100% on-device local OpenCV + EasyOCR + Tesseract text region detection.",
                  badge: "Local Air-Gapped",
                  icon: Cpu,
                  badgeStyle: "bg-slate-800 text-white",
                  activeBorder: "border-slate-800 bg-slate-100 ring-2 ring-slate-400/20",
                },
              ].map((eng) => {
                const Icon = eng.icon;
                const isSelected = aiEngine === eng.id;
                return (
                  <button
                    key={eng.id}
                    type="button"
                    onClick={() => setAiEngine(eng.id)}
                    className={`p-4 rounded-xl border text-left transition relative flex flex-col justify-between cursor-pointer ${
                      isSelected
                        ? `${eng.activeBorder} shadow-card`
                        : "border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className={`p-2 rounded-xl ${isSelected ? "bg-navy-900 text-white" : "bg-slate-100 text-slate-600"}`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${eng.badgeStyle}`}>
                          {eng.badge}
                        </span>
                      </div>
                      <p className={`text-xs font-display font-bold ${isSelected ? "text-slate-950" : "text-slate-800"}`}>
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
        )}

        {/* Food / Edible Commodity Category Toggle */}
        <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
          <div>
            <p className="text-xs font-bold text-slate-900">Food / Edible Commodity Category</p>
            <p className="text-xs text-slate-500 mt-0.5">
              Enforces Rule LM-06 (14-Digit FSSAI) and activates the Product Intelligence & Additives Engine
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsFoodProduct(!isFoodProduct)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              isFoodProduct ? "bg-blue-600" : "bg-slate-300"
            }`}
          >
            <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition duration-200 ease-in-out ${
              isFoodProduct ? "translate-x-5" : "translate-x-0"
            }`} />
          </button>
        </div>

        {/* Real-time Pipeline Progress */}
        {loading && (
          <div className="p-5 bg-navy-950 text-white rounded-2xl border border-navy-800 space-y-3 shadow-card">
            <div className="flex items-center justify-between">
              <span className="text-xs font-display font-bold text-blue-300">{pipelineStage}</span>
              <span className="text-xs font-mono font-extrabold text-white tabular-nums">{progress}%</span>
            </div>
            <div className="w-full bg-navy-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="grid grid-cols-4 sm:grid-cols-5 gap-1 pt-1">
              {(intakeMode === "video"
                ? ["Video Ingest", "Blur Gate", "Keyframing", "OCR Extraction", "Rule Audit"]
                : intakeMode === "panorama"
                ? ["Angle Ingest", "ORB Matching", "Unwrap Stitch", "OCR Extraction", "Report"]
                : aiEngine === "gemini"
                ? ["Intake", "Visual Gate", "Gemini AI", "Rule Audit", "Report"]
                : PIPELINE_STAGES
              ).map((step, idx) => {
                const active = progress >= (idx + 1) * 18;
                return (
                  <div key={step} className="text-center">
                    <p className={`text-[10px] font-semibold ${active ? "text-blue-400 font-bold" : "text-slate-500"}`}>
                      {step}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Submit Execution Button */}
        <button
          type="submit"
          disabled={loading || (intakeMode === "video" ? !videoFile : files.length === 0)}
          className="w-full py-3.5 px-5 bg-blue-600 hover:bg-blue-700 text-white font-display font-bold rounded-xl shadow-md shadow-blue-500/20 active:scale-[0.99] disabled:opacity-50 transition flex items-center justify-center space-x-2 cursor-pointer"
        >
          <Layers className="w-4 h-4" />
          <span>
            {loading
              ? "Executing Statutory Inspection Pipeline..."
              : intakeMode === "video"
              ? "Execute Video Keyframe & Statutory Audit"
              : intakeMode === "panorama"
              ? `Execute 360° Panorama Stitch & Audit (${files.length} Sectors)`
              : files.length > 1
              ? `Execute Statutory Verification (${files.length} Angles Loaded)`
              : "Execute Statutory Verification"}
          </span>
        </button>
      </form>
    </div>
  );
}
