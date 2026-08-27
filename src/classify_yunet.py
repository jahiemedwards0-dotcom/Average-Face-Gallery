from __future__ import annotations

import json
import math
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


TERMINAL_CLASSIFICATION = {
    "accepted",
    "manual_review",
    "rejected_no_face",
    "rejected_decode",
    "duplicate_file",
    "download_failed",
}


def safe_component(value: Any, default: str = "unknown") -> str:
    text = str(value or "").strip() or default
    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:120] or default


def rotate_image(image: np.ndarray, degrees: int) -> np.ndarray:
    if degrees == 0:
        return image
    if degrees == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if degrees == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if degrees == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError(f"Unsupported rotation {degrees}")


@dataclass
class PoseEstimate:
    yaw_abs: float
    yaw_signed: float
    view: str
    method: str
    uncertain: bool
    uncertainty_reason: str
    components: dict[str, float]


def estimate_yaw_from_yunet(face: np.ndarray) -> PoseEstimate:
    """Coarse 5-point yaw proxy using landmark and face-box asymmetry.

    YuNet returns bbox x,y,w,h, score and five landmarks (eye/eye/nose/mouth/mouth).
    This deliberately reports an estimate, not a metric 3D head-pose solution.
    """
    x, y, w, h = [float(v) for v in face[:4]]
    pts = np.asarray(face[4:14], dtype=float).reshape(5, 2)
    eye1, eye2, nose, mouth1, mouth2 = pts
    if eye1[0] > eye2[0]:
        eye1, eye2 = eye2, eye1
    if mouth1[0] > mouth2[0]:
        mouth1, mouth2 = mouth2, mouth1

    eye_mid = (eye1 + eye2) / 2.0
    mouth_mid = (mouth1 + mouth2) / 2.0
    iod = max(1.0, abs(eye2[0] - eye1[0]))
    face_cx = x + w / 2.0

    nose_eye_offset = (nose[0] - eye_mid[0]) / iod
    mouth_eye_offset = (mouth_mid[0] - eye_mid[0]) / iod
    nose_box_offset = (nose[0] - face_cx) / max(w / 2.0, 1.0)

    left_margin = max(1.0, eye1[0] - x)
    right_margin = max(1.0, x + w - eye2[0])
    edge_log_ratio = math.log(right_margin / left_margin)

    # Each term reacts differently to crop tightness; robust weighted blending is more
    # stable than relying on nose displacement alone. The scale is empirically coarse.
    signed_score = (
        0.48 * nose_eye_offset
        + 0.18 * mouth_eye_offset
        + 0.22 * nose_box_offset
        + 0.12 * edge_log_ratio
    )
    yaw_signed = max(-90.0, min(90.0, signed_score * 72.0))
    yaw_abs = abs(yaw_signed)

    if yaw_abs <= 15.0:
        view = "front"
    elif yaw_abs < 55.0:
        view = "three_quarter"
    else:
        view = "side"

    reasons: list[str] = []
    eye_ratio = iod / max(w, 1.0)
    if eye_ratio < 0.16:
        reasons.append("eye_landmarks_compressed")
    if eye_ratio > 0.72:
        reasons.append("implausible_eye_spacing")
    for name, p in (("eye1", eye1), ("eye2", eye2), ("nose", nose), ("mouth1", mouth1), ("mouth2", mouth2)):
        if not (x - 0.08*w <= p[0] <= x + 1.08*w and y - 0.08*h <= p[1] <= y + 1.08*h):
            reasons.append(f"{name}_outside_face_box")
            break
    # Nose and mouth offsets should usually agree on the direction of turn.
    if abs(nose_eye_offset) > 0.12 and abs(mouth_eye_offset) > 0.12 and nose_eye_offset * mouth_eye_offset < 0:
        reasons.append("landmark_asymmetry_disagreement")
    edge_strength = abs(edge_log_ratio)
    if yaw_abs >= 55 and edge_strength < 0.08 and abs(nose_box_offset) < 0.18:
        reasons.append("pose_geometry_disagreement")
    if yaw_abs <= 15 and (edge_strength > 0.55 or abs(nose_box_offset) > 0.38):
        reasons.append("detection_pose_disagreement")
    if abs(signed_score) > 1.25:
        reasons.append("pose_proxy_saturated")

    reasons = list(dict.fromkeys(reasons))
    return PoseEstimate(
        yaw_abs=round(yaw_abs, 2),
        yaw_signed=round(yaw_signed, 2),
        view=view,
        method="yunet_5pt_landmark_bbox_asymmetry_v1",
        uncertain=bool(reasons),
        uncertainty_reason=";".join(reasons),
        components={
            "nose_eye_offset": round(nose_eye_offset, 4),
            "mouth_eye_offset": round(mouth_eye_offset, 4),
            "nose_box_offset": round(nose_box_offset, 4),
            "eye_edge_log_ratio": round(edge_log_ratio, 4),
            "interocular_face_ratio": round(eye_ratio, 4),
        },
    )


class YuNetClassifier:
    def __init__(
        self,
        model_path: Path,
        *,
        min_confidence: float = 0.75,
        min_face_px: int = 80,
        min_face_area_fraction: float = 0.03,
        similar_face_ratio: float = 0.65,
    ) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"YuNet model not found: {model_path}")
        self.model_path = Path(model_path)
        self.min_confidence = float(min_confidence)
        self.min_face_px = int(min_face_px)
        self.min_face_area_fraction = float(min_face_area_fraction)
        self.similar_face_ratio = float(similar_face_ratio)
        self.detector = cv2.FaceDetectorYN.create(
            str(self.model_path), "", (320, 320), self.min_confidence, 0.3, 5000
        )

    def _detect_rotation(self, image: np.ndarray, degrees: int) -> tuple[np.ndarray, np.ndarray | None]:
        rotated = rotate_image(image, degrees)
        h, w = rotated.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(rotated)
        if faces is not None:
            faces = faces[faces[:, 14] >= self.min_confidence]
        return rotated, faces

    def classify(self, image_path: Path) -> dict[str, Any]:
        try:
            with Image.open(image_path) as pil:
                pil = ImageOps.exif_transpose(pil).convert("RGB")
                image = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
        except Exception:
            image = None
        if image is None:
            return {
                "classification_status": "rejected_decode",
                "face_count": 0,
                "face_confidence": "",
                "dominant_bbox": "",
                "tested_rotations": "[]",
                "detection_rotation": "",
                "estimated_yaw": "",
                "yaw_signed": "",
                "view_class": "",
                "pose_method": "",
                "uncertainty_reason": "decode_failed",
            }

        tested: list[dict[str, Any]] = []
        candidates: list[tuple[float, int, np.ndarray, np.ndarray, np.ndarray]] = []
        total_qualified = 0
        for degrees in (0, 90, 180, 270):
            rotated, faces = self._detect_rotation(image, degrees)
            count = 0 if faces is None else int(len(faces))
            max_score = "" if count == 0 else round(float(faces[:, 14].max()), 5)
            tested.append({"rotation": degrees, "face_count": count, "max_confidence": max_score})
            total_qualified += count
            if faces is not None:
                for face in faces:
                    x, y, w, h = [float(v) for v in face[:4]]
                    score = float(face[14])
                    area = max(0.0, w * h)
                    dominance = score * math.sqrt(max(area, 1.0))
                    candidates.append((dominance, degrees, rotated, face.copy(), faces.copy()))

        if not candidates:
            return {
                "classification_status": "rejected_no_face",
                "face_count": 0,
                "face_confidence": "",
                "dominant_bbox": "",
                "tested_rotations": json.dumps(tested, separators=(",", ":")),
                "detection_rotation": "",
                "estimated_yaw": "",
                "yaw_signed": "",
                "view_class": "",
                "pose_method": "",
                "uncertainty_reason": "no_detection_at_or_above_threshold",
            }

        candidates.sort(key=lambda item: item[0], reverse=True)
        _, degrees, rotated, dominant, faces_same_rotation = candidates[0]
        x, y, w, h = [float(v) for v in dominant[:4]]
        score = float(dominant[14])
        img_h, img_w = rotated.shape[:2]
        face_area_fraction = (w * h) / max(float(img_h * img_w), 1.0)
        same_areas = sorted((float(f[2] * f[3]) for f in faces_same_rotation), reverse=True)

        reasons: list[str] = []
        if min(w, h) < self.min_face_px or face_area_fraction < self.min_face_area_fraction:
            reasons.append("dominant_face_too_small")
        if len(same_areas) > 1 and same_areas[1] / max(same_areas[0], 1.0) >= self.similar_face_ratio:
            reasons.append("multiple_similarly_sized_faces")

        pose = estimate_yaw_from_yunet(dominant)
        if pose.uncertain:
            reasons.extend([x for x in pose.uncertainty_reason.split(";") if x])

        status = "manual_review" if reasons else "accepted"
        return {
            "classification_status": status,
            "face_count": int(len(faces_same_rotation)),
            "face_confidence": round(score, 6),
            "dominant_bbox": json.dumps([round(x, 2), round(y, 2), round(w, 2), round(h, 2)]),
            "tested_rotations": json.dumps(tested, separators=(",", ":")),
            "detection_rotation": degrees,
            "estimated_yaw": pose.yaw_abs,
            "yaw_signed": pose.yaw_signed,
            "view_class": pose.view if status == "accepted" else "",
            "pose_method": pose.method,
            "pose_components": json.dumps(pose.components, separators=(",", ":")),
            "uncertainty_reason": ";".join(dict.fromkeys(reasons)),
            "face_area_fraction": round(face_area_fraction, 6),
        }


def organize_file(
    source: Path,
    row: dict[str, Any],
    classification: dict[str, Any],
    organized_root: Path,
) -> str:
    status = classification.get("classification_status")
    country = safe_component(row.get("country"))
    region = safe_component(row.get("region"))
    gender = safe_component(row.get("gender_label") or "unknown")
    candidate = safe_component(row.get("candidate_id"), "candidate")
    ext = source.suffix.lower() or ".img"
    if status == "accepted":
        view = safe_component(classification.get("view_class"), "unknown")
        dest = organized_root / "accepted" / view / country / region / gender / f"{candidate}{ext}"
    elif status == "manual_review":
        dest = organized_root / "manual_review" / country / region / f"{candidate}{ext}"
    else:
        return ""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    try:
        os.link(source, dest)
    except OSError:
        shutil.copy2(source, dest)
    return str(dest)


def make_contact_sheet(records: list[dict[str, Any]], title: str, out_path: Path, thumb=(180, 180), columns=5) -> None:
    pad = 12
    label_h = 42
    header_h = 56
    rows = max(1, math.ceil(max(1, len(records)) / columns))
    width = columns * (thumb[0] + pad) + pad
    height = header_h + rows * (thumb[1] + label_h + pad) + pad
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 16), f"{title} — {len(records)}", fill="black")
    if not records:
        draw.text((pad, header_h + 20), "No images in this category.", fill="black")
    for i, rec in enumerate(records):
        path = Path(str(rec.get("organized_filename") or rec.get("local_filename") or ""))
        if not path.exists():
            continue
        try:
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail(thumb)
                tile = Image.new("RGB", thumb, "#efefef")
                tile.paste(im, ((thumb[0]-im.width)//2, (thumb[1]-im.height)//2))
        except Exception:
            continue
        row_i, col_i = divmod(i, columns)
        x = pad + col_i * (thumb[0] + pad)
        y = header_h + row_i * (thumb[1] + label_h + pad)
        sheet.paste(tile, (x, y))
        cid = str(rec.get("candidate_id") or "")
        yaw = rec.get("estimated_yaw")
        label = cid + (f" | yaw {yaw}°" if yaw not in (None, "", float("nan")) else "")
        draw.text((x, y + thumb[1] + 4), label[:28], fill="black")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=90)
