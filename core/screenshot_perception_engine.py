"""
Screenshot Perception Engine (AMAF 5.0)
Pure-Python + PIL + NumPy Visual Perception Pipeline for Android Multi-Phone Farm.
Inspired by:
- Microsoft OmniParser (Pure-vision gradient/connected-region UI detector for WebView/Canvas/Games)
- Google Research android_world M3A (Set-of-Mark SoM visual grounding badges #1, #2, ...)
- Alibaba Mobile-Agent-v2 (Coarse-to-Fine Crop & Bicubic Zoom for small icons/text)
- AirtestProject/Airtest (Fast Multi-Scale Normalized Cross-Correlation template matching)
- Maestro assertScreenshot (Pixel-level visual regression diffing & PSNR/MAE heatmap generation)
"""

import hashlib
import os
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper


class ScreenshotPerceptionEngine:
    """
    High-speed, zero-OpenCV visual perception engine combining ADB screenshot capture,
    OmniParser-style Sobel region detection, M3A Set-of-Mark annotation, Coarse-to-Fine
    Crop/Zoom, Airtest-style pyramid NCC template matching, and Maestro visual diffing.
    """

    def __init__(self, adb: Optional[ADBWrapper] = None, output_dir: Optional[Path] = None):
        self.adb = adb or ADBWrapper()
        self.output_dir = (
            Path(output_dir)
            if output_dir
            else (Path(__file__).resolve().parent.parent / "reports" / "screenshots")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.capture_history: List[Dict[str, Any]] = []

    def create_synthetic_screen_image(
        self,
        width: int = 720,
        height: int = 1600,
        elements: Optional[List[Dict[str, Any]]] = None,
        save_path: Optional[str] = None,
    ) -> str:
        """
        Create a clean synthetic RGB PNG screenshot using PIL.Image and ImageDraw
        with optional drawn rectangular UI elements, buttons, or puzzle tracks.
        Useful when a device is offline or during deterministic unit tests.
        """
        img = Image.new("RGB", (width, height), color=(244, 246, 250))
        draw = ImageDraw.Draw(img)

        default_elements = [
            {
                "x1": 0,
                "y1": 0,
                "x2": width,
                "y2": 96,
                "fill": (30, 41, 59),
                "outline": (15, 23, 42),
                "label": "Status & Header Bar",
            },
            {
                "x1": 40,
                "y1": 160,
                "x2": width - 40,
                "y2": 360,
                "fill": (255, 255, 255),
                "outline": (59, 130, 246),
                "label": "Hero Banner Card",
            },
            {
                "x1": 80,
                "y1": 440,
                "x2": width - 80,
                "y2": 530,
                "fill": (37, 99, 235),
                "outline": (29, 78, 216),
                "label": "Primary Action Button",
            },
            {
                "x1": 80,
                "y1": 580,
                "x2": width - 80,
                "y2": 670,
                "fill": (16, 185, 129),
                "outline": (5, 150, 105),
                "label": "Confirm / Login",
            },
            {
                "x1": 60,
                "y1": 760,
                "x2": width - 60,
                "y2": 920,
                "fill": (226, 232, 240),
                "outline": (100, 116, 139),
                "label": "Puzzle Slider Track",
            },
            {
                "x1": 90,
                "y1": 790,
                "x2": 190,
                "y2": 890,
                "fill": (245, 158, 11),
                "outline": (180, 83, 9),
                "label": "Slider Knob",
            },
        ]

        render_list = elements if elements is not None else default_elements
        for idx, el in enumerate(render_list):
            bounds = el.get("bounds", el)
            x1 = int(bounds.get("x1", 60))
            y1 = int(bounds.get("y1", 120 + idx * 140))
            x2 = int(bounds.get("x2", min(width - 60, x1 + 240)))
            y2 = int(bounds.get("y2", min(height - 60, y1 + 90)))
            fill = tuple(el.get("fill", (59, 130, 246)))
            outline = tuple(el.get("outline", (15, 23, 42)))
            label = str(el.get("label", el.get("text", f"Element_{idx + 1}")))

            draw.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=3)
            # Draw inner accent cross/text so template matching has unique gradient texture
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            draw.line([(x1 + 8, cy), (x2 - 8, cy)], fill=outline, width=1)
            draw.line([(cx, y1 + 8), (cx, y2 - 8)], fill=outline, width=1)
            if label:
                text_color = (255, 255, 255) if sum(fill) < 400 else (15, 23, 42)
                draw.text((x1 + 14, max(y1 + 6, cy - 6)), label, fill=text_color)

        if save_path:
            target = Path(save_path)
            target.parent.mkdir(parents=True, exist_ok=True)
        else:
            ts = int(time.time() * 1000)
            target = self.output_dir / f"synthetic_screen_{ts}.png"

        img.save(str(target), format="PNG")
        return str(target.resolve())

    def capture_screenshot_auto(
        self,
        serial: str,
        tag: str = "auto",
        fallback_synthetic: bool = True,
    ) -> Dict[str, Any]:
        """
        Capture a live PNG screenshot via ADB, falling back to a synthetic screenshot
        when offline/unavailable if fallback_synthetic=True. Computes full visual telemetry.
        """
        safe_serial = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(serial))
        ts_ms = int(time.time() * 1000)
        target_path = (self.output_dir / f"screen_{safe_serial}_{tag}_{ts_ms}.png").resolve()

        captured_live = False
        try:
            captured_live = bool(self.adb.capture_screenshot(serial, str(target_path)))
        except Exception:
            captured_live = False

        if (not captured_live or not target_path.exists() or target_path.stat().st_size == 0) and fallback_synthetic:
            self.create_synthetic_screen_image(save_path=str(target_path))

        raw_bytes = target_path.read_bytes()
        sha256_hex = hashlib.sha256(raw_bytes).hexdigest()

        img = Image.open(target_path).convert("RGB")
        width, height = img.size
        arr = np.asarray(img, dtype=np.float32)

        # Standard luminance grayscale conversion
        gray = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
        mean_brightness = float(np.mean(gray))
        contrast_std = float(np.std(gray))

        gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
        gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
        edge_density = float(np.mean(gx + gy) / 255.0)
        is_blank = bool(contrast_std < 2.0)

        record = {
            "serial": serial,
            "tag": tag,
            "screenshot_path": str(target_path),
            "width": int(width),
            "height": int(height),
            "sha256": sha256_hex,
            "mean_brightness": round(mean_brightness, 3),
            "contrast_std": round(contrast_std, 3),
            "edge_density": round(edge_density, 5),
            "is_blank": is_blank,
            "live_captured": captured_live,
            "timestamp": time.time(),
        }
        self.capture_history.append(record)
        return record

    def detect_pure_vision_regions(
        self,
        image_path: str,
        max_regions: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Pure-vision screen parser (OmniParser style) for WebView/Canvas/Flutter/Games
        where UIAutomator XML is empty or incomplete.
        Uses Sobel-like horizontal & vertical gradients and grid-patch connected components.
        """
        img = Image.open(image_path).convert("L")
        width, height = img.size
        gray = np.asarray(img, dtype=np.float32)

        gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
        gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
        grad = gx + gy

        patch_size = 36
        grid_h = max(1, (height + patch_size - 1) // patch_size)
        grid_w = max(1, (width + patch_size - 1) // patch_size)

        patch_scores = np.zeros((grid_h, grid_w), dtype=np.float32)
        for r in range(grid_h):
            y1 = r * patch_size
            y2 = min(height, (r + 1) * patch_size)
            for c in range(grid_w):
                x1 = c * patch_size
                x2 = min(width, (c + 1) * patch_size)
                patch = grad[y1:y2, x1:x2]
                if patch.size > 0:
                    patch_scores[r, c] = float(np.mean(patch))

        mean_energy = float(np.mean(patch_scores))
        std_energy = float(np.std(patch_scores))
        threshold = max(3.5, mean_energy + 0.35 * std_energy)
        active = patch_scores > threshold

        visited = np.zeros_like(active, dtype=bool)
        regions: List[Dict[str, Any]] = []

        for r in range(grid_h):
            for c in range(grid_w):
                if active[r, c] and not visited[r, c]:
                    queue = deque([(r, c)])
                    visited[r, c] = True
                    cells = []
                    while queue:
                        cr, cc = queue.popleft()
                        cells.append((cr, cc))
                        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < grid_h and 0 <= nc < grid_w:
                                if active[nr, nc] and not visited[nr, nc]:
                                    visited[nr, nc] = True
                                    queue.append((nr, nc))

                    min_r = min(cell[0] for cell in cells)
                    max_r = max(cell[0] for cell in cells)
                    min_c = min(cell[1] for cell in cells)
                    max_c = max(cell[1] for cell in cells)

                    x1 = int(min_c * patch_size)
                    y1 = int(min_r * patch_size)
                    x2 = int(min(width, (max_c + 1) * patch_size))
                    y2 = int(min(height, (max_r + 1) * patch_size))

                    # Tighten bounding box to active gradient pixels inside the patch cluster
                    sub_grad = grad[y1:y2, x1:x2]
                    ys, xs = np.where(sub_grad > threshold * 0.8)
                    if xs.size > 0 and ys.size > 0:
                        tx1 = x1 + int(np.min(xs))
                        ty1 = y1 + int(np.min(ys))
                        tx2 = x1 + int(np.max(xs)) + 1
                        ty2 = y1 + int(np.max(ys)) + 1
                        if (tx2 - tx1) >= 16 and (ty2 - ty1) >= 16:
                            x1, y1, x2, y2 = tx1, ty1, tx2, ty2

                    bw = int(x2 - x1)
                    bh = int(y2 - y1)
                    if bw < 16 or bh < 16:
                        continue
                    if bw >= int(width * 0.98) and bh >= int(height * 0.92):
                        continue

                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    edge_score = float(np.mean([patch_scores[cell] for cell in cells]))
                    regions.append(
                        {
                            "bounds": {
                                "x1": x1,
                                "y1": y1,
                                "x2": x2,
                                "y2": y2,
                                "width": bw,
                                "height": bh,
                                "center_x": cx,
                                "center_y": cy,
                            },
                            "edge_score": round(edge_score, 3),
                            "source": "pure_vision_sobel",
                        }
                    )

        regions.sort(key=lambda item: item["edge_score"], reverse=True)
        return regions[:max_regions]

    @staticmethod
    def _boxes_overlap_iou(b1: Dict[str, int], b2: Dict[str, int]) -> float:
        ix1 = max(b1["x1"], b2["x1"])
        iy1 = max(b1["y1"], b2["y1"])
        ix2 = min(b1["x2"], b2["x2"])
        iy2 = min(b1["y2"], b2["y2"])
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = float((ix2 - ix1) * (iy2 - iy1))
        a1 = float(max(1, (b1["x2"] - b1["x1"]) * (b1["y2"] - b1["y1"])))
        a2 = float(max(1, (b2["x2"] - b2["x1"]) * (b2["y2"] - b2["y1"])))
        return inter / min(a1, a2)

    def render_set_of_mark_screenshot(
        self,
        serial: str,
        screenshot_path: Optional[str] = None,
        xml_override: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Combine UIAutomator XML clickable/labeled elements AND pure-vision Sobel regions
        into an M3A Set-of-Mark (SoM) annotated screenshot with numbered badges (#1, #2, ...).
        """
        if not screenshot_path or not os.path.exists(screenshot_path):
            cap = self.capture_screenshot_auto(serial, tag="som_source", fallback_synthetic=True)
            screenshot_path = cap["screenshot_path"]

        xml_str = xml_override if xml_override is not None else ""
        if not xml_str:
            try:
                xml_str = self.adb.dump_ui_hierarchy(serial)
            except Exception:
                xml_str = ""

        xml_elements = self.adb.parse_ui_elements(xml_str) if xml_str else []
        vision_regions = self.detect_pure_vision_regions(screenshot_path, max_regions=15)

        img = Image.open(screenshot_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        width, height = img.size

        combined_items: List[Dict[str, Any]] = []
        existing_boxes: List[Dict[str, int]] = []

        for el in xml_elements:
            b = el.get("bounds")
            if not b:
                continue
            bw = b["x2"] - b["x1"]
            bh = b["y2"] - b["y1"]
            if bw <= 8 or bh <= 8:
                continue
            if bw >= width * 0.98 and bh >= height * 0.95:
                continue
            label = (
                el.get("text")
                or el.get("content_desc")
                or el.get("resource_id", "").split("/")[-1]
                or el.get("class", "").split(".")[-1]
                or "xml_node"
            )
            box = {
                "x1": int(b["x1"]),
                "y1": int(b["y1"]),
                "x2": int(b["x2"]),
                "y2": int(b["y2"]),
                "width": int(bw),
                "height": int(bh),
                "center_x": int(b["center_x"]),
                "center_y": int(b["center_y"]),
            }
            existing_boxes.append(box)
            combined_items.append(
                {
                    "label": str(label),
                    "source": "uiautomator_xml",
                    "bounds": box,
                }
            )

        for reg in vision_regions:
            b = reg["bounds"]
            if any(self._boxes_overlap_iou(b, eb) > 0.35 for eb in existing_boxes):
                continue
            existing_boxes.append(b)
            combined_items.append(
                {
                    "label": f"vision_region_{len(combined_items) + 1}",
                    "source": reg["source"],
                    "bounds": b,
                }
            )

        palette = [
            (239, 68, 68),
            (16, 185, 129),
            (59, 130, 246),
            (245, 158, 11),
            (168, 85, 247),
            (236, 72, 153),
            (14, 165, 233),
        ]

        marks: Dict[str, Dict[str, Any]] = {}
        for idx, item in enumerate(combined_items, start=1):
            color = palette[(idx - 1) % len(palette)]
            b = item["bounds"]
            x1, y1, x2, y2 = b["x1"], b["y1"], b["x2"], b["y2"]
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

            badge_text = f"#{idx}"
            badge_w = max(26, 10 + 8 * len(badge_text))
            badge_h = 20
            bx1 = max(0, min(width - badge_w, x1))
            by1 = max(0, y1 - badge_h if y1 >= badge_h else y1)
            draw.rectangle([bx1, by1, bx1 + badge_w, by1 + badge_h], fill=color)
            draw.text((bx1 + 4, by1 + 4), badge_text, fill=(255, 255, 255))

            mark_entry = {
                "mark_id": idx,
                "label": item["label"],
                "source": item["source"],
                "bounds": b,
                "center_x": int(b["center_x"]),
                "center_y": int(b["center_y"]),
            }
            marks[str(idx)] = mark_entry

        if output_path:
            out_path = Path(output_path).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            safe_serial = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(serial))
            ts = int(time.time() * 1000)
            out_path = (self.output_dir / f"som_{safe_serial}_{ts}.png").resolve()

        img.save(str(out_path), format="PNG")
        return {
            "serial": serial,
            "source_screenshot": str(screenshot_path),
            "annotated_screenshot_path": str(out_path),
            "marks_count": len(marks),
            "marks": marks,
        }

    def crop_and_zoom_region(
        self,
        screenshot_path: str,
        bounds: Dict[str, int],
        zoom_factor: int = 2,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Coarse-to-Fine Crop & Zoom (Mobile-Agent-v2 style) for inspecting dense UI regions
        or tiny buttons/icons with high-resolution bicubic interpolation.
        """
        img = Image.open(screenshot_path).convert("RGB")
        width, height = img.size

        x1 = max(0, min(width - 1, int(bounds.get("x1", 0))))
        y1 = max(0, min(height - 1, int(bounds.get("y1", 0))))
        x2 = max(x1 + 1, min(width, int(bounds.get("x2", width))))
        y2 = max(y1 + 1, min(height, int(bounds.get("y2", height))))

        cropped = img.crop((x1, y1, x2, y2))
        zf = max(1, int(zoom_factor))
        zw = max(1, (x2 - x1) * zf)
        zh = max(1, (y2 - y1) * zf)

        resample_filter = getattr(getattr(Image, "Resampling", Image), "BICUBIC")
        zoomed = cropped.resize((zw, zh), resample=resample_filter)

        if output_path:
            out_path = Path(output_path).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            ts = int(time.time() * 1000)
            out_path = (self.output_dir / f"crop_zoom_{ts}.png").resolve()

        zoomed.save(str(out_path), format="PNG")
        return {
            "cropped_path": str(out_path),
            "original_bounds": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "zoomed_width": int(zw),
            "zoomed_height": int(zh),
            "zoom_factor": zf,
        }

    @staticmethod
    def _ncc_search_map(screen: np.ndarray, tpl: np.ndarray) -> Tuple[float, int, int]:
        """
        Ultra-fast Normalized Cross-Correlation over a 2D search region using
        2D integral images (summed-area tables) for window variance and zero-copy einsum.
        Returns (best_score, best_top_y, best_left_x).
        """
        sh, sw = screen.shape
        th, tw = tpl.shape
        if th > sh or tw > sw:
            return -1.0, 0, 0

        n_pixels = float(th * tw)
        tpl_f = tpl.astype(np.float32, copy=False)
        screen_f = screen.astype(np.float32, copy=False)

        tpl_zm = tpl_f - float(np.mean(tpl_f))
        tpl_norm = float(np.sqrt(np.sum(tpl_zm * tpl_zm)))
        windows = np.lib.stride_tricks.sliding_window_view(screen_f, (th, tw))

        if tpl_norm < 1e-6:
            # Uniform template fallback: match by minimum absolute luminance difference
            mad = np.mean(np.abs(windows - float(np.mean(tpl_f))), axis=(-2, -1))
            best_idx = int(np.argmin(mad))
            by, bx = divmod(best_idx, mad.shape[1])
            score = float(max(-1.0, 1.0 - float(mad[by, bx]) / 128.0))
            return score, int(by), int(bx)

        # Since sum(tpl_zm) == 0, sum((W - mean(W)) * tpl_zm) == sum(W * tpl_zm)
        numerator = np.einsum("ijkl,kl->ij", windows, tpl_zm, optimize=True)

        # Compute window sum and sum-of-squares in O(1) via 2D padded integral images
        pad_s = np.pad(screen_f, ((1, 0), (1, 0)), mode="constant", constant_values=0.0)
        pad_sq = np.pad(screen_f * screen_f, ((1, 0), (1, 0)), mode="constant", constant_values=0.0)
        ii_s = np.cumsum(np.cumsum(pad_s, axis=0), axis=1)
        ii_sq = np.cumsum(np.cumsum(pad_sq, axis=0), axis=1)

        out_h = sh - th + 1
        out_w = sw - tw + 1
        win_sum = (
            ii_s[th : th + out_h, tw : tw + out_w]
            - ii_s[0:out_h, tw : tw + out_w]
            - ii_s[th : th + out_h, 0:out_w]
            + ii_s[0:out_h, 0:out_w]
        )
        win_sq_sum = (
            ii_sq[th : th + out_h, tw : tw + out_w]
            - ii_sq[0:out_h, tw : tw + out_w]
            - ii_sq[th : th + out_h, 0:out_w]
            + ii_sq[0:out_h, 0:out_w]
        )
        win_var = np.maximum(win_sq_sum - (win_sum * win_sum) / n_pixels, 0.0)
        denom = np.sqrt(win_var) * tpl_norm
        ncc = np.where(denom > 1e-6, numerator / np.maximum(denom, 1e-6), 0.0)

        best_idx = int(np.argmax(ncc))
        by, bx = divmod(best_idx, ncc.shape[1])
        best_score = float(np.clip(ncc[by, bx], -1.0, 1.0))
        return best_score, int(by), int(bx)

    def find_template_on_screen(
        self,
        screenshot_path: str,
        template_path: str,
        threshold: float = 0.65,
    ) -> Dict[str, Any]:
        """
        Airtest-style two-stage pyramid Normalized Cross-Correlation (NCC) template matcher.
        Stage 1 downsamples by 0.25 (or 0.5 for small templates < 60px) for <15ms coarse search,
        Stage 2 refines at full 1.0x resolution in a ±12px neighborhood around the coarse peak.
        """
        screen_img = Image.open(screenshot_path).convert("L")
        tpl_img = Image.open(template_path).convert("L")

        sw, sh = screen_img.size
        tw, th = tpl_img.size

        if tw > sw or th > sh:
            return {
                "matched": False,
                "confidence": 0.0,
                "center_x": 0,
                "center_y": 0,
                "bounds": {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "center_x": 0, "center_y": 0},
            }

        min_dim = min(tw, th)
        if min_dim < 24:
            scale = 1.0
        elif min_dim < 60:
            scale = 0.5
        else:
            scale = 0.25

        resample_filter = getattr(getattr(Image, "Resampling", Image), "BILINEAR")
        screen_full = np.asarray(screen_img, dtype=np.float32)
        tpl_full = np.asarray(tpl_img, dtype=np.float32)

        if scale < 1.0:
            c_sw = max(8, int(round(sw * scale)))
            c_sh = max(8, int(round(sh * scale)))
            c_tw = max(4, int(round(tw * scale)))
            c_th = max(4, int(round(th * scale)))

            s_small = np.asarray(screen_img.resize((c_sw, c_sh), resample=resample_filter), dtype=np.float32)
            t_small = np.asarray(tpl_img.resize((c_tw, c_th), resample=resample_filter), dtype=np.float32)
            _, c_y, c_x = self._ncc_search_map(s_small, t_small)

            approx_x = int(round(c_x / scale))
            approx_y = int(round(c_y / scale))
            margin = 12

            rx1 = max(0, approx_x - margin)
            ry1 = max(0, approx_y - margin)
            rx2 = min(sw, approx_x + tw + margin)
            ry2 = min(sh, approx_y + th + margin)

            roi = screen_full[ry1:ry2, rx1:rx2]
            score, local_y, local_x = self._ncc_search_map(roi, tpl_full)
            best_x1 = rx1 + local_x
            best_y1 = ry1 + local_y
        else:
            score, best_y1, best_x1 = self._ncc_search_map(screen_full, tpl_full)

        best_x2 = int(best_x1 + tw)
        best_y2 = int(best_y1 + th)
        best_cx = int((best_x1 + best_x2) // 2)
        best_cy = int((best_y1 + best_y2) // 2)
        conf = round(float(score), 4)

        return {
            "matched": bool(conf >= threshold),
            "confidence": conf,
            "center_x": best_cx,
            "center_y": best_cy,
            "bounds": {
                "x1": int(best_x1),
                "y1": int(best_y1),
                "x2": best_x2,
                "y2": best_y2,
                "center_x": best_cx,
                "center_y": best_cy,
            },
        }

    def compare_screenshots(
        self,
        before_path: str,
        after_path: str,
        diff_output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Maestro assertScreenshot style visual regression comparison.
        Computes MAE, changed_pixel_ratio, PSNR, and similarity_score, and renders a visual diff heatmap PNG.
        """
        img1 = Image.open(before_path).convert("RGB")
        img2 = Image.open(after_path).convert("RGB")

        if img2.size != img1.size:
            resample_filter = getattr(getattr(Image, "Resampling", Image), "BILINEAR")
            img2 = img2.resize(img1.size, resample=resample_filter)

        arr1 = np.asarray(img1, dtype=np.float32)
        arr2 = np.asarray(img2, dtype=np.float32)

        diff = np.abs(arr1 - arr2)
        mae = float(np.mean(diff))
        max_channel_diff = np.max(diff, axis=2)
        changed_pixel_ratio = float(np.mean(max_channel_diff > 15.0))
        mse = float(np.mean(diff ** 2))
        psnr = 99.0 if mae < 1e-6 or mse < 1e-9 else float(20.0 * np.log10(255.0 / np.sqrt(mse)))
        similarity_score = round(max(0.0, 100.0 * (1.0 - mae / 255.0)), 2)

        # Render heatmap overlay (dimmed baseline + bright red/yellow on changed pixels)
        base_dim = (arr1 * 0.35).astype(np.uint8)
        heat = base_dim.copy()
        changed_mask = max_channel_diff > 15.0
        intensity = np.clip(max_channel_diff * 2.0, 0, 255).astype(np.uint8)
        heat[changed_mask, 0] = 255
        heat[changed_mask, 1] = np.clip(255 - intensity[changed_mask], 0, 220)
        heat[changed_mask, 2] = 0

        if diff_output_path:
            diff_out = Path(diff_output_path).resolve()
            diff_out.parent.mkdir(parents=True, exist_ok=True)
        else:
            ts = int(time.time() * 1000)
            diff_out = (self.output_dir / f"diff_{ts}.png").resolve()

        Image.fromarray(heat, mode="RGB").save(str(diff_out), format="PNG")

        return {
            "similarity_score": similarity_score,
            "mae": round(mae, 3),
            "psnr": round(psnr, 2),
            "changed_pixel_ratio": round(changed_pixel_ratio, 4),
            "diff_image_path": str(diff_out),
            "is_visually_identical": bool(similarity_score >= 98.0),
        }


if __name__ == "__main__":
    engine = ScreenshotPerceptionEngine()
    print("[Self-Test] Creating synthetic screen image...")
    synth_path = engine.create_synthetic_screen_image()
    print(" -> Synthetic path:", synth_path)

    cap_meta = engine.capture_screenshot_auto("emulator-5554", tag="selftest")
    print(" -> Capture metadata:", {k: cap_meta[k] for k in ("width", "height", "mean_brightness", "contrast_std", "edge_density", "is_blank")})

    regions = engine.detect_pure_vision_regions(synth_path)
    print(f" -> Detected {len(regions)} pure-vision Sobel regions.")

    som = engine.render_set_of_mark_screenshot("emulator-5554", screenshot_path=synth_path)
    print(f" -> Rendered SoM screenshot with {som['marks_count']} marks at: {som['annotated_screenshot_path']}")

    crop_info = engine.crop_and_zoom_region(
        synth_path,
        bounds={"x1": 80, "y1": 430, "x2": 320, "y2": 535},
        zoom_factor=1,
    )
    t0 = time.perf_counter()
    match_res = engine.find_template_on_screen(synth_path, crop_info["cropped_path"])
    dt_ms = (time.perf_counter() - t0) * 1000.0
    print(f" -> Template match result ({dt_ms:.1f}ms):", match_res)

    diff_res = engine.compare_screenshots(synth_path, som["annotated_screenshot_path"])
    print(" -> Visual diff result:", diff_res)
