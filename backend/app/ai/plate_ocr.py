"""
Traffic AI Demo -- Vehicle Detection + License Plate OCR
========================================================

Pipeline (this is the whole idea of the project):

    video frame
        |
        v
    [1] YOLO vehicle detector  ->  finds cars / trucks / buses / motorcycles
        |
        v
    [2] YOLO license-plate detector  ->  finds the plate rectangle
        |
        v
    [3] crop the plate region out of the frame
        |
        v
    [4] OCR (EasyOCR)  ->  reads the characters on the plate
        |
        v
    [5] draw everything on the frame + print to terminal

Two SEPARATE models are used on purpose:
  * A normal pretrained YOLO (COCO) knows "car", "truck", "bus", "motorcycle"
    but does NOT know "license plate".
  * So a second YOLO, fine-tuned only to find license plates, is used for step 2.

Run:
    python main.py --source videos/traffic.mp4
    python main.py --source 0            # webcam
"""

import argparse
import time
import os
import cv2
import numpy as np
import torch  # only used to detect whether a CUDA GPU is available

from ultralytics import YOLO

# COCO class IDs that count as "a vehicle". This is fixed by the COCO dataset
# that the standard YOLO model was trained on.
VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

# Colours (B, G, R) used when drawing on the frame.
COLOR_VEHICLE = (0, 200, 0)     # green box around vehicles
COLOR_PLATE = (0, 0, 255)       # red box around plates
COLOR_OCR = (0, 255, 255)       # bright yellow for the recognised plate text
COLOR_TEXT_BG = (0, 0, 0)       # black background behind text


# --------------------------------------------------------------------------- #
# OCR wrapper
# --------------------------------------------------------------------------- #
# EasyOCR is restricted to these characters. Letters + digits only is the
# right constraint for ANY country's plates -- it does NOT impose a format
# (no fixed length, no fixed letter/digit pattern), it just stops the reader
# from emitting punctuation/symbols that never appear on a plate.
ALPHANUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class PlateOCR:
    """EasyOCR wrapper tuned for small, low-quality license-plate crops.

    NOTE: this project uses **EasyOCR**, not PaddleOCR (PaddlePaddle wheels are
    unreliable on Windows + Python 3.12). Both map a plate image -> text+conf.

    For each crop we: upscale it, build several preprocessing variants
    (original / contrast-enhanced / sharpened / thresholded), OCR each with an
    alphanumeric allowlist, and keep the highest-confidence read. No single
    preprocessing wins on every frame, so we try a few and let confidence pick.
    """

    def __init__(self, gpu=False):
        import easyocr  # imported here so the app still starts if OCR is absent
        # gpu=True runs on the NVIDIA GPU (needs a CUDA build of torch),
        # gpu=False falls back to CPU. Works everywhere, just slower on CPU.
        self.reader = easyocr.Reader(["en"], gpu=gpu)

    @staticmethod
    def _clean(text: str) -> str:
        # License plates are letters + digits only. Drop spaces / punctuation.
        return "".join(ch for ch in text.upper() if ch.isalnum())

    @staticmethod
    def _bbox_metrics(bbox):
        """Return (x_left, y_center, height) for an EasyOCR polygon bbox.

        ``bbox`` is EasyOCR's 4-point quad [[x,y], ...]; we only need the left
        edge (for left->right ordering) and the vertical center + height (for
        grouping fragments into rows).
        """
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        return min(xs), (min(ys) + max(ys)) / 2.0, (max(ys) - min(ys))

    def _assemble(self, results):
        """Join EasyOCR fragments into one plate string, reading TOP-TO-BOTTOM
        then LEFT-TO-RIGHT, plus the average confidence.

        Two-line plates -- common on Indian motorcycles and commercial
        vehicles, e.g. ``TN 01`` stacked over ``AB 1234`` -- must be read row by
        row, otherwise sorting purely by x interleaves the two lines into a
        jumbled string. Fragments are grouped into rows by vertical position: a
        new row begins when a fragment sits more than ~0.6x the median glyph
        height below the current row. A normal single-line plate collapses to
        one row, so this is a strict superset of the old left->right behaviour.
        """
        if not results:
            return None, 0.0

        # keep only fragments that survive cleaning, with their geometry
        frags = []
        for bbox, text, conf in results:
            cleaned = self._clean(text)
            if cleaned:
                x, yc, h = self._bbox_metrics(bbox)
                frags.append({"x": x, "y": yc, "h": h, "text": cleaned,
                              "conf": conf})
        if not frags:
            return None, 0.0

        # reference glyph height -> the vertical gap that separates two rows
        heights = sorted(f["h"] for f in frags)
        med_h = heights[len(heights) // 2] or 1.0
        row_gap = 0.6 * med_h

        # walk fragments top-to-bottom, starting a new row on a big vertical gap
        frags.sort(key=lambda f: f["y"])
        rows, current, row_y = [], [], None
        for f in frags:
            if row_y is None or (f["y"] - row_y) <= row_gap:
                current.append(f)
                row_y = sum(g["y"] for g in current) / len(current)  # row center
            else:
                rows.append(current)
                current, row_y = [f], f["y"]
        if current:
            rows.append(current)

        # read each row left-to-right, then stack the rows top-to-bottom
        pieces, confs = [], []
        for row in rows:
            row.sort(key=lambda f: f["x"])
            for f in row:
                pieces.append(f["text"])
                confs.append(f["conf"])

        return "".join(pieces), sum(confs) / len(confs)

    @staticmethod
    def _upscale(img, target_h=80):
        """Upscale small crops so characters are big enough for OCR (cubic)."""
        h, w = img.shape[:2]
        if h == 0 or w == 0:
            return img
        if h < target_h:
            scale = target_h / float(h)
            img = cv2.resize(img, (int(w * scale), int(h * scale)),
                             interpolation=cv2.INTER_CUBIC)
        return img

    @staticmethod
    def _variants(bgr):
        """Return [(name, image), ...] preprocessing variants to try in order.

        The original crop is kept first as the baseline/alternative; the others
        help when the plate is low-contrast, blurry, or unevenly lit.
        """
        variants = [("original", bgr)]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        # contrast enhancement (CLAHE) -- helps dim / backlit plates
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        variants.append(("clahe", clahe))
        # sharpen the contrast-enhanced image -- helps slightly blurred plates
        sharpen_k = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        variants.append(("sharp", cv2.filter2D(clahe, -1, sharpen_k)))
        # Otsu threshold -- helps clean, high-contrast plates become crisp b/w
        _, otsu = cv2.threshold(clahe, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(("otsu", otsu))
        return variants

    def read(self, plate_img, debug=False):
        """Return (text, confidence, info).

        ``info`` carries debug data: crop size, upscaled size, and the raw
        (text, conf) each preprocessing variant produced.
        """
        info = {"crop_size": None, "up_size": None, "variants": [],
                "raw": None, "conf": 0.0, "variant": None}
        if plate_img is None or plate_img.size == 0:
            return None, 0.0, info

        h0, w0 = plate_img.shape[:2]
        info["crop_size"] = (w0, h0)
        up = self._upscale(plate_img, target_h=80)
        info["up_size"] = (up.shape[1], up.shape[0])

        best_text, best_conf, best_name, best_img = None, 0.0, None, up
        for name, img in self._variants(up):
            results = self.reader.readtext(
                img, allowlist=ALPHANUM, detail=1, paragraph=False
            )
            text, conf = self._assemble(results)
            info["variants"].append((name, text, round(conf, 3)))
            if text and len(text) >= 4 and conf > best_conf:
                best_text, best_conf, best_name, best_img = text, conf, name, img
            if best_conf >= 0.85:  # already very confident -> stop early (faster)
                break

        info["raw"] = best_text
        info["conf"] = round(best_conf, 3)
        info["variant"] = best_name
        info["best_img"] = best_img
        if best_text is None:
            return None, 0.0, info
        return best_text, best_conf, info


# --------------------------------------------------------------------------- #
# Temporal aggregation (per-plate voting across consecutive frames)
# --------------------------------------------------------------------------- #
class PlateAggregator:
    """Collect OCR reads of the SAME plate over consecutive frames and return
    the most consistent text.

    This is lightweight per-plate voting: a plate detection is matched to the
    previous frame's plate by bounding-box overlap (IoU), and confident reads
    are accumulated as confidence-weighted votes. The winning string is the one
    with the most support across frames -- so a one-frame misread like "A8C1234"
    is outvoted by the repeated correct "ABC1234".

    It is NOT vehicle tracking / trajectories -- tracks are anonymous, local to
    a few frames, and expire quickly. Purely to stabilise the OCR text.
    """

    def __init__(self, iou_thresh=0.2, max_age=30, min_conf=0.25):
        self.iou_thresh = iou_thresh
        self.max_age = max_age        # frames a track survives without a match
        self.min_conf = min_conf      # ignore reads below this (very low conf)
        self.tracks = []
        self.finished = []            # tracks dropped by expire(), kept for export

    @staticmethod
    def _iou(a, b):
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        inter = iw * ih
        if inter == 0:
            return 0.0
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        return inter / float(area_a + area_b - inter)

    def update(self, box, text, conf, frame_idx, detect_conf=0.0,
               vehicle="vehicle"):
        """Add one frame's read for a plate; return the stable (voted) text.

        ``detect_conf`` (plate-box confidence) and ``vehicle`` (owning vehicle
        class) are recorded per track purely so the run can export a structured
        JSON later -- they do not affect the voting.
        """
        match, best_iou = None, self.iou_thresh
        for tr in self.tracks:
            iou = self._iou(box, tr["box"])
            if iou >= best_iou:
                match, best_iou = tr, iou
        if match is None:
            match = {"box": box, "votes": {}, "last": frame_idx,
                     "first": frame_idx, "history": [], "vehicle": vehicle,
                     "detect_confs": []}
            self.tracks.append(match)
        match["box"] = box
        match["last"] = frame_idx
        if detect_conf:
            match["detect_confs"].append(detect_conf)
        if vehicle and vehicle != "vehicle":
            match["vehicle"] = vehicle

        # weight each vote by its confidence; ignore very low-confidence reads
        if text and conf >= self.min_conf and len(text) >= 4:
            match["votes"][text] = match["votes"].get(text, 0.0) + conf
            # keep the individual frame read -> "multi-frame OCR evidence"
            match["history"].append({"frame": frame_idx, "text": text,
                                     "conf": round(float(conf), 3)})

        if not match["votes"]:
            return None
        # most consistent = highest total confidence-weighted support
        return max(match["votes"].items(), key=lambda kv: kv[1])[0]

    def expire(self, frame_idx):
        """Drop tracks not seen for a while so old plates don't linger."""
        keep = []
        for t in self.tracks:
            if frame_idx - t["last"] <= self.max_age:
                keep.append(t)
            elif t["votes"]:
                self.finished.append(t)   # archive read plates for JSON export
        self.tracks = keep

    def export(self, fps, plate_format="none"):
        """Build a list of structured observations from every plate track.

        One entry per distinct plate track (both still-active and expired),
        carrying the fused text, its confidence, the owning vehicle class,
        first/last time in seconds, and the per-frame OCR reads that voted.
        This is the real data the dashboard consumes.

        When ``plate_format == 'indian'`` the fused text is also run through
        Indian-format correction; ``plate`` holds the corrected value while
        ``plate_raw`` keeps the uncorrected vote so the UI can show before/after.
        """
        observations = []
        seen = {}  # collapse repeated fused text to its highest-confidence entry
        for tr in (self.finished + self.tracks):
            if not tr["votes"]:
                continue
            raw = max(tr["votes"].items(), key=lambda kv: kv[1])[0]
            # confidence for the badge = best OCR conf among reads of the winner
            winner_confs = [h["conf"] for h in tr["history"]
                            if h["text"] == raw]
            ocr_conf = max(winner_confs) if winner_confs else 0.0
            detect_conf = (max(tr["detect_confs"]) if tr["detect_confs"]
                           else 0.0)
            frames = sorted(tr["history"], key=lambda h: h["frame"])

            plate, fmt_valid = raw, None
            if plate_format == "indian":
                plate, fmt_valid = normalize_indian_plate(raw)

            obs = {
                "plate": plate,
                "plate_raw": raw,
                "format_valid": fmt_valid,
                "vehicle": tr.get("vehicle", "vehicle"),
                "detect_conf": round(float(detect_conf), 3),
                "ocr_conf": round(float(ocr_conf), 3),
                "confidence": int(round(ocr_conf * 100)),
                "quality": "Good" if ocr_conf >= 0.80 else "Degraded",
                "first_seen": round(tr["first"] / fps, 2),
                "last_seen": round(tr["last"] / fps, 2),
                "reads": len(frames),
                "frames": [
                    {"frame": h["frame"], "text": h["text"],
                     "conf": int(round(h["conf"] * 100))}
                    for h in frames
                ],
            }
            # if the same plate string appears in two tracks, keep the stronger
            prev = seen.get(plate)
            if prev is None or obs["confidence"] > prev["confidence"]:
                seen[plate] = obs
        observations = sorted(seen.values(),
                              key=lambda o: o["first_seen"])
        return observations


# --------------------------------------------------------------------------- #
# Indian-format plate correction
# --------------------------------------------------------------------------- #
# An Indian plate is [2-letter state][2-digit RTO][0-3 letter series][4 digits],
# e.g. OD 02 BC 2442. Knowing which slots MUST be letters vs digits lets us undo
# the systematic OCR confusions (8<->B, 5<->S, 0<->O ...) deterministically,
# instead of hoping voting picks the right glyph. This is OPT-IN (--plate-format
# indian) so it never mangles non-Indian plates (e.g. the US demo video).

# Valid state / UT codes (includes the old 'OR' Odisha code alongside 'OD').
STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
    "MZ", "NL", "OD", "OR", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK",
    "UP", "WB",
}

# glyph that landed in a DIGIT slot -> the digit it almost certainly is
_TO_DIGIT = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2",
             "A": "4", "S": "5", "G": "6", "T": "7", "B": "8"}
# glyph that landed in a LETTER slot -> the letter it almost certainly is
_TO_LETTER = {"0": "O", "1": "I", "2": "Z", "4": "A", "5": "S", "6": "G",
              "7": "T", "8": "B"}
# per-character alternatives used only to repair the 2-letter STATE code, where
# the confusion can be letter<->letter (O<->Q) and slot-typing alone can't help
_STATE_ALTS = {
    "O": ["O", "Q", "D", "0"], "Q": ["Q", "O"], "D": ["D", "O"], "0": ["O", "D", "Q"],
    "S": ["S", "5"], "5": ["S"], "B": ["B", "8"], "8": ["B"], "I": ["I", "1"],
    "1": ["I"], "Z": ["Z", "2"], "2": ["Z"], "G": ["G", "6"], "6": ["G"],
    "A": ["A", "4"], "4": ["A"], "T": ["T", "7"], "7": ["T"], "U": ["U", "V"],
    "V": ["V", "U"],
}


def _to_digits(seg):
    return "".join(_TO_DIGIT.get(c, c) if not c.isdigit() else c for c in seg)


def _to_letters(seg):
    return "".join(_TO_LETTER.get(c, c) if not c.isalpha() else c for c in seg)


def _fix_state(seg):
    """Return a valid 2-letter state code by trying confusion alternatives,
    else the letter-forced segment (best effort)."""
    a, b = seg[0], seg[1]
    for c1 in _STATE_ALTS.get(a, [a]):
        for c2 in _STATE_ALTS.get(b, [b]):
            if (c1 + c2) in STATE_CODES:
                return c1 + c2
    return _to_letters(seg)


def normalize_indian_plate(text):
    """Correct an OCR read toward a valid Indian plate. Returns (corrected, ok).

    ``ok`` is True only when the result matches the expected structure with a
    known state code -- callers can use it to KEEP confidence high on a clean
    correction and LOWER it (never silently "fix") when the read doesn't fit,
    in keeping with the confidence-aware design.
    """
    if not text:
        return text, False
    s = "".join(ch for ch in text.upper() if ch.isalnum())
    # standard plate is 8-11 chars (2 state + 2 rto + 0..3 series + 4 number)
    if not (8 <= len(s) <= 11):
        return text, False
    state = _fix_state(s[:2])
    district = _to_digits(s[2:4])
    series = _to_letters(s[4:-4])
    number = _to_digits(s[-4:])
    corrected = state + district + series + number
    ok = (state in STATE_CODES and district.isdigit() and number.isdigit()
          and (series == "" or series.isalpha()))
    return corrected, ok


# --------------------------------------------------------------------------- #
# Drawing helpers
# --------------------------------------------------------------------------- #
def draw_label(frame, text, x, y, box_color):
    """Draw text with a filled background so it stays readable on any video."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale, thick = 0.6, 2
    (tw, th), base = cv2.getTextSize(text, font, scale, thick)
    y = max(y, th + 6)  # keep label on screen if the box is at the top edge
    cv2.rectangle(frame, (x, y - th - base - 4), (x + tw + 4, y), COLOR_TEXT_BG, -1)
    cv2.putText(frame, text, (x + 2, y - base), font, scale, box_color, thick)


def draw_plate_labels(frame, box, lines):
    """Draw a stacked block of labels anchored to a plate box, kept on-screen.

    ``lines`` is a list of ``(text, scale, text_color)`` drawn top-to-bottom on a
    single black panel. This keeps each line (e.g. "PLATE 0.92" and the OCR
    characters) on its own row so they never overlap each other or the box.

    Placement is adaptive:
      * the panel sits just BELOW the plate box by default;
      * if there is no room below (plate near the bottom edge) it flips to ABOVE;
      * horizontal and vertical positions are clamped so nothing leaves the frame.
    """
    frame_h, frame_w = frame.shape[:2]
    px1, py1, px2, py2 = box
    font = cv2.FONT_HERSHEY_SIMPLEX
    thick = 2
    pad_x, pad_y = 6, 5   # padding inside the panel
    line_gap = 6          # vertical space between rows
    margin = 6            # space between the plate box and the panel

    # measure every line so we can size one panel that fits them all
    sizes, block_w, content_h = [], 0, 0
    for text, scale, _color in lines:
        (tw, th), base = cv2.getTextSize(text, font, scale, thick)
        sizes.append((th, base))
        block_w = max(block_w, tw)
        content_h += th + base
    block_w += 2 * pad_x
    block_h = content_h + 2 * pad_y + line_gap * (len(lines) - 1)

    # vertical: prefer below the box, flip above if it would run off the bottom
    top = py2 + margin
    if top + block_h > frame_h:
        top = py1 - margin - block_h
    top = max(0, min(top, frame_h - block_h))   # final clamp inside the frame

    # horizontal: align to the plate's left edge, clamp inside the frame
    left = max(0, min(px1, frame_w - block_w))

    # one solid background panel for strong contrast
    cv2.rectangle(frame, (left, top), (left + block_w, top + block_h),
                  COLOR_TEXT_BG, -1)

    # draw each row of text
    y = top + pad_y
    for (text, scale, color), (th, base) in zip(lines, sizes):
        y += th
        cv2.putText(frame, text, (left + pad_x, y), font, scale, color, thick)
        y += base + line_gap


def center_inside(inner_box, outer_box):
    """True if the center of inner_box lies within outer_box.

    Used to say "this plate belongs to that vehicle" for the terminal log.
    """
    ix1, iy1, ix2, iy2 = inner_box
    cx, cy = (ix1 + ix2) / 2, (iy1 + iy2) / 2
    ox1, oy1, ox2, oy2 = outer_box
    return ox1 <= cx <= ox2 and oy1 <= cy <= oy2


# --------------------------------------------------------------------------- #
# Main pipeline
# --------------------------------------------------------------------------- #
def run(args):
    # --- Pick the compute device ------------------------------------------ #
    # "auto" uses the GPU if a CUDA build of torch sees one, else CPU.
    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    if device.startswith("cuda"):
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "?"
        print(f"[setup] device: {device} ({gpu_name})")
    else:
        if args.device == "auto":
            print("[setup] device: cpu (no CUDA GPU visible to torch -- see README 'GPU')")
        else:
            print("[setup] device: cpu")
    use_gpu = device.startswith("cuda")

    # --- Load the two detection models ------------------------------------- #
    print(f"[setup] loading vehicle model: {args.vehicle_model}")
    vehicle_model = YOLO(args.vehicle_model)  # auto-downloads yolov8n.pt if missing

    plate_model = None
    if os.path.exists(args.plate_model):
        print(f"[setup] loading plate model:   {args.plate_model}")
        plate_model = YOLO(args.plate_model)
    else:
        print(f"[warn] plate model not found at '{args.plate_model}'.")
        print("[warn] running VEHICLE DETECTION ONLY (no plate reading).")
        print("[warn] see README.md for how to download license_plate_detector.pt")

    # --- Load OCR ---------------------------------------------------------- #
    ocr = None
    if plate_model is not None and not args.no_ocr:
        try:
            print("[setup] loading OCR (EasyOCR)... first run downloads ~100MB")
            ocr = PlateOCR(gpu=use_gpu)
        except Exception as e:  # noqa: BLE001 - demo should degrade, not crash
            print(f"[warn] could not start OCR ({e}). Plates boxed but not read.")

    # --- Open the video / webcam ------------------------------------------- #
    source = 0 if args.source in ("0", "webcam") else args.source
    if isinstance(source, str) and not os.path.exists(source):
        print(f"[error] video not found: {source}")
        return

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[error] could not open source: {source}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Optional: write the annotated video to outputs/
    writer = None
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.save, fourcc, fps, (width, height))
        print(f"[setup] saving annotated video to: {args.save}")

    # Temporal aggregation: votes OCR reads of the same plate across frames.
    # --min-ocr-conf sets the low-confidence cutoff below which reads are ignored.
    aggregator = PlateAggregator(min_conf=args.min_ocr_conf)

    # Debug mode: save the first few crops actually sent to OCR so they can be
    # eyeballed, and print raw/processed reads.
    debug_dir = os.path.join(os.path.dirname(args.save) if args.save else ".",
                             "debug_crops")
    debug_saved = 0
    if args.debug:
        os.makedirs("outputs/debug_crops", exist_ok=True)
        debug_dir = "outputs/debug_crops"
        print(f"[debug] saving example plate crops to: {debug_dir}/")

    print("[run] processing... press 'q' in the window to quit.\n")

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            if args.loop:
                # rewind to the start and keep playing (good for a live demo)
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            break  # end of video
        frame_idx += 1

        # Skip frames to keep the demo responsive on CPU (OCR is slow).
        if args.frame_skip > 1 and (frame_idx % args.frame_skip) != 0:
            continue

        timestamp = frame_idx / fps  # seconds into the video

        # Keep a clean copy of the frame BEFORE we draw anything on it. Plate
        # detection and cropping use this clean copy, otherwise OCR would read
        # our own on-screen labels (e.g. "CAR 0.91") as if they were a plate.
        clean = frame.copy()

        # --- [1] vehicle detection ---------------------------------------- #
        # classes=... restricts YOLO to vehicle categories only.
        v_results = vehicle_model(
            frame, conf=args.conf, classes=list(VEHICLE_CLASSES),
            device=device, verbose=False
        )[0]

        vehicle_boxes = []
        for box in v_results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            name = VEHICLE_CLASSES.get(cls_id, "vehicle")
            vehicle_boxes.append(((x1, y1, x2, y2), name))

            cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_VEHICLE, 2)
            draw_label(frame, f"{name.upper()} {conf:.2f}", x1, y1, COLOR_VEHICLE)

        # --- [2] license-plate detection ---------------------------------- #
        if plate_model is not None:
            p_results = plate_model(clean, conf=args.plate_conf,
                                    device=device, verbose=False)[0]
            H, W = clean.shape[:2]
            for box in p_results.boxes:
                px1, py1, px2, py2 = map(int, box.xyxy[0])
                p_conf = float(box.conf[0])
                cv2.rectangle(frame, (px1, py1), (px2, py2), COLOR_PLATE, 2)

                # --- [3] crop the plate from the ORIGINAL frame, with a small
                #         padding, clamped so we never read outside the frame.
                #         Padding gives OCR a little breathing room around the
                #         glyphs without pulling in a lot of background.
                pad_x = int(0.06 * (px2 - px1))
                pad_y = int(0.20 * (py2 - py1))
                cx1, cy1 = max(0, px1 - pad_x), max(0, py1 - pad_y)
                cx2, cy2 = min(W, px2 + pad_x), min(H, py2 + pad_y)
                plate_crop = clean[cy1:cy2, cx1:cx2]

                # --- [4] OCR: upscale + preprocess variants + allowlist ---- #
                plate_text, ocr_conf, info = (None, 0.0, {})
                if ocr is not None:
                    try:
                        plate_text, ocr_conf, info = ocr.read(
                            plate_crop, debug=args.debug)
                    except Exception:  # noqa: BLE001 - never crash on a bad crop
                        plate_text, ocr_conf, info = None, 0.0, {}

                # which vehicle does this plate sit inside? (for the JSON +log)
                owner = "vehicle"
                for vbox, vname in vehicle_boxes:
                    if center_inside((px1, py1, px2, py2), vbox):
                        owner = vname
                        break

                # --- temporal aggregation: vote across consecutive frames -- #
                stable_text = aggregator.update(
                    (px1, py1, px2, py2), plate_text, ocr_conf, frame_idx,
                    detect_conf=p_conf, vehicle=owner)

                # optional Indian-format correction of the fused text
                display_text = stable_text
                if stable_text and args.plate_format == "indian":
                    display_text, _ok = normalize_indian_plate(stable_text)

                # --- [5] display + terminal log --------------------------- #
                # Always show plate DETECTION confidence; add the STABLE (voted)
                # OCR text beneath it on its own row (never overlapping).
                labels = [(f"PLATE {p_conf:.2f}", 0.6, COLOR_PLATE)]
                if display_text:
                    labels.append((display_text, 0.8, COLOR_OCR))
                draw_plate_labels(frame, (px1, py1, px2, py2), labels)

                # --- debug logging + crop dumps --------------------------- #
                if args.debug and info.get("crop_size"):
                    cw, ch = info["crop_size"]
                    uw, uh = info.get("up_size", (cw, ch))
                    variants_str = " ".join(
                        f"{n}={t}({c})" for n, t, c in info.get("variants", []))
                    print(f"[debug] Plate crop size: {cw}x{ch} -> upscaled {uw}x{uh}")
                    print(f"[debug] Raw OCR: {info.get('raw')} | "
                          f"Confidence: {info.get('conf')} | "
                          f"variant: {info.get('variant')} | [{variants_str}]")
                    print(f"[debug] Final plate (stable): {stable_text}")
                    if debug_saved < 12 and info.get("best_img") is not None:
                        tag = (info.get("raw") or "none")
                        cv2.imwrite(f"{debug_dir}/plate_{debug_saved:02d}_"
                                    f"{tag}.png", info["best_img"])
                        debug_saved += 1

                # terminal log of the stable result (one line per read)
                if stable_text:
                    vehicle_name = "vehicle"
                    for vbox, vname in vehicle_boxes:
                        if center_inside((px1, py1, px2, py2), vbox):
                            vehicle_name = vname
                            break
                    print(
                        f"[{timestamp:5.1f}s] Vehicle: {vehicle_name:10s} | "
                        f"Plate: {display_text:12s} | "
                        f"frame OCR conf: {ocr_conf:.2f}"
                    )

            aggregator.expire(frame_idx)

        # --- output ------------------------------------------------------- #
        if writer is not None:
            writer.write(frame)

        if not args.no_display:
            cv2.imshow("Traffic AI Demo - vehicle + plate OCR", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("\n[run] stopped by user.")
                break

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()

    # --- structured JSON export (what the dashboard consumes) -------------- #
    if args.json_out:
        observations = aggregator.export(fps, args.plate_format)
        confs = [o["confidence"] for o in observations]
        payload = {
            "source": os.path.basename(str(source)),
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "device": device,
            "camera": args.camera_id,
            "camera_name": args.camera_name,
            "summary": {
                "frames_processed": frame_idx,
                "unique_plates": len(observations),
                "avg_confidence": round(sum(confs) / len(confs), 1) if confs else 0,
            },
            "observations": observations,
        }
        os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
        import json
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[done] wrote {len(observations)} plate observations -> {args.json_out}")

    print("\n[done] finished.")


def parse_args():
    p = argparse.ArgumentParser(description="Traffic AI demo: vehicle detection + plate OCR")
    p.add_argument("--source",
                   default="../videos/vidssave.com License Plate Detection Test 1080p.mp4",
                   help="path to a video file, or '0' for webcam")
    p.add_argument("--vehicle-model", default="yolov8n.pt",
                   help="YOLO model for vehicles (auto-downloads if missing)")
    p.add_argument("--plate-model", default="models/license_plate_detector.pt",
                   help="YOLO model fine-tuned to find license plates")
    p.add_argument("--conf", type=float, default=0.4,
                   help="confidence threshold for vehicle detection")
    p.add_argument("--plate-conf", type=float, default=0.3,
                   help="confidence threshold for plate detection")
    p.add_argument("--frame-skip", type=int, default=2,
                   help="process every Nth frame (higher = faster, choppier)")
    p.add_argument("--min-ocr-conf", type=float, default=0.3,
                   help="ignore OCR reads below this confidence when voting")
    p.add_argument("--device", default="auto",
                   help="compute device: 'auto' (GPU if available), 'cuda', 'cpu'")
    p.add_argument("--save", default=None,
                   help="optional path to save annotated video, e.g. outputs/out.mp4")
    p.add_argument("--json-out", default=None,
                   help="optional path to write structured results JSON for the dashboard")
    p.add_argument("--camera-id", default="CAM001",
                   help="camera id stamped into the JSON output")
    p.add_argument("--camera-name", default="North Gate",
                   help="camera name stamped into the JSON output")
    p.add_argument("--no-display", action="store_true",
                   help="do not open a window (useful when only saving)")
    p.add_argument("--loop", action="store_true",
                   help="restart the video when it ends (keeps the demo window live)")
    p.add_argument("--plate-format", default="none", choices=["none", "indian"],
                   help="'indian' applies Indian-format character correction to reads")
    p.add_argument("--no-ocr", action="store_true",
                   help="detect + box plates but skip character reading")
    p.add_argument("--debug", action="store_true",
                   help="print raw/processed OCR per plate and save example crops")
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
