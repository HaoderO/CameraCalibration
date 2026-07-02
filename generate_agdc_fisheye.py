"""
AGDC Mesh Table & Golden Reference — Fisheye (Scaramuzza Model)
=================================================================
使用 VMRImage1.jpg + OCamCalib 标定参数生成 AGDC 仿真数据集。

模型：Scaramuzza Omnidirectional Camera Model
  - Forward  (cam2world): 像素 (u,v) → 单位球面 3D 射线
  - Inverse  (world2cam): 3D 射线 → 像素 (u,v)
  - 矫正方式: 透视平面重投影 (同 undistort.m)

输出目录: agdc_test_fisheye/
"""

import numpy as np
import os, json
from pathlib import Path

# ============================================================
# 0. 路径
# ============================================================
BASE_DIR = Path(r"d:\Clone\CameraCalibration")
CALIB_DIR = Path(r"d:\Clone\CameraCalibration\相机标定课程\第七章\Scaramuzza_OCamCalib_v3.0_win")
OUT_DIR = BASE_DIR / "agdc_test_fisheye"
for d in ["source", "mesh/16x12", "mesh/32x24",
          "input/nv12", "input/nv16", "input/yuyv",
          "golden/nv12", "golden/nv16", "golden/yuyv",
          "verify"]:
    (OUT_DIR / d).mkdir(parents=True, exist_ok=True)

IMG_SRC  = CALIB_DIR / "VMRImage1.jpg"

print("=" * 72)
print("AGDC Fisheye — Scaramuzza Model")
print("=" * 72)
print(f"输入图像: {IMG_SRC}")

# ============================================================
# 1. 标定参数 (来自 get_ocam_model.m)
# ============================================================
# Scaramuzza 多项式系数 (5阶, ρ → f(ρ) = Z 分量)
SS = np.array([-1.405116937602191e+002,
                0.0,
                2.716608082380784e-004,
                5.257341861497706e-006,
               -1.067888507955045e-009], dtype=np.float64)

# 推算参数
CALIB_RADIUS = 498.0       # get_ocam_model.m 中的归一化半径
XC = 512.0                  # 几何中心 x (1024/2)
YC = 384.0                  # 几何中心 y (768/2)
C, D, E = 1.0, 0.0, 0.0    # 仿射参数 (calibration.m 默认值)

W_IN, H_IN = 1024, 768     # 输入鱼眼图像尺寸
W_OUT, H_OUT = 640, 480    # 输出透视图像尺寸
FC = 4.0                    # 虚拟相机距离参数 (同 undistort.m 风格, 越小越广角)

# ---- 内参验证: 用半径 r=498 时 Z应接近 0 ----
r_test = np.linspace(0, CALIB_RADIUS, 100)
ss_flip = SS[::-1]  # polyval 需要从高次到低次
z_test = np.polyval(ss_flip, r_test)
# 在半径 r=498 处, f(498) = polyval(ss, 498)
f_at_edge = np.polyval(ss_flip, CALIB_RADIUS)
print(f"\n标定多项式 SS 在 r={CALIB_RADIUS}: f(r)={f_at_edge:.4f}")
# 对应的射线角度 θ = atan(r / f(r))... 实际上对于单位球面:
# 射线方向 = [x, y, f(r)] normalized
# tan(入射角) = r / f(r)
theta_at_edge = np.arctan2(CALIB_RADIUS, f_at_edge)
print(f"  对应入射角 (从光轴): {np.rad2deg(theta_at_edge):.1f}°")

# ---- 仿射矩阵 ----
A = np.array([[C, D],
              [E, 1.0]], dtype=np.float64)
A_inv = np.linalg.inv(A)

print(f"\n推算参数:")
print(f"  图像中心 (xc, yc): ({XC}, {YC})")
print(f"  标定最大半径:       {CALIB_RADIUS} px")
print(f"  仿射 (c,d,e):       ({C}, {D}, {E})")
print(f"  输入尺寸:           {W_IN}×{H_IN}")
print(f"  输出尺寸:           {W_OUT}×{H_OUT}")
print(f"  虚拟相机 fc:        {FC}")

# ============================================================
# 2. 计算逆多项式 pol(θ) — 类 findinvpoly.m
# ============================================================
# Scaramuzza 模型中的 θ 定义:
#   θ = atan(Z / sqrt(X²+Y²))    (角度从 XY 平面量起)
#   对未归一化射线 [x, y, f(ρ)]:  θ = atan(f(ρ) / ρ)
#
#   中心 ρ→0:  f(0) = -140.5 → θ = atan(-∞) = -π/2 ≈ -1.5708
#   图像边缘 ρ=498: f(498) = 510.5 → θ = atan(510.5/498) = 0.7979
#
#   pol 定义域: [-π/2, 0.80], 值域: [0, 498]
#   pol(-π/2) ≈ 0 (中心点), pol(0.80) ≈ 498 (边缘)
#
#   注意: θ 可为负值! world2cam_fast 调用时 θ = atan(Nz/NORM),
#   Nz 为负 → θ 为负 → 直接传入 pol

THETA_ORDER = 5

# 在半径域密集采样
rho_samples = np.linspace(0, CALIB_RADIUS, 2000)
z_samples = np.polyval(ss_flip, rho_samples)

# θ = atan(f(ρ) / ρ),  ρ=0 时用极限: θ = -π/2
theta_samples = np.empty_like(rho_samples)
theta_samples[0] = -np.pi / 2.0  # ρ=0: atan(-∞) = -π/2
mask = rho_samples[1:] > 0
theta_samples[1:][mask] = np.arctan(z_samples[1:][mask] / rho_samples[1:][mask])

theta_max = theta_samples[-1]
theta_min = theta_samples[0]

print(f"\n逆多项式拟合:")
print(f"  θ 定义域: [{theta_min:.4f}, {theta_max:.4f}] rad = [{np.rad2deg(theta_min):.1f}°, {np.rad2deg(theta_max):.1f}°]")
print(f"  ρ 值域:   [0, {CALIB_RADIUS}] px")
print(f"  阶数: {THETA_ORDER}")

# 验证: pol(θ_min) ≈ 0, pol(θ_max) ≈ CALIB_RADIUS
print(f"  检查: pol({theta_min:.4f}) ≈ 0,  pol({theta_max:.4f}) ≈ {CALIB_RADIUS}")

# 最小二乘拟合 ρ = b₀ + b₁·θ + b₂·θ² + ... + bₙ·θⁿ
V = np.zeros((len(theta_samples), THETA_ORDER + 1))
for k in range(THETA_ORDER + 1):
    V[:, k] = theta_samples ** k
pol_coeffs, _, _, _ = np.linalg.lstsq(V, rho_samples, rcond=None)

rho_fit = np.polyval(pol_coeffs[::-1], theta_samples)
fit_err = np.abs(rho_fit - rho_samples).max()
print(f"  拟合 max 误差: {fit_err:.4f} px")
print(f"  pol(-π/2) = {np.polyval(pol_coeffs[::-1], -np.pi/2):.4f} (期望≈0)")
print(f"  pol({theta_max:.4f}) = {np.polyval(pol_coeffs[::-1], theta_max):.4f} (期望≈{CALIB_RADIUS})")

# ============================================================
# 3. Backward Mapping: 透视矫正图像 → 鱼眼图像
# ============================================================
print(f"\n生成 backward mapping ({W_OUT}×{H_OUT} → {W_IN}×{H_IN})...")

# 虚拟透视相机参数 (同 undistort.m)
Nxc = H_OUT / 2.0   # 240
Nyc = W_OUT / 2.0   # 320
Nz  = -W_OUT / FC   # -160

# 输出像素网格
u_out_grid, v_out_grid = np.meshgrid(np.arange(W_OUT, dtype=np.float64),
                                      np.arange(H_OUT, dtype=np.float64))

# 3D 点 (在虚拟像平面上, 未归一化 — 同 world2cam_fast)
Nx = v_out_grid - Nxc
Ny = u_out_grid - Nyc

# ---- world2cam_fast: 未归一化 3D 点 → 鱼眼像素 ----
# NORM = sqrt(Nx² + Ny²), 避免除零
NORM_xy = np.sqrt(Nx**2 + Ny**2)
NORM_xy = np.maximum(NORM_xy, 1e-12)
Nz_val = np.full_like(Nx, Nz)

# θ = atan(Nz / NORM) — Nz 为负, θ 为负 (world2cam_fast 不做绝对值!)
theta = np.arctan(Nz_val / NORM_xy)

# ρ = polyval(pol, θ) — 直接使用负 θ, pol 在负域也有定义
rho = np.polyval(pol_coeffs[::-1], theta)

# XY 方向投影
scale = rho / NORM_xy
x_cam = Nx * scale
y_cam = Ny * scale

# 仿射变换 + 加回中心
u_in = x_cam * C + y_cam * D + XC
v_in = x_cam * E + y_cam      + YC

print(f"  u_in 范围: [{u_in.min():.2f}, {u_in.max():.2f}]")
print(f"  v_in 范围: [{v_in.min():.2f}, {v_in.max():.2f}]")

# 标记有效像素 (落入鱼眼图内的)
valid_mask = (u_in >= 0) & (u_in < W_IN) & (v_in >= 0) & (v_in < H_IN)
print(f"  有效像素比例: {valid_mask.sum() / valid_mask.size * 100:.1f}%")

# ============================================================
# 4. 读取图像 & 生成黄金参考
# ============================================================
print(f"\n读取 VMRImage1.jpg...")
import cv2
def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    with open(str(path), 'rb') as f:
        data = f.read()
    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), flags)
def imwrite_unicode(path, img):
    _, buf = cv2.imencode(os.path.splitext(str(path))[1], img)
    with open(str(path), 'wb') as f:
        f.write(buf)

img_fisheye = imread_unicode(IMG_SRC, cv2.IMREAD_COLOR)  # BGR
print(f"  图像: {img_fisheye.shape}, dtype={img_fisheye.dtype}")

# 生成矫正黄金参考 (双线性插值)
print("生成透视矫正黄金参考图像...")
u_in_clip = np.clip(u_in, 0, W_IN - 1)
v_in_clip = np.clip(v_in, 0, H_IN - 1)

# 双线性插值
u0 = np.floor(u_in_clip).astype(np.int32)
v0 = np.floor(v_in_clip).astype(np.int32)
u1 = np.minimum(u0 + 1, W_IN - 1)
v1 = np.minimum(v0 + 1, H_IN - 1)
wu = (u_in_clip - u0.astype(np.float64)).reshape(H_OUT, W_OUT, 1)
wv = (v_in_clip - v0.astype(np.float64)).reshape(H_OUT, W_OUT, 1)

img_rect = ((1 - wv) * (1 - wu) * img_fisheye[v0, u0].astype(np.float64) +
             (1 - wv) * wu       * img_fisheye[v0, u1].astype(np.float64) +
             wv       * (1 - wu) * img_fisheye[v1, u0].astype(np.float64) +
             wv       * wu       * img_fisheye[v1, u1].astype(np.float64))
img_rect = np.clip(np.round(img_rect), 0, 255).astype(np.uint8)

# 无效区域置灰
img_rect[~valid_mask] = [128, 128, 128]

imwrite_unicode(OUT_DIR / "verify/golden_rectified_perspective.tif", img_rect)
print(f"  黄金参考: {OUT_DIR / 'verify/golden_rectified_perspective.tif'}")

# ============================================================
# 5. RGB → YUV 转换 & 保存
# ============================================================
print("\n" + "=" * 72)
print("YUV 格式转换")
print("=" * 72)

def rgb_to_yuv_bt601(img_bgr):
    img = img_bgr.astype(np.float64)
    B, G, R = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    Y  = 0.299 * R + 0.587 * G + 0.114 * B
    U  = -0.169 * R - 0.331 * G + 0.500 * B + 128.0
    V  = 0.500 * R - 0.419 * G - 0.081 * B + 128.0
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
        yuyv[:, col*4+0] = Y[:, col*2]
        yuyv[:, col*4+1] = U_sub[:, col]
        yuyv[:, col*4+2] = Y[:, col*2+1]
        yuyv[:, col*4+3] = V_sub[:, col]
    return yuyv

# --- 鱼眼输入 ---
Yf, Uf, Vf = rgb_to_yuv_bt601(img_fisheye)
for fmt_name, pack_fn, y_dir, uv_dir in [
    ("nv12", pack_nv12, "input/nv12", "input/nv12"),
    ("nv16", pack_nv16, "input/nv16", "input/nv16"),
    ("yuyv", None,      "input/yuyv", "input/yuyv"),
]:
    if fmt_name == "yuyv":
        data = pack_yuyv(Yf, Uf, Vf)
        data.tofile(str(OUT_DIR / uv_dir / "distorted_yuyv.bin"))
        print(f"  {fmt_name}: {OUT_DIR / uv_dir / 'distorted_yuyv.bin'} ({data.size} bytes)")
    else:
        Yp, UVp = pack_fn(Yf, Uf, Vf)
        Yp.tofile(str(OUT_DIR / y_dir / f"distorted_{fmt_name}_y.bin"))
        UVp.tofile(str(OUT_DIR / uv_dir / f"distorted_{fmt_name}_uv.bin"))
        print(f"  {fmt_name}: Y={OUT_DIR / y_dir / f'distorted_{fmt_name}_y.bin'} ({Yp.size}B)")
        print(f"           UV={OUT_DIR / uv_dir / f'distorted_{fmt_name}_uv.bin'} ({UVp.size}B)")

# --- 黄金参考输出 ---
Yr, Ur, Vr = rgb_to_yuv_bt601(img_rect)
for fmt_name, pack_fn, y_dir, uv_dir in [
    ("nv12", pack_nv12, "golden/nv12", "golden/nv12"),
    ("nv16", pack_nv16, "golden/nv16", "golden/nv16"),
    ("yuyv", None,      "golden/yuyv", "golden/yuyv"),
]:
    if fmt_name == "yuyv":
        data = pack_yuyv(Yr, Ur, Vr)
        data.tofile(str(OUT_DIR / uv_dir / "golden_yuyv.bin"))
    else:
        Yp, UVp = pack_fn(Yr, Ur, Vr)
        Yp.tofile(str(OUT_DIR / y_dir / f"golden_{fmt_name}_y.bin"))
        UVp.tofile(str(OUT_DIR / uv_dir / f"golden_{fmt_name}_uv.bin"))

# 独立平面
Yr.tofile(str(OUT_DIR / "golden/golden_y_plane.bin"))
Ur.tofile(str(OUT_DIR / "golden/golden_u_plane.bin"))
Vr.tofile(str(OUT_DIR / "golden/golden_v_plane.bin"))

# ============================================================
# 6. AGDC Mesh Table 生成 (36-bit 格式)
# ============================================================
print("\n" + "=" * 72)
print("AGDC Mesh Table 生成")
print("=" * 72)

FRAC_BITS = 5
FRAC_SCALE = 1 << FRAC_BITS

def float_to_u12_5(val):
    fixed = np.round(val * FRAC_SCALE).astype(np.int64)
    return np.clip(fixed, -(1<<17), (1<<17)-1).astype(np.int32)

MESH_CONFIGS = [
    ("16x12", 16, 12),
    ("32x24", 32, 24),
]

all_mesh_info = {}

for mesh_name, mesh_cols, mesh_rows in MESH_CONFIGS:
    grid_cols = mesh_cols + 1
    grid_rows = mesh_rows + 1
    num_nodes = grid_cols * grid_rows

    # 输出网格点 (在矫正图像中均匀分布)
    col_pos = np.linspace(0, W_OUT, grid_cols).astype(np.int32)
    row_pos = np.linspace(0, H_OUT, grid_rows).astype(np.int32)
    # 边界节点 (col=W_OUT 或 row=H_OUT) 超出一像素, 钳位到有效范围
    col_idx = np.clip(col_pos, 0, W_OUT - 1)
    row_idx = np.clip(row_pos, 0, H_OUT - 1)

    mesh_u = u_in[row_idx[:, None], col_idx[None, :]]
    mesh_v = v_in[row_idx[:, None], col_idx[None, :]]

    print(f"\n--- 网格 {mesh_name}: {grid_cols}×{grid_rows} = {num_nodes} 节点 ---")
    print(f"  mesh_u: [{mesh_u.min():.2f}, {mesh_u.max():.2f}]")
    print(f"  mesh_v: [{mesh_v.min():.2f}, {mesh_v.max():.2f}]")

    mesh_u_fixed = float_to_u12_5(mesh_u)
    mesh_v_fixed = float_to_u12_5(mesh_v)

    u_err = np.abs(mesh_u - mesh_u_fixed.astype(np.float64) / FRAC_SCALE).max()
    v_err = np.abs(mesh_v - mesh_v_fixed.astype(np.float64) / FRAC_SCALE).max()
    print(f"  u12.5 量化误差: u_max={u_err:.6f}, v_max={v_err:.6f}")

    # 封装 36-bit
    mesh_entries = np.zeros(num_nodes, dtype=np.uint64)
    for iy in range(grid_rows):
        for ix in range(grid_cols):
            addr = iy * grid_cols + ix
            mesh_entries[addr] = ((np.uint64(mesh_v_fixed[iy, ix]) & 0x3FFFF) << 18) | \
                                  (np.uint64(mesh_u_fixed[iy, ix]) & 0x3FFFF)

    mesh_dir = OUT_DIR / "mesh" / mesh_name

    # hex
    hex_path = mesh_dir / f"agdc_mesh_{mesh_name}_36bit.hex"
    with open(str(hex_path), 'w') as f:
        f.write(f"// AGDC Fisheye Mesh Table: {mesh_name} tiles (Scaramuzza model)\n")
        f.write(f"// Nodes: {grid_cols}x{grid_rows} = {num_nodes}\n")
        f.write(f"// Format: 36-bit = {{v[17:0], u[17:0]}}, u12.5 signed\n")
        f.write(f"// Fisheye image: {W_IN}x{H_IN}, Rectified: {W_OUT}x{H_OUT}\n\n")
        for addr in range(num_nodes):
            iy, ix = addr // grid_cols, addr % grid_cols
            entry = mesh_entries[addr]
            f.write(f"@{addr:04X}  // node({ix:02d},{iy:02d})  "
                    f"u=0x{int(mesh_u_fixed[iy,ix]) & 0x3FFFF:05X}({mesh_u[iy,ix]:10.2f})  "
                    f"v=0x{int(mesh_v_fixed[iy,ix]) & 0x3FFFF:05X}({mesh_v[iy,ix]:10.2f})  "
                    f"packed=0x{entry:09X}\n")
    print(f"  hex:     {hex_path}")

    # bin64
    bin64_path = mesh_dir / f"agdc_mesh_{mesh_name}_36bit_in_u64.bin"
    mesh_entries.tofile(str(bin64_path))
    print(f"  bin64:   {bin64_path} ({mesh_entries.nbytes}B)")

    # uv_fixed
    uv_path = mesh_dir / f"agdc_mesh_{mesh_name}_uv_fixed.bin"
    uv_flat = np.empty(num_nodes * 2, dtype=np.int32)
    uv_flat[0::2] = mesh_u_fixed.flatten()
    uv_flat[1::2] = mesh_v_fixed.flatten()
    uv_flat.tofile(str(uv_path))
    print(f"  uv_fixed:{uv_path} ({uv_flat.nbytes}B)")

    # C header
    h_path = mesh_dir / f"agdc_mesh_{mesh_name}.h"
    with open(str(h_path), 'w') as f:
        f.write(f"// AGDC Fisheye Mesh Table (Scaramuzza) - {mesh_name} tiles\n")
        f.write(f"#pragma once\n#include <stdint.h>\n\n")
        f.write(f"#define AGDC_MESH_COLS   {grid_cols}\n")
        f.write(f"#define AGDC_MESH_ROWS   {grid_rows}\n")
        f.write(f"#define AGDC_MESH_NODES  {num_nodes}\n")
        f.write(f"#define AGDC_IMG_WIDTH   {W_OUT}\n")
        f.write(f"#define AGDC_IMG_HEIGHT  {H_OUT}\n")
        f.write(f"#define AGDC_FRAC_BITS   {FRAC_BITS}\n\n")
        f.write(f"static const uint64_t agdc_mesh[{num_nodes}] = {{\n")
        for iy in range(grid_rows):
            vals = ", ".join(f"0x{mesh_entries[iy*grid_cols + ix]:09X}ULL" for ix in range(grid_cols))
            f.write(f"    {vals},\n")
        f.write(f"}};\n")
    print(f"  header:  {h_path}")

    all_mesh_info[mesh_name] = {
        "grid_cols": grid_cols, "grid_rows": grid_rows, "num_nodes": num_nodes,
        "u_range_float": [float(mesh_u.min()), float(mesh_u.max())],
        "v_range_float": [float(mesh_v.min()), float(mesh_v.max())],
    }

# ============================================================
# 7. 验证: 网格表重建 vs 全精度
# ============================================================
print(f"\n{'='*72}")
print("AGDC 网格表精度验证")
print(f"{'='*72}")

for mesh_name, mesh_cols, mesh_rows in MESH_CONFIGS:
    grid_cols = mesh_cols + 1; grid_rows = mesh_rows + 1
    col_pos = np.linspace(0, W_OUT, grid_cols)
    row_pos = np.linspace(0, H_OUT, grid_rows)
    c_idx = np.clip(np.round(col_pos).astype(np.int32), 0, W_OUT - 1)
    r_idx = np.clip(np.round(row_pos).astype(np.int32), 0, H_OUT - 1)
    mu = u_in[r_idx[:, None], c_idx[None, :]]
    mv = v_in[r_idx[:, None], c_idx[None, :]]

    out = np.full((H_OUT, W_OUT, 3), 128, dtype=np.float64)
    for iy in range(H_OUT):
        ry = max(1, min(np.searchsorted(row_pos, iy), grid_rows - 1))
        y0, y1 = int(row_pos[ry-1]), int(row_pos[ry])
        wy = (iy - y0) / max(y1 - y0, 1e-6)
        for ix in range(W_OUT):
            rx = max(1, min(np.searchsorted(col_pos, ix), grid_cols - 1))
            x0, x1 = int(col_pos[rx-1]), int(col_pos[rx])
            wx = (ix - x0) / max(x1 - x0, 1e-6)
            x_in = (1-wy)*((1-wx)*mu[ry-1,rx-1] + wx*mu[ry-1,rx]) + wy*((1-wx)*mu[ry,rx-1] + wx*mu[ry,rx])
            y_in = (1-wy)*((1-wx)*mv[ry-1,rx-1] + wx*mv[ry-1,rx]) + wy*((1-wx)*mv[ry,rx-1] + wx*mv[ry,rx])
            xi = int(np.clip(np.round(x_in), 0, W_IN-1))
            yi = int(np.clip(np.round(y_in), 0, H_IN-1))
            valid = (x_in >= 0 and x_in < W_IN and y_in >= 0 and y_in < H_IN)
            if valid:
                out[iy, ix, :] = img_fisheye[yi, xi, :]

    out = out.astype(np.uint8)
    diff = out.astype(np.float32) - img_rect.astype(np.float32)
    diff[~valid_mask] = 0
    mae = np.abs(diff[valid_mask]).mean() if valid_mask.any() else 0
    maxe = np.abs(diff).max()
    print(f"  {mesh_name}: MAE={mae:.4f}, MaxError={maxe:.0f}")
    imwrite_unicode(OUT_DIR / "verify" / f"reconstructed_mesh_{mesh_name}.tif", out)

# ============================================================
# 8. manifest.json
# ============================================================
manifest = {
    "description": "AGDC Mesh Table & Golden Reference — VMRImage1.jpg (Fisheye)",
    "model": "Scaramuzza Omnidirectional Camera Model",
    "calibration_source": str(CALIB_DIR / "get_ocam_model.m"),
    "parameters": {
        "ss": SS.tolist(),
        "xc": XC, "yc": YC,
        "c": C, "d": D, "e": E,
        "calib_radius": CALIB_RADIUS,
        "pol_coeffs_fitted": pol_coeffs.tolist(),
        "theta_order": THETA_ORDER,
        "theta_max_deg": float(np.rad2deg(theta_max)),
    },
    "image": {
        "input": str(IMG_SRC),
        "input_size": [W_IN, H_IN],
        "output_size": [W_OUT, H_OUT],
        "virtual_fc": FC,
    },
    "format_spec": {
        "mesh_node_format": "36-bit = {v[17:0], u[17:0]}",
        "coordinate_format": "u12.5 signed",
        "sram_addressing": "addr = iy * (mesh_cols+1) + ix",
        "frac_bits": 5,
    },
    "mesh_tables": all_mesh_info,
    "centroid_estimation_note": (
        "xc=512,yc=384 为 1024×768 的几何中心,"
        "无显式标定结果文件,从 get_ocam_model.m 推算"
    ),
}

with open(str(OUT_DIR / "manifest.json"), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

# 复制源图像
import shutil
shutil.copy2(str(IMG_SRC), str(OUT_DIR / "source/VMRImage1.jpg"))

print(f"\n{'='*72}")
print(f"完成! 输出目录: {OUT_DIR}")
print(f"{'='*72}")
