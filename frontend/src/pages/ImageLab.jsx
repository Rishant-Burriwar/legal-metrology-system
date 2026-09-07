import React, { useState, useRef, useCallback } from "react";
import { FlaskConical, Upload, Loader2, ZoomIn, ZoomOut, Eye, ChevronDown, ChevronUp, BarChart3, Layers, ImageIcon, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { API_BASE_URL } from "../api/client";

export default function ImageLab() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [activeSection, setActiveSection] = useState("stages");
  const [selectedVariant, setSelectedVariant] = useState(null);
  const [compareMode, setCompareMode] = useState(false);
  const [expandedStage, setExpandedStage] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setPreview(URL.createObjectURL(file));
    setResult(null);
    setError(null);
    setSelectedVariant(null);
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
      setResult(null);
      setError(null);
      setSelectedVariant(null);
    }
  }, []);

  const handleAnalyze = async () => {
    if (!selectedFile) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("image", selectedFile);

      const token = localStorage.getItem("lm_token");
      const res = await fetch(`${API_BASE_URL}/preprocess/analyze`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
      setSelectedVariant("variant_a");
    } catch (err) {
      setError(err.message || "Failed to analyze image");
    } finally {
      setLoading(false);
    }
  };

  const qualityColor = (score) => {
    if (score >= 70) return "text-emerald-400";
    if (score >= 40) return "text-amber-400";
    return "text-rose-400";
  };

  const metricBar = (value, max, color = "blue") => {
    const pct = Math.min(100, (value / max) * 100);
    const colors = {
      blue: "bg-blue-500",
      green: "bg-emerald-500",
      amber: "bg-amber-500",
      rose: "bg-rose-500",
    };
    return (
      <div className="w-full bg-slate-700/50 rounded-full h-1.5 mt-1">
        <div className={`${colors[color] || colors.blue} h-1.5 rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-br from-violet-600 to-blue-600 p-2.5 rounded-xl shadow-lg shadow-violet-500/20">
              <FlaskConical className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Image Preprocessing Lab</h1>
              <p className="text-xs text-slate-400">Visualize every CV pipeline stage • See what OCR receives</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Upload Zone */}
        {!result && (
          <div className="max-w-2xl mx-auto">
            <div
              onClick={() => fileInputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              className={`relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-300 ${
                preview
                  ? "border-blue-500/50 bg-slate-800/30"
                  : "border-slate-700 hover:border-violet-500/60 hover:bg-slate-800/20 bg-slate-900/30"
              }`}
            >
              <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileSelect} className="hidden" />

              {preview ? (
                <div className="space-y-4">
                  <img src={preview} alt="Selected" className="max-h-64 mx-auto rounded-lg shadow-2xl shadow-black/40 object-contain" />
                  <p className="text-sm text-slate-400">{selectedFile?.name} • {(selectedFile?.size / 1024).toFixed(1)} KB</p>
                  <p className="text-xs text-slate-500">Click or drop to change image</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-slate-800 flex items-center justify-center">
                    <ImageIcon className="w-8 h-8 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-base font-medium text-slate-300">Drop a product label image here</p>
                    <p className="text-sm text-slate-500 mt-1">or click to browse • PNG, JPG, WebP</p>
                  </div>
                </div>
              )}
            </div>

            {preview && (
              <button
                onClick={handleAnalyze}
                disabled={loading}
                className="mt-5 w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white py-3.5 px-6 rounded-xl font-semibold text-sm transition-all duration-300 shadow-lg shadow-violet-500/20 hover:shadow-violet-500/40 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Analyzing Pipeline Stages...</span>
                  </>
                ) : (
                  <>
                    <FlaskConical className="w-4 h-4" />
                    <span>Analyze Preprocessing Pipeline</span>
                  </>
                )}
              </button>
            )}

            {error && (
              <div className="mt-4 bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 text-sm text-rose-300">
                <div className="flex items-center space-x-2">
                  <XCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Top Bar: Quality Summary + Reset */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-800/40 border border-slate-700/60 rounded-2xl p-4 backdrop-blur-sm">
              <div className="flex items-center space-x-4">
                <div className={`text-3xl font-bold ${qualityColor(result.quality_assessment.quality_score)}`}>
                  {result.quality_assessment.quality_score}
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-200">Quality Score</div>
                  <div className="flex items-center space-x-1.5 mt-0.5">
                    {result.quality_assessment.is_acceptable ? (
                      <><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /><span className="text-xs text-emerald-400">Acceptable for OCR</span></>
                    ) : (
                      <><AlertTriangle className="w-3.5 h-3.5 text-rose-400" /><span className="text-xs text-rose-400">Below quality threshold</span></>
                    )}
                  </div>
                </div>
                <div className="hidden sm:block h-10 w-px bg-slate-700" />
                <div className="hidden sm:block text-xs text-slate-400 space-y-0.5">
                  <div>Original: {result.pipeline_summary.original_dimensions}</div>
                  <div>Cropped: {result.pipeline_summary.cropped_dimensions}</div>
                  <div>Skew: {result.pipeline_summary.skew_angle}°</div>
                </div>
              </div>

              <button
                onClick={() => { setResult(null); setSelectedVariant(null); }}
                className="flex items-center space-x-1.5 bg-slate-700/60 hover:bg-slate-700 text-slate-300 hover:text-white px-4 py-2 rounded-lg text-xs font-medium transition"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>New Image</span>
              </button>
            </div>

            {/* Rejection warnings */}
            {result.quality_assessment.rejection_reasons?.length > 0 && (
              <div className="bg-rose-500/10 border border-rose-500/25 rounded-xl p-4 space-y-2">
                <div className="text-sm font-medium text-rose-300 flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Quality Gate Issues</span>
                </div>
                {result.quality_assessment.rejection_reasons.map((r, i) => (
                  <p key={i} className="text-xs text-rose-300/80 ml-6">• {r}</p>
                ))}
              </div>
            )}

            {/* Section Tabs */}
            <div className="flex space-x-1 bg-slate-800/40 rounded-xl p-1 border border-slate-700/50">
              {[
                { key: "stages", label: "Pipeline Stages", icon: Layers },
                { key: "variants", label: "OCR Variants", icon: Eye },
              ].map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setActiveSection(key)}
                  className={`flex-1 flex items-center justify-center space-x-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
                    activeSection === key
                      ? "bg-gradient-to-r from-violet-600/90 to-blue-600/90 text-white shadow-md"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/40"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{label}</span>
                </button>
              ))}
            </div>

            {/* Pipeline Stages */}
            {activeSection === "stages" && result.stages && (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {Object.entries(result.stages).map(([key, stage]) => (
                  <div
                    key={key}
                    className="bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden hover:border-slate-600/60 transition-all group"
                  >
                    {/* Image */}
                    <div className="relative bg-slate-900/60 p-2">
                      <img
                        src={`data:image/png;base64,${stage.image}`}
                        alt={stage.label}
                        className="w-full h-48 object-contain rounded-lg"
                      />
                      <div className="absolute top-3 left-3 bg-slate-900/80 backdrop-blur-sm text-[10px] text-slate-300 px-2 py-0.5 rounded font-mono">
                        {key}
                      </div>
                    </div>

                    {/* Info */}
                    <div className="p-3 space-y-2">
                      <h3 className="text-sm font-semibold text-slate-200">{stage.label}</h3>
                      <p className="text-[11px] text-slate-400 leading-relaxed">{stage.description}</p>

                      {/* Metrics */}
                      {stage.metrics && (
                        <div className="grid grid-cols-3 gap-2 pt-1">
                          <div>
                            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Sharp</div>
                            <div className="text-xs font-semibold text-slate-300">{stage.metrics.sharpness}</div>
                            {metricBar(stage.metrics.sharpness, 500, stage.metrics.sharpness > 80 ? "green" : stage.metrics.sharpness > 40 ? "amber" : "rose")}
                          </div>
                          <div>
                            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Contrast</div>
                            <div className="text-xs font-semibold text-slate-300">{stage.metrics.contrast}</div>
                            {metricBar(stage.metrics.contrast, 80, "blue")}
                          </div>
                          <div>
                            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Bright</div>
                            <div className="text-xs font-semibold text-slate-300">{stage.metrics.brightness}</div>
                            {metricBar(stage.metrics.brightness, 255, "amber")}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* OCR Variants */}
            {activeSection === "variants" && result.variants && (
              <div className="space-y-4">
                {/* Variant Selector */}
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
                  {Object.entries(result.variants).map(([key, variant]) => {
                    const shortLabel = key.replace("variant_", "").toUpperCase();
                    const isActive = selectedVariant === key;
                    return (
                      <button
                        key={key}
                        onClick={() => setSelectedVariant(key)}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          isActive
                            ? "bg-blue-600/15 border-blue-500/50 shadow-lg shadow-blue-500/10"
                            : "bg-slate-800/30 border-slate-700/40 hover:border-slate-600/60"
                        }`}
                      >
                        <div className="flex items-center space-x-2 mb-1.5">
                          <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                            isActive ? "bg-blue-600 text-white" : "bg-slate-700 text-slate-400"
                          }`}>
                            {shortLabel}
                          </div>
                          <div className="text-[10px] text-slate-400">{variant.dimensions}</div>
                        </div>
                        <div className={`text-[11px] font-medium ${isActive ? "text-blue-300" : "text-slate-400"}`}>
                          Sharp: {variant.metrics.sharpness}
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Selected Variant Detail */}
                {selectedVariant && result.variants[selectedVariant] && (
                  <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl overflow-hidden">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
                      {/* Image */}
                      <div className="bg-slate-900/50 p-4 flex items-center justify-center min-h-[320px]">
                        <img
                          src={`data:image/png;base64,${result.variants[selectedVariant].image}`}
                          alt={result.variants[selectedVariant].label}
                          className="max-w-full max-h-[480px] object-contain rounded-lg shadow-2xl shadow-black/40"
                        />
                      </div>

                      {/* Details Panel */}
                      <div className="p-5 space-y-5">
                        <div>
                          <h3 className="text-lg font-bold text-white">{result.variants[selectedVariant].label}</h3>
                          <p className="text-sm text-slate-400 mt-1">{result.variants[selectedVariant].description}</p>
                          <div className="text-xs text-slate-500 mt-1.5">
                            Resolution: {result.variants[selectedVariant].dimensions}
                          </div>
                        </div>

                        <div className="space-y-3">
                          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Image Metrics</h4>
                          {Object.entries(result.variants[selectedVariant].metrics).map(([mk, mv]) => {
                            const maxes = { sharpness: 500, contrast: 80, brightness: 255 };
                            const colors = { sharpness: mv > 80 ? "green" : mv > 40 ? "amber" : "rose", contrast: "blue", brightness: "amber" };
                            return (
                              <div key={mk} className="space-y-1">
                                <div className="flex justify-between text-xs">
                                  <span className="text-slate-400 capitalize">{mk}</span>
                                  <span className="text-slate-200 font-semibold">{mv}</span>
                                </div>
                                {metricBar(mv, maxes[mk] || 100, colors[mk] || "blue")}
                              </div>
                            );
                          })}
                        </div>

                        {/* Compare with Original */}
                        <div>
                          <button
                            onClick={() => setCompareMode(!compareMode)}
                            className="flex items-center space-x-1.5 text-xs text-blue-400 hover:text-blue-300 transition"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>{compareMode ? "Hide Original" : "Compare with Original"}</span>
                          </button>
                          {compareMode && result.stages?.original && (
                            <div className="mt-3 bg-slate-900/50 rounded-lg p-3">
                              <div className="text-[10px] text-slate-500 mb-2 uppercase tracking-wider">Original Upload</div>
                              <img
                                src={`data:image/png;base64,${result.stages.original.image}`}
                                alt="Original"
                                className="max-h-40 object-contain rounded-lg mx-auto"
                              />
                            </div>
                          )}
                        </div>

                        <div className="text-[10px] text-slate-500 bg-slate-800/60 rounded-lg p-3 leading-relaxed">
                          <strong className="text-slate-400">Tip:</strong> This is the exact image that EasyOCR receives.
                          Variant A is the default. If OCR confidence is low, the pipeline
                          automatically tries B → D → C → E in sequence.
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
