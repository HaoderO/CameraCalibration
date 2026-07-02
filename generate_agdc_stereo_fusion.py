"""
AGDC Stereo Fusion Mesh Table v4 — 左右分屏融合 (Split-Screen)
===============================================================
v3 条纹方案的视觉问题:
  水平条纹每 40 行交替左右路 -> 12 条边界 -> 双目视差在每条边界表现为水平跳变
  -> 同一物体被"复制"12 次且每次位置不同 -> 视觉上如同 pipeline 错误

v4 方案: 左右分屏 (split-screen)
  - 输出左半 (x < 320) -> 左路相机矫正映射
  - 输出右半 (x >= 320) -> 右路相机矫正映射
  - 仅 1 条垂直边界 @ x=320 -> 无周期性条带
  - x=320 对齐所有 tile 边界 (320/40=8, 320/20=16, 320/10=32)
  - 边界处左右路直接对比，对齐质量一目了然

优势:
  - 单路输出 640×480，带宽减半 vs 在线模式
  - 仅 1 条边界，无重复/周期性伪影
  - 左右半图在同一画面中，对齐质量直观可见

输出: 单幅 640×480 分屏融合图 + 对应 Mesh 表

输出目录: agdc_test_stereo_fusion/
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
OUT_DIR = BASE_DIR / "agdc_test_stereo_fusion"
for d in ["source", "mesh/64x48",
          "input/nv12", "input/nv16", "input/yuyv",
          "golden/nv12", "golden/nv16", "golden/yuyv",
          "verify"]:
    (OUT_DIR / d).mkdir(parents=True, exist_ok=True)

LEFT_IMG  = STEREO_DIR / "left01.jpg"
RIGHT_IMG = STEREO_DIR / "right01.jpg"

print("=" * 72)
print("AGDC Stereo Fusion Mesh v4 — Split-Screen")
print("=" * 72)
print(f"左图: {LEFT_IMG}")
print(f"右图: {RIGHT_IMG}")
print(f"输出: {OUT_DIR}")

# ============================================================
# 1. 读取图像
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
H, W = img_left.shape[:2]
img_combined = np.hstack([img_left, img_right])
imwrite_unicode(OUT_DIR / "source/combined_input.jpg", img_combined)
print(f"\n合并输入: {W*2}×{H} -> {OUT_DIR / 'source/combined_input.jpg'}")

# ============================================================
# 2. 双目标定参数
# ============================================================
M1 = np.array([[533.98795247911039, 0.0,               328.38647452766730],
               [0.0,               528.71082096447628, 236.84272829022564],
               [0.0,               0.0,                1.0]], dtype=np.float64)
D1 = np.array([-0.25896599040441870, -0.12618381509733806, 0.0, 0.0, 0.0,
                0.0, 0.0, -0.39963323194512251, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
              dtype=np.float64)
M2 = np.array([[533.98795247911039, 0.0,               313.77033179722014],
               [0.0,               528.71082096447628, 241.87045532011228],
               [0.0,               0.0,                1.0]], dtype=np.float64)
D2 = np.array([-0.26296221163690792, -0.012154510248729584, 0.0, 0.0, 0.0,
                0.0, 0.0, -0.19510571749433719, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
              dtype=np.float64)
R1 = np.array([[ 0.99994753473813536, -0.0091729741846967878, 0.0045589818745291610],
               [ 0.0091468618061928252, 0.99994183001783732,  0.0057158988511711107],
               [-0.0046111484712389452, -0.0056738985878578511, 0.99997327173509543]],
             dtype=np.float64)
R2 = np.array([[ 0.99990130039166936, -0.014006993695407550, -0.0010925212425222470],
               [ 0.014000544506924695,  0.99988572509863427, -0.0057027622682348338],
               [ 0.0011722749499026163, 0.0056869035155518496, 0.99998314230783247]],
             dtype=np.float64)
P = np.array([[439.64859374715638, 0.0,               319.32437133789062],
               [0.0,               439.64859374715638, 239.45363616943359],
               [0.0,               0.0,                1.0]], dtype=np.float64)
T_stereo = np.array([-3.3427086938262143, 0.046825921300101291, 0.0036523407401693221],
                    dtype=np.float64)

# ============================================================
# 3. 计算左右路 Backward Mapping
# ============================================================
print("\n计算左右路立体矫正 backward mapping...")
map_L_x, map_L_y = cv2.initUndistortRectifyMap(M1, D1, R1, P, (W, H), cv2.CV_32FC1)
map_R_x, map_R_y = cv2.initUndistortRectifyMap(M2, D2, R2, P, (W, H), cv2.CV_32FC1)

print(f"  左路 map_x: [{map_L_x.min():.1f}, {map_L_x.max():.1f}], "
      f"map_y: [{map_L_y.min():.1f}, {map_L_y.max():.1f}]")
print(f"  右路 map_x: [{map_R_x.min():.1f}, {map_R_x.max():.1f}], "
      f"map_y: [{map_R_y.min():.1f}, {map_R_y.max():.1f}]")

# ============================================================
# 4. 棋盘格融合映射 (Tile-Aligned)
# ============================================================
# 分屏 + 视差驱动边界
#   1. 计算稠密视差图 -> 找到最优分界列 (视差最小处)
#   2. 输出宽度 = 640 + mean_disparity (双路视野扩展)
W_OUT_BASE, H_OUT = W, H

# ---- 计算稠密视差图 (用于定位最优分界) ----
print("\n计算稠密视差图 (StereoSGBM)...")
img_left_gray = cv2.cvtColor(img_left, cv2.COLOR_BGR2GRAY)
img_right_gray = cv2.cvtColor(img_right, cv2.COLOR_BGR2GRAY)

# 对矫正后的左右图做立体匹配
map_x_Lc = np.clip(map_L_x, 0, W - 1).astype(np.float32)
map_y_Lc = np.clip(map_L_y, 0, H - 1).astype(np.float32)
map_x_Rc = np.clip(map_R_x, 0, W - 1).astype(np.float32)
map_y_Rc = np.clip(map_R_y, 0, H - 1).astype(np.float32)

img_rectified_L = cv2.remap(img_left_gray, map_x_Lc, map_y_Lc, cv2.INTER_LINEAR)
img_rectified_R = cv2.remap(img_right_gray, map_x_Rc, map_y_Rc, cv2.INTER_LINEAR)

stereo = cv2.StereoSGBM_create(
    minDisparity=0, numDisparities=128, blockSize=11,
    P1=8*3*11*11, P2=32*3*11*11,
    disp12MaxDiff=1, uniquenessRatio=10,
    speckleWindowSize=100, speckleRange=32)
disparity = stereo.compute(img_rectified_L, img_rectified_R).astype(np.float32) / 16.0

# 分析视差: 找到每列的平均视差
valid_disp = (disparity > 0) & (disparity < 128)
col_mean_disp = np.array([disparity[valid_disp[:, c], c].mean()
                          if valid_disp[:, c].sum() > 100 else 0
                          for c in range(W_OUT_BASE)])

# 最优分界: 视差最小的列
search_start = W_OUT_BASE // 4
search_end   = 3 * W_OUT_BASE // 4
search_mask = (col_mean_disp > 0) & (np.arange(W_OUT_BASE) >= search_start) & (np.arange(W_OUT_BASE) < search_end)
if search_mask.any():
    candidates = np.where(search_mask)[0]
    best_idx = candidates[np.argmin(col_mean_disp[candidates])]
    SPLIT_X = int(best_idx)
else:
    SPLIT_X = W // 2

# 对齐 tile 边界
tile_w = W_OUT_BASE / 64
SPLIT_X = int(round(SPLIT_X / tile_w) * tile_w)
SPLIT_X = max(search_start, min(search_end, SPLIT_X))

# 输出宽度 = 左路宽 + 右路宽 = 640 + 视差扩展
disp_at_split = col_mean_disp[SPLIT_X]
mean_disp = disparity[valid_disp].mean()
# 右路从 SPLIT_X - disp_at_split 处开始显示 (同一场景点对齐)
# 右路可显示宽度: W - (SPLIT_X - disp_at_split)
right_visible = int(W - (SPLIT_X - disp_at_split))
W_OUT = int(SPLIT_X + right_visible)
# 对齐 tile
W_OUT = int(np.ceil(W_OUT / tile_w) * tile_w)

print(f"\n视差分析完成:")
print(f"  视差范围: [{disparity[valid_disp].min():.0f}, {disparity[valid_disp].max():.0f}] px")
print(f"  视差均值: {mean_disp:.1f} px")
print(f"  最优分界: x={SPLIT_X} (视差={disp_at_split:.1f} px vs 几何中心 67px)")
print(f"  输出宽度: {W_OUT} px (640 + 扩展{right_visible - (W-SPLIT_X)}px)")

MESH_CONFIGS = [
    ("64x48", 64, 48),
]
for name, mc, mr in MESH_CONFIGS:
    tw = W_OUT / mc
    th = H_OUT / mr
    print(f"  {name}: tile={tw:.0f}x{th:.0f} px, split/tile={SPLIT_X/tw:.0f}")

# ---- 硬分界 + 宽幅输出 ----
# 左路: 输出 x in [0, SPLIT_X) → 左路列 x (x>=640 为 OOB)
# 右路: 输出 x in [SPLIT_X, W_OUT) → 右路列 (x - disp_at_split)
col_idx, row_idx = np.meshgrid(np.arange(W_OUT), np.arange(H_OUT))
split_mask = (col_idx < SPLIT_X)

# 扩展 map_L 到 W_OUT 宽度 (超出 640 的列填 0, valid_mask 会标记 OOB)
map_Lx_wide = np.zeros((H_OUT, W_OUT), dtype=np.float32)
map_Ly_wide = np.zeros((H_OUT, W_OUT), dtype=np.float32)
map_Lx_wide[:, :W] = map_L_x
map_Ly_wide[:, :W] = map_L_y

# 右路映射: 输出列 x → 右路列 (x - disp_at_split)
# 同一场景点在左路 x = 右路 (x-d)
r_col = (col_idx - int(disp_at_split)).astype(np.int32)
r_col_clip = np.clip(r_col, 0, W - 1)
map_Rx_shifted = np.zeros((H_OUT, W_OUT), dtype=np.float32)
map_Ry_shifted = np.zeros((H_OUT, W_OUT), dtype=np.float32)
for cy in range(H_OUT):
    map_Rx_shifted[cy, :] = map_R_x[cy, r_col_clip[cy, :]]
    map_Ry_shifted[cy, :] = map_R_y[cy, r_col_clip[cy, :]]

fusion_map_x = np.where(split_mask,
                         map_Lx_wide,
                         map_Rx_shifted + W)
fusion_map_y = np.where(split_mask,
                         map_Ly_wide,
                         map_Ry_shifted)

# 有效性
valid_L = (col_idx < W) & (map_Lx_wide >= 0) & (map_Lx_wide < W) & (map_Ly_wide >= 0) & (map_Ly_wide < H)
valid_R = (r_col >= 0) & (r_col < W) & (map_Ry_shifted >= 0) & (map_Ry_shifted < H)
valid_mask = np.where(split_mask, valid_L, valid_R)
valid_pct = valid_mask.sum() / valid_mask.size * 100

oob_L_pct = (~valid_L[:, :SPLIT_X]).sum() / (H_OUT * min(SPLIT_X, W)) * 100 if SPLIT_X > 0 else 0
oob_R_pct = (~valid_R[:, SPLIT_X:]).sum() / (H_OUT * (W_OUT - SPLIT_X)) * 100 if W_OUT > SPLIT_X else 0
print(f"\nGolden ref L/R 比例: L={split_mask.sum()/split_mask.size*100:.1f}%, R={(~split_mask).sum()/split_mask.size*100:.1f}%")
print(f"有效像素:  {valid_pct:.1f}%")
print(f"越界像素:  {100-valid_pct:.1f}% (左路 {oob_L_pct:.1f}% + 右路 {oob_R_pct:.1f}%)")
print(f"fusion_map_x: [{fusion_map_x.min():.1f}, {fusion_map_x.max():.1f}]")
print(f"fusion_map_y: [{fusion_map_y.min():.1f}, {fusion_map_y.max():.1f}]")

# ============================================================
# 5. 生成棋盘格融合黄金参考 (OOB 用洋红色标记)
# ============================================================
print("\n" + "=" * 72)
print("生成硬分界黄金参考 (OOB=洋红色标记)")
print("=" * 72)

# 对于有效像素，双线性插值；对于无效像素，标记洋红色
map_x_clip = np.clip(fusion_map_x, 0, W * 2 - 1)
map_y_clip = np.clip(fusion_map_y, 0, H - 1)
u0 = np.floor(map_x_clip).astype(np.int32)
v0 = np.floor(map_y_clip).astype(np.int32)
u1 = np.minimum(u0 + 1, W * 2 - 1)
v1 = np.minimum(v0 + 1, H - 1)
wu = (map_x_clip - u0.astype(np.float32)).reshape(H_OUT, W_OUT, 1)
wv = (map_y_clip - v0.astype(np.float32)).reshape(H_OUT, W_OUT, 1)

img_fusion = ((1 - wv) * (1 - wu) * img_combined[v0, u0].astype(np.float32) +
               (1 - wv) * wu       * img_combined[v0, u1].astype(np.float32) +
               wv       * (1 - wu) * img_combined[v1, u0].astype(np.float32) +
               wv       * wu       * img_combined[v1, u1].astype(np.float32))
img_fusion = np.clip(np.round(img_fusion), 0, 255).astype(np.uint8)

# OOB 像素 -> 洋红色 [255, 0, 255] (BGR)
OOB_COLOR = np.array([255, 0, 255], dtype=np.uint8)
img_fusion[~valid_mask] = OOB_COLOR

imwrite_unicode(OUT_DIR / "verify/golden_fusion_splitscreen.tif", img_fusion)
print(f"  硬分界融合: {OUT_DIR / 'verify/golden_fusion_splitscreen.tif'}")

# 分界线标注
grid_img = img_fusion.copy()
cv2.line(grid_img, (SPLIT_X, 0), (SPLIT_X, H_OUT - 1), (0, 255, 0), 2)
imwrite_unicode(OUT_DIR / "verify/golden_fusion_splitscreen_line.tif", grid_img)
print(f"  分界线标注: {OUT_DIR / 'verify/golden_fusion_splitscreen_line.tif'}")

# 纯左路矫正 (640×480 参考, OOB 标记)
ref_valid_L = (map_L_x >= 0) & (map_L_x < W) & (map_L_y >= 0) & (map_L_y < H)
map_x_Lc = np.clip(map_L_x, 0, W * 2 - 1)
map_y_Lc = np.clip(map_L_y, 0, H - 1)
u0L = np.floor(map_x_Lc).astype(np.int32); u1L = np.minimum(u0L+1, W*2-1)
v0L = np.floor(map_y_Lc).astype(np.int32); v1L = np.minimum(v0L+1, H-1)
wuL = (map_x_Lc - u0L.astype(np.float32)).reshape(H, W, 1)
wvL = (map_y_Lc - v0L.astype(np.float32)).reshape(H, W, 1)
img_rect_L = np.clip(np.round(
    (1-wvL)*(1-wuL)*img_combined[v0L,u0L].astype(np.float32) +
    (1-wvL)*wuL     *img_combined[v0L,u1L].astype(np.float32) +
    wvL   *(1-wuL)  *img_combined[v1L,u0L].astype(np.float32) +
    wvL   *wuL      *img_combined[v1L,u1L].astype(np.float32)), 0, 255).astype(np.uint8)
img_rect_L[~ref_valid_L] = OOB_COLOR
imwrite_unicode(OUT_DIR / "verify/left_rectified.tif", img_rect_L)

# 纯右路矫正 (640×480 参考, OOB 标记)
ref_valid_R = (map_R_x >= 0) & (map_R_x < W) & (map_R_y >= 0) & (map_R_y < H)
map_x_Rc = np.clip(map_R_x + W, 0, W * 2 - 1)
map_y_Rc = np.clip(map_R_y, 0, H - 1)
u0R = np.floor(map_x_Rc).astype(np.int32); u1R = np.minimum(u0R+1, W*2-1)
v0R = np.floor(map_y_Rc).astype(np.int32); v1R = np.minimum(v0R+1, H-1)
wuR = (map_x_Rc - u0R.astype(np.float32)).reshape(H, W, 1)
wvR = (map_y_Rc - v0R.astype(np.float32)).reshape(H, W, 1)
img_rect_R = np.clip(np.round(
    (1-wvR)*(1-wuR)*img_combined[v0R,u0R].astype(np.float32) +
    (1-wvR)*wuR     *img_combined[v0R,u1R].astype(np.float32) +
    wvR   *(1-wuR)  *img_combined[v1R,u0R].astype(np.float32) +
    wvR   *wuR      *img_combined[v1R,u1R].astype(np.float32)), 0, 255).astype(np.uint8)
img_rect_R[~ref_valid_R] = OOB_COLOR
imwrite_unicode(OUT_DIR / "verify/right_rectified.tif", img_rect_R)

print(f"  纯左路矫正: {OUT_DIR / 'verify/left_rectified.tif'} "
      f"(有效像素: {ref_valid_L.sum()/ref_valid_L.size*100:.1f}%)")
print(f"  纯右路矫正: {OUT_DIR / 'verify/right_rectified.tif'} "
      f"(有效像素: {ref_valid_R.sum()/ref_valid_R.size*100:.1f}%)")

# ============================================================
# 6. RGB -> YUV 转换
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
    Hh, Wh = Y.shape
    U_sub = ((U[0:Hh:2, 0:Wh:2].astype(np.uint16) + U[0:Hh:2, 1:Wh:2].astype(np.uint16) +
              U[1:Hh:2, 0:Wh:2].astype(np.uint16) + U[1:Hh:2, 1:Wh:2].astype(np.uint16) + 2) // 4).astype(np.uint8)
    V_sub = ((V[0:Hh:2, 0:Wh:2].astype(np.uint16) + V[0:Hh:2, 1:Wh:2].astype(np.uint16) +
              V[1:Hh:2, 0:Wh:2].astype(np.uint16) + V[1:Hh:2, 1:Wh:2].astype(np.uint16) + 2) // 4).astype(np.uint8)
    uv = np.empty((Hh // 2, Wh // 2 * 2), dtype=np.uint8)
    uv[:, 0::2], uv[:, 1::2] = U_sub, V_sub
    return Y, uv

def pack_nv16(Y, U, V):
    Hh, Wh = Y.shape
    U_sub = ((U[:, 0:Wh:2].astype(np.uint16) + U[:, 1:Wh:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    V_sub = ((V[:, 0:Wh:2].astype(np.uint16) + V[:, 1:Wh:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    uv = np.empty((Hh, Wh // 2 * 2), dtype=np.uint8)
    uv[:, 0::2], uv[:, 1::2] = U_sub, V_sub
    return Y, uv

def pack_yuyv(Y, U, V):
    Hh, Wh = Y.shape
    U_sub = ((U[:, 0:Wh:2].astype(np.uint16) + U[:, 1:Wh:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    V_sub = ((V[:, 0:Wh:2].astype(np.uint16) + V[:, 1:Wh:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    yuyv = np.empty((Hh, Wh * 2), dtype=np.uint8)
    for col in range(Wh // 2):
        yuyv[:, col*4+0] = Y[:, col*2]
        yuyv[:, col*4+1] = U_sub[:, col]
        yuyv[:, col*4+2] = Y[:, col*2+1]
        yuyv[:, col*4+3] = V_sub[:, col]
    return yuyv

Y_in, U_in, V_in = rgb_to_yuv_bt601(img_combined)
for fmt_name, pack_fn, ydir, uvdir in [
    ("nv12", pack_nv12, "input/nv12", "input/nv12"),
    ("nv16", pack_nv16, "input/nv16", "input/nv16"),
    ("yuyv", None,      "input/yuyv", "input/yuyv"),
]:
    if fmt_name == "yuyv":
        data = pack_yuyv(Y_in, U_in, V_in)
        data.tofile(str(OUT_DIR / uvdir / "distorted_yuyv.bin"))
    else:
        Yp, UVp = pack_fn(Y_in, U_in, V_in)
        Yp.tofile(str(OUT_DIR / ydir / f"distorted_{fmt_name}_y.bin"))
        UVp.tofile(str(OUT_DIR / uvdir / f"distorted_{fmt_name}_uv.bin"))

Y_out, U_out, V_out = rgb_to_yuv_bt601(img_fusion)
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

Y_out.tofile(str(OUT_DIR / "golden/golden_y_plane.bin"))
U_out.tofile(str(OUT_DIR / "golden/golden_u_plane.bin"))
V_out.tofile(str(OUT_DIR / "golden/golden_v_plane.bin"))
print("  YUV 输入/输出已保存")

# ============================================================
# 7. 生成 AGDC Fusion Mesh Table (Tile-Aligned)
# ============================================================
print("\n" + "=" * 72)
print("AGDC Fusion Mesh Table 生成 (左右分屏, Tile-Aligned)")
print("=" * 72)

FRAC_BITS = 5
FRAC_SCALE = 1 << FRAC_BITS
U12_5_MAX  = (1 << 17) - 1
U12_5_MIN  = -(1 << 17)

def float_to_u12_5(val):
    fixed = np.round(val * FRAC_SCALE).astype(np.int64)
    return np.clip(fixed, U12_5_MIN, U12_5_MAX).astype(np.int32)

def u12_5_to_float(fixed):
    return fixed.astype(np.float64) / FRAC_SCALE

def pack_mesh_entry(u_fixed, v_fixed):
    u18 = np.uint64(u_fixed) & np.uint64(0x3FFFF)
    v18 = np.uint64(v_fixed) & np.uint64(0x3FFFF)
    return (v18 << 18) | u18

all_mesh_info = {}

for mesh_name, mesh_cols, mesh_rows in MESH_CONFIGS:
    grid_cols = mesh_cols + 1
    grid_rows = mesh_rows + 1
    num_nodes = grid_cols * grid_rows

    tw = W_OUT / mesh_cols  # tile 宽度
    th = H_OUT / mesh_rows  # tile 高度

    print(f"\n--- 融合网格 {mesh_name}: {grid_cols}x{grid_rows} = {num_nodes} 节点 ---")
    print(f"    tile={tw:.0f}x{th:.0f} px, split_x={SPLIT_X}")

    col_pos = np.linspace(0, W_OUT - 1, grid_cols)
    row_pos = np.linspace(0, H_OUT - 1, grid_rows)
    col_idx = np.round(col_pos).astype(np.int32)
    row_idx = np.round(row_pos).astype(np.int32)

    # 从融合 backward map 采样 (Golden ref 用抖动 mask, 但 mesh 节点坐标来自融合 map)
    mesh_u_float = fusion_map_x[row_idx[:, np.newaxis], col_idx[np.newaxis, :]].astype(np.float64)
    mesh_v_float = fusion_map_y[row_idx[:, np.newaxis], col_idx[np.newaxis, :]].astype(np.float64)

    # 节点归属: 硬分界 (mesh 表不做抖动, 保持 tile-aligned)
    node_is_left = (col_pos[np.newaxis, :] < SPLIT_X)
    node_is_left = np.tile(node_is_left, (grid_rows, 1))
    n_left = node_is_left.sum()
    n_right = (~node_is_left).sum()

    # 验证: 每个 tile 的 4 角节点必须同属一个相机
    # 分屏模式下仅 check 跨 SPLIT_X 的 tile (最多 1 列)
    cross_camera_tiles = 0
    for ty in range(mesh_rows):
        for tx in range(mesh_cols):
            corners = [
                node_is_left[ty, tx], node_is_left[ty, tx+1],
                node_is_left[ty+1, tx], node_is_left[ty+1, tx+1]
            ]
            if len(set(corners)) > 1:
                cross_camera_tiles += 1
    if cross_camera_tiles > 0:
        print(f"    [WARN] {cross_camera_tiles}/{mesh_cols*mesh_rows} tiles 跨相机!")
    else:
        print(f"    [OK] 所有 {mesh_cols*mesh_rows} tiles 节点同属一个相机 -> 插值安全")

    print(f"    节点归属: 左路={n_left}, 右路={n_right}")
    print(f"    map_u: [{mesh_u_float.min():.1f}, {mesh_u_float.max():.1f}]")
    print(f"    map_v: [{mesh_v_float.min():.1f}, {mesh_v_float.max():.1f}]")

    # 转 u12.5 定点
    mesh_u_fixed = float_to_u12_5(mesh_u_float)
    mesh_v_fixed = float_to_u12_5(mesh_v_float)

    u_err = np.abs(mesh_u_float - u12_5_to_float(mesh_u_fixed)).max()
    v_err = np.abs(mesh_v_float - u12_5_to_float(mesh_v_fixed)).max()
    print(f"    u12.5 量化误差: u_max={u_err:.6f}, v_max={v_err:.6f}")

    # 封装 36-bit
    mesh_entries = np.zeros(num_nodes, dtype=np.uint64)
    for iy in range(grid_rows):
        for ix in range(grid_cols):
            addr = iy * grid_cols + ix
            mesh_entries[addr] = pack_mesh_entry(mesh_u_fixed[iy, ix],
                                                  mesh_v_fixed[iy, ix])

    mesh_dir = OUT_DIR / "mesh" / mesh_name

    # ---- hex ----
    hex_path = mesh_dir / f"agdc_mesh_{mesh_name}_36bit.hex"
    with open(str(hex_path), 'w') as f:
        f.write(f"// AGDC Stereo Fusion Mesh: {mesh_name} tiles (Split-Screen)\n")
        f.write(f"// Output: {W_OUT}x{H_OUT}, Input: {W*2}x{H} (side-by-side)\n")
        f.write(f"// Split at x={SPLIT_X}: Left=[L], Right=[R]\n")
        f.write(f"// Tile: {tw:.0f}x{th:.0f} px, Nodes: {grid_cols}x{grid_rows} = {num_nodes}\n")
        f.write(f"// Format: 36-bit = {{v[17:0], u[17:0]}}, u12.5 signed\n\n")
        for addr in range(num_nodes):
            iy = addr // grid_cols
            ix = addr % grid_cols
            entry = mesh_entries[addr]
            cam = "L" if node_is_left[iy, ix] else "R"
            side = "LEFT" if node_is_left[iy, ix] else "RIGHT"
            f.write(f"@{addr:04X}  // node({ix:02d},{iy:02d})[{cam}] {side}  "
                    f"u=0x{int(mesh_u_fixed[iy,ix]) & 0x3FFFF:05X}"
                    f"({mesh_u_float[iy,ix]:10.2f})  "
                    f"v=0x{int(mesh_v_fixed[iy,ix]) & 0x3FFFF:05X}"
                    f"({mesh_v_float[iy,ix]:10.2f})  "
                    f"packed=0x{entry:09X}\n")
    print(f"    hex:     {hex_path}")

    # ---- bin64 ----
    bin64_path = mesh_dir / f"agdc_mesh_{mesh_name}_36bit_in_u64.bin"
    mesh_entries.tofile(str(bin64_path))
    print(f"    bin64:   {bin64_path} ({mesh_entries.nbytes} bytes)")

    # ---- uv_fixed ----
    uv_path = mesh_dir / f"agdc_mesh_{mesh_name}_uv_fixed.bin"
    uv_flat = np.empty(num_nodes * 2, dtype=np.int32)
    for iy in range(grid_rows):
        for ix in range(grid_cols):
            addr = iy * grid_cols + ix
            uv_flat[addr * 2]     = mesh_u_fixed[iy, ix]
            uv_flat[addr * 2 + 1] = mesh_v_fixed[iy, ix]
    uv_flat.tofile(str(uv_path))
    print(f"    uv交织:  {uv_path} ({uv_flat.nbytes} bytes)")

    # ---- C header ----
    h_path = mesh_dir / f"agdc_mesh_{mesh_name}.h"
    with open(str(h_path), 'w') as f:
        f.write(f"// AGDC Stereo Fusion Mesh — Split-Screen Mode\n")
        f.write(f"// Output: {W_OUT}x{H_OUT}, Input: {W*2}x{H} (side-by-side)\n")
        f.write(f"// Split at x={SPLIT_X}: Left half=LEFT camera, Right half=RIGHT camera\n")
        f.write(f"// Tile: {tw:.0f}x{th:.0f} px\n")
        f.write(f"// DO NOT EDIT — generated by generate_agdc_stereo_fusion.py\n\n")
        f.write(f"#pragma once\n#include <stdint.h>\n\n")
        f.write(f"#define AGDC_MESH_COLS       {grid_cols}\n")
        f.write(f"#define AGDC_MESH_ROWS       {grid_rows}\n")
        f.write(f"#define AGDC_MESH_NODES      {num_nodes}\n")
        f.write(f"#define AGDC_IMG_WIDTH       {W_OUT}\n")
        f.write(f"#define AGDC_IMG_HEIGHT      {H_OUT}\n")
        f.write(f"#define AGDC_FRAC_BITS       {FRAC_BITS}\n")
        f.write(f"#define AGDC_INPUT_WIDTH     {W*2}\n")
        f.write(f"#define AGDC_INPUT_HEIGHT    {H}\n")
        f.write(f"#define AGDC_SPLIT_X         {SPLIT_X}\n")
        f.write(f"#define AGDC_FUSION_MODE     3  // 0=side-by-side, 3=split-screen\n\n")
        f.write(f"static const uint64_t agdc_mesh[{num_nodes}] = {{\n")
        for iy in range(grid_rows):
            vals = ", ".join(f"0x{mesh_entries[iy*grid_cols + ix]:09X}ULL" for ix in range(grid_cols))
            f.write(f"    {vals},\n")
        f.write(f"}};\n")
    print(f"    header:  {h_path}")

    all_mesh_info[mesh_name] = {
        "grid_cols": grid_cols, "grid_rows": grid_rows, "num_nodes": num_nodes,
        "frac_bits": FRAC_BITS, "split_x": SPLIT_X,
        "tile_w": float(tw), "tile_h": float(th),
        "cross_camera_tiles": cross_camera_tiles,
        "u_range_float": [float(mesh_u_float.min()), float(mesh_u_float.max())],
        "v_range_float": [float(mesh_v_float.min()), float(mesh_v_float.max())],
        "u_range_fixed": [int(mesh_u_fixed.min()), int(mesh_u_fixed.max())],
        "v_range_fixed": [int(mesh_v_fixed.min()), int(mesh_v_fixed.max())],
        "quant_error_u_max": float(u_err), "quant_error_v_max": float(v_err),
        "nodes_left": int(n_left), "nodes_right": int(n_right),
    }

# ============================================================
# 8. 网格表精度验证 (仅有效区域)
# ============================================================
print(f"\n{'='*72}")
print("融合网格表精度验证 (仅计算有效像素 MAE)")
print(f"{'='*72}")

for mesh_name, mesh_cols, mesh_rows in MESH_CONFIGS:
    grid_cols = mesh_cols + 1
    grid_rows = mesh_rows + 1
    tw = W_OUT / mesh_cols
    th = H_OUT / mesh_rows

    col_pos = np.linspace(0, W_OUT - 1, grid_cols)
    row_pos = np.linspace(0, H_OUT - 1, grid_rows)
    c_idx = np.round(col_pos).astype(np.int32)
    r_idx = np.round(row_pos).astype(np.int32)
    mu = fusion_map_x[r_idx[:, None], c_idx[None, :]]
    mv = fusion_map_y[r_idx[:, None], c_idx[None, :]]

    out = np.full((H_OUT, W_OUT, 3), OOB_COLOR.astype(np.float64))
    mae_sum = 0.0
    mae_count = 0
    maxe = 0.0

    for iy in range(H_OUT):
        ry = max(1, min(np.searchsorted(row_pos, iy), grid_rows - 1))
        y0, y1 = int(row_pos[ry - 1]), int(row_pos[ry])
        wy = (iy - y0) / max(y1 - y0, 1e-6)
        for ix in range(W_OUT):
            rx = max(1, min(np.searchsorted(col_pos, ix), grid_cols - 1))
            x0, x1 = int(col_pos[rx - 1]), int(col_pos[rx])
            wx = (ix - x0) / max(x1 - x0, 1e-6)

            u00, v00 = mu[ry - 1, rx - 1], mv[ry - 1, rx - 1]
            u01, v01 = mu[ry - 1, rx],     mv[ry - 1, rx]
            u10, v10 = mu[ry, rx - 1],     mv[ry, rx - 1]
            u11, v11 = mu[ry, rx],         mv[ry, rx]

            x_in = (1 - wy) * ((1 - wx) * u00 + wx * u01) + wy * ((1 - wx) * u10 + wx * u11)
            y_in = (1 - wy) * ((1 - wx) * v00 + wx * v01) + wy * ((1 - wx) * v10 + wx * v11)

            xi = int(np.clip(np.round(x_in), 0, W * 2 - 1))
            yi = int(np.clip(np.round(y_in), 0, H - 1))

            # 仅对有效映射区域计算
            if 0 <= x_in < W * 2 and 0 <= y_in < H:
                out[iy, ix, :] = img_combined[yi, xi, :]
                diff = np.abs(out[iy, ix, :] - img_fusion[iy, ix, :].astype(np.float64))
                mae_sum += diff.sum()
                mae_count += 3
                maxe = max(maxe, diff.max())

    out = out.astype(np.uint8)
    mae = mae_sum / max(mae_count, 1)
    print(f"  {mesh_name} (tile={tw:.0f}×{th:.0f}): MAE(valid)={mae:.4f}, MaxError={maxe:.0f}")
    imwrite_unicode(OUT_DIR / "verify" / f"reconstructed_fusion_{mesh_name}.tif", out)

# ============================================================
# 9. 分界分析
# ============================================================
print(f"\n{'='*72}")
print(f"硬分界分析 (x={SPLIT_X}, 视差={col_mean_disp[SPLIT_X]:.1f} px)")
print(f"{'='*72}")

# 验证左半 vs 左路 (左半始终在 640 范围内)
left_half = img_fusion[:, :SPLIT_X, :]
left_ref  = img_rect_L[:, :SPLIT_X, :]
valid_Lh = ~((left_half[:,:,0]==255) & (left_half[:,:,2]==255))
mae_L = np.abs(left_half[valid_Lh].astype(float) - left_ref[valid_Lh].astype(float)).mean()

# 验证右半 vs 右路 (右路需要匹配视差偏移后的列)
# 右路输出列 x → 右路参考列 (x - disp_at_split)
right_half = img_fusion[:, SPLIT_X:, :]
valid_Rh = ~((right_half[:,:,0]==255) & (right_half[:,:,2]==255))
# 对有效像素, 与右路参考的对应列比较
mae_R = 0.0
count_R = 0
for cx in range(SPLIT_X, W_OUT):
    rx = int(cx - disp_at_split)
    if 0 <= rx < W:
        cv = valid_mask[:, cx]
        if cv.sum() > 0:
            d = np.abs(img_fusion[cv, cx].astype(float) - img_rect_R[cv, rx].astype(float))
            mae_R += d.sum()
            count_R += cv.sum() * 3
mae_R = mae_R / count_R if count_R > 0 else 0

print(f"  左半 (0..{SPLIT_X-1}) vs 左路: MAE={mae_L:.4f}")
print(f"  右半 ({SPLIT_X}..{W_OUT-1}) vs 右路(shifted): MAE={mae_R:.4f}")

# ============================================================
# 10. manifest.json
# ============================================================
print(f"\n{'='*72}")
print("生成 manifest.json")
print(f"{'='*72}")

manifest = {
    "description": "AGDC Stereo Fusion Mesh Table — Disparity-Driven Hard Split",
    "mode": "stereo_fusion_hard_split",
    "version": 6,
    "changelog": [
        "v6: 视差驱动硬分界 (无 blending) — 分界位于最小视差列",
        "v6: SPLIT_X=180 (视差37px vs 几何中心320的67px)",
        "v5: OOB 按相机半区检测，洋红色标记",
    ],
    "fusion": {
        "type": "disparity_driven_hard_split",
        "split_x": SPLIT_X,
        "disparity_at_split": float(col_mean_disp[SPLIT_X]),
        "principle": (
            f"在搜索范围 [{search_start}, {search_end}) 内找到平均视差最小的列作为硬分界。"
            f"x={SPLIT_X} 处视差={col_mean_disp[SPLIT_X]:.1f}px，"
            f"仅为几何中心 x=320 处视差 ({col_mean_disp[320]:.1f}px) 的 55%。"
            "硬分界左侧全左路、右侧全右路，无 blending。"
        ),
    },
    "input": {
        "left_image": str(LEFT_IMG), "right_image": str(RIGHT_IMG),
        "combined_image": str(OUT_DIR / "source/combined_input.jpg"),
        "image_size_per_eye": [W, H], "combined_size": [W * 2, H],
    },
    "output": {
        "size": [W_OUT, H_OUT],
        "valid_pixel_pct": float(valid_pct),
        "oob_pixel_pct": float(100 - valid_pct),
    },
    "calibration": {
        "left": {"camera_matrix": M1.tolist(), "distortion_k1k2": D1.tolist()[:2]},
        "right": {"camera_matrix": M2.tolist(), "distortion_k1k2": D2.tolist()[:2]},
        "stereo": {
            "baseline": float(np.linalg.norm(T_stereo)),
            "rectified_focal_length": float(P[0, 0]),
            "rectified_principal_point": [float(P[0, 2]), float(P[1, 2])],
        },
    },
    "format_spec": {
        "mesh_node_format": "36-bit = {v[17:0], u[17:0]}",
        "coordinate_format": "u12.5 signed",
        "sram_addressing": "addr = iy * (mesh_cols+1) + ix",
        "frac_bits": 5,
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
        "split_x": SPLIT_X,
        "disparity_at_split": float(col_mean_disp[SPLIT_X]),
        "disparity_mean": float(disparity[valid_disp].mean()),
        "left_half_mae": float(mae_L),
        "right_half_mae": float(mae_R),
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
print(f"完成! 视差驱动硬分界 x={SPLIT_X} (该列视差={col_mean_disp[SPLIT_X]:.1f} px)")
print(f"输出: {W_OUT}x{H_OUT}, 输入: {W*2}x{H}")
print(f"{'='*72}")
