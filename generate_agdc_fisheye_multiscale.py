"""
AGDC Mesh Table & Golden Reference — Fisheye Multiscale
=========================================================
从不同分辨率的鱼眼图像生成 AGDC 仿真数据集。
支持参数化缩放 Scaramuzza 标定参数。

用法:
    python generate_agdc_fisheye_multiscale.py

配置: 修改 CONFIGS 列表
"""

import numpy as np
import os, json, shutil
from pathlib import Path

# ============================================================
# 0. 基础参数 (来自 1024×768 原始标定)
# ============================================================
BASE_DIR = Path(r"d:\Clone\CameraCalibration")
CALIB_DIR = Path(r"d:\Clone\CameraCalibration\相机标定课程\第七章\Scaramuzza_OCamCalib_v3.0_win")

# 原始标定参数 (1024×768 基准)
SS_BASE = np.array([-1.405116937602191e+002,
                     0.0,
                     2.716608082380784e-004,
                     5.257341861497706e-006,
                    -1.067888507955045e-009], dtype=np.float64)
XC_BASE, YC_BASE = 512.0, 384.0
CALIB_RADIUS_BASE = 498.0
C, D, E = 1.0, 0.0, 0.0
FC = 4.0
W_OUT, H_OUT = 640, 480
THETA_ORDER = 5
FRAC_BITS = 5

# ============================================================
# 1. 多分辨率配置 (输出尺寸按 0.625× 输入比例缩放, 对齐 16×12 tile)
# ============================================================
# 输出宽度约束: 对齐 mesh_cols(16) 且 ≤ 输入宽度
# 输出高度约束: 对齐 mesh_rows(12) 且 ≤ 输入高度
def compute_output_size(w_in, h_in):
    """按 0.625 比例计算输出尺寸，对齐 16×12 tile 网格"""
    w_out = round(w_in * 0.625 / 16) * 16
    h_out = round(h_in * 0.625 / 12) * 12
    # 确保不超过输入
    w_out = min(w_out, w_in - w_in % 16) if w_out > w_in else w_out
    h_out = min(h_out, h_in - h_in % 12) if h_out > h_in else h_out
    return w_out, h_out

CONFIGS = [
    {"name": "1024x768", "w_in": 1024, "h_in": 768,
     "src_image": CALIB_DIR / "VMRImage1.jpg",
     "out_dir": BASE_DIR / "agdc_test_fisheye_1024x768"},
    {"name": "400x300",  "w_in": 400,  "h_in": 300,
     "src_image": BASE_DIR / "agdc_test_fisheye/source/VMRImage1_400x300.jpg",
     "out_dir": BASE_DIR / "agdc_test_fisheye_400x300"},
    {"name": "200x150",  "w_in": 200,  "h_in": 150,
     "src_image": BASE_DIR / "agdc_test_fisheye/source/VMRImage1_200x150.jpg",
     "out_dir": BASE_DIR / "agdc_test_fisheye_200x150"},
]

# 为每个配置计算输出尺寸
for cfg in CONFIGS:
    cfg["w_out"], cfg["h_out"] = compute_output_size(cfg["w_in"], cfg["h_in"])

MESH_CONFIGS = [("16x12", 16, 12), ("32x24", 32, 24)]
FRAC_SCALE = 1 << FRAC_BITS
SS_FLIP = SS_BASE[::-1]

import cv2

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    with open(str(path), 'rb') as f:
        data = f.read()
    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), flags)

def imwrite_unicode(path, img):
    _, buf = cv2.imencode(os.path.splitext(str(path))[1], img)
    with open(str(path), 'wb') as f:
        f.write(buf)

def float_to_u12_5(val):
    fixed = np.round(val * FRAC_SCALE).astype(np.int64)
    return np.clip(fixed, -(1 << 17), (1 << 17) - 1).astype(np.int32)

def rgb_to_yuv_bt601(img_bgr):
    img = img_bgr.astype(np.float64)
    B, G, R = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    Y = 0.299 * R + 0.587 * G + 0.114 * B
    U = -0.169 * R - 0.331 * G + 0.500 * B + 128.0
    V = 0.500 * R - 0.419 * G - 0.081 * B + 128.0
    return (np.clip(Y, 0, 255).astype(np.uint8),
            np.clip(U, 0, 255).astype(np.uint8),
            np.clip(V, 0, 255).astype(np.uint8))

def pack_nv12(Y, U, V):
    H, W = Y.shape
    U_sub = ((U[0:H:2, 0:W:2].astype(np.uint16) + U[0:H:2, 1:W:2].astype(np.uint16) +
              U[1:H:2, 0:W:2].astype(np.uint16) + U[1:H:2, 1:W:2].astype(np.uint16) + 2) // 4).astype(np.uint8)
    V_sub = ((V[0:H:2, 0:W:2].astype(np.uint16) + V[0:H:2, 1:W:2].astype(np.uint16) +
              V[1:H:2, 0:W:2].astype(np.uint16) + V[1:H:2, 1:W:2].astype(np.uint16) + 2) // 4).astype(np.uint8)
    uv = np.empty((H // 2, W // 2 * 2), dtype=np.uint8)
    uv[:, 0::2], uv[:, 1::2] = U_sub, V_sub
    return Y, uv

def pack_nv16(Y, U, V):
    H, W = Y.shape
    U_sub = ((U[:, 0:W:2].astype(np.uint16) + U[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    V_sub = ((V[:, 0:W:2].astype(np.uint16) + V[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    uv = np.empty((H, W // 2 * 2), dtype=np.uint8)
    uv[:, 0::2], uv[:, 1::2] = U_sub, V_sub
    return Y, uv

def pack_yuyv(Y, U, V):
    H, W = Y.shape
    U_sub = ((U[:, 0:W:2].astype(np.uint16) + U[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    V_sub = ((V[:, 0:W:2].astype(np.uint16) + V[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    yuyv = np.empty((H, W * 2), dtype=np.uint8)
    for col in range(W // 2):
        yuyv[:, col * 4 + 0] = Y[:, col * 2]
        yuyv[:, col * 4 + 1] = U_sub[:, col]
        yuyv[:, col * 4 + 2] = Y[:, col * 2 + 1]
        yuyv[:, col * 4 + 3] = V_sub[:, col]
    return yuyv


# ============================================================
# 2. 对每个配置生成数据
# ============================================================
for cfg in CONFIGS:
    name = cfg["name"]
    W_IN, H_IN = cfg["w_in"], cfg["h_in"]
    W_OUT, H_OUT = cfg["w_out"], cfg["h_out"]
    out_dir = cfg["out_dir"]
    scale = W_IN / 1024.0  # 缩放因子

    print("=" * 72)
    print(f"AGDC Fisheye — {name} (scale={scale:.6f})")
    print("=" * 72)

    # --- 建立目录结构 ---
    for d in ["source", "mesh/16x12", "mesh/32x24",
              "input/nv12", "input/nv16", "input/yuyv",
              "golden/nv12", "golden/nv16", "golden/yuyv", "verify"]:
        (out_dir / d).mkdir(parents=True, exist_ok=True)

    # --- 缩放标定参数 ---
    XC = XC_BASE * scale
    YC = YC_BASE * scale
    CALIB_RADIUS = CALIB_RADIUS_BASE * scale

    # ss 多项式缩放: Z 须与像素坐标同比例缩放以保持归一化射线方向不变
    # ρ' = scale · ρ, 要求 f'(ρ') = scale · f(ρ)
    # Σ a_k'·(scale·ρ)^k = scale · Σ a_k·ρ^k → a_k' = a_k · scale^(1-k)
    SS = SS_BASE.copy()
    SS[0] = SS_BASE[0] * scale          # a₀' = a₀ · scale
    SS[1] = SS_BASE[1]                  # a₁' = a₁
    SS[2] = SS_BASE[2] / scale          # a₂' = a₂ / scale
    SS[3] = SS_BASE[3] / (scale ** 2)   # a₃' = a₃ / scale²
    SS[4] = SS_BASE[4] / (scale ** 3)   # a₄' = a₄ / scale³
    ss_flip = SS[::-1]

    A = np.array([[C, D], [E, 1.0]], dtype=np.float64)
    A_inv = np.linalg.inv(A)

    print(f"\n缩放参数 (scale={scale:.6f}):")
    print(f"  输入尺寸:           {W_IN}×{H_IN}")
    print(f"  图像中心 (xc, yc): ({XC:.2f}, {YC:.2f})")
    print(f"  标定半径:           {CALIB_RADIUS:.2f} px")
    print(f"  输出尺寸:           {W_OUT}×{H_OUT}")
    print(f"  FC:                 {FC}")

    f_at_edge = np.polyval(ss_flip, CALIB_RADIUS)
    theta_at_edge = np.arctan2(CALIB_RADIUS, f_at_edge)
    print(f"  入射角范围:         {np.rad2deg(theta_at_edge):.1f}°")

    # --- 逆多项式拟合 ---
    rho_samples = np.linspace(0, CALIB_RADIUS, 2000)
    z_samples = np.polyval(ss_flip, rho_samples)
    theta_samples = np.empty_like(rho_samples)
    theta_samples[0] = -np.pi / 2.0
    mask = rho_samples[1:] > 0
    theta_samples[1:][mask] = np.arctan(z_samples[1:][mask] / rho_samples[1:][mask])
    theta_max = theta_samples[-1]
    theta_min = theta_samples[0]

    V_mat = np.zeros((len(theta_samples), THETA_ORDER + 1))
    for k in range(THETA_ORDER + 1):
        V_mat[:, k] = theta_samples ** k
    pol_coeffs, _, _, _ = np.linalg.lstsq(V_mat, rho_samples, rcond=None)

    rho_fit = np.polyval(pol_coeffs[::-1], theta_samples)
    fit_err = np.abs(rho_fit - rho_samples).max()
    print(f"  逆多项式拟合 max 误差: {fit_err:.4f} px")

    # --- Backward Mapping ---
    Nxc = H_OUT / 2.0
    Nyc = W_OUT / 2.0
    Nz = -W_OUT / FC

    u_out_grid, v_out_grid = np.meshgrid(
        np.arange(W_OUT, dtype=np.float64),
        np.arange(H_OUT, dtype=np.float64))

    Nx = v_out_grid - Nxc
    Ny = u_out_grid - Nyc
    NORM_xy = np.sqrt(Nx ** 2 + Ny ** 2)
    NORM_xy = np.maximum(NORM_xy, 1e-12)
    Nz_val = np.full_like(Nx, Nz)
    theta = np.arctan(Nz_val / NORM_xy)
    rho = np.polyval(pol_coeffs[::-1], theta)
    scale_map = rho / NORM_xy
    x_cam = Nx * scale_map
    y_cam = Ny * scale_map

    u_in = x_cam * C + y_cam * D + XC
    v_in = x_cam * E + y_cam + YC

    valid_mask = (u_in >= 0) & (u_in < W_IN) & (v_in >= 0) & (v_in < H_IN)
    print(f"  u_in 范围: [{u_in.min():.2f}, {u_in.max():.2f}]")
    print(f"  v_in 范围: [{v_in.min():.2f}, {v_in.max():.2f}]")
    print(f"  有效像素比例: {valid_mask.sum() / valid_mask.size * 100:.1f}%")

    # --- 单行 v_in 极差 (用于硬件约束分析) ---
    v_in_range_per_row = v_in.max(axis=1) - v_in.min(axis=1)
    print(f"  单行 v_in 极差: max={v_in_range_per_row.max():.1f} px, mean={v_in_range_per_row.mean():.1f} px")

    # --- 读取图像 & 黄金参考 ---
    img_fisheye = imread_unicode(cfg["src_image"], cv2.IMREAD_COLOR)
    print(f"\n源图像: {cfg['src_image']}, shape={img_fisheye.shape}")

    # 复制源图像
    shutil.copy2(str(cfg["src_image"]), str(out_dir / f"source/VMRImage1_{name}.jpg"))

    # 双线性插值生成黄金参考
    u_in_clip = np.clip(u_in, 0, W_IN - 1)
    v_in_clip = np.clip(v_in, 0, H_IN - 1)
    u0 = np.floor(u_in_clip).astype(np.int32)
    v0 = np.floor(v_in_clip).astype(np.int32)
    u1 = np.minimum(u0 + 1, W_IN - 1)
    v1 = np.minimum(v0 + 1, H_IN - 1)
    wu = (u_in_clip - u0.astype(np.float64)).reshape(H_OUT, W_OUT, 1)
    wv = (v_in_clip - v0.astype(np.float64)).reshape(H_OUT, W_OUT, 1)

    img_rect = ((1 - wv) * (1 - wu) * img_fisheye[v0, u0].astype(np.float64) +
                 (1 - wv) * wu * img_fisheye[v0, u1].astype(np.float64) +
                 wv * (1 - wu) * img_fisheye[v1, u0].astype(np.float64) +
                 wv * wu * img_fisheye[v1, u1].astype(np.float64))
    img_rect = np.clip(np.round(img_rect), 0, 255).astype(np.uint8)
    img_rect[~valid_mask] = [128, 128, 128]
    imwrite_unicode(out_dir / "verify/golden_rectified_perspective.tif", img_rect)

    # --- YUV 转换 & 保存 ---
    Yf, Uf, Vf = rgb_to_yuv_bt601(img_fisheye)
    for fmt_name, pack_fn, y_dir, uv_dir in [
        ("nv12", pack_nv12, "input/nv12", "input/nv12"),
        ("nv16", pack_nv16, "input/nv16", "input/nv16"),
        ("yuyv", None, "input/yuyv", "input/yuyv"),
    ]:
        if fmt_name == "yuyv":
            data = pack_yuyv(Yf, Uf, Vf)
            data.tofile(str(out_dir / uv_dir / "distorted_yuyv.bin"))
        else:
            Yp, UVp = pack_fn(Yf, Uf, Vf)
            Yp.tofile(str(out_dir / y_dir / f"distorted_{fmt_name}_y.bin"))
            UVp.tofile(str(out_dir / uv_dir / f"distorted_{fmt_name}_uv.bin"))

    Yr, Ur, Vr = rgb_to_yuv_bt601(img_rect)
    for fmt_name, pack_fn, y_dir, uv_dir in [
        ("nv12", pack_nv12, "golden/nv12", "golden/nv12"),
        ("nv16", pack_nv16, "golden/nv16", "golden/nv16"),
        ("yuyv", None, "golden/yuyv", "golden/yuyv"),
    ]:
        if fmt_name == "yuyv":
            data = pack_yuyv(Yr, Ur, Vr)
            data.tofile(str(out_dir / uv_dir / "golden_yuyv.bin"))
        else:
            Yp, UVp = pack_fn(Yr, Ur, Vr)
            Yp.tofile(str(out_dir / y_dir / f"golden_{fmt_name}_y.bin"))
            UVp.tofile(str(out_dir / uv_dir / f"golden_{fmt_name}_uv.bin"))

    Yr.tofile(str(out_dir / "golden/golden_y_plane.bin"))
    Ur.tofile(str(out_dir / "golden/golden_u_plane.bin"))
    Vr.tofile(str(out_dir / "golden/golden_v_plane.bin"))

    # --- AGDC Mesh Table 生成 ---
    all_mesh_info = {}
    for mesh_name, mesh_cols, mesh_rows in MESH_CONFIGS:
        grid_cols = mesh_cols + 1
        grid_rows = mesh_rows + 1
        num_nodes = grid_cols * grid_rows

        col_pos = np.linspace(0, W_OUT, grid_cols).astype(np.int32)
        row_pos = np.linspace(0, H_OUT, grid_rows).astype(np.int32)
        col_idx = np.clip(col_pos, 0, W_OUT - 1)
        row_idx = np.clip(row_pos, 0, H_OUT - 1)

        mesh_u = u_in[row_idx[:, None], col_idx[None, :]]
        mesh_v = v_in[row_idx[:, None], col_idx[None, :]]

        print(f"\n--- 网格 {mesh_name}: {grid_cols}×{grid_rows} = {num_nodes} 节点 ---")
        print(f"  tile: {W_OUT // mesh_cols}×{H_OUT // mesh_rows} px")
        print(f"  mesh_u: [{mesh_u.min():.2f}, {mesh_u.max():.2f}]")
        print(f"  mesh_v: [{mesh_v.min():.2f}, {mesh_v.max():.2f}]")

        mesh_u_fixed = float_to_u12_5(mesh_u)
        mesh_v_fixed = float_to_u12_5(mesh_v)

        # 封装 36-bit
        mesh_entries = np.zeros(num_nodes, dtype=np.uint64)
        for iy in range(grid_rows):
            for ix in range(grid_cols):
                addr = iy * grid_cols + ix
                mesh_entries[addr] = ((np.uint64(mesh_v_fixed[iy, ix]) & 0x3FFFF) << 18) | \
                                     (np.uint64(mesh_u_fixed[iy, ix]) & 0x3FFFF)

        mesh_dir = out_dir / "mesh" / mesh_name

        # hex
        with open(str(mesh_dir / f"agdc_mesh_{mesh_name}_36bit.hex"), 'w') as f:
            f.write(f"// AGDC Fisheye Mesh Table: {mesh_name} tiles (Scaramuzza) — {name}\n")
            f.write(f"// Nodes: {grid_cols}x{grid_rows} = {num_nodes}\n")
            f.write(f"// Format: 36-bit = {{v[17:0], u[17:0]}}, u12.5 signed\n")
            f.write(f"// Fisheye: {W_IN}x{H_IN}, Rectified: {W_OUT}x{H_OUT}, FC={FC}\n\n")
            for addr in range(num_nodes):
                iy, ix = addr // grid_cols, addr % grid_cols
                entry = mesh_entries[addr]
                f.write(f"@{addr:04X}  // node({ix:02d},{iy:02d})  "
                        f"u=0x{int(mesh_u_fixed[iy, ix]) & 0x3FFFF:05X}({mesh_u[iy, ix]:10.2f})  "
                        f"v=0x{int(mesh_v_fixed[iy, ix]) & 0x3FFFF:05X}({mesh_v[iy, ix]:10.2f})  "
                        f"packed=0x{entry:09X}\n")

        # bin64
        mesh_entries.tofile(str(mesh_dir / f"agdc_mesh_{mesh_name}_36bit_in_u64.bin"))

        # uv_fixed
        uv_flat = np.empty(num_nodes * 2, dtype=np.int32)
        uv_flat[0::2] = mesh_u_fixed.flatten()
        uv_flat[1::2] = mesh_v_fixed.flatten()
        uv_flat.tofile(str(mesh_dir / f"agdc_mesh_{mesh_name}_uv_fixed.bin"))

        # C header
        with open(str(mesh_dir / f"agdc_mesh_{mesh_name}.h"), 'w') as f:
            f.write(f"// AGDC Fisheye Mesh (Scaramuzza) - {mesh_name} tiles — {name}\n")
            f.write(f"#pragma once\n#include <stdint.h>\n\n")
            f.write(f"#define AGDC_MESH_COLS   {grid_cols}\n")
            f.write(f"#define AGDC_MESH_ROWS   {grid_rows}\n")
            f.write(f"#define AGDC_MESH_NODES  {num_nodes}\n")
            f.write(f"#define AGDC_IMG_WIDTH   {W_OUT}\n")
            f.write(f"#define AGDC_IMG_HEIGHT  {H_OUT}\n")
            f.write(f"#define AGDC_FRAC_BITS   {FRAC_BITS}\n\n")
            f.write(f"static const uint64_t agdc_mesh[{num_nodes}] = {{\n")
            for iy in range(grid_rows):
                vals = ", ".join(f"0x{mesh_entries[iy * grid_cols + ix]:09X}ULL" for ix in range(grid_cols))
                f.write(f"    {vals},\n")
            f.write(f"}};\n")

        all_mesh_info[mesh_name] = {
            "grid_cols": grid_cols, "grid_rows": grid_rows, "num_nodes": num_nodes,
            "tile_w": W_OUT // mesh_cols, "tile_h": H_OUT // mesh_rows,
            "u_range_float": [float(mesh_u.min()), float(mesh_u.max())],
            "v_range_float": [float(mesh_v.min()), float(mesh_v.max())],
        }

    # --- 验证: 网格表重建 vs 全精度 ---
    print(f"\n{'=' * 72}")
    print("网格表精度验证 (双线性插值 + NN 采样)")
    for mesh_name, mesh_cols, mesh_rows in MESH_CONFIGS:
        grid_cols = mesh_cols + 1
        grid_rows = mesh_rows + 1
        col_pos = np.linspace(0, W_OUT, grid_cols)
        row_pos = np.linspace(0, H_OUT, grid_rows)
        c_idx = np.clip(np.round(col_pos).astype(np.int32), 0, W_OUT - 1)
        r_idx = np.clip(np.round(row_pos).astype(np.int32), 0, H_OUT - 1)
        mu = u_in[r_idx[:, None], c_idx[None, :]]
        mv = v_in[r_idx[:, None], c_idx[None, :]]

        out = np.full((H_OUT, W_OUT, 3), 128, dtype=np.float64)
        for iy in range(H_OUT):
            ry = max(1, min(np.searchsorted(row_pos, iy), grid_rows - 1))
            y0, y1 = int(row_pos[ry - 1]), int(row_pos[ry])
            wy = (iy - y0) / max(y1 - y0, 1e-6)
            for ix in range(W_OUT):
                rx = max(1, min(np.searchsorted(col_pos, ix), grid_cols - 1))
                x0, x1 = int(col_pos[rx - 1]), int(col_pos[rx])
                wx = (ix - x0) / max(x1 - x0, 1e-6)
                x_in = (1 - wy) * ((1 - wx) * mu[ry - 1, rx - 1] + wx * mu[ry - 1, rx]) + \
                       wy * ((1 - wx) * mu[ry, rx - 1] + wx * mu[ry, rx])
                y_in = (1 - wy) * ((1 - wx) * mv[ry - 1, rx - 1] + wx * mv[ry - 1, rx]) + \
                       wy * ((1 - wx) * mv[ry, rx - 1] + wx * mv[ry, rx])
                xi = int(np.clip(np.round(x_in), 0, W_IN - 1))
                yi = int(np.clip(np.round(y_in), 0, H_IN - 1))
                if x_in >= 0 and x_in < W_IN and y_in >= 0 and y_in < H_IN:
                    out[iy, ix, :] = img_fisheye[yi, xi, :]

        out = out.astype(np.uint8)
        diff = out.astype(np.float32) - img_rect.astype(np.float32)
        diff[~valid_mask] = 0
        mae = np.abs(diff[valid_mask]).mean() if valid_mask.any() else 0
        maxe = np.abs(diff).max()
        print(f"  {mesh_name}: MAE={mae:.4f}, MaxError={maxe:.0f}")
        imwrite_unicode(out_dir / "verify" / f"reconstructed_mesh_{mesh_name}.tif", out)

    # --- manifest.json ---
    manifest = {
        "description": f"AGDC Mesh Table & Golden Reference — VMRImage1 {name} (Fisheye)",
        "model": "Scaramuzza Omnidirectional Camera Model",
        "scale": float(scale),
        "base_calibration": str(CALIB_DIR / "get_ocam_model.m"),
        "parameters": {
            "ss": SS.tolist(),
            "xc": float(XC), "yc": float(YC),
            "c": C, "d": D, "e": E,
            "calib_radius": float(CALIB_RADIUS),
            "pol_coeffs_fitted": pol_coeffs.tolist(),
            "theta_order": THETA_ORDER,
            "theta_max_deg": float(np.rad2deg(theta_max)),
        },
        "image": {
            "input": str(cfg["src_image"]),
            "input_size": [W_IN, H_IN],
            "output_size": [W_OUT, H_OUT],
            "virtual_fc": FC,
        },
        "hardware_constraints": {
            "per_row_v_in_span_max": float(v_in_range_per_row.max()),
            "per_row_v_in_span_mean": float(v_in_range_per_row.mean()),
            "line_buf_depth_typical": 70,
            "online_mode_feasible": bool(v_in_range_per_row.max() <= 70),
            "recommendation": "离线模式" if v_in_range_per_row.max() > 70 else "在线模式可行",
        },
        "format_spec": {
            "mesh_node_format": "36-bit = {v[17:0], u[17:0]}",
            "coordinate_format": "u12.5 signed",
            "sram_addressing": "addr = iy * (mesh_cols+1) + ix",
            "frac_bits": FRAC_BITS,
        },
        "mesh_tables": all_mesh_info,
    }
    with open(str(out_dir / "manifest.json"), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n完成! 输出目录: {out_dir}")

print(f"\n{'=' * 72}")
print("全部配置生成完毕!")
print(f"{'=' * 72}")
