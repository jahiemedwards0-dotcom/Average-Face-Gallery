from __future__ import annotations

import csv
import math
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

import cv2
import mediapipe as mp
import numpy as np
import requests
from PIL import Image

QIDS = """
Q114151333 Q97798464 Q122979270 Q123284509 Q130396983 Q56434240 Q42275814 Q91098708 Q113465829 Q111513207 Q121564922 Q1070892 Q108653147 Q125956784 Q970924 Q16186773 Q1452690 Q5831545 Q124547405 Q2617063 Q1427500 Q26838665 Q115253843 Q124407983 Q16020877 Q5941542 Q91231670 Q121141916 Q114350202 Q16661532 Q5983543 Q114284397 Q8016680 Q251862 Q107379567 Q19950105 Q88569185 Q139827164 Q124680095 Q91112052 Q16624326 Q6112289 Q34489788 Q42391140 Q27919326 Q50416447 Q1036356 Q28846115 Q5771849 Q110624198 Q6100089 Q6125055 Q19949648 Q3082388 Q134302833 Q5945758 Q5996346 Q113361829 Q1294997 Q16546230 Q24579373 Q28055713 Q59663279 Q18417257 Q2023034 Q23415055 Q65160298 Q1373223 Q346714 Q28026397 Q21941974 Q22304369 Q47500159 Q28026469 Q428038 Q2839532 Q6962910 Q741251 Q4353107 Q650983 Q6016674 Q16556710 Q109914078 Q22815263 Q28091150 Q63871962 Q26780801 Q63856896 Q121084872 Q50571960 Q94435007 Q19787500 Q113581150 Q113358934 Q728932 Q19506797 Q59754954 Q109591376 Q16868611 Q109660975 Q6774142 Q48982129 Q21936667 Q19952988 Q3144570 Q61518697 Q1703785 Q6050470 Q16685986 Q16979876 Q1032038 Q16196319 Q5954685 Q4929610 Q5382197 Q7688917 Q5925231 Q6750974 Q7628596 Q4025530 Q27671211 Q27671211 Q3605478 Q3605478 Q23641607 Q846086 Q59655870 Q3474203 Q10900259 Q5945231 Q9145064 Q54255629 Q111516944 Q58365024 Q123521606 Q16200402 Q14775760 Q18631698 Q64814798 Q96190117 Q2476512 Q102195189 Q983091 Q16300923 Q66310128 Q96335553 Q1839290 Q18613824 Q120734130 Q2435922 Q48917397 Q63226471 Q15055066 Q10290183 Q5925011 Q5769005 Q5771719 Q6968096 Q17276366 Q5802297 Q23907249 Q23641323 Q6110723 Q17364549 Q65159448 Q62995595 Q18223509 Q122146738 Q5759823 Q5997075 Q18643822 Q28055682 Q6110831 Q5736171 Q20016713 Q29405052 Q26488726 Q6124183 Q1647809 Q16146906 Q60448192 Q23907155 Q19519157 Q40742806 Q131390253 Q26710813 Q5851513 Q2383614 Q26916844 Q174551 Q5550274 Q52005880 Q35599937 Q85772216 Q16146246 Q5974594 Q137261837 Q3064249 Q65018192 Q65018192 Q96677616 Q11252036 Q5554695 Q20109680 Q55189120 Q16191183 Q102104819 Q63684016 Q70088712 Q110630467 Q18221096 Q437836 Q63683352 Q970467 Q109563161 Q26465252 Q1806613 Q6167750 Q114399751 Q113612928 Q21694283 Q5725144 Q6405354 Q85684660 Q237467 Q29052147 Q127513288 Q16735435 Q8060948 Q12164731 Q132089370 Q30904398 Q114399751 Q1981903 Q368441 Q5639362 Q21001010 Q5949408 Q9015744 Q20991889 Q2878985 Q5993201 Q29376389 Q55237613 Q6168131 Q117344066 Q5376629 Q141152366 Q7089857 Q56066028 Q56294288 Q3541194 Q138646381 Q59756693 Q21065097 Q85699960 Q84763432 Q6555486 Q2723197 Q15229412 Q65013174 Q65013174 Q60031472 Q296965 Q63342260 Q51796168 Q6003481 Q56250366 Q6547740 Q18718817 Q21856062 Q6850425 Q41658575 Q20968365 Q66738093 Q21856277 Q23907268 Q70118092 Q62118467 Q5750328 Q118596781 Q72419224 Q5483821 Q5616172 Q561621 Q23907196 Q19667521 Q93275357 Q6756570 Q41587454 Q5394816 Q16612848 Q51685746 Q5888694 Q138297347 Q6109642 Q114886953 Q3318808 Q9009165 Q25413242 Q134401528 Q47538734 Q3735066 Q20948811 Q7131705 Q2553193 Q5835788 Q140088188 Q6436448 Q55097276 Q5992361 Q16186990 Q2313245 Q107297634 Q2409543 Q58433838 Q16147435 Q65167372 Q118111821 Q1613729 Q29027516 Q41156807 Q132859888 Q5833805 Q16300610 Q64099923 Q16941866 Q524685 Q6037545 Q6056241 Q3424470 Q509164 Q2057751 Q68838444 Q4353514 Q127604397 Q28033884 Q65965693 Q39058310 Q42295231 Q5571374 Q5893695 Q5954777 Q56378550 Q110103476 Q2889056 Q19560051 Q51685466 Q7145656 Q6119968 Q6128520 Q2641796 Q51078050 Q29010854 Q6170499 Q94706986 Q5665345 Q20013005 Q104847432 Q1706512 Q1706512 Q20740881 Q5817670 Q2840134 Q104852316 Q4497659 Q123337877 Q20995119 Q74249843 Q108150858 Q9025043 Q925167 Q19722004 Q28501273 Q81215452 Q1362609 Q3357006 Q98034086 Q55814321 Q2179224 Q9075375 Q63801221 Q537339 Q127291475 Q36027294 Q6111237 Q5925435 Q1269772 Q705977 Q33093740 Q28048262 Q5913379 Q5971585 Q438488 Q27859501 Q62939333 Q5751476 Q231348 Q28650094 Q18414114 Q20017110 Q1259738 Q1259738 Q5925008 Q2733919 Q5644072 Q1876444 Q6055815 Q59771455 Q5904363 Q1571578 Q6700569 Q51048820 Q27728364 Q16302250 Q22957678
""".split()

# The uploaded CSV has 416 rows but 409 unique people/images.
# Keep one image per person so repeated people are omitted.
QIDS = list(dict.fromkeys(QIDS))

OUT = Path(os.environ.get("OUTPUT_DIR", "query3_pose_sorted"))
for name in ("front", "three_quarter", "side", "uncertain"):
    (OUT / name).mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "query3-pose-sort/1.0 (GitHub Actions; educational dataset)"})


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]


def entity_metadata(qids):
    out = {}
    api = "https://www.wikidata.org/w/api.php"
    for batch in chunks(qids, 50):
        params = {
            "action": "wbgetentities",
            "ids": "|".join(batch),
            "props": "labels|claims",
            "languages": "en|es",
            "format": "json",
        }
        r = SESSION.get(api, params=params, timeout=60)
        r.raise_for_status()
        entities = r.json().get("entities", {})
        for qid in batch:
            e = entities.get(qid, {})
            labels = e.get("labels", {})
            label = labels.get("es", labels.get("en", {})).get("value", qid)
            claims = e.get("claims", {}).get("P18", [])
            filename = None
            if claims:
                try:
                    filename = claims[0]["mainsnak"]["datavalue"]["value"]
                except Exception:
                    filename = None
            out[qid] = {"label": label, "commons_filename": filename}
        time.sleep(0.15)
    return out


def safe_slug(s):
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s.strip())
    return s.strip("._")[:90] or "person"


def download_commons(filename, dest_base):
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(filename, safe="")
    last = None
    for attempt in range(4):
        try:
            r = SESSION.get(url, timeout=120, allow_redirects=True)
            r.raise_for_status()
            ctype = r.headers.get("content-type", "")
            if not ctype.startswith("image/"):
                raise RuntimeError(f"not an image: {ctype}")
            suffix = Path(filename).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
                suffix = ".jpg"
            path = dest_base.with_suffix(suffix)
            path.write_bytes(r.content)
            return path, url
        except Exception as e:
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(last)


def load_rgb(path):
    with Image.open(path) as im:
        im = im.convert("RGB")
        # Limit extremely large Commons files for landmark detection only.
        max_dim = 2200
        if max(im.size) > max_dim:
            scale = max_dim / max(im.size)
            im = im.resize((int(im.width * scale), int(im.height * scale)))
        return np.asarray(im)


def estimate_pose(rgb, face_mesh):
    h, w = rgb.shape[:2]
    result = face_mesh.process(rgb)
    if not result.multi_face_landmarks:
        return "uncertain", None, None, 0, "no_face_mesh"

    faces = []
    for lmset in result.multi_face_landmarks:
        pts = lmset.landmark
        xs = np.array([p.x for p in pts])
        ys = np.array([p.y for p in pts])
        area = max(0.0, (xs.max() - xs.min()) * (ys.max() - ys.min()))
        faces.append((area, pts))
    faces.sort(key=lambda x: x[0], reverse=True)
    pts = faces[0][1]

    # PnP yaw estimate from stable facial landmarks.
    idx = [1, 152, 33, 263, 61, 291]
    image_points = np.array([(pts[i].x * w, pts[i].y * h) for i in idx], dtype=np.float64)
    model_points = np.array([
        (0.0, 0.0, 0.0),
        (0.0, -330.0, -65.0),
        (-225.0, 170.0, -135.0),
        (225.0, 170.0, -135.0),
        (-150.0, -150.0, -125.0),
        (150.0, -150.0, -125.0),
    ], dtype=np.float64)
    focal = float(w)
    center = (w / 2.0, h / 2.0)
    camera = np.array([[focal, 0, center[0]], [0, focal, center[1]], [0, 0, 1]], dtype=np.float64)
    dist = np.zeros((4, 1), dtype=np.float64)
    yaw_pnp = None
    try:
        ok, rvec, _ = cv2.solvePnP(model_points, image_points, camera, dist, flags=cv2.SOLVEPNP_ITERATIVE)
        if ok:
            rmat, _ = cv2.Rodrigues(rvec)
            angles = cv2.RQDecomp3x3(rmat)[0]
            yaw_pnp = float(angles[1])
            while yaw_pnp > 90:
                yaw_pnp -= 180
            while yaw_pnp < -90:
                yaw_pnp += 180
    except Exception:
        yaw_pnp = None

    # Independent 2-D asymmetry estimate: nose displacement relative to eye span.
    x1, x2 = sorted([pts[33].x, pts[263].x])
    eye_span = max(1e-6, x2 - x1)
    eye_mid = (x1 + x2) / 2.0
    nose_offset = abs((pts[1].x - eye_mid) / eye_span)
    yaw_proxy = min(90.0, nose_offset * 105.0)

    if yaw_pnp is None or not math.isfinite(yaw_pnp):
        yaw = yaw_proxy
    else:
        # Blend rather than trusting either noisy estimate alone.
        yaw = 0.65 * abs(yaw_pnp) + 0.35 * yaw_proxy

    # Conservative bins. Near boundaries go to uncertain for later manual review.
    if 13.0 <= yaw <= 17.0 or 47.0 <= yaw <= 53.0:
        category = "uncertain"
        note = "boundary"
    elif yaw < 15.0:
        category = "front"
        note = ""
    elif yaw < 50.0:
        category = "three_quarter"
        note = ""
    else:
        category = "side"
        note = ""
    return category, yaw, yaw_pnp, len(faces), note


def main():
    meta = entity_metadata(QIDS)
    rows = []
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=5, refine_landmarks=False, min_detection_confidence=0.35) as mesh:
        for i, qid in enumerate(QIDS, 1):
            m = meta.get(qid, {})
            label = m.get("label", qid)
            commons_filename = m.get("commons_filename")
            stem = f"{i:04d}_{safe_slug(label)}_{qid}"
            status = "ok"
            err = ""
            local_path = None
            source_url = ""
            category = "uncertain"
            yaw = yaw_pnp = None
            face_count = 0
            note = ""
            try:
                if not commons_filename:
                    raise RuntimeError("no P18 image on Wikidata")
                temp_base = OUT / "_downloads" / stem
                temp_base.parent.mkdir(parents=True, exist_ok=True)
                local_path, source_url = download_commons(commons_filename, temp_base)
                rgb = load_rgb(local_path)
                category, yaw, yaw_pnp, face_count, note = estimate_pose(rgb, mesh)
                final_path = OUT / category / local_path.name
                local_path.replace(final_path)
                local_path = final_path
            except Exception as e:
                status = "error"
                err = str(e)[:500]
                if local_path and local_path.exists():
                    final_path = OUT / "uncertain" / local_path.name
                    local_path.replace(final_path)
                    local_path = final_path
            rows.append({
                "qid": qid,
                "personLabel": label,
                "commons_filename": commons_filename or "",
                "category": category,
                "estimated_yaw_deg": "" if yaw is None else f"{yaw:.2f}",
                "pnp_yaw_deg": "" if yaw_pnp is None else f"{yaw_pnp:.2f}",
                "faces_detected": face_count,
                "status": status,
                "note": note,
                "error": err,
                "source_url": source_url,
                "output_file": "" if local_path is None else str(local_path.relative_to(OUT)),
            })
            print(f"[{i}/{len(QIDS)}] {label}: {category} yaw={yaw}", flush=True)

    dl = OUT / "_downloads"
    if dl.exists():
        try:
            dl.rmdir()
        except OSError:
            pass

    manifest = OUT / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    counts = {k: sum(r["category"] == k for r in rows) for k in ("front", "three_quarter", "side", "uncertain")}
    errors = sum(r["status"] != "ok" for r in rows)
    (OUT / "README.txt").write_text(
        "Query-3 Wikimedia images sorted by estimated head pose.\n"
        f"Unique people: {len(QIDS)}\n"
        + "\n".join(f"{k}: {v}" for k, v in counts.items())
        + f"\nDownload/classification errors: {errors}\n\n"
        "Pose bins: front <15 degrees, three-quarter 15-50 degrees, side >=50 degrees.\n"
        "Images near thresholds and images without a reliable face mesh are placed in uncertain.\n"
        "The largest detected face is treated as the subject when an image contains multiple faces.\n"
        "See manifest.csv for the person, source image, estimated yaw, and classification.\n",
        encoding="utf-8",
    )
    print("COUNTS", counts, "errors", errors)


if __name__ == "__main__":
    main()
