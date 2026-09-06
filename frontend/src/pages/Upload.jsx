import React, { useState, useRef } from "react";
import { Upload as UploadIcon, Camera, CheckCircle2, AlertCircle, Sparkles, FileImage, Layers } from "lucide-react";
import { inspectionApi, API_BASE_URL } from "../api/client";

export default function Upload({ onInspectionComplete }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [productName, setProductName] = useState("");
  const [brand, setBrand] = useState("");
  const [isFoodProduct, setIsFoodProduct] = useState(true);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [pipelineStage, setPipelineStage] = useState("");
  const [error, setError] = useState(null);

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const sampleLabels = [
    {
      id: "compliant",
      title: "Compliant Biscuit Label",
      subtitle: "Full compliance (100% Score)",
      product: "NutriCrunch Almond Cookies",
      brand: "Suncrest Foods",
      food: true,
      url: `${API_BASE_URL}/sample_images/compliant_label.png`,
      badge: "Pass",
    },
    {
      id: "non_compliant",
      title: "Non-Compliant Chocolate Bar",
      subtitle: "Missing taxes & customer care",
      product: "ChocoDelight Premium Bar",
      brand: "ChocoDelight",
      food: true,
      url: `${API_BASE_URL}/sample_images/non_compliant_label.png`,
      badge: "Fail",
    },
    {
      id: "partial",
      title: "Herbal Soap Label",
      subtitle: "Minor issue (phone only, no email)",
      product: "Himalayan Herbal Soap",
      brand: "AyurVeda Organics",
      food: false,
      url: `${API_BASE_URL}/sample_images/partial_label.png`,
      badge: "Partial",
    },
  ];

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
      setError(null);
    }
  };

  const handleSelectSample = async (sample) => {
    try {
      setLoading(true);
      setPipelineStage("Loading sample label image...");
      const response = await fetch(sample.url);
      const blob = await response.blob();
      const sampleFile = new File([blob], `${sample.id}_label.png`, { type: "image/png" });

      setFile(sampleFile);
      setPreview(URL.createObjectURL(sampleFile));
      setProductName(sample.product);
      setBrand(sample.brand);
      setIsFoodProduct(sample.food);
      setError(null);
    } catch (err) {
      setError("Could not load sample image. Please upload a file manually.");
    } finally {
      setLoading(false);
      setPipelineStage("");
    }
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!file) {
      setError("Please select or capture a label image to inspect.");
      return;
    }

    setLoading(true);
    setError(null);
    setProgress(15);
    setPipelineStage("Uploading package image...");

    try {
      const formData = new FormData();
      formData.append("image", file);
      formData.append("product_name", productName.trim() || "Packaged Product");
      formData.append("brand", brand.trim() || "Unbranded");
      formData.append("is_food_product", isFoodProduct ? "true" : "false");

      // Simulated pipeline progress steps while server processes EasyOCR & CV
      const timer1 = setTimeout(() => {
        setProgress(35);
        setPipelineStage("OpenCV: Denoising, deskewing & cropping label contour...");
      }, 600);

      const timer2 = setTimeout(() => {
        setProgress(65);
        setPipelineStage("OCR Engine: Extracting label typography via EasyOCR...");
      }, 1600);

      const timer3 = setTimeout(() => {
        setProgress(85);
        setPipelineStage("Rule Engine: Validating against Legal Metrology Rules, 2011...");
      }, 2600);

      const result = await inspectionApi.upload(formData);

      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setProgress(100);
      setPipelineStage("Report generated successfully!");

      setTimeout(() => {
        onInspectionComplete(result);
      }, 500);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to process label image. Please check image quality and try again.");
      setLoading(false);
      setProgress(0);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">New Label Compliance Inspection</h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload or capture a product packaging label photo to automatically evaluate mandatory Legal Metrology declarations.
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start space-x-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" />
          <div>
            <p className="font-semibold">Inspection Error</p>
            <p className="text-xs text-rose-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* 1-Click Sample Testing Cards */}
      <div className="mb-8 bg-blue-50/60 border border-blue-200/80 rounded-2xl p-5">
        <div className="flex items-center space-x-2 mb-3">
          <Sparkles className="w-4 h-4 text-blue-600" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-blue-900">
            Quick Sample Test (1-Click Hackathon Demo)
          </h2>
        </div>
        <p className="text-xs text-blue-800/80 mb-4">
          Select any pre-configured test label to instantly populate and run the complete computer vision pipeline:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {sampleLabels.map((sample) => (
            <button
              key={sample.id}
              type="button"
              onClick={() => handleSelectSample(sample)}
              disabled={loading}
              className="text-left p-3.5 bg-white rounded-xl border border-blue-200 hover:border-blue-400 hover:shadow-md transition text-slate-800 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-900 line-clamp-1">{sample.title}</span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      sample.badge === "Pass"
                        ? "bg-emerald-100 text-emerald-800"
                        : sample.badge === "Fail"
                        ? "bg-rose-100 text-rose-800"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {sample.badge}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 line-clamp-2">{sample.subtitle}</p>
              </div>
              <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-blue-600 font-semibold">
                <span>Select Sample</span>
                <span>→</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Upload Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
        {/* Image Input Area */}
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Label Photo / Capture
          </label>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/*"
            className="hidden"
          />
          <input
            type="file"
            ref={cameraInputRef}
            onChange={handleFileChange}
            accept="image/*"
            capture="environment"
            className="hidden"
          />

          {!preview ? (
            <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:border-blue-500 hover:bg-blue-50/30 transition cursor-pointer">
              <div className="flex flex-col items-center">
                <div className="p-3 bg-blue-50 text-blue-600 rounded-full mb-3">
                  <FileImage className="w-8 h-8" />
                </div>
                <p className="text-sm font-semibold text-slate-700">Drag & drop label photo or click to browse</p>
                <p className="text-xs text-slate-400 mt-1">Supports PNG, JPG, JPEG up to 15MB</p>

                <div className="mt-4 flex flex-wrap gap-2 justify-center">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="inline-flex items-center px-3.5 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 shadow-sm"
                  >
                    <UploadIcon className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
                    Browse Photo
                  </button>
                  <button
                    type="button"
                    onClick={() => cameraInputRef.current?.click()}
                    className="inline-flex items-center px-3.5 py-1.5 border border-blue-300 rounded-lg text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 shadow-sm"
                  >
                    <Camera className="w-3.5 h-3.5 mr-1.5 text-blue-600" />
                    Take Photo
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="relative border rounded-xl overflow-hidden bg-slate-900/5 p-4 flex flex-col sm:flex-row items-center gap-4">
              <img
                src={preview}
                alt="Label preview"
                className="max-h-48 max-w-full rounded-lg shadow-sm object-contain bg-white"
              />
              <div className="flex-1 text-center sm:text-left">
                <div className="flex items-center justify-center sm:justify-start space-x-1 text-emerald-600 text-xs font-semibold mb-1">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Image Loaded ({file?.name || "Sample Label"})</span>
                </div>
                <p className="text-xs text-slate-500">Ready for OpenCV contour detection & EasyOCR</p>
                <div className="mt-3 flex gap-2 justify-center sm:justify-start">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="px-3 py-1 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Change Image
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setFile(null);
                      setPreview(null);
                    }}
                    className="px-3 py-1 bg-white border border-rose-200 rounded-lg text-xs font-medium text-rose-600 hover:bg-rose-50"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Product Details Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Product Name
            </label>
            <input
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="e.g. NutriCrunch Almond Cookies"
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Brand / Manufacturer
            </label>
            <input
              type="text"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="e.g. Suncrest Foods"
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>
        </div>

        {/* Commodity Category Toggle */}
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
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200 ease-in-out ${
                isFoodProduct ? "translate-x-5" : "translate-x-0"
              }`}
            />
          </button>
        </div>

        {/* Progress Bar during Pipeline Execution */}
        {loading && (
          <div className="p-4 bg-blue-50 rounded-xl border border-blue-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-blue-900">{pipelineStage}</span>
              <span className="text-xs font-extrabold text-blue-700">{progress}%</span>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || !file}
          className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-md shadow-blue-500/20 disabled:opacity-50 transition flex items-center justify-center space-x-2"
        >
          <Layers className="w-4 h-4" />
          <span>{loading ? "Running Metrology Pipeline..." : "Execute Compliance Verification"}</span>
        </button>
      </form>
    </div>
  );
}
