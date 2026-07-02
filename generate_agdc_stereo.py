"""
AGDC Stereo Mesh Table Generator — Online Mode (Side-by-Side)
================================================================
模拟 AGDC 在线模式的双目图像输入：
  1. 将 left01.jpg + right01.jpg 横向拼接为一张 1280×480 图像
  2. 使用双目标定参数 (intrinsics.yml + extrinsics.yml) 计算立体矫正映射
  3. 生成合并图像的 AGDC Mesh Table (36-bit 格式)

在线模式数据流:
  合并输入 (1280×480, 左|右) ──AGDC──→ 合并矫正输出 (1280×480)
  Mesh Table: backward mapping, 输出坐标 → 输入坐标

输出目录: agdc_test_stereo/
"""

import numpy as np
import os
import json
from pathlib import Path

# ============================================================
# 0. 路径配置
# ============================================================
BASE_DIR = Path(r"d:\Clone\CameraCalibration")
STEREO_DIR = Path(r"d:\Clone\CameraCalibration\相机标定课程\第一章 标定基础知识 code & data\matlab_sample\stereo_example")
OUT_DIR = BASE_DIR / "agdc_test_stereo"
for d in ["source", "mesh/16x12", "mesh/32x24", "mesh/64x48",
          "input/nv12", "input/nv16", "input/yuyv",
          "golden/nv12", "golden/nv16", "golden/yuyv",
          "verify"]:
    (OUT_DIR / d).mkdir(parents=True, exist_ok=True)

LEFT_IMG  = STEREO_DIR / "left01.jpg"
RIGHT_IMG = STEREO_DIR / "right01.jpg"

print("=" * 72)
print("AGDC Stereo Mesh Table Generator — Online Mode")
print("=" * 72)
print(f"左图: {LEFT_IMG}")
print(f"右图: {RIGHT_IMG}")
print(f"输出: {OUT_DIR}")

# ============================================================
# 1. 读取图像 (OpenCV Unicode workaround)
# ============================================================
import cv2

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    with open(str(path), 'rb') as f:
        data = f.read()
    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), flags)

def imwrite_unicode(path, img):
    ext = os.path.splitext(str(path))[1]
    _, buf = cv2.imencode(ext, img)
    with open(str(path), 'wb') as f:
        f.write(buf)

img_left  = imread_unicode(LEFT_IMG, cv2.IMREAD_COLOR)
img_right = imread_unicode(RIGHT_IMG, cv2.IMREAD_COLOR)

if img_left is None:
    raise FileNotFoundError(f"无法读取: {LEFT_IMG}")
if img_right is None:
    raise FileNotFoundError(f"无法读取: {RIGHT_IMG}")

H, W = img_left.shape[:2]
print(f"\n单幅图像: {W}×{H}")
print(f"合并图像: {W*2}×{H}")

# 横向拼接 → 模拟在线模式输入
img_combined = np.hstack([img_left, img_right])  # BGR, 1280×480
imwrite_unicode(OUT_DIR / "source/combined_input.jpg", img_combined)
print(f"合并输入已保存: {OUT_DIR / 'source/combined_input.jpg'}")

# ============================================================
# 2. 双目标定参数 (来自 intrinsics.yml / extrinsics.yml)
# ============================================================
# --- 左相机内参 ---
M1 = np.array([[533.98795247911039, 0.0,               328.38647452766730],
               [0.0,               528.71082096447628, 236.84272829022564],
               [0.0,               0.0,                1.0]], dtype=np.float64)

D1 = np.array([-0.25896599040441870, -0.12618381509733806, 0.0, 0.0, 0.0,
                0.0, 0.0, -0.39963323194512251, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
              dtype=np.float64)

# --- 右相机内参 ---
M2 = np.array([[533.98795247911039, 0.0,               313.77033179722014],
               [0.0,               528.71082096447628, 241.87045532011228],
               [0.0,               0.0,                1.0]], dtype=np.float64)

D2 = np.array([-0.26296221163690792, -0.012154510248729584, 0.0, 0.0, 0.0,
                0.0, 0.0, -0.19510571749433719, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
              dtype=np.float64)

# --- 立体矫正矩阵 ---
R1 = np.array([[ 0.99994753473813536, -0.0091729741846967878, 0.0045589818745291610],
               [ 0.0091468618061928252, 0.99994183001783732,  0.0057158988511711107],
               [-0.0046111484712389452, -0.0056738985878578511, 0.99997327173509543]],
             dtype=np.float64)

R2 = np.array([[ 0.99990130039166936, -0.014006993695407550, -0.0010925212425222470],
               [ 0.014000544506924695,  0.99988572509863427, -0.0057027622682348338],
               [ 0.0011722749499026163, 0.0056869035155518496, 0.99998314230783247]],
             dtype=np.float64)

# 矫正后投影矩阵 (新内参)
P1 = np.array([[439.64859374715638, 0.0,               319.32437133789062, 0.0],
               [0.0,               439.64859374715638, 239.45363616943359, 0.0],
               [0.0,               0.0,                1.0,                0.0]], dtype=np.float64)

P2 = np.array([[439.64859374715638, 0.0,               319.32437133789062, -1469.7622415046644],
               [0.0,               439.64859374715638, 239.45363616943359, 0.0],
               [0.0,               0.0,                1.0,                0.0]], dtype=np.float64)

# --- 外参 ---
R_stereo = np.array([[ 0.99997149582007883,  0.0048210099105817578, 0.0058108012180958738],
                     [-0.0048866654218067693, 0.99992378064158749,  0.011338139551511776],
                     [-0.0057556970394097434, -0.011366211808527505, 0.99991883729666486]],
                   dtype=np.float64)

T_stereo = np.array([-3.3427086938262143, 0.046825921300101291, 0.0036523407401693221],
                    dtype=np.float64)

Q = np.array([[1.0, 0.0, 0.0, -319.32437133789062],
              [0.0, 1.0, 0.0, -239.45363616943359],
              [0.0, 0.0, 0.0,  439.64859374715638],
              [0.0, 0.0, 0.29912905729369360, 0.0]], dtype=np.float64)

print(f"\n左相机内参 M1:\n{M1}")
print(f"左相机畸变 D1 (前5个): {D1[:5]}")
print(f"右相机内参 M2:\n{M2}")
print(f"右相机畸变 D2 (前5个): {D2[:5]}")
print(f"基线长度: |T| = {np.linalg.norm(T_stereo):.4f} 单位")
print(f"矫正焦距: fx={P1[0,0]:.2f}, fy={P1[1,1]:.2f}")
print(f"矫正主点: cx={P1[0,2]:.2f}, cy={P1[1,2]:.2f}")

# ============================================================
# 3. 计算立体矫正映射 (Backward: 矫正输出 → 畸变输入)
# ============================================================
print("\n" + "=" * 72)
print("计算立体矫正 Backward Mapping")
print("=" * 72)

# 对每路相机独立计算 initUndistortRectifyMap
# 左眼: 矫正图坐标 → 左畸变图坐标
map_L_x, map_L_y = cv2.initUndistortRectifyMap(
    M1, D1, R1, P1[:, :3], (W, H), cv2.CV_32FC1)

# 右眼: 矫正图坐标 → 右畸变图坐标
map_R_x, map_R_y = cv2.initUndistortRectifyMap(
    M2, D2, R2, P2[:, :3], (W, H), cv2.CV_32FC1)

print(f"左路 map_x 范围: [{map_L_x.min():.2f}, {map_L_x.max():.2f}]")
print(f"左路 map_y 范围: [{map_L_y.min():.2f}, {map_L_y.max():.2f}]")
print(f"右路 map_x 范围: [{map_R_x.min():.2f}, {map_R_x.max():.2f}]")
print(f"右路 map_y 范围: [{map_R_y.min():.2f}, {map_R_y.max():.2f}]")

# ============================================================
# 4. 构建合并图像的 Backward Mapping
# ============================================================
# 合并输出图像 (1280×480):
#   左半 [0..639]   → 来源于左路矫正映射
#   右半 [640..1279] → 来源于右路矫正映射, x偏移 +W
print("\n构建合并图像 backward mapping (1280×480)...")

W_combined = W * 2  # 1280

# 合并映射: 输出坐标 → 合并输入图像中的坐标
# 右路需要加上左图像的宽度偏移
map_combined_x = np.zeros((H, W_combined), dtype=np.float32)
map_combined_y = np.zeros((H, W_combined), dtype=np.float32)

# 左半
map_combined_x[:, :W] = map_L_x
map_combined_y[:, :W] = map_L_y

# 右半 (偏移到合并图像的右半部分)
map_combined_x[:, W:] = map_R_x + W  # 右图在合并图像中的起始位置
map_combined_y[:, W:] = map_R_y

print(f"合并 map_x 范围: [{map_combined_x.min():.2f}, {map_combined_x.max():.2f}]")
print(f"合并 map_y 范围: [{map_combined_y.min():.2f}, {map_combined_y.max():.2f}]")

# ============================================================
# 5. 生成矫正黄金参考 (Bilinear interpolation)
# ============================================================
print("\n" + "=" * 72)
print("生成立体矫正黄金参考图像")
print("=" * 72)

map_x_clip = np.clip(map_combined_x, 0, W_combined - 1)
map_y_clip = np.clip(map_combined_y, 0, H - 1)

# 双线性插值
u0 = np.floor(map_x_clip).astype(np.int32)
v0 = np.floor(map_y_clip).astype(np.int32)
u1 = np.minimum(u0 + 1, W_combined - 1)
v1 = np.minimum(v0 + 1, H - 1)
wu = (map_x_clip - u0.astype(np.float32)).reshape(H, W_combined, 1)
wv = (map_y_clip - v0.astype(np.float32)).reshape(H, W_combined, 1)

img_rect_combined = ((1 - wv) * (1 - wu) * img_combined[v0, u0].astype(np.float32) +
                      (1 - wv) * wu       * img_combined[v0, u1].astype(np.float32) +
                      wv       * (1 - wu) * img_combined[v1, u0].astype(np.float32) +
                      wv       * wu       * img_combined[v1, u1].astype(np.float32))
img_rect_combined = np.clip(np.round(img_rect_combined), 0, 255).astype(np.uint8)

imwrite_unicode(OUT_DIR / "verify/golden_rectified_stereo.tif", img_rect_combined)
print(f"黄金参考: {OUT_DIR / 'verify/golden_rectified_stereo.tif'}")

# 同时保存左右分离的矫正图
img_rect_L = img_rect_combined[:, :W]
img_rect_R = img_rect_combined[:, W:]
imwrite_unicode(OUT_DIR / "verify/left_rectified.tif", img_rect_L)
imwrite_unicode(OUT_DIR / "verify/right_rectified.tif", img_rect_R)
print(f"左路矫正: {OUT_DIR / 'verify/left_rectified.tif'}")
print(f"右路矫正: {OUT_DIR / 'verify/right_rectified.tif'}")

# 绘制水平参考线验证极线对齐
check_img = img_rect_combined.copy()
for y in range(0, H, 48):
    cv2.line(check_img, (0, y), (W_combined - 1, y), (0, 255, 0), 1)
imwrite_unicode(OUT_DIR / "verify/epipolar_check.tif", check_img)
print(f"极线检查: {OUT_DIR / 'verify/epipolar_check.tif'}")

# ============================================================
# 6. RGB → YUV 转换
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

# --- 合并输入 (畸变) → YUV ---
Y_in, U_in, V_in = rgb_to_yuv_bt601(img_combined)

for fmt_name, pack_fn, ydir, uvdir in [
    ("nv12", pack_nv12, "input/nv12", "input/nv12"),
    ("nv16", pack_nv16, "input/nv16", "input/nv16"),
    ("yuyv", None,      "input/yuyv", "input/yuyv"),
]:
    if fmt_name == "yuyv":
        data = pack_yuyv(Y_in, U_in, V_in)
        data.tofile(str(OUT_DIR / uvdir / "distorted_yuyv.bin"))
        print(f"  {fmt_name}: {OUT_DIR / uvdir / 'distorted_yuyv.bin'} ({data.size} bytes)")
    else:
        Yp, UVp = pack_fn(Y_in, U_in, V_in)
        Yp.tofile(str(OUT_DIR / ydir / f"distorted_{fmt_name}_y.bin"))
        UVp.tofile(str(OUT_DIR / uvdir / f"distorted_{fmt_name}_uv.bin"))
        print(f"  {fmt_name}: Y={OUT_DIR / ydir / f'distorted_{fmt_name}_y.bin'} ({Yp.size}B)")
        print(f"           UV={OUT_DIR / uvdir / f'distorted_{fmt_name}_uv.bin'} ({UVp.size}B)")

# --- 矫正输出 (黄金参考) → YUV ---
Y_out, U_out, V_out = rgb_to_yuv_bt601(img_rect_combined)

for fmt_name, pack_fn, ydir, uvdir in [
    ("nv12", pack_nv12, "golden/nv12", "golden/nv12"),
    ("nv16", pack_nv16, "golden/nv16", "golden/nv16"),
    ("yuyv", None,      "golden/yuyv", "golden/yuyv"),
]:
    if fmt_name == "yuyv":
        data = pack_yuyv(Y_out, U_out, V_out)
        data.tofile(str(OUT_DIR / uvdir / "golden_yuyv.bin"))
    else:
        Yp, UVp = pack_fn(Y_out, U_out, V_out)
        Yp.tofile(str(OUT_DIR / ydir / f"golden_{fmt_name}_y.bin"))
        UVp.tofile(str(OUT_DIR / uvdir / f"golden_{fmt_name}_uv.bin"))

# 独立平面
Y_out.tofile(str(OUT_DIR / "golden/golden_y_plane.bin"))
U_out.tofile(str(OUT_DIR / "golden/golden_u_plane.bin"))
V_out.tofile(str(OUT_DIR / "golden/golden_v_plane.bin"))
print("  独立 Y/U/V 平面已保存")

# ============================================================
# 7. 生成 AGDC Mesh Table (36-bit 格式)
# ============================================================
print("\n" + "=" * 72)
print("AGDC Stereo Mesh Table 生成")
print("=" * 72)

FRAC_BITS = 5
FRAC_SCALE = 1 << FRAC_BITS  # 32
U12_5_MAX  = (1 << 17) - 1   # 131071
U12_5_MIN  = -(1 << 17)      # -131072

def float_to_u12_5(val):
    fixed = np.round(val * FRAC_SCALE).astype(np.int64)
    return np.clip(fixed, U12_5_MIN, U12_5_MAX).astype(np.int32)

def u12_5_to_float(fixed):
    return fixed.astype(np.float64) / FRAC_SCALE

def pack_mesh_entry(u_fixed, v_fixed):
    u18 = np.uint64(u_fixed) & np.uint64(0x3FFFF)
    v18 = np.uint64(v_fixed) & np.uint64(0x3FFFF)
    return (v18 << 18) | u18

# 网格配置: 16x12, 32x24, 64x48
MESH_CONFIGS = [
    ("16x12", 16, 12),
    ("32x24", 32, 24),
    ("64x48", 64, 48),
]

all_mesh_info = {}

for mesh_name, mesh_cols, mesh_rows in MESH_CONFIGS:
    grid_cols = mesh_cols + 1  # x方向节点数 (覆盖 1280 宽)
    grid_rows = mesh_rows + 1  # y方向节点数 (覆盖 480 高)
    num_nodes = grid_cols * grid_rows

    print(f"\n--- 网格 {mesh_name}: {grid_cols}×{grid_rows} = {num_nodes} 节点 ---")

    # 输出网格点在矫正图中的均匀位置 (1280×480 合并输出)
    col_pos = np.linspace(0, W_combined - 1, grid_cols)
    row_pos = np.linspace(0, H - 1, grid_rows)

    col_idx = np.round(col_pos).astype(np.int32)
    row_idx = np.round(row_pos).astype(np.int32)

    # 从合并 backward map 中采样
    mesh_u_float = map_combined_x[row_idx[:, np.newaxis], col_idx[np.newaxis, :]].astype(np.float64)
    mesh_v_float = map_combined_y[row_idx[:, np.newaxis], col_idx[np.newaxis, :]].astype(np.float64)

    print(f"  mesh_u 范围: [{mesh_u_float.min():.4f}, {mesh_u_float.max():.4f}]")
    print(f"  mesh_v 范围: [{mesh_v_float.min():.4f}, {mesh_v_float.max():.4f}]")

    # 验证节点归属
    left_mask = col_pos < W
    right_mask = col_pos >= W
    print(f"  左路节点: {left_mask.sum()} (u范围 [{mesh_u_float[:, left_mask].min():.2f}, {mesh_u_float[:, left_mask].max():.2f}])")
    print(f"  右路节点: {right_mask.sum()} (u范围 [{mesh_u_float[:, right_mask].min():.2f}, {mesh_u_float[:, right_mask].max():.2f}])")

    # 转 u12.5 定点
    mesh_u_fixed = float_to_u12_5(mesh_u_float)
    mesh_v_fixed = float_to_u12_5(mesh_v_float)

    # 量化误差验证
    u_recon = u12_5_to_float(mesh_u_fixed)
    v_recon = u12_5_to_float(mesh_v_fixed)
    u_err = np.abs(mesh_u_float - u_recon).max()
    v_err = np.abs(mesh_v_float - v_recon).max()
    print(f"  u12.5 量化误差: u_max={u_err:.6f}, v_max={v_err:.6f} (1 LSB={1.0/FRAC_SCALE:.6f})")

    # 封装 36-bit
    mesh_entries = np.zeros(num_nodes, dtype=np.uint64)
    for iy in range(grid_rows):
        for ix in range(grid_cols):
            addr = iy * grid_cols + ix
            mesh_entries[addr] = pack_mesh_entry(mesh_u_fixed[iy, ix],
                                                  mesh_v_fixed[iy, ix])

    mesh_dir = OUT_DIR / "mesh" / mesh_name

    # ---- SRAM hex 文件 ----
    hex_path = mesh_dir / f"agdc_mesh_{mesh_name}_36bit.hex"
    with open(str(hex_path), 'w') as f:
        f.write(f"// AGDC Stereo Mesh Table: {mesh_name} tiles (Online Mode)\n")
        f.write(f"// Combined image: {W_combined}x{H} (Left|Right stereo pair)\n")
        f.write(f"// Nodes: {grid_cols}x{grid_rows} = {num_nodes}\n")
        f.write(f"// Format: 36-bit = {{v[17:0], u[17:0]}}, u12.5 signed\n")
        f.write(f"// SRAM addr = iy * {grid_cols} + ix\n")
        f.write(f"// Columns 0..{grid_cols//2-1}/{grid_cols//2}..{grid_cols-1}: Left/Right camera\n")
        f.write(f"// Baseline: {np.linalg.norm(T_stereo):.4f} units\n\n")
        for addr in range(num_nodes):
            iy = addr // grid_cols
            ix = addr % grid_cols
            entry = mesh_entries[addr]
            cam = "L" if ix < grid_cols // 2 else "R"
            f.write(f"@{addr:04X}  // node({ix:02d},{iy:02d})[{cam}]  "
                    f"u=0x{int(mesh_u_fixed[iy,ix]) & 0x3FFFF:05X}({mesh_u_float[iy,ix]:10.2f})  "
                    f"v=0x{int(mesh_v_fixed[iy,ix]) & 0x3FFFF:05X}({mesh_v_float[iy,ix]:10.2f})  "
                    f"packed=0x{entry:09X}\n")
    print(f"  hex:     {hex_path}")

    # ---- bin64 二进制 ----
    bin64_path = mesh_dir / f"agdc_mesh_{mesh_name}_36bit_in_u64.bin"
    mesh_entries.tofile(str(bin64_path))
    print(f"  bin64:   {bin64_path} ({mesh_entries.nbytes} bytes)")

    # ---- uv_fixed 交织 ----
    uv_path = mesh_dir / f"agdc_mesh_{mesh_name}_uv_fixed.bin"
    uv_flat = np.empty(num_nodes * 2, dtype=np.int32)
    for iy in range(grid_rows):
        for ix in range(grid_cols):
            addr = iy * grid_cols + ix
            uv_flat[addr * 2]     = mesh_u_fixed[iy, ix]
            uv_flat[addr * 2 + 1] = mesh_v_fixed[iy, ix]
    uv_flat.tofile(str(uv_path))
    print(f"  uv交织:  {uv_path} ({uv_flat.nbytes} bytes)")

    # ---- C header ----
    h_path = mesh_dir / f"agdc_mesh_{mesh_name}.h"
    with open(str(h_path), 'w') as f:
        f.write(f"// AGDC Stereo Mesh Table (Online Mode) — {mesh_name} tiles\n")
        f.write(f"// Combined input: {W_combined}x{H}, Left|Right stereo pair\n")
        f.write(f"// DO NOT EDIT — generated by generate_agdc_stereo.py\n\n")
        f.write(f"#pragma once\n")
        f.write(f"#include <stdint.h>\n\n")
        f.write(f"#define AGDC_MESH_COLS   {grid_cols}\n")
        f.write(f"#define AGDC_MESH_ROWS   {grid_rows}\n")
        f.write(f"#define AGDC_MESH_NODES  {num_nodes}\n")
        f.write(f"#define AGDC_IMG_WIDTH   {W_combined}\n")
        f.write(f"#define AGDC_IMG_HEIGHT  {H}\n")
        f.write(f"#define AGDC_FRAC_BITS   {FRAC_BITS}\n")
        f.write(f"#define AGDC_LEFT_W      {W}\n")
        f.write(f"#define AGDC_STEREO_BL   {np.linalg.norm(T_stereo):.6f}f\n\n")
        f.write(f"// SRAM table: v[17:0] @ bits[35:18], u[17:0] @ bits[17:0]\n")
        f.write(f"static const uint64_t agdc_mesh[{num_nodes}] = {{\n")
        for iy in range(grid_rows):
            vals = ", ".join(f"0x{mesh_entries[iy*grid_cols + ix]:09X}ULL" for ix in range(grid_cols))
            f.write(f"    {vals},\n")
        f.write(f"}};\n\n")
        f.write(f"// Float debug reference\n")
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
    print(f"  header:  {h_path}")

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
# 8. 网格表精度验证
# ============================================================
print(f"\n{'='*72}")
print("AGDC 网格表精度验证 (网格表双线性 vs 全精度矫正)")
print(f"{'='*72}")

for mesh_name, mesh_cols, mesh_rows in MESH_CONFIGS:
    grid_cols = mesh_cols + 1
    grid_rows = mesh_rows + 1

    col_pos = np.linspace(0, W_combined - 1, grid_cols)
    row_pos = np.linspace(0, H - 1, grid_rows)
    c_idx = np.round(col_pos).astype(np.int32)
    r_idx = np.round(row_pos).astype(np.int32)
    mu = map_combined_x[r_idx[:, None], c_idx[None, :]]
    mv = map_combined_y[r_idx[:, None], c_idx[None, :]]

    out = img_combined.astype(np.float64).copy()
    for iy in range(H):
        ry = max(1, min(np.searchsorted(row_pos, iy), grid_rows - 1))
        y0, y1 = int(row_pos[ry - 1]), int(row_pos[ry])
        wy = (iy - y0) / max(y1 - y0, 1e-6)
        for ix in range(W_combined):
            rx = max(1, min(np.searchsorted(col_pos, ix), grid_cols - 1))
            x0, x1 = int(col_pos[rx - 1]), int(col_pos[rx])
            wx = (ix - x0) / max(x1 - x0, 1e-6)

            u00, v00 = mu[ry - 1, rx - 1], mv[ry - 1, rx - 1]
            u01, v01 = mu[ry - 1, rx],     mv[ry - 1, rx]
            u10, v10 = mu[ry, rx - 1],     mv[ry, rx - 1]
            u11, v11 = mu[ry, rx],         mv[ry, rx]

            x_in = (1 - wy) * ((1 - wx) * u00 + wx * u01) + wy * ((1 - wx) * u10 + wx * u11)
            y_in = (1 - wy) * ((1 - wx) * v00 + wx * v01) + wy * ((1 - wx) * v10 + wx * v11)

            xi = int(np.clip(np.round(x_in), 0, W_combined - 1))
            yi = int(np.clip(np.round(y_in), 0, H - 1))
            out[iy, ix, :] = img_combined[yi, xi, :]

    out = out.astype(np.uint8)
    diff = out.astype(np.float32) - img_rect_combined.astype(np.float32)
    mae = np.abs(diff).mean()
    maxe = np.abs(diff).max()

    print(f"  {mesh_name}: MAE={mae:.4f}, MaxError={maxe:.0f}")
    imwrite_unicode(OUT_DIR / "verify" / f"reconstructed_mesh_{mesh_name}.tif", out)

# ============================================================
# 9. 畸变分析
# ============================================================
print(f"\n{'='*72}")
print("畸变特征分析")
print(f"{'='*72}")

# 分析左路和右路各自的畸变幅度
# 左路: backward map 相对于恒等映射的偏移
disp_L_x = map_L_x - np.tile(np.arange(W, dtype=np.float32), (H, 1))
disp_L_y = map_L_y - np.tile(np.arange(H, dtype=np.float32).reshape(H, 1), (1, W))
disp_R_x = map_R_x - np.tile(np.arange(W, dtype=np.float32), (H, 1))
disp_R_y = map_R_y - np.tile(np.arange(H, dtype=np.float32).reshape(H, 1), (1, W))

print(f"左路畸变位移 (矫正→畸变):")
print(f"  Δx: min={disp_L_x.min():.2f}, max={disp_L_x.max():.2f} px")
print(f"  Δy: min={disp_L_y.min():.2f}, max={disp_L_y.max():.2f} px")
print(f"  最大位移幅度: {np.sqrt(disp_L_x**2 + disp_L_y**2).max():.2f} px")

print(f"右路畸变位移 (矫正→畸变):")
print(f"  Δx: min={disp_R_x.min():.2f}, max={disp_R_x.max():.2f} px")
print(f"  Δy: min={disp_R_y.min():.2f}, max={disp_R_y.max():.2f} px")
print(f"  最大位移幅度: {np.sqrt(disp_R_x**2 + disp_R_y**2).max():.2f} px")

# 极线对齐误差 (左右矫正图中对应点的 y 偏差应接近 0)
# 在左右图同行的随机位置采样
y_diff_LR = np.abs(disp_L_y - disp_R_y)
print(f"\n极线对齐误差 (左右 y 偏差):")
print(f"  均值: {y_diff_LR.mean():.4f} px")
print(f"  最大: {y_diff_LR.max():.4f} px")

# ============================================================
# 10. 汇总 manifest.json
# ============================================================
print(f"\n{'='*72}")
print("生成汇总 manifest.json")
print(f"{'='*72}")

manifest = {
    "description": "AGDC Stereo Mesh Table & Golden Reference — Online Mode (Side-by-Side)",
    "mode": "stereo_online",
    "input": {
        "left_image": str(LEFT_IMG),
        "right_image": str(RIGHT_IMG),
        "combined_image": str(OUT_DIR / "source/combined_input.jpg"),
        "image_size_per_eye": [W, H],
        "combined_size": [W_combined, H],
    },
    "calibration": {
        "source": {
            "intrinsics": str(BASE_DIR / "相机标定课程/第一章 标定基础知识 code & data/calib/data/intrinsics.yml"),
            "extrinsics": str(BASE_DIR / "相机标定课程/第一章 标定基础知识 code & data/calib/data/extrinsics.yml"),
        },
        "left": {
            "camera_matrix": M1.tolist(),
            "distortion": D1.tolist()[:5],  # 只显示前5个非零参数
        },
        "right": {
            "camera_matrix": M2.tolist(),
            "distortion": D2.tolist()[:5],
        },
        "stereo": {
            "R": R_stereo.tolist(),
            "T": T_stereo.tolist(),
            "baseline": float(np.linalg.norm(T_stereo)),
            "rectified_focal_length": float(P1[0, 0]),
            "rectified_principal_point": [float(P1[0, 2]), float(P1[1, 2])],
            "Q_matrix": Q.tolist(),
        },
    },
    "format_spec": {
        "mesh_node_format": "36-bit = {v[17:0], u[17:0]}",
        "coordinate_format": "u12.5 signed (12-bit integer + 5-bit fractional)",
        "sram_addressing": "addr = iy * (mesh_cols+1) + ix, row-major",
        "frac_bits": 5,
        "frac_scale": 32,
        "lsb_value": 0.03125,
    },
    "mesh_tables": {},
    "yuv_inputs": {
        "nv12_y": str(OUT_DIR / "input/nv12/distorted_nv12_y.bin"),
        "nv12_uv": str(OUT_DIR / "input/nv12/distorted_nv12_uv.bin"),
        "nv16_y": str(OUT_DIR / "input/nv16/distorted_nv16_y.bin"),
        "nv16_uv": str(OUT_DIR / "input/nv16/distorted_nv16_uv.bin"),
        "yuyv": str(OUT_DIR / "input/yuyv/distorted_yuyv.bin"),
    },
    "golden_reference": {
        "nv12_y": str(OUT_DIR / "golden/nv12/golden_nv12_y.bin"),
        "nv12_uv": str(OUT_DIR / "golden/nv12/golden_nv12_uv.bin"),
        "nv16_y": str(OUT_DIR / "golden/nv16/golden_nv16_y.bin"),
        "nv16_uv": str(OUT_DIR / "golden/nv16/golden_nv16_uv.bin"),
        "yuyv": str(OUT_DIR / "golden/yuyv/golden_yuyv.bin"),
        "y_plane": str(OUT_DIR / "golden/golden_y_plane.bin"),
        "u_plane": str(OUT_DIR / "golden/golden_u_plane.bin"),
        "v_plane": str(OUT_DIR / "golden/golden_v_plane.bin"),
    },
    "validation": {
        "epipolar_alignment_error_mean_px": float(y_diff_LR.mean()),
        "epipolar_alignment_error_max_px": float(y_diff_LR.max()),
    },
}

for mesh_name, _, _ in MESH_CONFIGS:
    manifest["mesh_tables"][mesh_name] = {
        **all_mesh_info[mesh_name],
        "hex_file": str(OUT_DIR / "mesh" / mesh_name / f"agdc_mesh_{mesh_name}_36bit.hex"),
        "bin64_file": str(OUT_DIR / "mesh" / mesh_name / f"agdc_mesh_{mesh_name}_36bit_in_u64.bin"),
        "uv_interleaved_file": str(OUT_DIR / "mesh" / mesh_name / f"agdc_mesh_{mesh_name}_uv_fixed.bin"),
        "c_header": str(OUT_DIR / "mesh" / mesh_name / f"agdc_mesh_{mesh_name}.h"),
    }

manifest_path = OUT_DIR / "manifest.json"
with open(str(manifest_path), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f"  {manifest_path}")

# ============================================================
# 11. 输出目录树
# ============================================================
print(f"\n{'='*72}")
print(f"输出目录树")
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
        if size >= 1024: size /= 1024; unit = "KB"
        print(f"{prefix}{path.name}  ({size:.1f} {unit})")

print_tree(OUT_DIR)

print(f"\n{'='*72}")
print(f"完成! 生成脚本: {Path(__file__).resolve()}")
print(f"{'='*72}")
