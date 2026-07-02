# AGDC Test Data — Image1.tif 标定数据集

> 生成日期：2026-06-29
> 标定工具：MATLAB Calibration Toolbox (Bouguet)
> 标定图像：`Image1.tif` (640×480 棋盘格)

---

## 目录结构

```
agdc_test/
├── README.md                              ← 本文件
├── manifest.json                          ← 结构化索引（供脚本/Agent读取）
│
├── source/                                ← 原始标定图像
│   ├── Image1.tif                         ←   畸变原图 (BGR, 640×480)
│   └── Image_rect1.tif                    ←   MATLAB 矫正结果 (BGR, 640×480)
│
├── mesh/                                  ← AGDC 网格映射表
│   ├── 16x12/                             ←   16×12 tiles, 17×13 = 221 节点
│   │   ├── agdc_mesh_16x12_36bit.hex      ←     SRAM hex (含注释)
│   │   ├── agdc_mesh_16x12_36bit_in_u64.bin ←   64-bit LE binary
│   │   ├── agdc_mesh_16x12_uv_fixed.bin   ←     u/v int32 交织
│   │   └── agdc_mesh_16x12.h              ←     C header (float+fixed)
│   └── 32x24/                             ←   32×24 tiles, 33×25 = 825 节点
│       ├── agdc_mesh_32x24_36bit.hex
│       ├── agdc_mesh_32x24_36bit_in_u64.bin
│       ├── agdc_mesh_32x24_uv_fixed.bin
│       └── agdc_mesh_32x24.h
│
├── input/                                 ← 仿真激励输入 (畸变图 → YUV)
│   ├── nv12/                              ←   YUV420SP (NV12)
│   │   ├── distorted_nv12_y.bin
│   │   └── distorted_nv12_uv.bin
│   ├── nv16/                              ←   YUV422SP (NV16)
│   │   ├── distorted_nv16_y.bin
│   │   └── distorted_nv16_uv.bin
│   └── yuyv/                              ←   YUV422I (YUYV)
│       └── distorted_yuyv.bin
│
├── golden/                                ← 黄金参考输出 (矫正图 → YUV)
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
    ├── diff_analytic_vs_matlab_bi.png     ←   解析法 vs MATLAB (×5)
    ├── diff_analytic_vs_matlab_nn.png     ←   解析法(NN) vs MATLAB (×5)
    ├── golden_rectified_analytic_bi.tif   ←   解析法双线性矫正
    ├── golden_rectified_analytic_nn.tif   ←   解析法最近邻矫正
    ├── reconstructed_mesh_16x12.tif       ←   16×12 网格表重建
    └── reconstructed_mesh_32x24.tif       ←   32×24 网格表重建
```

---

## 标定参数

来源：`相机标定课程/第一章 标定基础知识 code & data/matlab_sample/calib_example/Calib_Results.m`

| 参数     | 符号  | 值                 |
| -------- | ----- | ------------------ |
| 焦距 x   | fx    | 657.4461078692183  |
| 焦距 y   | fy    | 657.8766602560904  |
| 主点 x   | cx    | 303.1853197952834  |
| 主点 y   | cy    | 242.7084811638757  |
| 径向 k1  | kc(1) | -0.255414841834118 |
| 径向 k2  | kc(2) | 0.124449907410458  |
| 切向 p1  | kc(3) | -0.000216975662453 |
| 切向 p2  | kc(4) | 0.000074351611502  |
| 径向 k3  | kc(5) | 0.0                |
| 图像尺寸 | —    | 640 × 480         |

---

## 畸变特征分析 (vspan)

**vspan = v_畸变 − v_矫正**：矫正前后，同一像素点在垂直方向上的行偏移。

该图像为**桶形畸变**（k1 < 0），畸变图四角向内收缩。矫正时 backward mapping 从矫正图反查畸变图坐标，角落像素映射回畸变图中更靠近中心的区域。

### 全图统计

| 指标                   | 值                   | 位置                   |
| ---------------------- | -------------------- | ---------------------- |
| **最大向下偏移** | **+19.74 px**  | 右上角 (639, 0)        |
| **最大向上偏移** | **−19.14 px** | 右下角 (639, 479)      |
| 左上角 (0, 0)          | +17.87 px            |                        |
| 左下角 (479, 0)        | −17.29 px           |                        |
| 中心 (320, 240)        | ≈ 0 px              | 过主点的垂直线偏移为 0 |

### 关键区域

```
v_矫正=0   (顶部):  v_畸变 ∈ [17.9, 19.7]   → Δv ≈ +18~20 px (向下找)
v_矫正=240 (中间):  v_畸变 ≈ 240            → Δv ≈ 0
v_矫正=479 (底部):  v_畸变 ∈ [459.9, 461.7] → Δv ≈ −17~−19 px (向上找)
```

### 对称性

由于主点 cy=242.7 接近图像中心 240，偏移分布近似对称：

- 顶部和底部偏移大小相当（19.7 vs 19.1）
- 左右两侧差异来自切向畸变 p1, p2 的非对称贡献（量级仅 0.0002，影响 < 1 px）

### 硬件设计含义

| 含义                   | 数值                            |
| ---------------------- | ------------------------------- |
| vspan 最大值           | 19.74 px                        |
| AGDC 行缓冲器最小深度  | ≥ 20 行（容纳最远垂直回查）    |
| 网格内 v 跨度 (16×12) | 平均 38.6 px/tile, 最大约 48 px |

---

## AGDC Mesh 表规格

### 映射方向: Backward (rectify → distort)

Mesh 表存储的是**反向映射**：对矫正后图像的每个网格节点 `(u_out, v_out)`，
给出其在畸变原图中的来源坐标 `(u_in, v_in)`。

```
AGDC 硬件数据流:

  矫正图 (输出)                         畸变图 (输入)
  ┌────────────────┐                  ┌────────────────┐
  │ u_out = 0      │ ─── 查表 ──────→ │ u_in = 14.79   │
  │ v_out = 0      │     node(0,0)    │ v_in = 7.85     │
  │                │                  │                │
  │ u_out = 320    │ ─── 插值 ──────→ │ u_in ≈ 314     │
  │ v_out = 240    │   4邻域节点       │ v_in ≈ 240     │
  └────────────────┘                  └────────────────┘

  处理流程:
    逐行扫描输出像素 (u_out, v_out)
    → 查 AGDC 网格表 + 双线性插值 → 得 (u_in, v_in)
    → 从畸变图 (u_in, v_in) 取像素 → 填入输出位置
```

验证示例 —— 节点 `(0,0)`，桶形畸变 (k1<0) 使畸变图角落内缩，
矫正图角落在畸变图中对应更内侧像素：

```
node(00,00):  u_in=14.79  v_in=7.85   ← 矫正图(0,0)来自畸变图(14.79, 7.85)
node(16,00):  u_in=619.50 v_in=7.85   ← 矫正图(639,0)来自畸变图(619.50, 7.85)
```

若为正向 (distort→rectify)，(0,0) 会映射到矫正图负坐标区域，但表中存的是正值 → 确认为反向。

### 数据格式 (每个节点 36-bit)

```
┌──────────────────┬──────────────────┐
│   v[17:0]        │   u[17:0]        │
│   bits [35:18]   │   bits [17:0]    │
└──────────────────┴──────────────────┘
```

| 字段           | 位宽             | 格式         | 整数位 | 小数位 | 范围                 |
| -------------- | ---------------- | ------------ | ------ | ------ | -------------------- |
| u              | 18-bit           | signed u12.5 | 12     | 5      | [-4096, +4095.96875] |
| v              | 18-bit           | signed u12.5 | 12     | 5      | [-4096, +4095.96875] |
| **总计** | **36-bit** | —           | —     | —     | —                   |

- **1 LSB** = 1/32 = 0.03125 pixel
- **u, v** = 畸变图像中的浮点坐标 × 32，四舍五入取整
- **负值**用二进制补码表示

### SRAM 寻址

```
addr = iy × (mesh_cols + 1) + ix
```

| 网格   | 瓦片数 | 网格点 (cols+1) × (rows+1) | 节点总数 |
| ------ | ------ | --------------------------- | -------- |
| 16×12 | 16×12 | 17×13                      | 221      |
| 32×24 | 32×24 | 33×25                      | 825      |

### Mesh 表文件格式说明

#### 1. `*.hex` — SRAM 初始化文件 (含注释)

```
@0000  // node(00,00)  u_fixed=0x01DA3( 14.7936)  v_fixed=0x000FB(  7.8538)  packed=0x003F6E8E
@0001  // node(01,00)  u_fixed=0x03125( 54.7901)  v_fixed=0x00104(  8.1570)  packed=0x00041149
```

- 每行格式：`@<addr>  // node(<ix>,<iy>)  u_fixed=<hex>(<float>)  v_fixed=<hex>(<float>)  packed=<36bit_hex>`
- `packed` 值 = `(v_fixed << 18) | u_fixed`，低位 36 bit 有效
- 可用 `$readmemh` 直接载入 Verilog SRAM 模型

#### 2. `*_36bit_in_u64.bin` — 64-bit Little-Endian 二进制

- 每个节点占 8 字节 (uint64_t LE)
- 节点数 = `(mesh_cols+1) × (mesh_rows+1)`
- 直接 `fread(buf, 8, num_nodes, fp)` 读取

#### 3. `*_uv_fixed.bin` — u/v 交织 int32 二进制

- 每个节点 2 个 int32 LE：[u_fixed, v_fixed, u_fixed, v_fixed, ...]
- 条目数 = 节点数 × 2

#### 4. `*.h` — C header

- 包含 `agdc_mesh` (uint64_t packed)、`agdc_mesh_u_float`、`agdc_mesh_v_float` 三个数组
- 宏定义：`AGDC_MESH_COLS`, `AGDC_MESH_ROWS`, `AGDC_MESH_NODES`, `AGDC_IMG_WIDTH`, `AGDC_IMG_HEIGHT`, `AGDC_FRAC_BITS`

---

## YUV 图像数据规格

### 颜色空间参数

- 标准：BT.601 (SD)
- Y = 0.299R + 0.587G + 0.114B
- U = -0.169R - 0.331G + 0.500B + 128
- V = 0.500R - 0.419G - 0.081B + 128
- 位深：8-bit，范围 [0, 255]

### 三种子采样格式

#### NV12 (YUV420SP)

```
Y plane:  W×H     (640×480 = 307200 bytes)
UV plane: W×H/2   (640×240 = 153600 bytes) — 交错 UVUVUV...
子采样:   2×2 块平均
布局:     YYYYYYYY...
         UVUVUVUV...
```

#### NV16 (YUV422SP)

```
Y plane:  W×H     (640×480 = 307200 bytes)
UV plane: W×H     (640×480 = 307200 bytes) — 交错 UVUVUV...
子采样:   水平每 2 像素平均
布局:     YYYYYYYY...
         UVUVUVUV...
```

#### YUYV (YUV422I)

```
打包:     W×2 × H  (1280×480 = 614400 bytes)
布局:     Y0 U0 Y1 V0  Y2 U1 Y3 V1 ...
子采样:   水平每 2 像素平均
```

### 文件分类

| 用途                      | 文件前缀                  | 内容                                        |
| ------------------------- | ------------------------- | ------------------------------------------- |
| **仿真激励输入**    | `distorted_*`           | Image1.tif (畸变原图) 的 YUV 格式           |
| **黄金参考输出**    | `golden_*`              | Image_rect1.tif (MATLAB 矫正图) 的 YUV 格式 |
| **独立 Y/U/V 平面** | `golden_y_plane.bin` 等 | 矫正图逐像素 Y/U/V，供逐点比对              |

---

## AGDC 寄存器配置

### 本测试集的推荐寄存器配置


以 **16×12 tiles、NV12 格式、离线模式** 为例（与 `AGDC_register_spec.md` 严格对齐）。
SRAM 基地址、帧缓冲地址为示例值，实际按系统内存布局调整。

```
// ============================================================
// Step 1: 初始化 — 确保模块禁用
// ============================================================
WR AGDC_BASE + 0x04 = 0x00000000   // CTRL: enable_rectify=0, 禁用模块

// ============================================================
// Step 2: 配置寄存器组 (INT_RAW.busy=0 期间写入)
// ============================================================

// --- 帧尺寸 ---
WR AGDC_BASE + 0x08 = 0x01E00280   // INPUT_SIZE:  input_h=480 (0x1E0), input_w=640 (0x280), step4
WR AGDC_BASE + 0x0C = 0x00000000   // ROI_ORIGIN:  roi_x=0, roi_y=0 (全局坐标域起点)
WR AGDC_BASE + 0x10 = 0x01E00280   // OUTPUT_SIZE: output_h=480, output_w=640, step4

// --- 网格 ---
WR AGDC_BASE + 0x14 = 0x00000C10   // MESH_GRID: mesh_rows=12 (0x0C), mesh_cols=16 (0x10)
                                    //   实际节点数 = (16+1) × (12+1) = 221

// --- 格式 ---
WR AGDC_BASE + 0x18 = 0x00000000   // FORMAT_CTRL:
                                    //   cfg_input_format  = 00 (NV12)
                                    //   cfg_output_format = 00 (NV12)
                                    //   cfg_chroma_siting = 00 (co-sited)
                                    //   所有 swap 位 = 0

// --- 总线地址 (16B 对齐, 低4位硬件强制为0) ---
WR AGDC_BASE + 0x1C = 0x00001000   // SRC_Y_BASE_ADDR:  输入 Y 平面 DRAM 地址 (示例)
WR AGDC_BASE + 0x20 = 0x00000000   // SRC_UV_BASE_ADDR: 0=连续布局, UV=Y + input_h×stride
WR AGDC_BASE + 0x24 = 0x00100000   // DST_Y_BASE_ADDR:  输出 Y 平面 DRAM 地址 (示例)
WR AGDC_BASE + 0x28 = 0x00000000   // DST_UV_BASE_ADDR: 0=连续布局

// --- 行跨度 ---
WR AGDC_BASE + 0x2C = 0x00000280   // SRC_STRIDE: 640 bytes/row
WR AGDC_BASE + 0x30 = 0x00000280   // DST_STRIDE: 640 bytes/row

// --- ISP 行缓冲 (离线模式忽略, 保留默认值) ---
WR AGDC_BASE + 0x34 = 0x00004646   // ISP_LINE_BUF_CFG: depth=70, y_off=70, uv_off=70

// --- 中断 ---
WR AGDC_BASE + 0x40 = 0x00000001   // INT_MSK: msk_frame_done=1 (仅使能帧完成中断)

// ============================================================
// Step 3: 锁存配置并启动帧处理
// ============================================================
WR AGDC_BASE + 0x04 = 0x00000005   // CTRL: enable_rectify=1 (bit0) + start_frame=1 (bit2, SC)
                                    //   start_frame 硬件自动清零, 同时锁存 cfg→work

// ============================================================
// Step 4: 等待完成 (轮询或中断)
// ============================================================
// 轮询: while (RD AGDC_BASE + 0x3C & 0x100 == 0);   // 等 INT_RAW.busy=0
// 中断: ISR 读 INT_CLR (0x44) → 确认 frame_done → 写回清除
```

**寄存器来源对照**（与 `AGDC_register_spec.md` 完全一致）：

| 偏移     | 名称             | 配置值         | 说明                                 |
| -------- | ---------------- | -------------- | ------------------------------------ |
| `0x04` | CTRL             | `0x00000005` | enable_rectify=1, start_frame=1 (SC) |
| `0x08` | INPUT_SIZE       | `0x01E00280` | input_h=480, input_w=640             |
| `0x0C` | ROI_ORIGIN       | `0x00000000` | 无裁剪                               |
| `0x10` | OUTPUT_SIZE      | `0x01E00280` | output_h=480, output_w=640           |
| `0x14` | MESH_GRID        | `0x00000C10` | rows=12, cols=16                     |
| `0x18` | FORMAT_CTRL      | `0x00000000` | NV12 in/out                          |
| `0x1C` | SRC_Y_BASE_ADDR  | 示例           | 16B 对齐                             |
| `0x20` | SRC_UV_BASE_ADDR | `0x00000000` | 连续布局                             |
| `0x24` | DST_Y_BASE_ADDR  | 示例           | 16B 对齐                             |
| `0x28` | DST_UV_BASE_ADDR | `0x00000000` | 连续布局                             |
| `0x2C` | SRC_STRIDE       | `0x00000280` | 640                                  |
| `0x30` | DST_STRIDE       | `0x00000280` | 640                                  |
| `0x34` | ISP_LINE_BUF_CFG | `0x00004646` | 默认 (离线忽略)                      |
| `0x40` | INT_MSK          | `0x00000001` | frame_done 中断                      |

---

## 精度验证结果

| 对比项                    | MAE       | MaxError | 说明                     |
| ------------------------- | --------- | -------- | ------------------------ |
| 解析法 vs OpenCV map      | 7×10⁻⁶ | —       | 畸变模型实现正确         |
| 解析法 Bilinear vs MATLAB | 0.084     | 8        | 极微小差异，来自插值精度 |
| u12.5 量化误差            | ≤0.016   | < ½ LSB | 定点格式精度充足         |

---

## 典型使用流程

### 1. 载入 Mesh 表

```c
// 读取 hex 文件
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
```

### 2. 仿真激励

```verilog
// Verilog: 读取 YUV 二进制文件
initial begin
    $readmemh("distorted_nv12_y.bin",  y_buffer);
    $readmemh("distorted_nv12_uv.bin", uv_buffer);
end
```

### 3. 验证输出

```python
import numpy as np

# 读取黄金参考
golden_y = np.fromfile("golden_y_plane.bin", dtype=np.uint8).reshape(480, 640)

# 读取硬件输出
hw_output = np.fromfile("hw_output_y.bin", dtype=np.uint8).reshape(480, 640)

# 逐像素对比
diff = hw_output.astype(np.float32) - golden_y.astype(np.float32)
mae = np.mean(np.abs(diff))
print(f"MAE vs golden: {mae:.4f}")
```

---

## 重新生成

修改参数后运行：

```
python generate_agdc_golden.py
```

可配置项（脚本顶部）：

- `MESH_CONFIGS`：网格密度列表
- `FRAC_BITS`：定点小数位宽
- `OUT_DIR`：输出目录路径

---

## 依赖

- Python 3.8+
- numpy
- OpenCV (cv2) — 仅用于读取/写入图像和验证对比；**Mesh 表核心计算不依赖 OpenCV 畸变函数**

---

## manifest.json 结构

```json
{
  "calibration": { "fc": [...], "cc": [...], "kc": [...] },
  "format_spec": {
    "mesh_node_format": "36-bit = {v[17:0], u[17:0]}",
    "coordinate_format": "u12.5 signed",
    "sram_addressing": "addr = iy * (mesh_cols+1) + ix",
    "frac_bits": 5
  },
  "mesh_tables": {
    "16x12": { "grid_cols": 17, "grid_rows": 13, "num_nodes": 221, ... },
    "32x24": { "grid_cols": 33, "grid_rows": 25, "num_nodes": 825, ... }
  },
  "yuv_inputs": { "nv12_y": "...", "nv12_uv": "...", ... },
  "golden_reference": { "nv12_y": "...", ... },
  "validation": { ... }
}
```

所有路径均为绝对路径。Agent 可直接解析 JSON 获取所需文件位置。
