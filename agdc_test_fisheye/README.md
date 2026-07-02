# AGDC Test Data — VMRImage1.jpg 鱼眼标定数据集

> 生成日期：2026-06-30  
> 标定工具：OCamCalib v3.0 (Scaramuzza Omnidirectional Camera Model)  
> 标定图像：`VMRImage1.jpg` (1024×768 鱼眼)

---

## 目录结构

```
agdc_test_fisheye/
├── README.md
├── manifest.json
├── source/
│   └── VMRImage1.jpg                     ← 原始鱼眼图像 (1024×768)
├── mesh/
│   ├── 16x12/                             ←   16×12 tiles (221节点)
│   └── 32x24/                             ←   32×24 tiles (825节点)
├── input/                                 ←   仿真激励 (鱼眼→YUV)
│   ├── nv12/
│   ├── nv16/
│   └── yuyv/
├── golden/                                ←   黄金参考 (透视矫正→YUV)
│   ├── nv12/
│   ├── nv16/
│   ├── yuyv/
│   ├── golden_y_plane.bin
│   ├── golden_u_plane.bin
│   └── golden_v_plane.bin
└── verify/
    ├── golden_rectified_perspective.tif   ←   黄金参考矫正图像
    ├── reconstructed_mesh_16x12.tif       ←   16×12 网格重建
    └── reconstructed_mesh_32x24.tif       ←   32×24 网格重建
```

---

## 标定参数

来源：`第七章/Scaramuzza_OCamCalib_v3.0_win/get_ocam_model.m`

### Scaramuzza 全向模型

鱼眼相机使用 Scaramuzza 多项式模型，与 pinhole 模型的本质区别：

```
Pinhole (Image1):   像素 → 归一化坐标 → 加畸变 → 像素     (Brown-Conrady 5参数)
Fisheye (VMRImage1): 像素 → 仿射校正 → 多项式 Z=f(ρ) → 3D射线     (Scaramuzza 多项式)
```

**正向 (cam2world)** — 像素 → 3D 单位球面射线：
```
1. [u'; v'] = A⁻¹ · ([u; v] - [xc; yc])
2. ρ = sqrt(u'² + v'²)
3. Z = polyval(ss, ρ) = a₀ + a₁·ρ + a₂·ρ² + a₃·ρ³ + a₄·ρ⁴
4. ray = normalize([u'; v'; Z])
```

**逆向 (world2cam)** — 3D 射线 → 像素：
```
1. θ = atan(Z / sqrt(X²+Y²))                    (射线与XY平面的夹角)
2. ρ = polyval(pol, θ) = polyfit(θ, ρ, 5)       (逆多项式)
3. x = X/√(X²+Y²) · ρ,  y = Y/√(X²+Y²) · ρ
4. [u; v] = A · [x; y] + [xc; yc]
```

### 参数值

| 参数 | 符号 | 值 | 来源 |
|------|------|-----|------|
| 多项式系数 | `ss` | `[-140.51, 0, 2.717e-4, 5.257e-6, -1.068e-9]` | `get_ocam_model.m` |
| 图像中心 x | `xc` | 512.0 | 推算 (1024/2) |
| 图像中心 y | `yc` | 384.0 | 推算 (768/2) |
| 标定半径 | — | 498 px | `get_ocam_model.m` 归一化基准 |
| 仿射 c, d, e | `c,d,e` | 1.0, 0, 0 | `calibration.m` 默认值 |
| 入射角范围 | θ_max | 45.7° | f(498)=510.5 → atan(498/510.5) |
| 输入尺寸 | — | 1024 × 768 | |
| 输出尺寸 | — | 640 × 480 | |
| 虚拟相机距离 | fc | 4.0 | 越小越广角 |

> ⚠️ **(xc, yc)** 和 **(c,d,e)** 没有显式标定结果文件 (Omni_Calib_Results.mat 不存在)，
> 使用几何中心 + 默认仿射。若需精确值，需在 MATLAB 中重新标定。

### 逆多项式 (θ → ρ)

| 系数 | 值 |
|------|-----|
| b₀ | ≈ 0 |
| b₁ | ≈ 500 |
| ... | 5阶最小二乘拟合，max 误差 < 0.27 px |

---

## AGDC Mesh 表规格

### 映射方向: Backward (rectify → fisheye)

与 pinhole 版本一致，存储**反向映射**：对透视矫正图像的每个节点 `(u_out, v_out)`，
给出其在鱼眼原图中的来源坐标 `(u_in, v_in)`。

### 数据格式 (每节点 36-bit)

```
┌──────────────────┬──────────────────┐
│   v[17:0]        │   u[17:0]        │
│   bits [35:18]   │   bits [17:0]    │
└──────────────────┴──────────────────┘
```

- **u12.5 signed**: 1符号 + 12整数 + 5小数，1 LSB = 1/32 px
- **SRAM 寻址**: `addr = iy × (mesh_cols+1) + ix`

### 网格坐标范围

| 网格 | u 范围 | v 范围 | 网格节点位置 |
|------|--------|--------|---------|
| 16×12 | [346.8, 676.8] | [193.3, 574.4] | 均匀 17×13 = 221 节点, tile=40×40 px |
| 32×24 | [346.8, 676.8] | [193.3, 574.4] | 均匀 33×25 = 825 节点, tile=20×20 px |

> **注意**: 当前 FC=4.0 下，所有 mesh 节点均落在鱼眼图像 [0, 1024] × [0, 768] 范围内，
> 有效比例 100%。网格节点位置与 AGDC tile 边界严格对齐（`linspace(0, W_OUT, grid_cols)`）。

---

## 映射方向差异与硬件约束

### 与 pinhole (Image1) 的关键差异

| | Pinhole Image1 | Fisheye VMRImage1 |
|---|---|---|
| 输入尺寸 | 640×480 | 1024×768 |
| 输出尺寸 | 640×480 (同输入) | 640×480 (透视投影) |
| 有效像素比例 | ~100% | 100% (FC=4.0 下全有效) |
| u12.5 覆盖 | 全部正值 (0~640) | 全部正值 (347~677) |
| 逐行 v_in 极差 | ~20 px (行内源垂直跨度) | **381 px** (行内源垂直跨度) |
| 逆多项式来源 | 解析畸变公式 | 数值拟合 (5阶, 误差<0.27px) |
| 坐标约定 | u↔u_out, v↔v_out | axis swap: u↔v_out, v↔u_out |

### 在线模式约束

```
单行 v_in 极差 max = 381 px >> line_buf_depth (典型值 70)
```

**根本原因**: Scaramuzza 模型的 axis swap 约定使 `v_in` 主要取决于 `u_out`（输出列）。
同一输出行从左到右 640 列，对应 v_in ∈ [193, 574]，固定跨度 381 px。
这是 **单行内** 的垂直跨度，无法通过纵向 slice 降低。

```
逐行 vspan (相邻行间位移) = 0.17 px  ← 不是瓶颈!
单行内 v_in 极差          = 381 px  ← 真正的瓶颈!
```

**结论**: 离线模式必须。在线模式不可行（单行需缓存 381 行源数据）。

---

## 本测试集的推荐寄存器配置

以 **16×12 tiles、NV12 格式、离线模式** 为例（与 `AGDC_register_spec.md` 严格对齐）。

```
// ============================================================
// Step 1: 初始化
// ============================================================
WR AGDC_BASE + 0x04 = 0x00000000   // CTRL: enable_rectify=0

// ============================================================
// Step 2: 配置寄存器组 (INT_RAW.busy=0 期间)
// ============================================================

// --- 帧尺寸 (输入=鱼眼图, 输出=透视矫正图) ---
WR AGDC_BASE + 0x08 = 0x03000400   // INPUT_SIZE:  input_h=768 (0x300), input_w=1024 (0x400)
WR AGDC_BASE + 0x0C = 0x00000000   // ROI_ORIGIN:  roi_x=0, roi_y=0
WR AGDC_BASE + 0x10 = 0x01E00280   // OUTPUT_SIZE: output_h=480, output_w=640

// --- 网格 ---
WR AGDC_BASE + 0x14 = 0x00000C10   // MESH_GRID: mesh_rows=12, mesh_cols=16

// --- 格式 ---
WR AGDC_BASE + 0x18 = 0x00000000   // FORMAT_CTRL: NV12 in/out

// --- 总线地址 (16B对齐, 低4位硬件强制为0) ---
WR AGDC_BASE + 0x1C = <src_y_addr>   // SRC_Y_BASE_ADDR: 输入 Y 平面 (1024×768)
WR AGDC_BASE + 0x20 = <src_uv_addr>  // SRC_UV_BASE_ADDR: = <src_y_addr> + 0x000C0000 (连续布局)
WR AGDC_BASE + 0x24 = <dst_y_addr>   // DST_Y_BASE_ADDR: 输出 Y 平面 (640×480)
WR AGDC_BASE + 0x28 = <dst_uv_addr>  // DST_UV_BASE_ADDR: = <dst_y_addr> + 0x0004B000 (连续布局)

// --- 行跨度 ---
WR AGDC_BASE + 0x2C = 0x00000400   // SRC_STRIDE: 1024 bytes/row
WR AGDC_BASE + 0x30 = 0x00000280   // DST_STRIDE: 640 bytes/row

// --- ISP 行缓冲 (离线模式忽略) ---
WR AGDC_BASE + 0x34 = 0x00004646   // ISP_LINE_BUF_CFG: 默认

// --- 中断 ---
WR AGDC_BASE + 0x40 = 0x00000001   // INT_MSK: frame_done

// ============================================================
// Step 3: 启动
// ============================================================
WR AGDC_BASE + 0x04 = 0x00000005   // CTRL: enable_rectify=1 + start_frame=1 (SC)

// Step 4: 等待 busy=0 或 frame_done 中断
```

### Mesh 表加载注意事项

**必须加载 `36bit_in_u64.bin`**，不是 `uv_fixed.bin`：

| 文件 | 格式 | 用途 |
|------|------|------|
| `agdc_mesh_16x12_36bit_in_u64.bin` | uint64 LE, 36-bit packed `{v[17:0], u[17:0]}` | **AGDC SRAM 加载** |
| `agdc_mesh_16x12_uv_fixed.bin` | int32 pairs (u, v) | 备选/调试用 |

> ⚠️ 若误加载 `uv_fixed.bin` 并按 36-bit 解析：u 坐标碰巧正确，v 坐标变为垃圾值（震荡于 ±3584）。
> 这将导致每个 tile 使用完全错误的源图像行 → **分块严重、错位**。

### Slice / ROI 降低行缓冲需求分析

若需在线模式或减小 DDR 带宽，可配合 slice + ROI 宽度裁剪：

| ROI 宽度 | 单行 v_in 极差 | line_buf≤70 时最大 slice_h | passes |
|---------|-------------|--------------------------|--------|
| 640 (全宽) | 381 px | 不可行 | — |
| 320 | 190 px | 不可行 | — |
| 160 | 89 px | 32 行 | 15 |
| 120 | ~70 px | 40 行 | 12 |

> **关键**: 仅靠纵向 slice 无效（单行 v_in 极差不变）。必须同时缩小 **ROI 宽度** 才能降低行缓冲需求。

**与 pinhole 配置的关键差异**：

| 寄存器 | Pinhole (Image1) | Fisheye (VMRImage1) | 差异原因 |
|--------|------------------|---------------------|---------|
| `INPUT_SIZE` | `0x01E00280` | `0x03000400` | 输入 1024×768 vs 640×480 |
| `SRC_STRIDE` | `0x00000280` | `0x00000400` | 输入行宽 1024 vs 640 |
| `SRC_UV_BASE_ADDR` | 连续布局 | `SRC_Y_BASE + 0xC0000` | Y 平面 786432 bytes |
| `DST_UV_BASE_ADDR` | 连续布局 | `DST_Y_BASE + 0x4B000` | Y 平面 307200 bytes |
| 在线模式可行性 | 可行 (行内v极差≈20) | **不可行** (行内v极差=381) | axis swap 导致 |
| slice 需求 | 不需要 | **强烈推荐** (离线 + ROI 宽度裁剪) | 行内跨度 381px |

---

## 精度验证

| 对比项 | 值 | 说明 |
|--------|-----|------|
| 逆多项式拟合误差 | max 0.27 px | 5阶最小二乘 |
| u12.5 量化误差 | ≤ 0.016 px | < ½ LSB |
| Mesh 16×12 vs 全精度 | MAE=5.50, MaxErr=189 | 网格插值+NN采样 (验证用) |
| Mesh 32×24 vs 全精度 | MAE=4.27, MaxErr=186 | 加倍密度精度提升 |

> 验证脚本使用 nearest-neighbor 采样，MAE/MaxErr 不代表 AGDC 实际输出质量
> （AGDC 使用双线性插值，精度应更高）。网格表本身精度充足 (u12.5 量化 < 0.016px)。

---

## 多分辨率配置

source 目录下有三张同场景不同分辨率的鱼眼图像。对应数据集已生成到独立目录：

| 输入 | 输出 | 缩放 | 输出目录 | u_in 范围 | v_in 范围 | 单行 v_in 极差 | 在线 |
|------|------|------|---------|-----------|-----------|--------------|------|
| 1024×768 | **640×480** | 1.000 | `..._1024x768/` | [346.8, 676.8] | [193.3, 574.4] | 381 px | 不可行 |
| 400×300 | **256×192** | 0.391 | `..._400x300/` | [135.5, 264.2] | [75.5, 224.2] | 149 px | 不可行 |
| 200×150 | **128×96** | 0.195 | `..._200x150/` | [67.7, 131.9] | [37.8, 112.0] | 74 px | 临界 |

> **关键**: 入射角 45.7° 在所有分辨率下保持一致（与图像缩放无关的物理属性）。
> 单行 v_in 极差随分辨率降低而降低：200×150 时仅 74 px，接近 line_buf=70，
> 配合小幅度 ROI 宽度裁剪即可实现在线模式。

### 各分辨率寄存器配置差异

输出尺寸统一为 640×480，FC=4.0。仅以下寄存器随输入分辨率变化：

| 寄存器 | 1024×768 → 640×480 | 400×300 → 256×192 | 200×150 → 128×96 |
|--------|---------------------|--------------------|--------------------|
| `INPUT_SIZE` | `0x03000400` | `0x012C0190` | `0x009600C8` |
| `OUTPUT_SIZE` | `0x01E00280` | `0x00C00100` | `0x00600080` |
| `SRC_STRIDE` | `0x400` (1024) | `0x190` (400) | `0xC8` (200) |
| `DST_STRIDE` | `0x280` (640) | `0x100` (256) | `0x80` (128) |

> 详细寄存器配置见各输出目录下的 README.md。

---

## 重新生成

```
python generate_agdc_fisheye.py              # 仅 1024×768 (当前目录)
python generate_agdc_fisheye_multiscale.py    # 全部 3 个分辨率
```

可调参数（脚本顶部）：
- `FC`：虚拟相机距离 (越小越广角，当前 4.0)
- `W_OUT, H_OUT`：输出透视图像尺寸
- `MESH_CONFIGS`：网格密度
- `XC, YC`：图像中心（当前为几何中心推算值）

---

## manifest.json 结构

```json
{
  "model": "Scaramuzza Omnidirectional Camera Model",
  "parameters": {
    "ss": [-140.51, 0, 2.717e-4, ...],
    "xc": 512.0, "yc": 384.0,
    "c": 1.0, "d": 0.0, "e": 0.0,
    "pol_coeffs_fitted": [...],
    "theta_max_deg": 44.3
  },
  "image": {
    "input_size": [1024, 768],
    "output_size": [640, 480],
    "virtual_fc": 4.0
  },
  "centroid_estimation_note": "几何中心推算，非显式标定值"
}
```
