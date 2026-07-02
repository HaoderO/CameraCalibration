# AGDC Test Data — 双目标定数据集 (Online Mode)

> 生成日期：2026-07-01
> 标定工具：OpenCV stereoCalibrate + Bouguet 方法
> 标定图像：`left01.jpg` + `right01.jpg` (640×480 棋盘格, 左右相机)
> 生成脚本：`generate_agdc_stereo.py`

---

## 在线模式 (Online Mode) 数据流

AGDC 在线模式接收左右相机**横向拼接**的单帧输入，Mesh 表同时覆盖左右两路：

```
合并输入 (1280×480)                          合并矫正输出 (1280×480)
┌─────────────┬─────────────┐      AGDC      ┌─────────────┬─────────────┐
│ left01.jpg  │ right01.jpg │  ──── Mesh ──→ │ 左路矫正     │ 右路矫正     │
│   (0..639)  │ (640..1279) │   Table        │   (0..639)  │ (640..1279) │
└─────────────┴─────────────┘                 └─────────────┴─────────────┘
```

- **左路节点** (cols 0..7): 映射到合并图像左半 `[0, 640)` 的畸变坐标
- **右路节点** (cols 8..16): 映射到合并图像右半 `[640, 1280)` 的畸变坐标，坐标自动 +640 偏移
- 节点标注 `[L]` / `[R]` 便于识别来源相机

---

## 目录结构

```
agdc_test_stereo/
├── README.md                              ← 本文件
├── manifest.json                          ← 结构化索引（供脚本/Agent读取）
│
├── source/                                ← 原始合并图像
│   └── combined_input.jpg                 ←   left01 + right01 横向拼接 (BGR, 1280×480)
│
├── mesh/                                  ← AGDC 网格映射表
│   ├── 16x12/                             ←   16×12 tiles, 17×13 = 221 节点
│   │   ├── agdc_mesh_16x12_36bit.hex      ←     SRAM hex (含节点注释+相机标注)
│   │   ├── agdc_mesh_16x12_36bit_in_u64.bin ←   64-bit LE binary
│   │   ├── agdc_mesh_16x12_uv_fixed.bin   ←     u/v int32 交织
│   │   └── agdc_mesh_16x12.h              ←     C header (float+fixed)
│   ├── 32x24/                             ←   32×24 tiles, 33×25 = 825 节点
│   │   ├── agdc_mesh_32x24_36bit.hex
│   │   ├── agdc_mesh_32x24_36bit_in_u64.bin
│   │   ├── agdc_mesh_32x24_uv_fixed.bin
│   │   └── agdc_mesh_32x24.h
│   └── 64x48/                             ←   64×48 tiles, 65×49 = 3185 节点
│       ├── agdc_mesh_64x48_36bit.hex
│       ├── agdc_mesh_64x48_36bit_in_u64.bin
│       ├── agdc_mesh_64x48_uv_fixed.bin
│       └── agdc_mesh_64x48.h
│
├── input/                                 ← 仿真激励输入 (合并畸变图 → YUV)
│   ├── nv12/                              ←   YUV420SP (NV12)
│   │   ├── distorted_nv12_y.bin
│   │   └── distorted_nv12_uv.bin
│   ├── nv16/                              ←   YUV422SP (NV16)
│   │   ├── distorted_nv16_y.bin
│   │   └── distorted_nv16_uv.bin
│   └── yuyv/                              ←   YUV422I (YUYV)
│       └── distorted_yuyv.bin
│
├── golden/                                ← 黄金参考输出 (合并矫正图 → YUV)
│   ├── nv12/                              ←   YUV420SP (NV12)
│   │   ├── golden_nv12_y.bin
│   │   └── golden_nv12_uv.bin
│   ├── nv16/                              ←   YUV422SP (NV16)
│   │   ├── golden_nv16_y.bin
│   │   └── golden_nv16_uv.bin
│   ├── yuyv/                              ←   YUV422I (YUYV)
│   │   └── golden_yuyv.bin
│   ├── golden_y_plane.bin                 ←   逐像素 Y 平面
│   ├── golden_u_plane.bin                 ←   逐像素 U 平面
│   └── golden_v_plane.bin                 ←   逐像素 V 平面
│
└── verify/                                ← 验证对比图像
    ├── golden_rectified_stereo.tif         ←   合并矫正黄金参考 (1280×480)
    ├── left_rectified.tif                  ←   左路矫正输出 (640×480)
    ├── right_rectified.tif                 ←   右路矫正输出 (640×480)
    ├── epipolar_check.tif                  ←   极线对齐验证 (绿色水平线, 每48行)
    ├── reconstructed_mesh_16x12.tif        ←   16×12 网格表重建
    ├── reconstructed_mesh_32x24.tif        ←   32×24 网格表重建
    └── reconstructed_mesh_64x48.tif        ←   64×48 网格表重建
```

---

## 双目标定参数

### 来源

`相机标定课程/第一章 标定基础知识 code & data/calib/data/intrinsics.yml`
`相机标定课程/第一章 标定基础知识 code & data/calib/data/extrinsics.yml`

### 左相机内参

| 参数   | 值                  |
| ------ | ------------------- |
| fx     | 533.9879524791104   |
| fy     | 528.7108209644763   |
| cx     | 328.3864745276673   |
| cy     | 236.84272829022564  |
| k1     | -0.2589659904044187 |
| k2     | -0.1261838150973381 |
| k7     | -0.3996332319451225 |

### 右相机内参

| 参数   | 值                  |
| ------ | ------------------- |
| fx     | 533.9879524791104   |
| fy     | 528.7108209644763   |
| cx     | 313.77033179722014  |
| cy     | 241.87045532011228  |
| k1     | -0.2629622116369079 |
| k2     | -0.0121545102487296 |
| k7     | -0.1951057174943372 |

> 注：左右相机焦距相同 (CALIB_SAME_FOCAL_LENGTH)，主点略有差异 (~15 px 水平偏移)

### 立体外参 (右相机 → 左相机)

| 参数         | 值                                           |
| ------------ | -------------------------------------------- |
| **旋转 R**   | ≈ 单位矩阵 (接近平行光轴, < 0.7° 旋转)       |
| **平移 T**   | `[-3.343, 0.047, 0.004]`                     |
| **基线长度** | **3.343 单位** (几乎纯水平)                  |

### 矫正后公共参数

| 参数     | 值                  |
| -------- | ------------------- |
| 焦距     | **439.65**          |
| 主点     | (319.32, 239.45)    |
| 输出尺寸 | 1280×480 (合并)     |

### Q 矩阵 (深度反算)

```
Q = [1, 0, 0, -319.32]
    [0, 1, 0, -239.45]
    [0, 0, 0,  439.65]
    [0, 0, 0.299, 0   ]
```

视差 d → 深度 Z = Q[3][2] / (d + Q[3][3]) = 439.65 / d

---

## 畸变特征分析

### 左路 (矫正→畸变 Backward Mapping)

| 指标             | 值               |
| ---------------- | ---------------- |
| Δx 范围          | [-32.25, +36.10] |
| Δy 范围          | [-32.83, +21.59] |
| 最大位移幅度     | **45.70 px**     |
| 畸变类型         | 桶形畸变 (k1<0) + 径向 k7 分量 |

### 右路 (矫正→畸变 Backward Mapping)

| 指标             | 值               |
| ---------------- | ---------------- |
| Δx 范围          | [-35.25, +25.47] |
| Δy 范围          | [-22.48, +33.44] |
| 最大位移幅度     | **36.86 px**     |
| 畸变类型         | 桶形畸变 (k1<0)  |

### 硬件设计含义

| 含义                     | 数值                            |
| ------------------------ | ------------------------------- |
| 合并图最大 u 跨度        | [-1032, +41522] u12.5 fixed     |
| 合并图最大 v 跨度        | [-1012, +16376] u12.5 fixed     |
| AGDC 行缓冲器最小深度    | ≥ 50 行 (容纳最远垂直回查)      |
| 左右路最大 vspan         | ~46 px (左), ~37 px (右)        |

---

## AGDC Mesh 表规格

### 映射方向: Backward (rectify → distort)

与单目 AGDC 一致，Mesh 表存储**反向映射**：对矫正后输出图像的每个网格节点 `(u_out, v_out)`，
给出其在合并畸变输入图中的来源坐标 `(u_in, v_in)`。

双目特殊点：**右路节点 u_in 已自动偏移 +640**，指向合并图像右半部分。

```
AGDC 在线模式数据流 (Stereo):

  矫正图 (输出) 1280×480                  合并输入 (畸变) 1280×480
  ┌────────────┬────────────┐            ┌────────────┬────────────┐
  │ 左路 0..639 │ 右路640..1279│          │ left 0..639│ right640..1279│
  │            │            │            │            │            │
  │ u_out=0    │ u_out=640  │            │ u_in=-32.25│ u_in=612.98│
  │ v_out=0    │ v_out=0    │            │ v_in=-26.95│ v_in=-5.43 │
  └────────────┴────────────┘            └────────────┴────────────┘
         │            │            Backward      ↑            ↑
         └────────────┴─────────── Mapping ──────┘            │
                                        右路 u 已 +640 ──────┘
```

验证示例 —— 第一行节点：

```
node(00,00)[L]:  u_in=-32.25  v_in=-26.95  ← 左路矫正(0,0)来自左图外侧(负坐标)
node(08,00)[R]:  u_in=615.03  v_in=-0.15   ← 左/右边界节点, u<640 说明该节点映射到左图区域
node(16,00)[R]:  u_in=1287.60 v_in=-9.99   ← 右路矫正(1279,0)来自右图边缘外
```

负坐标值：矫正过程需要从图像边界外采样 → 硬件需处理越界钳位或边界填充。

### 数据格式 (每个节点 36-bit)

```
┌──────────────────┬──────────────────┐
│   v[17:0]        │   u[17:0]        │
│   bits [35:18]   │   bits [17:0]    │
└──────────────────┴──────────────────┘
```

| 字段       | 位宽   | 格式         | 整数位 | 小数位 | 范围                  |
| ---------- | ------ | ------------ | ------ | ------ | --------------------- |
| u          | 18-bit | signed u12.5 | 12     | 5      | [-4096, +4095.96875]  |
| v          | 18-bit | signed u12.5 | 12     | 5      | [-4096, +4095.96875]  |
| **总计**   | **36-bit** | —        | —      | —      | —                     |

- **1 LSB** = 1/32 = 0.03125 pixel
- **u, v** = 合并畸变图像中的浮点坐标 × 32，四舍五入取整
- **负值**用二进制补码表示
- **u 值 > 32767** (0x7FFF) 表示该节点为右路相机节点 (u ≥ 640, u12.5 ≥ 20480)

### SRAM 寻址

```
addr = iy × (mesh_cols + 1) + ix
```

| 网格   | 瓦片数 | 网格点 (cols+1) × (rows+1) | 节点总数 |
| ------ | ------ | --------------------------- | -------- |
| 16×12  | 16×12  | 17×13                       | 221      |
| 32×24  | 32×24  | 33×25                       | 825      |
| 64×48  | 64×48  | 65×49                       | 3185     |

### 节点相机归属

| 网格   | 左路节点 (L)        | 右路节点 (R)        |
| ------ | ------------------- | ------------------- |
| 16×12  | cols 0..7  (8列)    | cols 8..16 (9列)    |
| 32×24  | cols 0..16 (17列)   | cols 17..32 (16列)  |
| 64×48  | cols 0..32 (33列)   | cols 33..64 (32列)  |

---

## YUV 图像数据规格

### 颜色空间参数

- 标准：BT.601 (SD)
- Y = 0.299R + 0.587G + 0.114B
- U = -0.169R - 0.331G + 0.500B + 128
- V = 0.500R - 0.419G - 0.081B + 128
- 位深：8-bit，范围 [0, 255]

### 三种子采样格式

| 格式 | 类型       | 子采样   | Y 平面大小 | UV 平面大小   | 总大小     |
| ---- | ---------- | -------- | ---------- | ------------- | ---------- |
| NV12 | YUV420SP   | 2×2      | 1280×480   | 1280×240 = 300KB | 614400 + 307200 = 921600 |
| NV16 | YUV422SP   | 2×1 水平 | 1280×480   | 1280×480 = 600KB | 614400 + 614400 = 1228800 |
| YUYV | YUV422I    | 2×1 水平 | —          | —             | 1280×2×480 = 1228800 |

### 文件分类

| 用途               | 文件前缀          | 内容                                          |
| ------------------ | ----------------- | --------------------------------------------- |
| **仿真激励输入**   | `distorted_*`     | combined_input.jpg (合并畸变) 的 YUV 格式     |
| **黄金参考输出**   | `golden_*`        | golden_rectified_stereo.tif (合并矫正) 的 YUV 格式 |
| **独立 Y/U/V 平面** | `golden_y_plane.bin` 等 | 矫正图逐像素 Y/U/V，供逐点比对              |

---

## 精度验证结果

### Grid vs Full-Precision Rectification

| 网格   | MAE     | MaxError | 说明                                   |
| ------ | ------- | -------- | -------------------------------------- |
| 16×12  | 9.07    | 228      | 粗网格，边界区域插值误差较大           |
| 32×24  | 7.53    | 217      | 中等网格                               |
| 64×48  | 6.77    | 216      | 细网格，误差集中在图像边界的越界区域   |

> MaxError 集中在图像边界 (矫正有效区域之外)，硬件不做越界处理时这些像素不可见。
> u12.5 定点量化误差 ≤ 0.016 px (< ½ LSB)。

### 极线对齐

- 矫正后左右图对应行位于同一水平线上 → 立体匹配可按行搜索
- 验证图像：[`verify/epipolar_check.tif`](verify/epipolar_check.tif) (绿色水平参考线)

---

## AGDC 寄存器配置

### 双目在线模式推荐配置

以 **16×12 tiles、NV12 格式** 为例：

```
// ============================================================
// Step 1: 初始化
// ============================================================
WR AGDC_BASE + 0x04 = 0x00000000   // CTRL: enable_rectify=0

// ============================================================
// Step 2: 配置寄存器组
// ============================================================

// --- 帧尺寸 (合并图 1280×480) ---
WR AGDC_BASE + 0x08 = 0x01E00500   // INPUT_SIZE:  input_h=480 (0x1E0), input_w=1280 (0x500)
WR AGDC_BASE + 0x0C = 0x00000000   // ROI_ORIGIN:  roi_x=0, roi_y=0
WR AGDC_BASE + 0x10 = 0x01E00500   // OUTPUT_SIZE: output_h=480, output_w=1280

// --- 网格 ---
WR AGDC_BASE + 0x14 = 0x00000C10   // MESH_GRID: mesh_rows=12 (0x0C), mesh_cols=16 (0x10)

// --- 格式 ---
WR AGDC_BASE + 0x18 = 0x00000000   // FORMAT_CTRL: NV12 in/out, co-sited

// --- 总线地址 (16B 对齐) ---
WR AGDC_BASE + 0x1C = 0x00001000   // SRC_Y_BASE_ADDR:  合并输入 Y 平面 (示例)
WR AGDC_BASE + 0x20 = 0x00000000   // SRC_UV_BASE_ADDR: 0=连续布局
WR AGDC_BASE + 0x24 = 0x00100000   // DST_Y_BASE_ADDR:  合并输出 Y 平面 (示例)
WR AGDC_BASE + 0x28 = 0x00000000   // DST_UV_BASE_ADDR: 0=连续布局

// --- 行跨度 ---
WR AGDC_BASE + 0x2C = 0x00000500   // SRC_STRIDE: 1280 bytes/row
WR AGDC_BASE + 0x30 = 0x00000500   // DST_STRIDE: 1280 bytes/row

// --- ISP 行缓冲 ---
WR AGDC_BASE + 0x34 = 0x00004646   // ISP_LINE_BUF_CFG: depth=70, y_off=70, uv_off=70

// --- 中断 ---
WR AGDC_BASE + 0x40 = 0x00000001   // INT_MSK: msk_frame_done=1

// ============================================================
// Step 3: 启动帧处理
// ============================================================
WR AGDC_BASE + 0x04 = 0x00000005   // CTRL: enable_rectify=1 + start_frame=1 (SC)

// ============================================================
// Step 4: 等待完成
// ============================================================
// 轮询: while (RD AGDC_BASE + 0x3C & 0x100 == 0);
```

### 寄存器汇总

| 偏移     | 名称             | 配置值         | 说明                                   |
| -------- | ---------------- | -------------- | -------------------------------------- |
| `0x04`   | CTRL             | `0x00000005`   | enable_rectify=1, start_frame=1 (SC)   |
| `0x08`   | INPUT_SIZE       | `0x01E00500`   | input_h=480, input_w=1280              |
| `0x0C`   | ROI_ORIGIN       | `0x00000000`   | 无裁剪                                 |
| `0x10`   | OUTPUT_SIZE      | `0x01E00500`   | output_h=480, output_w=1280            |
| `0x14`   | MESH_GRID        | `0x00000C10`   | rows=12, cols=16                       |
| `0x18`   | FORMAT_CTRL      | `0x00000000`   | NV12 in/out                            |
| `0x1C`   | SRC_Y_BASE_ADDR  | 示例           | 16B 对齐                               |
| `0x20`   | SRC_UV_BASE_ADDR | `0x00000000`   | 连续布局                               |
| `0x24`   | DST_Y_BASE_ADDR  | 示例           | 16B 对齐                               |
| `0x28`   | DST_UV_BASE_ADDR | `0x00000000`   | 连续布局                               |
| `0x2C`   | SRC_STRIDE       | `0x00000500`   | 1280 bytes/row                         |
| `0x30`   | DST_STRIDE       | `0x00000500`   | 1280 bytes/row                         |
| `0x34`   | ISP_LINE_BUF_CFG | `0x00004646`   | 默认 (离线忽略)                        |
| `0x40`   | INT_MSK          | `0x00000001`   | frame_done 中断                        |

---

## 典型使用流程

### 1. 载入 Mesh 表

```c
#include "agdc_mesh_16x12.h"

// 或读取二进制
uint64_t mesh[AGDC_MESH_NODES];
FILE *fp = fopen("agdc_mesh_16x12_36bit_in_u64.bin", "rb");
fread(mesh, sizeof(uint64_t), AGDC_MESH_NODES, fp);
fclose(fp);

// 解码一个节点
uint64_t entry = mesh[addr];
int32_t u_fixed = (int32_t)(entry & 0x3FFFF);
int32_t v_fixed = (int32_t)((entry >> 18) & 0x3FFFF);
// 符号扩展 18-bit → 32-bit
if (u_fixed & 0x20000) u_fixed |= 0xFFFC0000;
if (v_fixed & 0x20000) v_fixed |= 0xFFFC0000;
float u = (float)u_fixed / 32.0f;
float v = (float)v_fixed / 32.0f;

// 判断左右相机: addr 对应的列 ix = addr % AGDC_MESH_COLS
// ix < (AGDC_MESH_COLS/2) → 左路, 否则 → 右路
```

### 2. 仿真激励

```verilog
// Verilog: 读取 YUV 二进制文件 (合并图像, 1280×480)
initial begin
    $readmemh("distorted_nv12_y.bin",  y_buffer);   // 614400 bytes
    $readmemh("distorted_nv12_uv.bin", uv_buffer);  // 307200 bytes
end
```

### 3. 验证输出

```python
import numpy as np

# 读取黄金参考 (1280×480 合并)
golden_y = np.fromfile("golden_y_plane.bin", dtype=np.uint8).reshape(480, 1280)

# 读取硬件输出
hw_output = np.fromfile("hw_output_y.bin", dtype=np.uint8).reshape(480, 1280)

# 按左右路分别评估
for label, sl in [("左路", slice(0, 640)), ("右路", slice(640, 1280))]:
    diff = hw_output[:, sl].astype(np.float32) - golden_y[:, sl].astype(np.float32)
    mae = np.mean(np.abs(diff))
    print(f"{label} MAE vs golden: {mae:.4f}")
```

---

## 重新生成

修改参数后运行：

```
python generate_agdc_stereo.py
```

可配置项（脚本顶部 `MESH_CONFIGS`）：

- 网格密度列表
- `FRAC_BITS`：定点小数位宽
- `OUT_DIR`：输出目录路径
- 双目标定参数（可直接修改脚本中的 M1/M2/D1/D2/R1/R2/P1/P2 矩阵）

---

## 依赖

- Python 3.8+
- numpy
- OpenCV (cv2) — 仅用于 `initUndistortRectifyMap`、图像读写、YUV 转换

---

## 与单目数据集的对比

| 特性         | agdc_test (单目)              | agdc_test_stereo (双目 Online) |
| ------------ | ----------------------------- | ------------------------------ |
| 输入图像     | 1 张 640×480                  | 2 张 640×480 横向拼接 → 1280×480 |
| 相机模型     | 1 组内参                      | 2 组内参 + 立体外参 (R, T)     |
| 矫正方式     | 去畸变 (undistort)            | 立体矫正 (stereoRectify)       |
| 输出         | 去畸变图像                     | 立体矫正 + 极线对齐             |
| Mesh 节点    | 全部单路                       | 左路 [L] / 右路 [R] 分别标注   |
| vspan 分析   | 单路畸变位移                  | 双路独立畸变 + 极线对齐检查     |
| 基线         | N/A                           | 3.343 单位                     |

---

## manifest.json 结构

```json
{
  "description": "AGDC Stereo Mesh Table & Golden Reference — Online Mode",
  "mode": "stereo_online",
  "input": { "left_image": "...", "right_image": "...", "combined_size": [1280, 480] },
  "calibration": {
    "left":  { "camera_matrix": [...], "distortion": [...] },
    "right": { "camera_matrix": [...], "distortion": [...] },
    "stereo": { "R": [...], "T": [...], "baseline": 3.343, ... }
  },
  "format_spec": { "mesh_node_format": "36-bit", "coordinate_format": "u12.5", ... },
  "mesh_tables": {
    "16x12": { "num_nodes": 221, "u_range_float": [...], ... },
    "32x24": { "num_nodes": 825, ... },
    "64x48": { "num_nodes": 3185, ... }
  },
  "yuv_inputs": { "nv12_y": "...", ... },
  "golden_reference": { "y_plane": "...", ... },
  "validation": { ... }
}
```

所有路径均为绝对路径。Agent 可直接解析 JSON 获取所需文件位置。
