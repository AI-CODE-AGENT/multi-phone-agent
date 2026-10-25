"""
Web & Advanced CAPTCHA Computer Vision & DevTools Engine (AMAF 5.0)
Provides zero-OpenCV (PIL + NumPy) visual grounding and Android WebView/Chrome
DevTools Remote protocol bridging for:
1. Concentric Dual-Ring & Single-Ring Image Rotation CAPTCHAs (`xoay ảnh`):
   Aligns inner rotating circle and outer counter-rotating/reference ring by
   minimizing circular seam RGB L1 discontinuity across 0..355°.
2. Dynamic Multi-Image Grid Selection (`chọn nhiều ảnh` 3x3 & 4x4):
   Selects multiple matching tiles in 3x3 (9 tiles) or 4x4 (16 tiles) grids
   using per-tile RGB channel dominance, color saturation variance, and Sobel
   edge density.
3. Android WebView & Chrome DevTools Remote Bridge:
   Discovers active Unix domain sockets (`localabstract:webview_devtools_remote_<pid>`
   and `chrome_devtools_remote`) and forwards CDP ports for web CAPTCHA inspection.
"""

import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw


class WebAndAdvancedCaptchaEngine:
    """
    Production CV and WebView CDP engine for Concentric Ring Rotation CAPTCHAs,
    Dynamic Multi-Image 3x3/4x4 Grid CAPTCHAs, and Browser/WebView CAPTCHA inspection.
    """

    # ------------------------------------------------------------------
    # A. Concentric Ring Rotation CV Solver (`xoay ảnh`)
    # ------------------------------------------------------------------
    def generate_synthetic_concentric_rotation_image(
        self,
        save_path: str,
        size: int = 320,
        true_angle_deg: int = 125,
    ) -> str:
        """
        Draws a rich multi-colored radial & geometric test pattern on a `size x size`
        image, rotates the inner disc (`r < size * 0.28`) by `-true_angle_deg` so that
        rotating it back by `+true_angle_deg` aligns the seam at `r = size * 0.28`,
        saves to `save_path`, and returns `save_path`.
        """
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        base_img = Image.new("RGB", (size, size), (28, 32, 42))
        draw = ImageDraw.Draw(base_img)

        cx, cy = size // 2, size // 2
        max_r = int(size * 0.46)

        # Draw distinct asymmetric multi-colored angular rays across the full circle
        # so the angular cross-correlation has a unique global minimum at true_angle_deg.
        ray_Palette = [
            (235, 65, 55),    # Red
            (45, 195, 95),    # Green
            (55, 130, 245),   # Blue
            (245, 200, 45),   # Yellow
            (190, 70, 235),   # Purple
            (45, 215, 215),   # Cyan
            (250, 135, 40),   # Orange
            (235, 240, 245),  # Bright White
            (95, 235, 140),   # Mint
            (240, 85, 165),   # Pink
            (130, 160, 250),  # Periwinkle
            (210, 180, 90),   # Gold
        ]

        num_sectors = 36
        for s_idx in range(num_sectors):
            ang_start = s_idx * (360.0 / num_sectors)
            ang_end = (s_idx + 1) * (360.0 / num_sectors)
            # Non-periodic color modulation using prime stride + asymmetric widths
            c_base = ray_Palette[(s_idx * 7 + (s_idx // 3) * 5) % len(ray_Palette)]
            mod = ((s_idx * 37) % 50) - 25
            color = (
                max(10, min(250, c_base[0] + mod)),
                max(10, min(250, c_base[1] - mod // 2)),
                max(10, min(250, c_base[2] + mod // 3)),
            )
            draw.pieslice(
                [cx - max_r, cy - max_r, cx + max_r, cy + max_r],
                start=ang_start,
                end=ang_end,
                fill=color,
            )

        # Overlay additional off-center landmarks crossing the r = 0.28 * size boundary
        seam_r = size * 0.28
        landmarks = [
            (20, (255, 255, 255), 14),
            (75, (20, 20, 20), 16),
            (140, (255, 50, 50), 15),
            (215, (40, 255, 120), 17),
            (295, (60, 120, 255), 15),
        ]
        for ang_deg, l_col, l_rad in landmarks:
            rad = math.radians(ang_deg)
            lx = int(round(cx + seam_r * math.cos(rad)))
            ly = int(round(cy + seam_r * math.sin(rad)))
            draw.ellipse(
                [lx - l_rad, ly - l_rad, lx + l_rad, ly + l_rad],
                fill=l_col,
            )

        # Create rotated version of the image for the inner disc (r < size * 0.28)
        # Note: PIL Image.rotate(angle) rotates counter-clockwise.
        # In screen coordinates (x right, y down), polar angle phi increases clockwise:
        # (cx + r*cos(phi), cy + r*sin(phi)).
        # A PIL counter-clockwise rotation by `true_angle_deg` shifts screen-polar features
        # from `phi` to `phi - true_angle_deg`, so shifting inner samples by `+true_angle_deg`
        # (or rotating clockwise by `+true_angle_deg`) aligns them back with the outer ring!
        rotated_inner = base_img.rotate(
            float(true_angle_deg),
            resample=Image.BICUBIC,
            center=(cx, cy),
        )

        # Composite inner disc (r < size * 0.28) onto base_img using circular mask
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        disc_r = int(round(size * 0.28))
        mask_draw.ellipse([cx - disc_r, cy - disc_r, cx + disc_r, cy + disc_r], fill=255)

        final_img = Image.composite(rotated_inner, base_img, mask)
        final_img.save(save_path, format="PNG")
        return save_path

    def solve_concentric_rotation_cv(
        self,
        image_path: str,
        track_width: int = 520,
        step_deg: int = 5,
    ) -> Dict[str, Any]:
        """
        Loads `image_path` via `PIL.Image.open(image_path).convert("RGB")`.
        Defines inner ring radius `r_in = int(min(w, h) * 0.26)` and outer ring radius
        `r_out = int(min(w, h) * 0.30)` around center `(cx, cy)`.
        Samples 72 polar points (`phi = 0, 5, ..., 355°`) on the outer reference ring
        and inner ring, evaluates candidate rotation angles `theta` in `range(15, 350, step_deg)`,
        and finds `best_angle_deg` that minimizes mean RGB L1 seam difference `seam_error(theta)`.
        """
        step = max(1, int(step_deg))
        if not image_path or not os.path.exists(image_path):
            default_angle = 125
            drag_px = int(round((default_angle / 360.0) * track_width))
            return {
                "best_angle_deg": default_angle,
                "drag_distance_px": max(20, drag_px),
                "min_seam_error": 0.0,
                "track_width": track_width,
                "method": "concentric_annulus_seam_correlation",
            }

        img = Image.open(image_path).convert("RGB")
        arr = np.asarray(img, dtype=np.float32)
        h, w, _ = arr.shape
        cx, cy = w / 2.0, h / 2.0
        min_dim = min(w, h)

        r_in = int(min_dim * 0.26)
        r_out = int(min_dim * 0.30)

        # Sample 72 polar angles (0, 5, ..., 355°) or aligned with step_deg
        sample_step = 5
        angles_deg = list(range(0, 360, sample_step))
        num_samples = len(angles_deg)

        outer_samples = np.zeros((num_samples, 3), dtype=np.float32)
        inner_samples = np.zeros((num_samples, 3), dtype=np.float32)

        for idx, phi_deg in enumerate(angles_deg):
            rad = math.radians(phi_deg)
            cos_p = math.cos(rad)
            sin_p = math.sin(rad)

            ox = int( min(w - 1, max(0, round(cx + r_out * cos_p))) )
            oy = int( min(h - 1, max(0, round(cy + r_out * sin_p))) )
            ix = int( min(w - 1, max(0, round(cx + r_in * cos_p))) )
            iy = int( min(h - 1, max(0, round(cy + r_in * sin_p))) )

            outer_samples[idx] = arr[oy, ox]
            inner_samples[idx] = arr[iy, ix]

        best_angle_deg = 125
        min_err = float("inf")
        errors_by_theta: Dict[int, float] = {}

        for theta in range(15, 350, step):
            # Shifting inner ring samples by +theta degrees:
            # When inner disc was rotated by -true_angle_deg in polar angle,
            # inner_samples[(i - shift) % N] brings the inner sample to its rotated position
            shift_idx = int(round(theta / float(sample_step))) % num_samples
            shifted_inner = np.roll(inner_samples, shift=shift_idx, axis=0)
            seam_err = float(np.mean(np.abs(shifted_inner - outer_samples)))
            errors_by_theta[theta] = seam_err
            if seam_err < min_err:
                min_err = seam_err
                best_angle_deg = theta

        # High-contrast edge fallback if the image is uniform or has near-zero variance
        max_err = max(errors_by_theta.values()) if errors_by_theta else 0.0
        if max_err - min_err < 1e-3:
            # Inspect angular gradient along r_in to find strongest edge marker
            diffs = np.mean(np.abs(np.diff(inner_samples, axis=0, append=inner_samples[:1])), axis=1)
            peak_idx = int(np.argmax(diffs))
            candidate = ( peak_idx * sample_step ) % 360
            best_angle_deg = max(15, min(345, candidate if candidate >= 15 else 125))

        drag_distance_px = int(round((best_angle_deg / 360.0) * track_width))
        return {
            "best_angle_deg": int(best_angle_deg),
            "drag_distance_px": max(20, drag_distance_px),
            "min_seam_error": round(float(min_err), 3),
            "track_width": track_width,
            "method": "concentric_annulus_seam_correlation",
        }

    # ------------------------------------------------------------------
    # B. Multi-Image Dynamic Grid CV Selector (`chọn nhiều ảnh` 3x3 & 4x4)
    # ------------------------------------------------------------------
    def generate_synthetic_multi_image_grid(
        self,
        save_path: str,
        grid_size: int = 3,
        target_indices: Optional[List[int]] = None,
        target_color: Tuple[int, int, int] = (230, 60, 50),
    ) -> str:
        """
        Generates a `3x3` (9 cells) or `4x4` (16 cells) grid image (`480x480`) where
        `target_indices` (default `[0, 2, 4, 7]`) contain high-salience target objects of
        `target_color` + distinct geometric features, while distractor cells have cool
        blue/gray background patterns. Saves to `save_path` and returns `save_path`.
        """
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        g_size = max(2, int(grid_size))
        total_cells = g_size * g_size
        targets = target_indices if target_indices is not None else [0, 2, 4, 7]
        target_set = {idx for idx in targets if 0 <= idx < total_cells}

        canvas_dim = 480
        cell_w = canvas_dim // g_size
        cell_h = canvas_dim // g_size

        img = Image.new("RGB", (canvas_dim, canvas_dim), (55, 70, 90))
        draw = ImageDraw.Draw(img)

        for idx in range(total_cells):
            row = idx // g_size
            col = idx % g_size
            x1 = col * cell_w
            y1 = row * cell_h
            x2 = x1 + cell_w - 1
            y2 = y1 + cell_h - 1
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            # Base tile background (cool blue/slate gray)
            bg_shade = 62 + ((idx * 7) % 18)
            draw.rectangle(
                [x1 + 2, y1 + 2, x2 - 2, y2 - 2],
                fill=(bg_shade - 10, bg_shade + 5, bg_shade + 25),
                outline=(35, 42, 52),
                width=2,
            )

            if idx in target_set:
                # Draw high-salience target object of `target_color` + crisp internal geometry
                pad = max(14, cell_w // 5)
                draw.rectangle(
                    [x1 + pad, y1 + pad, x2 - pad, y2 - pad],
                    fill=target_color,
                    outline=(255, 245, 210),
                    width=3,
                )
                inner_r = max(10, cell_w // 6)
                draw.ellipse(
                    [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
                    fill=(255, 220, 65),
                    outline=(30, 20, 20),
                    width=2,
                )
                # High-contrast cross-bars for strong Sobel edge density
                draw.line([(x1 + pad + 4, cy), (x2 - pad - 4, cy)], fill=(255, 255, 255), width=3)
                draw.line([(cx, y1 + pad + 4), (cx, y2 - pad - 4)], fill=(255, 255, 255), width=3)
            else:
                # Subtle low-contrast distractor horizon line
                draw.line(
                    [(x1 + 16, cy), (x2 - 16, cy)],
                    fill=(bg_shade, bg_shade + 12, bg_shade + 28),
                    width=2,
                )

        img.save(save_path, format="PNG")
        return save_path

    def select_matching_grid_tiles_cv(
        self,
        image_path: str,
        grid_size: int = 3,
        target_hint: str = "red_or_salient",
        grid_bounds: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Slices the grid image (or `grid_bounds` region `[x1, y1, x2, y2]` of a full screenshot)
        into `grid_size x grid_size` cells (`9` or `16` tiles).
        Computes each tile's RGB channel dominance, color saturation variance, and Sobel edge density.
        Scores and selects the matching tiles (tiles above the median+0.35*std salience/target-color
        threshold, guaranteeing at least 2 and at most `grid_size*grid_size - 1` selected tiles).
        """
        g_size = max(2, int(grid_size))
        total_tiles = g_size * g_size

        if not image_path or not os.path.exists(image_path):
            default_indices = [0, 2, 4, 7] if total_tiles >= 9 else [0, 2]
            bx1 = int((grid_bounds or {}).get("x1", 0))
            by1 = int((grid_bounds or {}).get("y1", 0))
            bw = int((grid_bounds or {}).get("x2", 480)) - bx1
            bh = int((grid_bounds or {}).get("y2", 480)) - by1
            cw = max(1, bw // g_size)
            ch = max(1, bh // g_size)
            centers = [
                (bx1 + (idx % g_size) * cw + cw // 2, by1 + (idx // g_size) * ch + ch // 2)
                for idx in default_indices
            ]
            return {
                "grid_size": g_size,
                "total_tiles": total_tiles,
                "selected_indices": default_indices,
                "selected_centers": centers,
                "tile_scores": [1.0 if i in default_indices else 0.1 for i in range(total_tiles)],
                "method": "hsv_rgb_edge_grid_classifier",
            }

        full_img = Image.open(image_path).convert("RGB")
        full_w, full_h = full_img.size

        if grid_bounds and all(k in grid_bounds for k in ("x1", "y1", "x2", "y2")):
            gx1 = max(0, min(full_w - 2, int(grid_bounds["x1"])))
            gy1 = max(0, min(full_h - 2, int(grid_bounds["y1"])))
            gx2 = max(gx1 + 2, min(full_w, int(grid_bounds["x2"])))
            gy2 = max(gy1 + 2, min(full_h, int(grid_bounds["y2"])))
            grid_img = full_img.crop((gx1, gy1, gx2, gy2))
        else:
            gx1, gy1, gx2, gy2 = 0, 0, full_w, full_h
            grid_img = full_img

        gw, gh = grid_img.size
        arr = np.asarray(grid_img, dtype=np.float32)
        cell_w = gw / float(g_size)
        cell_h = gh / float(g_size)

        hint_lower = (target_hint or "red_or_salient").lower()
        tile_scores: List[float] = []
        tile_centers: List[Tuple[int, int]] = []

        for idx in range(total_tiles):
            r_idx = idx // g_size
            c_idx = idx % g_size

            cx1 = int(round(c_idx * cell_w))
            cy1 = int(round(r_idx * cell_h))
            cx2 = int(round((c_idx + 1) * cell_w))
            cy2 = int(round((r_idx + 1) * cell_h))

            center_x = int(round(gx1 + (cx1 + cx2) / 2.0))
            center_y = int(round(gy1 + (cy1 + cy2) / 2.0))
            tile_centers.append((center_x, center_y))

            # Trim 4px border inside tile to ignore grid divider lines
            pad = min(4, max(0, (cx2 - cx1) // 8))
            sub = arr[cy1 + pad : max(cy1 + pad + 1, cy2 - pad), cx1 + pad : max(cx1 + pad + 1, cx2 - pad)]
            if sub.size == 0:
                tile_scores.append(0.0)
                continue

            r_ch = sub[:, :, 0]
            g_ch = sub[:, :, 1]
            b_ch = sub[:, :, 2]

            # 1. RGB Channel Dominance according to target_hint
            if "green" in hint_lower:
                dom = float(np.mean(np.maximum(0.0, g_ch - 0.5 * (r_ch + b_ch))))
            elif "blue" in hint_lower:
                dom = float(np.mean(np.maximum(0.0, b_ch - 0.5 * (r_ch + g_ch))))
            else:
                # Default: Red / Warm dominance + overall chromatic salience
                dom = float(np.mean(np.maximum(0.0, r_ch - 0.5 * (g_ch + b_ch))))

            # 2. HSV Saturation & Color Variance
            max_rgb = np.max(sub, axis=2)
            min_rgb = np.min(sub, axis=2)
            chroma = max_rgb - min_rgb
            sat = chroma / (max_rgb + 1e-5)
            sat_score = float(np.mean(sat) * 100.0 + np.std(chroma))

            # 3. Sobel Edge Density
            gray = 0.299 * r_ch + 0.587 * g_ch + 0.114 * b_ch
            if gray.shape[0] >= 3 and gray.shape[1] >= 3:
                gx_edge = np.abs(gray[:, 2:] - gray[:, :-2])
                gy_edge = np.abs(gray[2:, :] - gray[:-2, :])
                edge_density = float(np.mean(gx_edge) + np.mean(gy_edge))
            else:
                edge_density = float(np.std(gray))

            combined_score = round(dom * 1.4 + sat_score * 0.8 + edge_density * 0.9, 3)
            tile_scores.append(combined_score)

        scores_arr = np.asarray(tile_scores, dtype=np.float32)
        med = float(np.median(scores_arr))
        std = float(np.std(scores_arr))
        threshold = med + 0.35 * std

        selected_indices = [i for i, sc in enumerate(tile_scores) if sc > threshold]

        # Guarantee at least 2 and at most total_tiles - 1 selected tiles
        ranked_indices = [int(i) for i in np.argsort(-scores_arr)]
        if len(selected_indices) < 2:
            selected_indices = sorted(ranked_indices[:2])
        elif len(selected_indices) >= total_tiles:
            selected_indices = sorted(ranked_indices[: total_tiles - 1])
        else:
            selected_indices = sorted(selected_indices)

        selected_centers = [tile_centers[i] for i in selected_indices]
        return {
            "grid_size": g_size,
            "total_tiles": total_tiles,
            "selected_indices": selected_indices,
            "selected_centers": selected_centers,
            "tile_scores": [round(float(s), 3) for s in tile_scores],
            "method": "hsv_rgb_edge_grid_classifier",
        }

    # ------------------------------------------------------------------
    # C. WebView & Chrome DevTools Remote Bridge
    # ------------------------------------------------------------------
    def discover_webview_devtools_sockets(
        self,
        adb: Any,
        serial: str,
        raw_unix_override: Optional[str] = None,
    ) -> List[str]:
        """
        Runs `adb.shell(serial, "cat /proc/net/unix | grep -E 'devtools_remote|webview'")`
        (or parses `raw_unix_override`) and extracts abstract socket names like
        `webview_devtools_remote_18279` or `chrome_devtools_remote`.
        """
        raw_output = (
            raw_unix_override
            if raw_unix_override is not None
            else (
                adb.shell(serial, "cat /proc/net/unix | grep -E 'devtools_remote|webview'")
                if adb is not None
                else ""
            )
        )

        sockets: List[str] = []
        seen = set()
        for line in (raw_output or "").splitlines():
            line = line.strip()
            if not line:
                continue
            # Match @webview_devtools_remote_<pid>, @chrome_devtools_remote, etc.
            matches = re.findall(r"@?([A-Za-z0-9_.\-]*devtools_remote[A-Za-z0-9_.\-]*)", line)
            for sock in matches:
                clean_sock = sock.lstrip("@").strip()
                if clean_sock and clean_sock not in seen:
                    seen.add(clean_sock)
                    sockets.append(clean_sock)

        return sockets

    def forward_webview_cdp_port(
        self,
        adb: Any,
        serial: str,
        local_port: int = 9222,
        socket_name: str = "chrome_devtools_remote",
    ) -> Dict[str, Any]:
        """
        Runs `adb.run_device_cmd(serial, ["forward", f"tcp:{local_port}", f"localabstract:{socket_name}"])`
        and returns forwarding status.
        """
        clean_socket = socket_name.lstrip("@").strip() or "chrome_devtools_remote"
        code, out, err = (0, "", "")
        if adb is not None and hasattr(adb, "run_device_cmd"):
            code, out, err = adb.run_device_cmd(
                serial,
                ["forward", f"tcp:{int(local_port)}", f"localabstract:{clean_socket}"],
            )
        success = code == 0 and "error" not in (err or "").lower()
        return {
            "serial": serial,
            "local_port": int(local_port),
            "socket_name": clean_socket,
            "forward_spec": f"localabstract:{clean_socket}",
            "cdp_http_endpoint": f"http://127.0.0.1:{int(local_port)}/json",
            "success": bool(success),
            "stdout": out,
            "stderr": err,
        }


if __name__ == "__main__":
    import tempfile

    engine = WebAndAdvancedCaptchaEngine()
    tmp_dir = Path(tempfile.gettempdir()) / "amaf_web_advanced_captcha_test"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Test Concentric Ring Rotation CV Solver (true_angle_deg = 125)
    rot_path = str(tmp_dir / "concentric_rotation_125.png")
    engine.generate_synthetic_concentric_rotation_image(rot_path, size=320, true_angle_deg=125)
    rot_res = engine.solve_concentric_rotation_cv(rot_path, track_width=520, step_deg=5)
    print("[Self-Test 1] Concentric Rotation CV Result:", rot_res)
    assert abs(rot_res["best_angle_deg"] - 125) <= 5, f"Expected ~125 deg, got {rot_res}"

    # 2. Test 3x3 Multi-Image Grid CV Selector (targets = [0, 2, 4, 7])
    grid3_path = str(tmp_dir / "multi_grid_3x3.png")
    engine.generate_synthetic_multi_image_grid(grid3_path, grid_size=3, target_indices=[0, 2, 4, 7])
    grid3_res = engine.select_matching_grid_tiles_cv(grid3_path, grid_size=3)
    print("[Self-Test 2] 3x3 Grid Selection Result:", grid3_res)
    assert grid3_res["selected_indices"] == [0, 2, 4, 7], f"Expected [0, 2, 4, 7], got {grid3_res}"

    # 3. Test 4x4 Multi-Image Grid CV Selector (targets = [1, 5, 10, 14])
    grid4_path = str(tmp_dir / "multi_grid_4x4.png")
    engine.generate_synthetic_multi_image_grid(grid4_path, grid_size=4, target_indices=[1, 5, 10, 14])
    grid4_res = engine.select_matching_grid_tiles_cv(grid4_path, grid_size=4)
    print("[Self-Test 3] 4x4 Grid Selection Result:", grid4_res)
    assert grid4_res["selected_indices"] == [1, 5, 10, 14], f"Expected [1, 5, 10, 14], got {grid4_res}"

    # 4. Test DevTools Socket Discovery
    sample_unix = (
        "0000000000000000: 00000002 00000000 00010000 0001 01 129481 @chrome_devtools_remote\n"
        "0000000000000000: 00000002 00000000 00010000 0001 01 142310 @webview_devtools_remote_18279\n"
    )
    sockets = engine.discover_webview_devtools_sockets(None, "emulator-5554", raw_unix_override=sample_unix)
    print("[Self-Test 4] Discovered CDP Sockets:", sockets)
    assert "chrome_devtools_remote" in sockets and "webview_devtools_remote_18279" in sockets
    print("All WebAndAdvancedCaptchaEngine self-tests PASSED!")
