from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


ROTATIONS = [0, 90, 180, 270]


def rotate_image(img: np.ndarray, rotation: int) -> np.ndarray:
    if rotation == 0:
        return img
    if rotation == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    if rotation == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    if rotation == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError(rotation)


def inverse_point(x: float, y: float, rotation: int, orig_w: int, orig_h: int) -> Tuple[float, float]:
    if rotation == 0:
        return x, y
    if rotation == 90:
        return y, (orig_h - 1) - x
    if rotation == 180:
        return (orig_w - 1) - x, (orig_h - 1) - y
    if rotation == 270:
        return (orig_w - 1) - y, x
    raise ValueError(rotation)


def inverse_bbox(box: List[float], rotation: int, orig_w: int, orig_h: int) -> List[float]:
    x, y, w, h = box
    corners = [
        inverse_point(x, y, rotation, orig_w, orig_h),
        inverse_point(x + w, y, rotation, orig_w, orig_h),
        inverse_point(x, y + h, rotation, orig_w, orig_h),
        inverse_point(x + w, y + h, rotation, orig_w, orig_h),
    ]
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return [max(0.0, min(xs)), max(0.0, min(ys)), max(xs) - min(xs), max(ys) - min(ys)]


def inverse_landmarks(points: np.ndarray, rotation: int, orig_w: int, orig_h: int) -> np.ndarray:
    return np.asarray([inverse_point(float(x), float(y), rotation, orig_w, orig_h) for x, y in points], dtype=np.float32)


def normalize_yunet_row(row: np.ndarray) -> Dict[str, Any]:
    row = np.asarray(row, dtype=float).reshape(-1)
    return {
        "bbox": row[:4].tolist(),
        "landmarks": row[4:14].reshape(5, 2).tolist(),
        "confidence": float(row[14]),
    }


def _pnp_yaw(landmarks: np.ndarray, image_w: int, image_h: int) -> Optional[float]:
    # Generic 5-point face model. Absolute yaw is intentionally coarse.
    # Point order is YuNet: right eye, left eye, nose, right mouth, left mouth.
    model = np.array(
        [
            [-30.0, 32.0, -30.0],
            [30.0, 32.0, -30.0],
            [0.0, 0.0, 0.0],
            [-25.0, -28.0, -20.0],
            [25.0, -28.0, -20.0],
        ],
        dtype=np.float64,
    )
    image_points = np.asarray(landmarks, dtype=np.float64)
    focal = float(max(image_w, image_h))
    camera = np.array(
        [[focal, 0, image_w / 2.0], [0, focal, image_h / 2.0], [0, 0, 1]],
        dtype=np.float64,
    )
    dist = np.zeros((4, 1), dtype=np.float64)
    try:
        ok, rvec, _ = cv2.solvePnP(model, image_points, camera, dist, flags=cv2.SOLVEPNP_EPNP)
        if not ok:
            return None
        rot, _ = cv2.Rodrigues(rvec)
        # OpenCV Euler extraction; yaw around vertical axis.
        sy = math.sqrt(rot[0, 0] ** 2 + rot[1, 0] ** 2)
        singular = sy < 1e-6
        if not singular:
            yaw = math.degrees(math.atan2(-rot[2, 0], sy))
        else:
            yaw = math.degrees(math.atan2(-rot[2, 0], sy))
        if not math.isfinite(yaw):
            return None
        return float(yaw)
    except cv2.error:
        return None


def heuristic_yaw(landmarks: np.ndarray, bbox: List[float]) -> Tuple[float, Dict[str, float]]:
    pts = np.asarray(landmarks, dtype=float)
    eyes = sorted(pts[:2], key=lambda p: p[0])
    mouths = sorted(pts[3:5], key=lambda p: p[0])
    left_eye, right_eye = np.asarray(eyes[0]), np.asarray(eyes[1])
    left_mouth, right_mouth = np.asarray(mouths[0]), np.asarray(mouths[1])
    nose = pts[2]
    box_w = max(float(bbox[2]), 1.0)

    eye_mid_x = (left_eye[0] + right_eye[0]) / 2.0
    mouth_mid_x = (left_mouth[0] + right_mouth[0]) / 2.0
    center_x = (eye_mid_x + mouth_mid_x) / 2.0
    nose_shift_norm = (nose[0] - center_x) / (0.5 * box_w)

    dl = abs(nose[0] - left_eye[0])
    dr = abs(right_eye[0] - nose[0])
    asymmetry = abs(dl - dr) / max(dl + dr, 1e-6)

    eye_span_ratio = abs(right_eye[0] - left_eye[0]) / box_w
    mouth_span_ratio = abs(right_mouth[0] - left_mouth[0]) / box_w

    shift_component = min(85.0, 105.0 * abs(nose_shift_norm))
    asym_component = min(85.0, 82.0 * asymmetry)
    eye_compression_component = np.clip((0.34 - eye_span_ratio) / 0.16, 0.0, 1.0) * 70.0
    mouth_compression_component = np.clip((0.31 - mouth_span_ratio) / 0.15, 0.0, 1.0) * 55.0

    yaw_mag = float(max(shift_component, asym_component, eye_compression_component, mouth_compression_component))
    sign = 1.0 if nose_shift_norm >= 0 else -1.0
    return sign * yaw_mag, {
        "nose_shift_norm": float(nose_shift_norm),
        "eye_asymmetry": float(asymmetry),
        "eye_span_ratio": float(eye_span_ratio),
        "mouth_span_ratio": float(mouth_span_ratio),
        "heuristic_abs_yaw": float(yaw_mag),
    }


def estimate_pose(landmarks: np.ndarray, bbox: List[float], image_w: int, image_h: int) -> Dict[str, Any]:
    hyaw, metrics = heuristic_yaw(landmarks, bbox)
    pyaw = _pnp_yaw(landmarks, image_w, image_h)
    reasons: List[str] = []

    if pyaw is None:
        yaw = hyaw
        method = "yunet_5pt_asymmetry_eye_compression"
        reasons.append("pnp_unavailable")
        disagreement = None
    else:
        # Blend toward the heuristic because five-point PnP is sensitive to generic 3D assumptions.
        sign = np.sign(hyaw if abs(hyaw) >= 5 else pyaw) or 1.0
        yaw_abs = 0.55 * abs(float(pyaw)) + 0.45 * abs(float(hyaw))
        yaw = float(sign * min(yaw_abs, 90.0))
        method = "yunet_5pt_pnp+asymmetry_eye_compression"
        disagreement = abs(abs(float(pyaw)) - abs(float(hyaw)))
        if disagreement > 25:
            reasons.append("pnp_heuristic_disagreement")

    abs_yaw = abs(float(yaw))
    if abs_yaw <= 15:
        view = "front"
    elif abs_yaw < 55:
        view = "three_quarter"
    else:
        view = "side"

    # Landmark degeneracy checks.
    if metrics["eye_span_ratio"] < 0.08 or metrics["mouth_span_ratio"] < 0.06:
        reasons.append("landmark_geometry_unstable")
    if metrics["eye_span_ratio"] > 0.70 or metrics["mouth_span_ratio"] > 0.75:
        reasons.append("landmark_geometry_implausible")

    return {
        "estimated_yaw": round(float(yaw), 2),
        "abs_yaw": round(abs_yaw, 2),
        "view": view,
        "pose_method": method,
        "pose_metrics": json.dumps(metrics, ensure_ascii=False),
        "pnp_yaw": "" if pyaw is None else round(float(pyaw), 2),
        "pose_disagreement_deg": "" if disagreement is None else round(float(disagreement), 2),
        "pose_uncertainty_reason": ";".join(sorted(set(reasons))),
    }


@dataclass
class YuNetClassifier:
    model_path: Path
    min_confidence: float = 0.75
    min_face_area_fraction: float = 0.04
    similar_face_area_ratio: float = 0.70

    def __post_init__(self) -> None:
        self.detector = cv2.FaceDetectorYN.create(
            str(self.model_path),
            "",
            (320, 320),
            score_threshold=float(self.min_confidence),
            nms_threshold=0.3,
            top_k=5000,
        )

    def classify(self, image_path: Path) -> Dict[str, Any]:
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            return {
                "classification_status": "rejected_decode",
                "face_count": 0,
                "confidence": "",
                "dominant_bbox": "",
                "tested_rotations": "[]",
                "estimated_yaw": "",
                "view": "",
                "pose_method": "",
                "pose_uncertainty_reason": "opencv_decode_failed",
            }

        orig_h, orig_w = image.shape[:2]
        tested = []
        candidates: List[Dict[str, Any]] = []

        for rotation in ROTATIONS:
            rotated = rotate_image(image, rotation)
            h, w = rotated.shape[:2]
            self.detector.setInputSize((w, h))
            _, faces = self.detector.detect(rotated)
            qualifying = []
            if faces is not None:
                for row in faces:
                    parsed = normalize_yunet_row(row)
                    if parsed["confidence"] >= self.min_confidence:
                        qualifying.append(parsed)
            max_conf = max([f["confidence"] for f in qualifying], default=0.0)
            tested.append({"rotation": rotation, "face_count": len(qualifying), "max_confidence": round(max_conf, 5)})
            for f in qualifying:
                f["rotation"] = rotation
                area = max(0.0, f["bbox"][2]) * max(0.0, f["bbox"][3])
                f["area"] = area
                f["rank_score"] = f["confidence"] * math.sqrt(max(area, 1.0))
                candidates.append(f)

        if not candidates:
            return {
                "classification_status": "rejected_no_face",
                "face_count": 0,
                "confidence": "",
                "dominant_bbox": "",
                "tested_rotations": json.dumps(tested),
                "estimated_yaw": "",
                "view": "",
                "pose_method": "",
                "pose_uncertainty_reason": "no_detection_at_or_above_threshold",
            }

        # Select best in-plane rotation using confidence and face size.
        by_rotation: Dict[int, List[Dict[str, Any]]] = {}
        for c in candidates:
            by_rotation.setdefault(c["rotation"], []).append(c)
        best_rotation = max(
            by_rotation,
            key=lambda r: max((c["rank_score"] for c in by_rotation[r]), default=0.0),
        )
        faces = sorted(by_rotation[best_rotation], key=lambda c: (c["rank_score"], c["confidence"]), reverse=True)
        dominant = faces[0]

        bbox_orig = inverse_bbox(dominant["bbox"], best_rotation, orig_w, orig_h)
        lm_rot = np.asarray(dominant["landmarks"], dtype=np.float32)
        lm_orig = inverse_landmarks(lm_rot, best_rotation, orig_w, orig_h)
        face_area_fraction = float((bbox_orig[2] * bbox_orig[3]) / max(orig_w * orig_h, 1))
        reasons: List[str] = []

        if face_area_fraction < self.min_face_area_fraction:
            reasons.append("dominant_face_too_small")

        if len(faces) > 1:
            second = faces[1]
            if second["area"] / max(dominant["area"], 1.0) >= self.similar_face_area_ratio:
                reasons.append("several_similarly_sized_faces")

        pose = estimate_pose(lm_orig, bbox_orig, orig_w, orig_h)
        if pose["pose_uncertainty_reason"]:
            reasons.extend(pose["pose_uncertainty_reason"].split(";"))

        status = "manual_review" if reasons else "accepted"
        return {
            "classification_status": status,
            "face_count": len(faces),
            "confidence": round(float(dominant["confidence"]), 6),
            "dominant_bbox": json.dumps([round(float(v), 2) for v in bbox_orig]),
            "dominant_landmarks": json.dumps([[round(float(x), 2), round(float(y), 2)] for x, y in lm_orig]),
            "tested_rotations": json.dumps(tested),
            "selected_rotation": best_rotation,
            "face_area_fraction": round(face_area_fraction, 6),
            **pose,
            "pose_uncertainty_reason": ";".join(sorted(set(reasons))),
        }
