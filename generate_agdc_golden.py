"""
AGDC Mesh Table & Golden Reference Generator (v2)
==================================================
严格按照硬件规格生成：

1. AGDC Mesh Table
   - 纯解析畸变公式，不依赖 OpenCV 畸变函数
   - 每节点 36-bit = {v[17:0], u[17:0]}，u12.5 signed 定点数
   - SRAM 寻址：addr = iy * (mesh_cols+1) + ix，行主序
   - 网格点数：(mesh_cols+1) × (mesh_rows+1)

2. 畸变输入图像 → YUV 三格式转换（仿真激励输入）
   - YUV420SP (NV12) 8-bit
   - YUV422SP (NV16) 8-bit
   - YUV422I  (YUYV) 8-bit

3. 黄金参考模型 = Image_rect1.tif 的 YUV 三格式（期望输出）

全部输出绝对路径。
"""

import numpy as np
import os
import struct
import json
from pathlib import Path

# ============================================================
# 0. 路径与输出目录
# ============================================================
BASE_DIR = Path(r"d:\Clone\CameraCalibration")
CALIB_DIR = Path(r"d:\Clone\CameraCalibration\相机标定课程\第一章 标定基础知识 code & data\matlab_sample\calib_example")
OUT_DIR = BASE_DIR / "agdc_test"
OUT_DIR.mkdir(exist_ok=True)

IMG_DISTORTED_PATH = CALIB_DIR / "Image1.tif"
IMG_RECTIFIED_PATH = CALIB_DIR / "Image_rect1.tif"

print("=" * 72)
print("AGDC Mesh Table & Golden Reference Generator")
print("=" * 72)
print(f"输入畸变图像:   {IMG_DISTORTED_PATH}")
print(f"输入矫正图像:   {IMG_RECTIFIED_PATH}")
print(f"输出目录:       {OUT_DIR}")

# ============================================================
# 1. 标定参数 (来自 Calib_Results.m)
# ============================================================
fc   = np.array([657.446107869218281, 657.876660256090418], dtype=np.float64)  # fx, fy
cc   = np.array([303.185319795283419, 242.708481163875661], dtype=np.float64)  # cx, cy
kc   = np.array([-0.255414841834118, 0.124449907410458,
                 -0.000216975662453, 0.000074351611502, 0.0], dtype=np.float64)  # k1,k2,p1,p2,k3
W, H = 640, 480

# ---- 构建内参矩阵 ----
K = np.array([[fc[0], 0,      cc[0]],
              [0,      fc[1], cc[1]],
              [0,      0,     1    ]], dtype=np.float64)
K_inv = np.linalg.inv(K)

print(f"\n内参 K:\n{K}")
print(f"畸变系数 kc = {kc}")
print(f"图像尺寸: {W} x {H}")

# ============================================================
# 2. 纯解析 Backward Distortion Mapping
# ============================================================
# 对输出（矫正后）坐标 (u_out, v_out)，计算其在输入（畸变）图像中的坐标
# 使用 Bouguet MATLAB Calibration Toolbox 的 Brown-Conrady 模型：
#
#   1. 归一化:  xn = (u_out - cx) / fx
#               yn = (v_out - cy) / fy
#   2. r² = xn² + yn²
#   3. 径向畸变:
#        xd1 = xn * (1 + k1*r² + k2*r⁴ + k5*r⁶)
#        yd1 = yn * (1 + k1*r² + k2*r⁴ + k5*r⁶)
#   4. 切向畸变:
#        xd = xd1 + 2*p1*xn*yn + p2*(r² + 2*xn²)
#        yd = yd1 + p1*(r² + 2*yn²) + 2*p2*xn*yn
#   5. 像素化:  u_in = fx * xd + cx
#               v_in = fy * yd + cy

k1, k2, p1, p2, k5 = kc

print("\n计算全分辨率 backward mapping (解析法, 无 OpenCV)...")

# 输出图像网格
u_out, v_out = np.meshgrid(np.arange(W, dtype=np.float64),
                            np.arange(H, dtype=np.float64))  # (H, W)

# Step 1: 归一化
xn = (u_out - cc[0]) / fc[0]
yn = (v_out - cc[1]) / fc[1]

# Step 2: r²
r2 = xn * xn + yn * yn
r4 = r2 * r2
r6 = r2 * r4

# Step 3: 径向畸变
radial = 1.0 + k1 * r2 + k2 * r4 + k5 * r6
xd = xn * radial
yd = yn * radial

# Step 4: 切向畸变
xd = xd + 2.0 * p1 * xn * yn + p2 * (r2 + 2.0 * xn * xn)
yd = yd + p1 * (r2 + 2.0 * yn * yn) + 2.0 * p2 * xn * yn

# Step 5: 像素化
map_u = fc[0] * xd + cc[0]  # 输入图像 x 坐标 (H, W)
map_v = fc[1] * yd + cc[1]  # 输入图像 y 坐标 (H, W)

# 统计
print(f"  map_u 范围: [{map_u.min():.4f}, {map_u.max():.4f}]")
print(f"  map_v 范围: [{map_v.min():.4f}, {map_v.max():.4f}]")

# ---- 验证与 OpenCV 的一致性 ----
import cv2
# OpenCV 的畸变格式: [k1,k2,p1,p2,k3,k4,k5,k6,s1,s2,s3,s4,tau_x,tau_y]
# MATLAB 的 kc = [k1,k2,p1,p2,k3]，OpenCV 兼容此 5 参数格式
cv_map1, cv_map2 = cv2.initUndistortRectifyMap(K, kc.reshape(1,5), None, K, (W,H), cv2.CV_32FC1)
diff_u = np.abs(map_u - cv_map1.astype(np.float64))
diff_v = np.abs(map_v - cv_map2.astype(np.float64))
print(f"  与 OpenCV 偏差: map_u MAE={diff_u.mean():.6f}, map_v MAE={diff_v.mean():.6f}")

# ============================================================
# 3. 读取图像
# ============================================================
def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    """OpenCV imread with Unicode path support."""
    with open(str(path), 'rb') as f:
        data = f.read()
    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), flags)

def imwrite_unicode(path, img):
    ext = os.path.splitext(str(path))[1]
    _, buf = cv2.imencode(ext, img)
    with open(str(path), 'wb') as f:
        f.write(buf)

img_dist = imread_unicode(IMG_DISTORTED_PATH, cv2.IMREAD_COLOR)  # BGR
img_rect = imread_unicode(IMG_RECTIFIED_PATH, cv2.IMREAD_COLOR)  # BGR

if img_dist is None:
    raise FileNotFoundError(f"无法读取: {IMG_DISTORTED_PATH}")
if img_rect is None:
    raise FileNotFoundError(f"无法读取: {IMG_RECTIFIED_PATH}")

print(f"\n畸变图像 (Image1.tif):   shape={img_dist.shape}, dtype={img_dist.dtype}")
print(f"矫正图像 (Image_rect1.tif): shape={img_rect.shape}, dtype={img_rect.dtype}")

# ============================================================
# 4. RGB → YUV 转换
# ============================================================
def rgb_to_yuv_bt601(img_bgr):
    """
    BGR → YUV (BT.601 SD)
    Y  =  0.299*R + 0.587*G + 0.114*B
    U  = -0.169*R - 0.331*G + 0.500*B + 128
    V  =  0.500*R - 0.419*G - 0.081*B + 128

    输入: BGR uint8 (H, W, 3)
    返回: Y (H,W), U (H,W), V (H,W) 均为 uint8
    """
    img = img_bgr.astype(np.float64)
    B, G, R = img[:, :, 0], img[:, :, 1], img[:, :, 2]

    Y = 0.299 * R + 0.587 * G + 0.114 * B
    U = -0.169 * R - 0.331 * G + 0.500 * B + 128.0
    V = 0.500 * R - 0.419 * G - 0.081 * B + 128.0

    return (np.clip(Y, 0, 255).astype(np.uint8),
            np.clip(U, 0, 255).astype(np.uint8),
            np.clip(V, 0, 255).astype(np.uint8))

def pack_nv12(Y, U, V):
    """YUV420SP (NV12): Y 全分辨率 + UV 交错 (2x2 子采样)"""
    H, W = Y.shape
    # UV 子采样: 每 2x2 块取平均
    U_sub = (U[0:H:2, 0:W:2].astype(np.uint16) +
             U[0:H:2, 1:W:2].astype(np.uint16) +
             U[1:H:2, 0:W:2].astype(np.uint16) +
             U[1:H:2, 1:W:2].astype(np.uint16) + 2) // 4
    V_sub = (V[0:H:2, 0:W:2].astype(np.uint16) +
             V[0:H:2, 1:W:2].astype(np.uint16) +
             V[1:H:2, 0:W:2].astype(np.uint16) +
             V[1:H:2, 1:W:2].astype(np.uint16) + 2) // 4
    U_sub = U_sub.astype(np.uint8)
    V_sub = V_sub.astype(np.uint8)
    # 交错: UVUVUV...
    uv_interleaved = np.empty((H // 2, W // 2 * 2), dtype=np.uint8)
    uv_interleaved[:, 0::2] = U_sub
    uv_interleaved[:, 1::2] = V_sub
    return Y, uv_interleaved

def pack_nv16(Y, U, V):
    """YUV422SP (NV16): Y 全分辨率 + UV 交错 (仅水平 2x1 子采样)"""
    H, W = Y.shape
    # 水平子采样
    U_sub = ((U[:, 0:W:2].astype(np.uint16) +
              U[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    V_sub = ((V[:, 0:W:2].astype(np.uint16) +
              V[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    # 交错: UVUVUV...
    uv_interleaved = np.empty((H, W // 2 * 2), dtype=np.uint8)
    uv_interleaved[:, 0::2] = U_sub
    uv_interleaved[:, 1::2] = V_sub
    return Y, uv_interleaved

def pack_yuyv(Y, U, V):
    """YUV422I (YUYV): YUYV 打包 (仅水平 2x1 子采样)"""
    H, W = Y.shape
    # 水平子采样
    U_sub = ((U[:, 0:W:2].astype(np.uint16) +
              U[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    V_sub = ((V[:, 0:W:2].astype(np.uint16) +
              V[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    # 打包: Y0 U0 Y1 V0 Y2 U1 Y3 V1 ...
    yuyv = np.empty((H, W * 2), dtype=np.uint8)
    for col in range(W // 2):
        yuyv[:, col * 4 + 0] = Y[:, col * 2]
        yuyv[:, col * 4 + 1] = U_sub[:, col]
        yuyv[:, col * 4 + 2] = Y[:, col * 2 + 1]
        yuyv[:, col * 4 + 3] = V_sub[:, col]
    return yuyv

# ---- 转换畸变图像 → YUV 三种格式 ----
print("\n" + "=" * 72)
print("YUV 格式转换 (畸变输入图像 → 仿真激励)")
print("=" * 72)

Y_dist, U_dist, V_dist = rgb_to_yuv_bt601(img_dist)

# NV12
Y_nv12, UV_nv12 = pack_nv12(Y_dist, U_dist, V_dist)
nv12_path_y   = OUT_DIR / "distorted_nv12_y.bin"
nv12_path_uv  = OUT_DIR / "distorted_nv12_uv.bin"
nv12_path_meta = OUT_DIR / "distorted_nv12.json"
Y_nv12.tofile(str(nv12_path_y))
UV_nv12.tofile(str(nv12_path_uv))
print(f"\nYUV420SP (NV12):")
print(f"  Y  plane: {nv12_path_y}  ({Y_nv12.size} bytes, {Y_nv12.shape})")
print(f"  UV plane: {nv12_path_uv}  ({UV_nv12.size} bytes, {UV_nv12.shape})")

# NV16
Y_nv16, UV_nv16 = pack_nv16(Y_dist, U_dist, V_dist)
nv16_path_y   = OUT_DIR / "distorted_nv16_y.bin"
nv16_path_uv  = OUT_DIR / "distorted_nv16_uv.bin"
Y_nv16.tofile(str(nv16_path_y))
UV_nv16.tofile(str(nv16_path_uv))
print(f"\nYUV422SP (NV16):")
print(f"  Y  plane: {nv16_path_y}  ({Y_nv16.size} bytes, {Y_nv16.shape})")
print(f"  UV plane: {nv16_path_uv}  ({UV_nv16.size} bytes, {UV_nv16.shape})")

# YUYV
yuyv_data = pack_yuyv(Y_dist, U_dist, V_dist)
yuyv_path = OUT_DIR / "distorted_yuyv.bin"
yuyv_data.tofile(str(yuyv_path))
print(f"\nYUV422I (YUYV):")
print(f"  YUYV packed: {yuyv_path}  ({yuyv_data.size} bytes, {yuyv_data.shape})")

# ---- 转换矫正图像 → YUV 三种格式 (黄金参考) ----
print("\n" + "=" * 72)
print("YUV 格式转换 (矫正图像 → 黄金参考输出)")
print("=" * 72)

Y_rect, U_rect, V_rect = rgb_to_yuv_bt601(img_rect)

# NV12
Yr_nv12, UVr_nv12 = pack_nv12(Y_rect, U_rect, V_rect)
gr_nv12_y   = OUT_DIR / "golden_nv12_y.bin"
gr_nv12_uv  = OUT_DIR / "golden_nv12_uv.bin"
Yr_nv12.tofile(str(gr_nv12_y))
UVr_nv12.tofile(str(gr_nv12_uv))
print(f"\nYUV420SP (NV12):")
print(f"  Y  plane: {gr_nv12_y}  ({Yr_nv12.size} bytes, {Yr_nv12.shape})")
print(f"  UV plane: {gr_nv12_uv}  ({UVr_nv12.size} bytes, {UVr_nv12.shape})")

# NV16
Yr_nv16, UVr_nv16 = pack_nv16(Y_rect, U_rect, V_rect)
gr_nv16_y   = OUT_DIR / "golden_nv16_y.bin"
gr_nv16_uv  = OUT_DIR / "golden_nv16_uv.bin"
Yr_nv16.tofile(str(gr_nv16_y))
UVr_nv16.tofile(str(gr_nv16_uv))
print(f"\nYUV422SP (NV16):")
print(f"  Y  plane: {gr_nv16_y}  ({Yr_nv16.size} bytes, {Yr_nv16.shape})")
print(f"  UV plane: {gr_nv16_uv}  ({UVr_nv16.size} bytes, {UVr_nv16.shape})")

# YUYV
yuyv_rect = pack_yuyv(Y_rect, U_rect, V_rect)
gr_yuyv_path = OUT_DIR / "golden_yuyv.bin"
yuyv_rect.tofile(str(gr_yuyv_path))
print(f"\nYUV422I (YUYV):")
print(f"  YUYV packed: {gr_yuyv_path}  ({yuyv_rect.size} bytes, {yuyv_rect.shape})")

# 保存完整平面供参考 (Y, U, V 独立)
Y_rect.tofile(str(OUT_DIR / "golden_y_plane.bin"))
U_rect.tofile(str(OUT_DIR / "golden_u_plane.bin"))
V_rect.tofile(str(OUT_DIR / "golden_v_plane.bin"))
print(f"\n独立 Y/U/V 平面 (逐像素参考):")
print(f"  Y: {OUT_DIR / 'golden_y_plane.bin'}  ({Y_rect.size} bytes)")
print(f"  U: {OUT_DIR / 'golden_u_plane.bin'}  ({U_rect.size} bytes)")
print(f"  V: {OUT_DIR / 'golden_v_plane.bin'}  ({V_rect.size} bytes)")

# ============================================================
# 5. 生成 AGDC Mesh Table (36-bit 格式)
# ============================================================
print("\n" + "=" * 72)
print("AGDC Mesh Table 生成")
print("=" * 72)

# ---- u12.5 定点数工具函数 ----
FRAC_BITS = 5
FRAC_SCALE = 1 << FRAC_BITS  # 32
U12_5_MAX  = (1 << 17) - 1   # 131071  (18-bit signed max positive)
U12_5_MIN  = -(1 << 17)      # -131072

def float_to_u12_5(val):
    """浮点数 → u12.5 有符号 18-bit 定点数，饱和截断"""
    fixed = np.round(val * FRAC_SCALE).astype(np.int64)
    fixed = np.clip(fixed, U12_5_MIN, U12_5_MAX)
    return fixed.astype(np.int32)

def u12_5_to_float(fixed):
    """u12.5 定点 → 浮点"""
    return fixed.astype(np.float64) / FRAC_SCALE

def pack_mesh_entry(u_fixed, v_fixed):
    """
    封装一个 AGDC 节点:
      36-bit = {v[17:0], u[17:0]}
      u 在低 18-bit，v 在高 18-bit
    返回 64-bit 整数便于存储
    """
    u18 = np.uint64(u_fixed) & np.uint64(0x3FFFF)
    v18 = np.uint64(v_fixed) & np.uint64(0x3FFFF)
    return (v18 << 18) | u18

# ---- 网格配置 ----
# 默认: 16x12 tiles → 17x13 nodes，同时生成 32x24 tiles
MESH_CONFIGS = [
    # (名称, mesh_cols, mesh_rows)
    ("16x12", 16, 12),   # 17x13 = 221 nodes
    ("32x24", 32, 24),   # 33x25 = 825 nodes
]

all_mesh_info = {}

for mesh_name, mesh_cols, mesh_rows in MESH_CONFIGS:
    grid_cols = mesh_cols + 1  # 网格点数 (列)
    grid_rows = mesh_rows + 1  # 网格点数 (行)
    num_nodes = grid_cols * grid_rows

    print(f"\n--- 网格 {mesh_name}: {grid_cols}x{grid_rows} = {num_nodes} 节点 ---")

    # 输出网格点在去畸变图像中的均匀位置
    col_pos = np.linspace(0, W - 1, grid_cols)
    row_pos = np.linspace(0, H - 1, grid_rows)

    # 从全分辨率 backward map 中采样 (解析法结果)
    col_idx = np.round(col_pos).astype(np.int32)
    row_idx = np.round(row_pos).astype(np.int32)
    mesh_u_float = map_u[row_idx[:, np.newaxis], col_idx[np.newaxis, :]]  # (grid_rows, grid_cols)
    mesh_v_float = map_v[row_idx[:, np.newaxis], col_idx[np.newaxis, :]]  # (grid_rows, grid_cols)

    print(f"  mesh_u_float 范围: [{mesh_u_float.min():.4f}, {mesh_u_float.max():.4f}]")
    print(f"  mesh_v_float 范围: [{mesh_v_float.min():.4f}, {mesh_v_float.max():.4f}]")

    # 转 u12.5 定点
    mesh_u_fixed = float_to_u12_5(mesh_u_float)
    mesh_v_fixed = float_to_u12_5(mesh_v_float)

    # 验证定点误差
    u_recon = u12_5_to_float(mesh_u_fixed)
    v_recon = u12_5_to_float(mesh_v_fixed)
    u_err = np.abs(mesh_u_float - u_recon).max()
    v_err = np.abs(mesh_v_float - v_recon).max()
    print(f"  u12.5 量化误差: u_max={u_err:.6f}, v_max={v_err:.6f} (1 LSB = {1.0/FRAC_SCALE:.6f})")

    # ---- 封装为 36-bit entries ----
    mesh_entries = np.zeros(num_nodes, dtype=np.uint64)
    for iy in range(grid_rows):
        for ix in range(grid_cols):
            addr = iy * grid_cols + ix
            mesh_entries[addr] = pack_mesh_entry(mesh_u_fixed[iy, ix],
                                                  mesh_v_fixed[iy, ix])

    # ---- 输出格式 A: SRAM hex 文件 (每行一个 36-bit 值 → 64-bit hex) ----
    hex_path = OUT_DIR / f"agdc_mesh_{mesh_name}_36bit.hex"
    with open(str(hex_path), 'w') as f:
        f.write(f"// AGDC Mesh Table: {mesh_name} tiles\n")
        f.write(f"// Nodes: {grid_cols}x{grid_rows} = {num_nodes}\n")
        f.write(f"// Format per node: 36-bit = {{v[17:0], u[17:0]}}, u12.5 signed\n")
        f.write(f"// SRAM addr = iy * {grid_cols} + ix\n")
        f.write(f"// Image: {W}x{H}\n")
        f.write(f"// Hex values: 64-bit container, lower 36 bits valid\n\n")
        for addr in range(num_nodes):
            iy = addr // grid_cols
            ix = addr % grid_cols
            entry = mesh_entries[addr]
            u_val = mesh_u_fixed[iy, ix]
            v_val = mesh_v_fixed[iy, ix]
            f.write(f"@{addr:04X}  // node({ix:02d},{iy:02d})  "
                    f"u_fixed=0x{u_val & 0x3FFFF:05X}({mesh_u_float[iy,ix]:10.4f})  "
                    f"v_fixed=0x{v_val & 0x3FFFF:05X}({mesh_v_float[iy,ix]:10.4f})  "
                    f"packed=0x{entry:09X}\n")
    print(f"  SRAM hex (含注释): {hex_path}")

    # ---- 输出格式 B: 纯二进制 (每节点 8 字节, little-endian 64-bit) ----
    bin64_path = OUT_DIR / f"agdc_mesh_{mesh_name}_36bit_in_u64.bin"
    mesh_entries.astype(np.uint64).tofile(str(bin64_path))
    print(f"  64-bit LE binary:  {bin64_path}  ({mesh_entries.nbytes} bytes)")

    # ---- 输出格式 C: u/v 分离定点表 (int32, 供 C/RTL 仿真直接引用) ----
    uv_path = OUT_DIR / f"agdc_mesh_{mesh_name}_uv_fixed.bin"
    # 交织存储: [u00, v00, u01, v01, ...]
    uv_interleaved = np.empty(num_nodes * 2, dtype=np.int32)
    for iy in range(grid_rows):
        for ix in range(grid_cols):
            addr = iy * grid_cols + ix
            uv_interleaved[addr * 2]     = mesh_u_fixed[iy, ix]
            uv_interleaved[addr * 2 + 1] = mesh_v_fixed[iy, ix]
    uv_interleaved.tofile(str(uv_path))
    print(f"  u/v交织 int32:    {uv_path}  ({uv_interleaved.nbytes} bytes)")

    # ---- 输出格式 D: C header (定点 + 封装值) ----
    h_path = OUT_DIR / f"agdc_mesh_{mesh_name}.h"
    with open(str(h_path), 'w') as f:
        f.write(f"// AGDC Mesh Table for Image1.tif ({W}x{H})\n")
        f.write(f"// Grid: {mesh_name} tiles ({grid_cols}x{grid_rows} nodes)\n")
        f.write(f"// Format: u12.5 signed, 36-bit/node = {{v[17:0], u[17:0]}}\n")
        f.write(f"// DO NOT EDIT — generated by generate_agdc_golden.py\n\n")
        f.write(f"#pragma once\n")
        f.write(f"#include <stdint.h>\n\n")
        f.write(f"#define AGDC_MESH_COLS   {grid_cols}\n")
        f.write(f"#define AGDC_MESH_ROWS   {grid_rows}\n")
        f.write(f"#define AGDC_MESH_NODES  {num_nodes}\n")
        f.write(f"#define AGDC_IMG_WIDTH   {W}\n")
        f.write(f"#define AGDC_IMG_HEIGHT  {H}\n")
        f.write(f"#define AGDC_FRAC_BITS   5\n\n")

        # 封装表
        f.write(f"// SRAM table: v[17:0] @ bits[35:18], u[17:0] @ bits[17:0]\n")
        f.write(f"static const uint64_t agdc_mesh[{num_nodes}] = {{\n")
        for iy in range(grid_rows):
            line_entries = []
            for ix in range(grid_cols):
                addr = iy * grid_cols + ix
                line_entries.append(f"0x{mesh_entries[addr]:09X}ULL")
            f.write(f"    // row {iy:02d}, node({0:02d}..{grid_cols-1:02d})\n")
            f.write(f"    {', '.join(line_entries)},\n")
        f.write(f"}};\n\n")

        f.write(f"// XY coordinates as float (debug reference)\n")
        f.write(f"static const float agdc_mesh_u_float[{grid_rows}][{grid_cols}] = {{\n")
        for iy in range(grid_rows):
            vals = ", ".join(f"{mesh_u_float[iy,ix]:12.5f}f" for ix in range(grid_cols))
            f.write(f"    {{ {vals} }},\n")
        f.write(f"}};\n\n")
        f.write(f"static const float agdc_mesh_v_float[{grid_rows}][{grid_cols}] = {{\n")
        for iy in range(grid_rows):
            vals = ", ".join(f"{mesh_v_float[iy,ix]:12.5f}f" for ix in range(grid_cols))
            f.write(f"    {{ {vals} }},\n")
        f.write(f"}};\n")
    print(f"  C header:          {h_path}")

    # ---- 记录元信息 ----
    all_mesh_info[mesh_name] = {
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "num_nodes": num_nodes,
        "frac_bits": FRAC_BITS,
        "u_range_float": [float(mesh_u_float.min()), float(mesh_u_float.max())],
        "v_range_float": [float(mesh_v_float.min()), float(mesh_v_float.max())],
        "u_range_fixed": [int(mesh_u_fixed.min()), int(mesh_u_fixed.max())],
        "v_range_fixed": [int(mesh_v_fixed.min()), int(mesh_v_fixed.max())],
        "quant_error_u_max": float(u_err),
        "quant_error_v_max": float(v_err),
    }

# ============================================================
# 6. 黄金参考模型验证 (解析法 vs MATLAB)
# ============================================================
print("\n" + "=" * 72)
print("黄金参考模型验证")
print("=" * 72)

# 使用解析法全分辨率映射，对畸变图做 remap
# 最近邻 (模拟硬件初步验证)
map_u_clip = np.clip(map_u, 0, W - 1)
map_v_clip = np.clip(map_v, 0, H - 1)
ui = np.round(map_u_clip).astype(np.int32)
vi = np.round(map_v_clip).astype(np.int32)

img_rect_analytic_nn = img_dist[vi, ui]  # (H, W, 3)

# 双线性插值
u0 = np.floor(map_u_clip).astype(np.int32)
v0 = np.floor(map_v_clip).astype(np.int32)
u1 = np.minimum(u0 + 1, W - 1)
v1 = np.minimum(v0 + 1, H - 1)
wu = map_u_clip - u0.astype(np.float64)
wv = map_v_clip - v0.astype(np.float64)
wu = wu.reshape(H, W, 1)
wv = wv.reshape(H, W, 1)

img_rect_analytic_bi = ((1 - wv) * (1 - wu) * img_dist[v0, u0].astype(np.float64) +
                         (1 - wv) * wu       * img_dist[v0, u1].astype(np.float64) +
                         wv       * (1 - wu) * img_dist[v1, u0].astype(np.float64) +
                         wv       * wu       * img_dist[v1, u1].astype(np.float64))
img_rect_analytic_bi = np.clip(np.round(img_rect_analytic_bi), 0, 255).astype(np.uint8)

# 与 MATLAB 黄金参考对比
diff_nn = img_rect_analytic_nn.astype(np.float32) - img_rect.astype(np.float32)
diff_bi = img_rect_analytic_bi.astype(np.float32) - img_rect.astype(np.float32)

print(f"\n解析法 NN  vs MATLAB Image_rect1.tif:")
print(f"  MAE={np.abs(diff_nn).mean():.4f}, MaxError={np.abs(diff_nn).max():.0f}")
print(f"\n解析法 Bilinear vs MATLAB Image_rect1.tif:")
print(f"  MAE={np.abs(diff_bi).mean():.4f}, MaxError={np.abs(diff_bi).max():.0f}")

# 保存差异图
imwrite_unicode(OUT_DIR / "diff_analytic_vs_matlab_nn.png",
                np.clip(np.abs(diff_nn) * 5, 0, 255).astype(np.uint8))
imwrite_unicode(OUT_DIR / "diff_analytic_vs_matlab_bi.png",
                np.clip(np.abs(diff_bi) * 5, 0, 255).astype(np.uint8))
imwrite_unicode(OUT_DIR / "golden_rectified_analytic_bi.tif", img_rect_analytic_bi)
imwrite_unicode(OUT_DIR / "golden_rectified_analytic_nn.tif", img_rect_analytic_nn)

print(f"\n差异图 (x5): {OUT_DIR / 'diff_analytic_vs_matlab_nn.png'}")
print(f"差异图 (x5): {OUT_DIR / 'diff_analytic_vs_matlab_bi.png'}")

# ---- 用 AGDC 网格表 (双线性插值重建) 验证 ----
print(f"\n{'='*72}")
print("AGDC 网格表精度验证 (网格表 + 双线性插值 vs 全精度)")
print(f"{'='*72}")

for mesh_name, mesh_cols, mesh_rows in MESH_CONFIGS:
    grid_cols = mesh_cols + 1
    grid_rows = mesh_rows + 1

    # 重新采样
    col_pos = np.linspace(0, W - 1, grid_cols)
    row_pos = np.linspace(0, H - 1, grid_rows)
    col_idx_m = np.round(col_pos).astype(np.int32)
    row_idx_m = np.round(row_pos).astype(np.int32)
    mesh_u = map_u[row_idx_m[:, None], col_idx_m[None, :]]
    mesh_v = map_v[row_idx_m[:, None], col_idx_m[None, :]]

    # 双线性插值重建
    out = img_dist.astype(np.float64).copy()
    for iy in range(H):
        ry = np.searchsorted(row_pos, iy)
        ry = max(1, min(ry, grid_rows - 1))
        y0, y1 = int(row_pos[ry - 1]), int(row_pos[ry])
        wy = (iy - y0) / max(y1 - y0, 1e-6)
        for ix in range(W):
            rx = np.searchsorted(col_pos, ix)
            rx = max(1, min(rx, grid_cols - 1))
            x0, x1 = int(col_pos[rx - 1]), int(col_pos[rx])
            wx = (ix - x0) / max(x1 - x0, 1e-6)

            u00, v00 = mesh_u[ry - 1, rx - 1], mesh_v[ry - 1, rx - 1]
            u01, v01 = mesh_u[ry - 1, rx],     mesh_v[ry - 1, rx]
            u10, v10 = mesh_u[ry, rx - 1],     mesh_v[ry, rx - 1]
            u11, v11 = mesh_u[ry, rx],         mesh_v[ry, rx]

            x_in = (1 - wy) * ((1 - wx) * u00 + wx * u01) + wy * ((1 - wx) * u10 + wx * u11)
            y_in = (1 - wy) * ((1 - wx) * v00 + wx * v01) + wy * ((1 - wx) * v10 + wx * v11)

            xi = int(np.clip(np.round(x_in), 0, W - 1))
            yi = int(np.clip(np.round(y_in), 0, H - 1))
            out[iy, ix, :] = img_dist[yi, xi, :]

    out = out.astype(np.uint8)
    diff_mesh = out.astype(np.float32) - img_rect.astype(np.float32)
    mae_m = np.abs(diff_mesh).mean()
    maxe_m = np.abs(diff_mesh).max()
    print(f"  {mesh_name}: MAE={mae_m:.4f}, MaxError={maxe_m:.0f}")

    imwrite_unicode(OUT_DIR / f"reconstructed_mesh_{mesh_name}.tif", out)
    print(f"    重建图像: {OUT_DIR / f'reconstructed_mesh_{mesh_name}.tif'}")

# ============================================================
# 7. 汇总索引文件
# ============================================================
print("\n" + "=" * 72)
print("生成汇总索引")
print("=" * 72)

manifest = {
    "description": "AGDC Mesh Table & Golden Reference — Image1.tif",
    "calibration": {
        "source": str(CALIB_DIR / "Calib_Results.m"),
        "fc": fc.tolist(),
        "cc": cc.tolist(),
        "kc": kc.tolist(),
        "image_size": [W, H],
    },
    "input_image": str(IMG_DISTORTED_PATH),
    "reference_image": str(IMG_RECTIFIED_PATH),
    "format_spec": {
        "mesh_node_format": "36-bit = {v[17:0], u[17:0]}",
        "coordinate_format": "u12.5 signed (12-bit integer + 5-bit fractional)",
        "sram_addressing": "addr = iy * (mesh_cols+1) + ix, row-major",
        "frac_bits": 5,
        "frac_scale": 32,
        "lsb_value": 1.0 / 32,
    },
    "mesh_tables": {},
    "yuv_inputs": {
        "nv12_y": str(nv12_path_y),
        "nv12_uv": str(nv12_path_uv),
        "nv16_y": str(nv16_path_y),
        "nv16_uv": str(nv16_path_uv),
        "yuyv": str(yuyv_path),
    },
    "golden_reference": {
        "nv12_y": str(gr_nv12_y),
        "nv12_uv": str(gr_nv12_uv),
        "nv16_y": str(gr_nv16_y),
        "nv16_uv": str(gr_nv16_uv),
        "yuyv": str(gr_yuyv_path),
        "y_plane": str(OUT_DIR / "golden_y_plane.bin"),
        "u_plane": str(OUT_DIR / "golden_u_plane.bin"),
        "v_plane": str(OUT_DIR / "golden_v_plane.bin"),
    },
    "validation": {
        "analytic_vs_matlab_nn_mae": float(np.abs(diff_nn).mean()),
        "analytic_vs_matlab_bi_mae": float(np.abs(diff_bi).mean()),
        "analytic_vs_matlab_bi_maxerr": float(np.abs(diff_bi).max()),
    },
}

for mesh_name in MESH_CONFIGS:
    name = mesh_name[0]
    manifest["mesh_tables"][name] = {
        **all_mesh_info[name],
        "hex_file": str(OUT_DIR / f"agdc_mesh_{name}_36bit.hex"),
        "bin64_file": str(OUT_DIR / f"agdc_mesh_{name}_36bit_in_u64.bin"),
        "uv_interleaved_file": str(OUT_DIR / f"agdc_mesh_{name}_uv_fixed.bin"),
        "c_header": str(OUT_DIR / f"agdc_mesh_{name}.h"),
    }

manifest_path = OUT_DIR / "manifest.json"
with open(str(manifest_path), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f"汇总索引: {manifest_path}")

# ============================================================
# 8. 输出完整文件清单
# ============================================================
print(f"\n{'='*72}")
print(f"全部输出文件")
print(f"{'='*72}\n")

def print_tree(path, prefix=""):
    path = Path(path)
    if path.is_dir():
        print(f"{prefix}{path.name}/")
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        for item in items:
            print_tree(item, prefix + "  ")
    else:
        size = path.stat().st_size
        unit = "B"
        if size >= 1024:
            size /= 1024; unit = "KB"
        print(f"{prefix}{path.name}  ({size:.1f} {unit})")

print_tree(OUT_DIR)

print(f"\n生成脚本: {Path(__file__).resolve()}")
print("完成。")
