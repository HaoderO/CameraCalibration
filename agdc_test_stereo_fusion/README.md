# AGDC Test Data — 双目条纹融合数据集 v3 (Stripe Mode)

> 生成日期：2026-07-01
> 生成脚本：`generate_agdc_stereo_fusion.py` v3

---

## 版本演进

| 版本 | 方案 | 问题 |
|------|------|------|
| v1 | 棋盘格 32×32 px | tile 40px ≠ checker 32px → 大部分 tile 跨相机 |
| v2 | 棋盘格 40×40 / 80×80 | 共享角节点在相邻格中属不同相机，无法同时服务两个 tile |
| **v3** | **水平条纹 40px** | 条纹行边界与 tile 行天然对齐，但边界 tile 仍跨相机（见下） |

---

## v3 方案: 水平条纹交替

### 原理

```
条纹 0 (y=0..39):  全部采样左路矫正映射 -> 合并图左半  [0, 640)
条纹 1 (y=40..79): 全部采样右路矫正映射 -> 合并图右半 [640, 1280)
条纹 2 (y=80..119):全部采样左路矫正映射 -> ...
...
```

输出 640×480，每 40 行切换一次左右路。

### 关键验证

| 验证项 | 结果 |
|--------|------|
| Golden reference 条纹行 vs 纯左路矫正 | **MAE = 0.00** (完全一致) |
| Golden reference 条纹行 vs 纯右路矫正 | MAE = 5.65 (差异来自 OOB 区域处理) |
| OOB 像素占比 | **13.0%** (洋红色标记) |
| Mesh 节点相机归属一致性 | 同行节点同相机 → 水平插值安全 ✓ |

### Mesh 表与插值限制

**Golden reference 是正确的** — 每像素独立选择左/右路，无跨相机混合。

**Mesh 重建图像在条纹边界处有插值伪影** — 原因：
1. 条纹边界 (y=40, 80, ...) 处的 tile 跨越两个条纹
2. 该 tile 的上下角节点属不同相机
3. 双线性插值在垂直方向混合了不同相机的坐标

这是**所有交替相机模式的数学必然**（共享边界节点只能存一个坐标值）。两个解决方案：
- **方案 A** (推荐): 使用 Golden reference 验证硬件输出；Mesh 表用于生成合理插值
- **方案 B**: 每个 mesh 密度使用匹配的条纹高度（16×12→40px, 32×24→20px, 64×48→10px），可消除同密度下的跨相机插值

---

## 目录结构

```
agdc_test_stereo_fusion/
├── README.md
├── manifest.json
├── source/
│   └── combined_input.jpg                 ← left01+right01 横向拼接 (1280×480)
├── mesh/
│   ├── 16x12/  (17×13=221 nodes, tile=40×40)
│   ├── 32x24/  (33×25=825 nodes, tile=20×20)
│   └── 64x48/  (65×49=3185 nodes, tile=10×10)
├── input/    ← 合并畸变图 YUV (NV12/NV16/YUYV, 1280×480)
├── golden/   ← 条纹融合图 YUV (NV12/NV16/YUYV, 640×480)
└── verify/
    ├── golden_fusion_stripe.tif            ← 条纹融合黄金参考 (640×480, OOB=洋红)
    ├── golden_fusion_stripe_grid.tif       ← 叠加条纹边界线
    ├── left_rectified.tif                  ← 纯左路矫正 (对照, OOB=洋红)
    ├── right_rectified.tif                 ← 纯右路矫正 (对照, OOB=洋红)
    └── reconstructed_fusion_*.tif          ← Mesh 表重建 (有边界插值伪影)
```

---

## 双目标定参数

| 参数 | 左相机 | 右相机 |
|------|--------|--------|
| fx, fy | 533.99, 528.71 | 533.99, 528.71 |
| cx, cy | 328.39, 236.84 | 313.77, 241.87 |
| k1, k2 | -0.259, -0.126 | -0.263, -0.012 |
| 矫正 fx=fy | 439.65 | 439.65 |
| 基线 | 3.343 单位 | |

---

## AGDC 寄存器配置 (Stripe Fusion)

```
// 输入: 1280×480 合并, 输出: 640×480 条纹融合
WR AGDC + 0x08 = 0x01E00500  // INPUT_SIZE: h=480, w=1280
WR AGDC + 0x10 = 0x01E00280  // OUTPUT_SIZE: h=480, w=640  (vs online mode 1280)
WR AGDC + 0x14 = 0x00000C10  // MESH_GRID: 16x12
WR AGDC + 0x2C = 0x00000500  // SRC_STRIDE: 1280
WR AGDC + 0x30 = 0x00000280  // DST_STRIDE: 640  (vs online mode 1280)
WR AGDC + 0x04 = 0x00000005  // start
```

## 重新生成

```bash
python generate_agdc_stereo_fusion.py
```

配置项：`STRIPE_HEIGHT` (默认 40px)、`MESH_CONFIGS`、标定矩阵。
