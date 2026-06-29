"""
AGDC (Adaptive Geometric Distortion Correction) Mesh Table & Golden Reference Generator
=========================================================================================
使用 Image1.tif 及其 MATLAB 标定参数 (Calib_Results.m) 生成：
1. AGDC 网格映射表 (mesh table) — 硬件去畸变 IP 所需的查找表
2. 黄金参考模型 (golden reference) — 与 Image_rect1.tif 对比验证

原理：
  AGDC 硬件对输出(矫正后)图像划分网格，每个网格点存储对应输入(畸变)图像中的坐标。
  硬件在处理时对网格点间做双线性插值，实现实时畸变矫正。

  本脚本生成 backward mapping：
  - 对每个输出网格点 (u_out, v_out)，计算其在输入图像中的对应坐标 (u_in, v_in)
  - 存储为定点数格式，供硬件直接使用
"""

import cv2
import numpy as np
import os
import json

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    """OpenCV imread with Unicode path support on Windows."""
    with open(path, 'rb') as f:
        data = f.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(arr, flags)

def imwrite_unicode(path, img):
    """OpenCV imwrite with Unicode path support on Windows."""
    ext = os.path.splitext(path)[1]
    _, buf = cv2.imencode(ext, img)
    with open(path, 'wb') as f:
        f.write(buf)

# ============================================================
# 0. 路径配置
# ============================================================
BASE = "d:/Clone/CameraCalibration/相机标定课程/第一章 标定基础知识 code & data/matlab_sample/calib_example"
IMG_IN = os.path.join(BASE, "Image1.tif")
IMG_RECT_REF = os.path.join(BASE, "Image_rect1.tif")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agdc_output")
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# 1. 标定参数 (来自 Calib_Results.m for Image #1)
# ============================================================
# --- 内参 ---
fc = np.array([657.446107869218281, 657.876660256090418])  # 焦距 [fx, fy]
cc = np.array([303.185319795283419, 242.708481163875661])  # 主点 [cx, cy]
alpha_c = 0.0  # 偏斜系数

# --- 畸变系数 [k1, k2, p1, p2, k3] ---
#   kc(1:2): 径向畸变 k1, k2
#   kc(3:4): 切向畸变 p1, p2
#   kc(5):   径向畸变 k3
kc = np.array([-0.255414841834118, 0.124449907410458, -0.000216975662453, 0.000074351611502, 0.0])

# --- 图像尺寸 ---
W, H = 640, 480

# --- Image #1 外参 (此处用于完整性，mesh表生成主要依赖内参) ---
omc_1 = np.array([1.654979, 1.651950, -0.6693785])  # 旋转向量 (Rodrigues)
Tc_1 = np.array([-177.8374, -83.98, 853.0169])      # 平移向量

# ============================================================
# 2. 构建相机矩阵与畸变系数（OpenCV 格式）
# ============================================================
camera_matrix = np.array([
    [fc[0], alpha_c * fc[0], cc[0]],
    [0,     fc[1],           cc[1]],
    [0,     0,               1    ]
], dtype=np.float64)

dist_coeffs = kc.astype(np.float64).reshape(1, 5)  # OpenCV 期望 (1, 5)

print("=" * 70)
print("相机标定参数")
print("=" * 70)
print(f"内参矩阵 K:\n{camera_matrix}")
print(f"畸变系数 [k1,k2,p1,p2,k3]: {dist_coeffs.flatten()}")
print(f"图像尺寸: {W} x {H}")

# ============================================================
# 3. 读取输入畸变图像
# ============================================================
img_distorted = imread_unicode(IMG_IN, cv2.IMREAD_GRAYSCALE)
if img_distorted is None:
    img_distorted = imread_unicode(IMG_IN, cv2.IMREAD_COLOR)
print(f"\n输入图像 (Image1.tif): shape={img_distorted.shape}, dtype={img_distorted.dtype}")

# ============================================================
# 4. 生成全分辨率 backward mapping (OpenCV)
# ============================================================
# initUndistortRectifyMap 生成的是从输出(矫正后)→输入(畸变)的映射
# map_x[u',v'] = u   map_y[u',v'] = v
print("\n生成全分辨率 backward mapping (OpenCV initUndistortRectifyMap)...")
map1, map2 = cv2.initUndistortRectifyMap(
    camera_matrix, dist_coeffs, None,  # 不旋转
    camera_matrix,  # newCameraMatrix: 相同内参，保持相同视角
    (W, H),
    cv2.CV_32FC1
)
# map1: shape (H, W), 值为对应输入图像的 x 坐标 (u)
# map2: shape (H, W), 值为对应输入图像的 y 坐标 (v)
print(f"map1 (x-mapping): shape={map1.shape}, dtype={map1.dtype}")
print(f"map2 (y-mapping): shape={map2.shape}, dtype={map2.dtype}")

# ============================================================
# 5. 生成黄金参考图像 (去畸变结果)
# ============================================================
print("\n生成黄金参考图像 (cv2.remap)...")
img_rectified = cv2.remap(img_distorted, map1, map2, cv2.INTER_LINEAR)
imwrite_unicode(os.path.join(OUT_DIR, "golden_ref_rectified.tif"), img_rectified)
print(f"黄金参考图像已保存: golden_ref_rectified.tif")

# 与 MATLAB 矫正结果对比
img_rect_matlab = imread_unicode(IMG_RECT_REF, cv2.IMREAD_GRAYSCALE)
if img_rect_matlab is None:
    img_rect_matlab = imread_unicode(IMG_RECT_REF, cv2.IMREAD_COLOR)

if img_rect_matlab is not None:
    print(f"\nMATLAB参考图像 (Image_rect1.tif): shape={img_rect_matlab.shape}")
    if img_rect_matlab.shape == img_rectified.shape:
        diff = img_rectified.astype(np.float32) - img_rect_matlab.astype(np.float32)
        mae = np.mean(np.abs(diff))
        max_err = np.max(np.abs(diff))
        print(f"与 MATLAB 结果对比: MAE={mae:.4f}, MaxError={max_err:.1f}")

        # 保存差异图
        diff_vis = np.clip(np.abs(diff) * 5, 0, 255).astype(np.uint8)
        imwrite_unicode(os.path.join(OUT_DIR, "diff_vs_matlab.png"), diff_vis)
        print("差异图已保存: diff_vs_matlab.png")
    else:
        print(f"尺寸不匹配: golden={img_rectified.shape}, matlab={img_rect_matlab.shape}")
else:
    print("警告: 无法读取 Image_rect1.tif")

# ============================================================
# 6. AGDC 网格映射表生成
# ============================================================
# AGDC 典型配置：
#   - 网格尺寸 (grid_cols x grid_rows)，常见 16x16, 32x24, 64x48 等
#   - 每个网格点存储 (x_in, y_in) 定点数坐标
#   - 格式：X 和 Y 分别存储，或多路交织
#   - 精度：典型 1/256 pixel (Q8.8) 或 1/16 pixel (Q12.4)

def generate_agdc_mesh(map_x, map_y, grid_cols, grid_rows, frac_bits=8):
    """
    从全分辨率 backward mapping 生成 AGDC 网格表

    参数:
        map_x, map_y: 全分辨率映射 (H, W)，存储每个输出像素对应的输入坐标
        grid_cols:    水平方向网格点数
        grid_rows:    垂直方向网格点数
        frac_bits:    定点数小数位宽

    返回:
        mesh_x: (grid_rows, grid_cols) — 各网格点的输入 x 坐标 (定点数)
        mesh_y: (grid_rows, grid_cols) — 各网格点的输入 y 坐标 (定点数)
        mesh_info: 网格表元信息
    """
    H, W = map_x.shape

    # 生成网格点在输出图像中的位置 (均匀采样)
    # col_pos: 输出图像中网格列的 x 坐标
    # row_pos: 输出图像中网格行的 y 坐标
    col_pos = np.linspace(0, W - 1, grid_cols).astype(np.int32)
    row_pos = np.linspace(0, H - 1, grid_rows).astype(np.int32)

    # 采样映射表
    mesh_x = map_x[row_pos[:, np.newaxis], col_pos[np.newaxis, :]]  # (grid_rows, grid_cols)
    mesh_y = map_y[row_pos[:, np.newaxis], col_pos[np.newaxis, :]]  # (grid_rows, grid_cols)

    # 转换为定点数
    scale = 2 ** frac_bits
    mesh_x_fixed = np.round(mesh_x * scale).astype(np.int32)
    mesh_y_fixed = np.round(mesh_y * scale).astype(np.int32)

    mesh_info = {
        "description": "AGDC Mesh Table for Image1.tif",
        "image_size": {"width": W, "height": H},
        "grid_size": {"cols": grid_cols, "rows": grid_rows},
        "fixed_point": {"frac_bits": frac_bits, "scale": scale},
        "camera_matrix": camera_matrix.tolist(),
        "dist_coeffs": dist_coeffs.flatten().tolist(),
        "mesh_col_positions": col_pos.tolist(),
        "mesh_row_positions": row_pos.tolist(),
    }

    return mesh_x, mesh_y, mesh_x_fixed, mesh_y_fixed, mesh_info


# 生成多组网格密度
print("\n" + "=" * 70)
print("AGDC 网格映射表生成")
print("=" * 70)

for grid_name, grid_cols, grid_rows in [
    ("16x12", 17, 13),   # 16x12 个 tile，17x13 个网格点
    ("32x24", 33, 25),   # 32x24 个 tile
    ("64x48", 65, 49),   # 64x48 个 tile
]:
    print(f"\n--- 网格 {grid_name} ({grid_cols}x{grid_rows} 网格点) ---")

    mesh_x, mesh_y, mesh_x_fixed, mesh_y_fixed, mesh_info = generate_agdc_mesh(
        map1, map2, grid_cols, grid_rows, frac_bits=8
    )

    print(f"  mesh_x 范围: [{mesh_x.min():.3f}, {mesh_x.max():.3f}]")
    print(f"  mesh_y 范围: [{mesh_y.min():.3f}, {mesh_y.max():.3f}]")
    print(f"  mesh_x_fixed (Q8.8) 范围: [{mesh_x_fixed.min()}, {mesh_x_fixed.max()}]")
    print(f"  mesh_y_fixed (Q8.8) 范围: [{mesh_y_fixed.min()}, {mesh_y_fixed.max()}]")

    # 最大值检查 (Q8.8 有符号可表示 ±32768，即 ±128.0 pixel)
    # 对于 640x480 图像，需要 Q11.4 或更大范围
    # 实际硬件通常用 Q16.16 或自定义位宽
    max_val = max(abs(mesh_x_fixed).max(), abs(mesh_y_fixed).max())
    bits_needed = int(np.ceil(np.log2(max_val + 1))) + 1  # +1 for sign
    print(f"  定点数有效位宽需求: {bits_needed} bits (含符号位)")

    # 保存网格表
    prefix = f"agdc_mesh_{grid_name.replace('x', 'x')}"
    grid_dir = os.path.join(OUT_DIR, prefix)
    os.makedirs(grid_dir, exist_ok=True)

    # ---- 格式 A: 纯文本 C header (float) ----
    with open(os.path.join(grid_dir, f"{prefix}_float.h"), "w") as f:
        f.write(f"// AGDC Mesh Table - {grid_name} tiles\n")
        f.write(f"// Image: Image1.tif ({W}x{H})\n")
        f.write(f"// Grid: {grid_cols}x{grid_rows} points\n")
        f.write(f"// Format: float\n\n")
        f.write(f"#define AGDC_MESH_COLS {grid_cols}\n")
        f.write(f"#define AGDC_MESH_ROWS {grid_rows}\n")
        f.write(f"#define AGDC_IMAGE_WIDTH {W}\n")
        f.write(f"#define AGDC_IMAGE_HEIGHT {H}\n\n")

        # X 表
        f.write(f"// Mesh X (input x-coordinate for each output grid point)\n")
        f.write(f"static const float agdc_mesh_x[{grid_rows}][{grid_cols}] = {{\n")
        for i in range(grid_rows):
            f.write("    {" + ", ".join(f"{v:10.4f}f" for v in mesh_x[i]) + "}")
            f.write(",\n" if i < grid_rows - 1 else "\n")
        f.write("};\n\n")

        # Y 表
        f.write(f"// Mesh Y (input y-coordinate for each output grid point)\n")
        f.write(f"static const float agdc_mesh_y[{grid_rows}][{grid_cols}] = {{\n")
        for i in range(grid_rows):
            f.write("    {" + ", ".join(f"{v:10.4f}f" for v in mesh_y[i]) + "}")
            f.write(",\n" if i < grid_rows - 1 else "\n")
        f.write("};\n")

    print(f"  已保存: {prefix}_float.h")

    # ---- 格式 B: C header (Q8.8 定点数) ----
    with open(os.path.join(grid_dir, f"{prefix}_fixed.h"), "w") as f:
        f.write(f"// AGDC Mesh Table - {grid_name} tiles\n")
        f.write(f"// Image: Image1.tif ({W}x{H})\n")
        f.write(f"// Grid: {grid_cols}x{grid_rows} points\n")
        f.write(f"// Format: Q8.8 fixed-point (int16_t)\n\n")
        f.write(f"#include <stdint.h>\n\n")
        f.write(f"#define AGDC_MESH_COLS {grid_cols}\n")
        f.write(f"#define AGDC_MESH_ROWS {grid_rows}\n")
        f.write(f"#define AGDC_IMAGE_WIDTH {W}\n")
        f.write(f"#define AGDC_IMAGE_HEIGHT {H}\n")
        f.write(f"#define AGDC_FRAC_BITS 8\n")
        f.write(f"#define AGDC_FIXED_SCALE 256\n\n")

        # X 表
        f.write(f"// Mesh X (input x-coordinate in Q8.8)\n")
        f.write(f"static const int16_t agdc_mesh_x[{grid_rows}][{grid_cols}] = {{\n")
        for i in range(grid_rows):
            f.write("    {" + ", ".join(f"{v:6d}" for v in mesh_x_fixed[i]) + "}")
            f.write(",\n" if i < grid_rows - 1 else "\n")
        f.write("};\n\n")

        # Y 表
        f.write(f"// Mesh Y (input y-coordinate in Q8.8)\n")
        f.write(f"static const int16_t agdc_mesh_y[{grid_rows}][{grid_cols}] = {{\n")
        for i in range(grid_rows):
            f.write("    {" + ", ".join(f"{v:6d}" for v in mesh_y_fixed[i]) + "}")
            f.write(",\n" if i < grid_rows - 1 else "\n")
        f.write("};\n")

    print(f"  已保存: {prefix}_fixed.h")

    # ---- 格式 C: 纯二进制文件 (供硬件/仿真直接读取) ----
    # 交织格式: [x00, y00, x01, y01, ...] 逐行
    interleaved = np.zeros((grid_rows, grid_cols, 2), dtype=np.int16)
    interleaved[:, :, 0] = mesh_x_fixed.astype(np.int16)
    interleaved[:, :, 1] = mesh_y_fixed.astype(np.int16)
    interleaved.tofile(os.path.join(grid_dir, f"{prefix}_interleaved_i16.bin"))
    print(f"  已保存: {prefix}_interleaved_i16.bin (interleaved XY, int16)")

    # 分离格式: X 表 + Y 表
    mesh_x_fixed.astype(np.int16).tofile(os.path.join(grid_dir, f"{prefix}_x_i16.bin"))
    mesh_y_fixed.astype(np.int16).tofile(os.path.join(grid_dir, f"{prefix}_y_i16.bin"))
    print(f"  已保存: {prefix}_x_i16.bin, {prefix}_y_i16.bin (separate X/Y, int16)")

    # ---- 格式 D: JSON (可读, 用于仿真验证) ----
    mesh_json = {
        "mesh_info": mesh_info,
        "mesh_x_float": mesh_x.tolist(),
        "mesh_y_float": mesh_y.tolist(),
        "mesh_x_fixed_q8_8": mesh_x_fixed.tolist(),
        "mesh_y_fixed_q8_8": mesh_y_fixed.tolist(),
    }
    with open(os.path.join(grid_dir, f"{prefix}.json"), "w") as f:
        json.dump(mesh_json, f, indent=2)
    print(f"  已保存: {prefix}.json")

# ============================================================
# 7. 黄金参考模型 — 仿真验证
# ============================================================
print("\n" + "=" * 70)
print("黄金参考模型 — 使用网格表+双线性插值重建矫正图像")
print("=" * 70)

def agdc_remap_bilinear(img, mesh_x, mesh_y, grid_cols, grid_rows):
    """
    使用 AGDC 网格表 + 双线性插值重建矫正图像 (模拟硬件行为)
    与 cv2.remap 全分辨率映射对比以验证网格表精度
    """
    H, W = img.shape[:2]
    out = np.zeros_like(img, dtype=np.float32)

    # 网格点在输出图像中的位置
    col_pos = np.linspace(0, W - 1, grid_cols)
    row_pos = np.linspace(0, H - 1, grid_rows)

    for y_out in range(H):
        # 找到当前行在网格中的位置
        ry = np.searchsorted(row_pos, y_out)
        if ry == 0:
            ry = 1
        elif ry >= grid_rows:
            ry = grid_rows - 1

        y0 = int(row_pos[ry - 1])
        y1 = int(row_pos[ry])
        wy = (y_out - y0) / max(y1 - y0, 1)

        for x_out in range(W):
            rx = np.searchsorted(col_pos, x_out)
            if rx == 0:
                rx = 1
            elif rx >= grid_cols:
                rx = grid_cols - 1

            x0 = int(col_pos[rx - 1])
            x1 = int(col_pos[rx])
            wx = (x_out - x0) / max(x1 - x0, 1)

            # 四个角点在输入图像中的坐标
            x00 = mesh_x[ry - 1, rx - 1]
            y00 = mesh_y[ry - 1, rx - 1]
            x01 = mesh_x[ry - 1, rx]
            y01 = mesh_y[ry - 1, rx]
            x10 = mesh_x[ry, rx - 1]
            y10 = mesh_y[ry, rx - 1]
            x11 = mesh_x[ry, rx]
            y11 = mesh_y[ry, rx]

            # 双线性插值
            x_in = (1 - wy) * ((1 - wx) * x00 + wx * x01) + wy * ((1 - wx) * x10 + wx * x11)
            y_in = (1 - wy) * ((1 - wx) * y00 + wx * y01) + wy * ((1 - wx) * y10 + wx * y11)

            # 最近邻采样 (为简化，实际硬件可能用双线性读取)
            xi = int(np.clip(np.round(x_in), 0, W - 1))
            yi = int(np.clip(np.round(y_in), 0, H - 1))
            out[y_out, x_out] = img[yi, xi]

    return out.astype(img.dtype)


# 对每种网格密度验证
for grid_name, grid_cols, grid_rows in [
    ("16x12", 17, 13),
    ("32x24", 33, 25),
    ("64x48", 65, 49),
]:
    print(f"\n--- 验证网格 {grid_name} ---")
    mesh_x, mesh_y, _, _, _ = generate_agdc_mesh(map1, map2, grid_cols, grid_rows)

    # 使用网格表重建矫正图像
    reconstructed = agdc_remap_bilinear(img_distorted, mesh_x, mesh_y, grid_cols, grid_rows)

    # 与黄金参考对比
    diff = img_rectified.astype(np.float32) - reconstructed.astype(np.float32)
    mae = np.mean(np.abs(diff))
    max_err = np.max(np.abs(diff))
    rmse = np.sqrt(np.mean(diff ** 2))
    print(f"  MAE={mae:.4f}, MaxError={max_err:.1f}, RMSE={rmse:.4f}")

    # 保存重建结果
    imwrite_unicode(os.path.join(OUT_DIR, f"reconstructed_{grid_name.replace('x', 'x')}.tif"), reconstructed)

# ============================================================
# 8. 汇总报告
# ============================================================
print("\n" + "=" * 70)
print("生成完毕！输出目录:", OUT_DIR)
print("=" * 70)
print("""
文件清单:
  golden_ref_rectified.tif          — 黄金参考矫正图像 (全精度)
  diff_vs_matlab.png                — 与 MATLAB 矫正结果差异图

  agdc_mesh_16x12/
    ├── agdc_mesh_16x12_float.h     — C header (浮点)
    ├── agdc_mesh_16x12_fixed.h     — C header (Q8.8定点)
    ├── agdc_mesh_16x12_interleaved_i16.bin — 交织二进制
    ├── agdc_mesh_16x12_x_i16.bin   — X表二进制
    ├── agdc_mesh_16x12_y_i16.bin   — Y表二进制
    └── agdc_mesh_16x12.json        — JSON 格式

  agdc_mesh_32x24/                  — 同上, 32x24 网格
  agdc_mesh_64x48/                  — 同上, 64x48 网格

  reconstructed_16x12.tif           — 16x12 网格重建结果
  reconstructed_32x24.tif           — 32x24 网格重建结果
  reconstructed_64x48.tif           — 64x48 网格重建结果
""")
