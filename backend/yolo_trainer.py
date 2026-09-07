"""
YOLO Label Field Detector — Training Scaffold
==============================================
Generates a YOLO-format training dataset from existing inspection records
and trains a YOLOv8-nano model to detect legal metrology field zones on packaging labels.

Usage:
    cd backend
    python yolo_trainer.py                        # Full train run
    python yolo_trainer.py --epochs 20 --imgsz 416 --cpu   # Fast CPU run
    python yolo_trainer.py --generate-only         # Dataset generation only

Output:
    backend/dataset/         — YOLO-format dataset (images + labels + yaml)
    backend/models/yolo_label_detector.pt — trained model weights

Prerequisites:
    pip install ultralytics torch torchvision
    pip install sqlalchemy  (already in requirements.txt)

Class Definitions (YOLO label indices):
    0 — product_name
    1 — date_fssai       (manufacturing/expiry dates AND FSSAI number)
    2 — mrp_quantity     (MRP price and net quantity)
    3 — manufacturer     (manufacturer/marketer address block)
    4 — general_text     (other text regions)
"""

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).parent.resolve()
DATASET_DIR = BACKEND_DIR / "dataset"
MODEL_DIR = BACKEND_DIR / "models"
STORAGE_DIR = BACKEND_DIR / "storage" / "images"
DB_PATH = BACKEND_DIR / "legal_metrology.db"

IMAGES_TRAIN = DATASET_DIR / "images" / "train"
IMAGES_VAL = DATASET_DIR / "images" / "val"
LABELS_TRAIN = DATASET_DIR / "labels" / "train"
LABELS_VAL = DATASET_DIR / "labels" / "val"

CLASS_NAMES = ["product_name", "date_fssai", "mrp_quantity", "manufacturer", "general_text"]
CLASS_MAP = {name: idx for idx, name in enumerate(CLASS_NAMES)}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def load_inspections_from_db(db_path: Path) -> List[Dict]:
    """Load inspection records that have extracted_data and stored images."""
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, image_path, cropped_image_path, extracted_data, ocr_blocks
            FROM inspections
            WHERE extracted_data IS NOT NULL
              AND (cropped_image_path IS NOT NULL OR image_path IS NOT NULL)
            ORDER BY id DESC
            LIMIT 2000
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        logger.info(f"Loaded {len(rows)} inspection records from DB.")
        return rows
    except Exception as e:
        logger.error(f"Failed to load DB: {e}")
        return []


# ---------------------------------------------------------------------------
# Annotation generation
# ---------------------------------------------------------------------------

def resolve_image_path(row: Dict) -> Optional[Path]:
    """Find the actual image file for an inspection record."""
    for url_key in ("cropped_image_path", "image_path"):
        url = row.get(url_key, "")
        if not url:
            continue
        # Strip leading /storage/images/ prefix
        filename = url.lstrip("/").replace("storage/images/", "")
        candidate = STORAGE_DIR / filename
        if candidate.exists():
            return candidate
    return None


def _field_to_class(field_name: str) -> int:
    """Map extracted_data field name to YOLO class index."""
    mapping = {
        "manufacturer_details": CLASS_MAP["manufacturer"],
        "net_quantity":         CLASS_MAP["mrp_quantity"],
        "mrp":                  CLASS_MAP["mrp_quantity"],
        "manufacture_date":     CLASS_MAP["date_fssai"],
        "customer_care":        CLASS_MAP["general_text"],
        "fssai_license":        CLASS_MAP["date_fssai"],
        "country_of_origin":    CLASS_MAP["general_text"],
    }
    return mapping.get(field_name, CLASS_MAP["general_text"])


def generate_annotations_from_blocks(
    img_h: int,
    img_w: int,
    ocr_blocks: Optional[List[Dict]],
    extracted_data: Dict,
) -> List[Tuple[int, float, float, float, float]]:
    """
    Generate YOLO bounding box annotations from OCR block data.

    If block-level bounding boxes are available (from EasyOCR), use them.
    Otherwise fall back to heuristic zone placement based on extracted field positions.

    Returns list of (class_id, cx, cy, bw, bh) in normalized [0,1] coords.
    """
    annotations = []

    # --- Strategy 1: Use OCR blocks with known bbox coordinates ---
    if ocr_blocks:
        for block in ocr_blocks:
            box = block.get("box", [])
            text = block.get("text", "")
            if not box or len(box) < 2:
                continue

            # box is [[x1,y1],[x2,y1],[x2,y2],[x1,y2]] or [[x1,y1],[x2,y2]]
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x1, x2 = min(xs), max(xs)
            y1, y2 = min(ys), max(ys)

            if x2 - x1 < 5 or y2 - y1 < 3:
                continue

            # Determine class from text content
            cls_id = CLASS_MAP["general_text"]
            text_lower = text.lower()
            if any(k in text_lower for k in ("fssai", "lic no", "licence")):
                cls_id = CLASS_MAP["date_fssai"]
            elif any(k in text_lower for k in ("mfg", "mfd", "exp", "best before", "packed")):
                cls_id = CLASS_MAP["date_fssai"]
            elif any(k in text_lower for k in ("mrp", "m.r.p", "₹", "rs.", "price")):
                cls_id = CLASS_MAP["mrp_quantity"]
            elif any(k in text_lower for k in ("net", "kg", "gm", "ml", "ltr", "pcs")):
                cls_id = CLASS_MAP["mrp_quantity"]
            elif any(k in text_lower for k in ("manufactured", "marketed", "packed by", "pvt", "ltd", "industries")):
                cls_id = CLASS_MAP["manufacturer"]

            # Normalize
            cx = ((x1 + x2) / 2.0) / img_w
            cy = ((y1 + y2) / 2.0) / img_h
            bw = (x2 - x1) / img_w
            bh = (y2 - y1) / img_h

            cx = min(max(cx, 0.001), 0.999)
            cy = min(max(cy, 0.001), 0.999)
            bw = min(bw, 0.999)
            bh = min(bh, 0.999)

            annotations.append((cls_id, cx, cy, bw, bh))

    # --- Strategy 2: Heuristic zone placement from extracted field statuses ---
    if not annotations and extracted_data:
        # Generate rough zone boxes based on common Indian packaging layouts
        zones = {
            "product_name":    (0.5, 0.12, 0.8, 0.20),  # top center
            "date_fssai":      (0.5, 0.82, 0.9, 0.14),  # bottom band
            "mrp_quantity":    (0.75, 0.45, 0.4, 0.15),  # right center
            "manufacturer":    (0.3, 0.65, 0.55, 0.25),  # bottom-left block
        }

        field_zone_map = {
            "manufacturer_details": "manufacturer",
            "fssai_license":        "date_fssai",
            "manufacture_date":     "date_fssai",
            "mrp":                  "mrp_quantity",
            "net_quantity":         "mrp_quantity",
        }

        for field, zone_key in field_zone_map.items():
            field_result = extracted_data.get(field, {})
            if field_result.get("status") in ("found", "low_confidence"):
                zone = zones.get(zone_key)
                if zone:
                    cx, cy, bw, bh = zone
                    cls_id = CLASS_MAP.get(zone_key, CLASS_MAP["general_text"])
                    annotations.append((cls_id, cx, cy, bw, bh))

    return annotations


# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------

def build_dataset(inspections: List[Dict], val_fraction: float = 0.15) -> int:
    """
    Build YOLO-format dataset from inspection records.
    Returns number of successfully annotated samples.
    """
    # Create directory structure
    for d in (IMAGES_TRAIN, IMAGES_VAL, LABELS_TRAIN, LABELS_VAL):
        d.mkdir(parents=True, exist_ok=True)

    annotated = 0
    skipped = 0

    np.random.seed(42)
    indices = np.random.permutation(len(inspections))
    val_count = max(1, int(len(inspections) * val_fraction))
    val_indices = set(indices[:val_count].tolist())

    for raw_idx, insp in enumerate(inspections):
        img_path = resolve_image_path(insp)
        if img_path is None:
            skipped += 1
            continue

        img = cv2.imread(str(img_path))
        if img is None:
            skipped += 1
            continue

        h, w = img.shape[:2]

        # Parse stored data
        try:
            ext_data = (
                json.loads(insp["extracted_data"])
                if isinstance(insp["extracted_data"], str)
                else insp["extracted_data"] or {}
            )
        except Exception:
            ext_data = {}

        try:
            ocr_blocks = (
                json.loads(insp.get("ocr_blocks", "[]") or "[]")
                if isinstance(insp.get("ocr_blocks"), str)
                else insp.get("ocr_blocks") or []
            )
        except Exception:
            ocr_blocks = []

        annotations = generate_annotations_from_blocks(h, w, ocr_blocks, ext_data)
        if not annotations:
            skipped += 1
            continue

        is_val = raw_idx in val_indices
        img_dest_dir = IMAGES_VAL if is_val else IMAGES_TRAIN
        lbl_dest_dir = LABELS_VAL if is_val else LABELS_TRAIN

        fname = f"insp_{insp['id']}_{img_path.stem}"
        img_out = img_dest_dir / f"{fname}.jpg"
        lbl_out = lbl_dest_dir / f"{fname}.txt"

        # Save image
        cv2.imwrite(str(img_out), img, [cv2.IMWRITE_JPEG_QUALITY, 92])

        # Save YOLO label file
        with open(lbl_out, "w") as f:
            for cls_id, cx, cy, bw, bh in annotations:
                f.write(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

        annotated += 1

    logger.info(f"Dataset built: {annotated} annotated, {skipped} skipped.")
    return annotated


def write_dataset_yaml() -> Path:
    """Write the dataset.yaml config file for YOLOv8 training."""
    yaml_path = DATASET_DIR / "dataset.yaml"
    content = f"""# Legal Metrology Label Field Detector — YOLO Dataset
path: {DATASET_DIR.resolve()}
train: images/train
val: images/val

nc: {len(CLASS_NAMES)}
names: {CLASS_NAMES}
"""
    yaml_path.write_text(content)
    logger.info(f"Dataset YAML written to {yaml_path}")
    return yaml_path


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(
    yaml_path: Path,
    epochs: int = 50,
    imgsz: int = 640,
    batch: int = 8,
    device: str = "cpu",
) -> Path:
    """Train YOLOv8-nano model and save to models/yolo_label_detector.pt."""
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    output_model = MODEL_DIR / "yolo_label_detector.pt"

    logger.info(f"Starting YOLOv8-nano training: epochs={epochs}, imgsz={imgsz}, device={device}")

    model = YOLO("yolov8n.pt")  # Downloads ~6 MB pretrained nano weights

    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project=str(MODEL_DIR / "runs"),
        name="label_detector",
        exist_ok=True,
        patience=15,          # Early stopping if no improvement for 15 epochs
        save=True,
        val=True,
        verbose=True,
        workers=0,            # 0 = main process only (safe on Windows)
        single_cls=False,
        rect=True,            # Rectangular training (faster for varied aspect ratios)
        cache=False,
        augment=True,
        degrees=10.0,         # Rotation augmentation (labels are sometimes tilted)
        fliplr=0.0,           # Don't flip horizontally (text direction matters)
        mosaic=0.5,
        copy_paste=0.0,
    )

    # Copy best weights to the expected location
    best_weights = MODEL_DIR / "runs" / "label_detector" / "weights" / "best.pt"
    if best_weights.exists():
        shutil.copy(str(best_weights), str(output_model))
        logger.info(f"Best model saved to {output_model}")
    else:
        logger.warning("Could not find best.pt — saving last.pt instead")
        last_weights = MODEL_DIR / "runs" / "label_detector" / "weights" / "last.pt"
        if last_weights.exists():
            shutil.copy(str(last_weights), str(output_model))

    return output_model


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Train YOLO label field detector from existing inspection data."
    )
    parser.add_argument("--epochs",        type=int, default=50,  help="Training epochs (default: 50)")
    parser.add_argument("--imgsz",         type=int, default=640, help="Image size (default: 640)")
    parser.add_argument("--batch",         type=int, default=8,   help="Batch size (default: 8)")
    parser.add_argument("--cpu",           action="store_true",   help="Force CPU training")
    parser.add_argument("--val-fraction",  type=float, default=0.15, help="Validation split fraction")
    parser.add_argument("--generate-only", action="store_true",   help="Only generate dataset, skip training")
    parser.add_argument("--clean",         action="store_true",   help="Delete existing dataset before regenerating")
    args = parser.parse_args()

    if args.clean and DATASET_DIR.exists():
        logger.info(f"Cleaning existing dataset at {DATASET_DIR}")
        shutil.rmtree(DATASET_DIR)

    # Step 1: Load inspection data
    inspections = load_inspections_from_db(DB_PATH)
    if not inspections:
        logger.error(
            "No inspection records found in the database.\n"
            "Run the application, upload some product images, and then re-run this trainer."
        )
        sys.exit(1)

    # Step 2: Build dataset
    num_samples = build_dataset(inspections, val_fraction=args.val_fraction)
    if num_samples < 5:
        logger.error(
            f"Only {num_samples} annotated samples generated — not enough to train.\n"
            "Upload more product label images through the web app first."
        )
        sys.exit(1)

    yaml_path = write_dataset_yaml()

    if args.generate_only:
        logger.info(f"Dataset generation complete ({num_samples} samples). Skipping training.")
        return

    # Step 3: Train
    device = "cpu" if args.cpu else ("0" if _gpu_available() else "cpu")
    if device == "cpu":
        # Reduce defaults for CPU run
        if args.epochs == 50:
            args.epochs = 25
        if args.imgsz == 640:
            args.imgsz = 416
        logger.info("CPU mode: using epochs=25, imgsz=416 for reasonable training time.")

    output_model = train(
        yaml_path=yaml_path,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
    )

    logger.info(
        f"\n✅ Training complete!\n"
        f"   Model saved to: {output_model}\n"
        f"   Restart the backend server to activate the model."
    )


def _gpu_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


if __name__ == "__main__":
    main()
