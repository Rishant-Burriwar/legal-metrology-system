import React, { useState } from "react";
import { 
  Download, 
  ArrowLeft, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  FileText, 
  Eye, 
  Tag, 
  Calendar, 
  Building2, 
  PhoneCall, 
  ShieldCheck, 
  Layers,
  Sparkles,
  Gauge,
  Activity,
  Repeat
} from "lucide-react";
import ScoreGauge from "../components/ScoreGauge";
import StatusBadge from "../components/StatusBadge";
import { inspectionApi, API_BASE_URL } from "../api/client";

export default function Report({ inspection, onBack, onNewInspection }) {
  const [activeOcrTab, setActiveOcrTab] = useState("validated"); // "validated" | "raw"
  const [showRawOcr, setShowRawOcr] = useState(false);
  const [selectedImageModal, setSelectedImageModal] = useState(null);

  if (!inspection) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <p className="text-slate-500">No inspection report loaded.</p>
        <button
          onClick={onBack}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  const origImageUrl = inspection.image_path?.startsWith("http")
    ? inspection.image_path
    : `${API_BASE_URL}${inspection.image_path || ""}`;

  const croppedImageUrl = inspection.cropped_image_path
    ? (inspection.cropped_image_path.startsWith("http")
        ? inspection.cropped_image_path
        : `${API_BASE_URL}${inspection.cropped_image_path}`)
    : origImageUrl;

  const pdfDownloadUrl = inspectionApi.getPdfUrl(inspection.id);

  const isCompliant = inspection.overall_status === "Compliant";
  const violations = inspection.violations || [];
  const extData = inspection.extracted_data || {};

  const passedCount = violations.filter((v) => v.status === "Pass").length;
  const failedCount = violations.filter((v) => v.status === "Fail").length;

  const qualityMetrics = inspection.quality_assessment?.metrics || {};
  const qualityScore = inspection.quality_score ?? 0.0;
  const ocrConf = inspection.ocr_confidence ? Math.round(inspection.ocr_confidence * 100) : 0;
  const retries = inspection.ocr_retry_count ?? 0;

  const renderFieldValue = (field) => {
    if (!field) return <span className="text-slate-400 font-normal italic">Not Detected</span>;
    const isUncertain = field.status === "uncertain" || field.value?.includes("uncertain");

    if (isUncertain) {
      return (
        <div className="space-y-1">
          <span className="inline-flex items-center px-2 py-0.5 rounded bg-orange-100 text-orange-800 font-mono text-xs font-semibold">
            <AlertTriangle className="w-3 h-3 mr-1 text-orange-600 shrink-0" />
            [uncertain — please upload a clearer image]
          </span>
          <p className="text-[11px] text-orange-700 font-medium">
            OCR confidence fell below verification threshold. Value withheld to prevent error.
          </p>
        </div>
      );
    }

    return field.value || <span className="text-slate-400 font-normal italic">Not Detected</span>;
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Top Navigation & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <button
          onClick={onBack}
          className="inline-flex items-center text-xs font-semibold text-slate-600 hover:text-slate-900 transition"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Dashboard
        </button>

        <div className="flex items-center space-x-3">
          <button
            onClick={onNewInspection}
            className="px-3.5 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 transition"
          >
            New Inspection
          </button>
          <a
            href={pdfDownloadUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-sm shadow-blue-500/20 transition"
          >
            <Download className="w-3.5 h-3.5 mr-1.5" />
            Download PDF Report
          </a>
        </div>
      </div>

      {/* Header Summary Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Left Metadata */}
          <div className="space-y-3 flex-1">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono font-bold text-slate-400">INSPECTION #{inspection.id}</span>
              <StatusBadge status={inspection.overall_status} type="verdict" size="lg" />
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {inspection.product_name}
            </h1>

            <div className="flex flex-wrap gap-y-2 gap-x-4 text-xs text-slate-500">
              <div>
                <span className="font-semibold text-slate-700">Brand:</span> {inspection.brand}
              </div>
              <div>
                <span className="font-semibold text-slate-700">Date:</span>{" "}
                {new Date(inspection.created_at).toLocaleString()}
              </div>
              <div>
                <span className="font-semibold text-slate-700">Rules Passed:</span> {passedCount} / {violations.length}
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed pt-1">
              {isCompliant
                ? "All statutory declarations under Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011 have been successfully verified and found compliant."
                : `Non-compliance identified: ${failedCount} mandatory declaration(s) failed statutory verification criteria.`}
            </p>
          </div>

          {/* Right Gauge */}
          <div className="shrink-0 border-t md:border-t-0 md:border-l border-slate-100 pt-4 md:pt-0 md:pl-8">
            <ScoreGauge score={inspection.compliance_score} />
          </div>
        </div>
      </div>

      {/* Image Quality & OCR Engine Diagnostic Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Quality Score Card */}
        <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm flex items-start space-x-3">
          <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl shrink-0">
            <Gauge className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Quality Score</span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-800">
                {qualityScore >= 80 ? "Crisp" : qualityScore >= 60 ? "Good" : "Acceptable"}
              </span>
            </div>
            <p className="text-xl font-black text-slate-900 mt-1">
              {qualityScore.toFixed(1)} <span className="text-xs text-slate-400 font-semibold">/ 100</span>
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Laplacian Sharpness: {qualityMetrics.sharpness_laplacian ?? "N/A"}
            </p>
          </div>
        </div>

        {/* OCR Confidence Card */}
        <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm flex items-start space-x-3">
          <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl shrink-0">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">OCR Confidence</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${ocrConf >= 75 ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                {ocrConf >= 75 ? "High" : "Moderate"}
              </span>
            </div>
            <p className="text-xl font-black text-slate-900 mt-1">
              {ocrConf}% <span className="text-xs text-slate-400 font-semibold">Avg Consensus</span>
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Disambiguated typography stream
            </p>
          </div>
        </div>

        {/* Retries / Passes Card */}
        <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm flex items-start space-x-3">
          <div className="p-2.5 bg-purple-50 text-purple-600 rounded-xl shrink-0">
            <Repeat className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Multi-Pass Pipeline</span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-100 text-purple-800">
                {retries > 0 ? "Adaptive Retry" : "Single Pass"}
              </span>
            </div>
            <p className="text-xl font-black text-slate-900 mt-1">
              {retries === 0 ? "1 Pass" : `${retries + 1} Passes`}
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {retries > 0 ? `${retries} retry stage(s) triggered` : "Target confidence met in Pass 1"}
            </p>
          </div>
        </div>
      </div>

      {/* Side-by-Side Images (Original vs OpenCV Cropped) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-800">
              Computer Vision Pipeline: Region Detection & Rectification
            </h2>
          </div>
          <span className="text-xs text-slate-400">Click any image to enlarge</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Original */}
          <div className="border border-slate-200 rounded-xl p-3 bg-slate-50/50">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-600 mb-2">
              <span>Original Input Capture</span>
              <span className="text-[10px] text-slate-400">
                {qualityMetrics.width ? `${qualityMetrics.width}×${qualityMetrics.height} px` : "Input Photo"}
              </span>
            </div>
            <div
              className="h-48 bg-white rounded-lg overflow-hidden border border-slate-200 flex items-center justify-center cursor-pointer group"
              onClick={() => setSelectedImageModal(origImageUrl)}
            >
              <img
                src={origImageUrl}
                alt="Original"
                className="max-h-full max-w-full object-contain group-hover:scale-105 transition duration-200"
              />
            </div>
          </div>

          {/* Cropped & Rectified */}
          <div className="border border-blue-200 rounded-xl p-3 bg-blue-50/20">
            <div className="flex items-center justify-between text-xs font-semibold text-blue-900 mb-2">
              <span>OpenCV Cropped, Deskewed & Rectified Label</span>
              <span className="text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-bold">
                Contour Detected
              </span>
            </div>
            <div
              className="h-48 bg-white rounded-lg overflow-hidden border border-blue-200 flex items-center justify-center cursor-pointer group"
              onClick={() => setSelectedImageModal(croppedImageUrl)}
            >
              <img
                src={croppedImageUrl}
                alt="Cropped Label"
                className="max-h-full max-w-full object-contain group-hover:scale-105 transition duration-200"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Mandatory Declarations Checklist Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-800">
              Legal Metrology Rules, 2011 Checklist
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Rule-by-rule verification breakdown under statutory provisions
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold px-2 py-1 rounded bg-emerald-50 text-emerald-700">
              {passedCount} Passed
            </span>
            {failedCount > 0 && (
              <span className="text-xs font-semibold px-2 py-1 rounded bg-rose-50 text-rose-700">
                {failedCount} Failed
              </span>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-600 uppercase font-semibold">
              <tr>
                <th className="py-3 px-4 text-left">Rule Code</th>
                <th className="py-3 px-4 text-left">Mandatory Requirement</th>
                <th className="py-3 px-4 text-left">Severity</th>
                <th className="py-3 px-4 text-left">Status</th>
                <th className="py-3 px-4 text-left">Inspection Findings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {violations.map((v, idx) => (
                <tr key={idx} className={v.status === "Fail" ? "bg-rose-50/30" : "hover:bg-slate-50/50"}>
                  <td className="py-3 px-4 font-mono font-bold text-slate-800">{v.rule_code}</td>
                  <td className="py-3 px-4 font-medium text-slate-700 max-w-xs">{v.description}</td>
                  <td className="py-3 px-4">
                    <StatusBadge status={v.severity} />
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge status={v.status} />
                  </td>
                  <td className="py-3 px-4 text-slate-600">{v.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Extracted Declarations Cards with Disambiguation & Uncertainty Protection */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Tag className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-800">
              Structured Field Extractions (NLP, Disambiguation & Validation)
            </h2>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Net Qty */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-slate-500">Net Quantity</span>
              <StatusBadge status={extData.net_quantity?.status || "not_found"} />
            </div>
            <div className="text-sm font-bold text-slate-800 mt-1">
              {renderFieldValue(extData.net_quantity)}
            </div>
          </div>

          {/* MRP */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-slate-500">Maximum Retail Price (MRP)</span>
              <StatusBadge status={extData.mrp?.status || "not_found"} />
            </div>
            <div className="text-sm font-bold text-slate-800 mt-1">
              {renderFieldValue(extData.mrp)}
            </div>
          </div>

          {/* Mfg Date */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-slate-500">Date of Mfg / Packing</span>
              <StatusBadge status={extData.manufacture_date?.status || "not_found"} />
            </div>
            <div className="text-sm font-bold text-slate-800 mt-1">
              {renderFieldValue(extData.manufacture_date)}
            </div>
          </div>

          {/* Customer Care */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-slate-500">Consumer Care Contact</span>
              <StatusBadge status={extData.customer_care?.status || "not_found"} />
            </div>
            <div className="text-sm font-bold text-slate-800 mt-1">
              {renderFieldValue(extData.customer_care)}
            </div>
          </div>

          {/* FSSAI */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-slate-500">FSSAI License Number</span>
              <StatusBadge status={extData.fssai_license?.status || "not_found"} />
            </div>
            <div className="text-sm font-bold text-slate-800 mt-1 font-mono">
              {renderFieldValue(extData.fssai_license)}
            </div>
          </div>

          {/* Country of Origin */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-slate-500">Country of Origin</span>
              <StatusBadge status={extData.country_of_origin?.status || "not_found"} />
            </div>
            <div className="text-sm font-bold text-slate-800 mt-1">
              {renderFieldValue(extData.country_of_origin)}
            </div>
          </div>

          {/* Manufacturer Details */}
          <div className="md:col-span-2 p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-slate-500">Manufacturer / Packer Name & Address</span>
              <StatusBadge status={extData.manufacturer_details?.status || "not_found"} />
            </div>
            <div className="text-sm font-bold text-slate-800 mt-1">
              {renderFieldValue(extData.manufacturer_details)}
            </div>
          </div>
        </div>
      </div>

      {/* Tabbed OCR Typography Stream Viewer (Validated vs Raw) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-blue-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              OCR Typography Stream
            </h2>
          </div>

          {/* Tab Selection */}
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => {
                setActiveOcrTab("validated");
                setShowRawOcr(true);
              }}
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition ${
                activeOcrTab === "validated" && showRawOcr
                  ? "bg-white text-blue-700 shadow-sm"
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
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition ${
                activeOcrTab === "raw" && showRawOcr
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Raw Engine Output
            </button>
            <button
              type="button"
              onClick={() => setShowRawOcr(!showRawOcr)}
              className="px-2.5 py-1 text-xs text-slate-500 hover:text-slate-800 font-medium"
            >
              {showRawOcr ? "Collapse ▲" : "Expand ▼"}
            </button>
          </div>
        </div>

        {showRawOcr && (
          <div className="p-4 rounded-xl bg-slate-900 text-slate-200 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto">
            {activeOcrTab === "validated"
              ? (inspection.validated_ocr_text || inspection.raw_ocr_text || "No text extracted by OCR engine.")
              : (inspection.raw_ocr_text || "No raw text extracted by OCR engine.")}
          </div>
        )}
      </div>

      {/* Image Modal */}
      {selectedImageModal && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setSelectedImageModal(null)}
        >
          <div className="max-w-3xl max-h-[90vh] bg-white rounded-2xl overflow-hidden p-2 shadow-2xl">
            <img
              src={selectedImageModal}
              alt="Enlarged view"
              className="max-h-[85vh] max-w-full object-contain rounded-xl"
            />
          </div>
        </div>
      )}
    </div>
  );
}
