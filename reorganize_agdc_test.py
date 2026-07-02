"""Reorganize agdc_test into categorized subdirectories."""
import os, json, shutil
from pathlib import Path

ROOT = Path(r"d:\Clone\CameraCalibration\agdc_test")

# ---- 1. Plan: source → target subdirs ----
PLAN = {
    "source": ["Image1.tif", "Image_rect1.tif"],
    "mesh/16x12": [
        "agdc_mesh_16x12_36bit.hex", "agdc_mesh_16x12_36bit_in_u64.bin",
        "agdc_mesh_16x12_uv_fixed.bin", "agdc_mesh_16x12.h",
    ],
    "mesh/32x24": [
        "agdc_mesh_32x24_36bit.hex", "agdc_mesh_32x24_36bit_in_u64.bin",
        "agdc_mesh_32x24_uv_fixed.bin", "agdc_mesh_32x24.h",
    ],
    "input/nv12":  ["distorted_nv12_y.bin", "distorted_nv12_uv.bin"],
    "input/nv16":  ["distorted_nv16_y.bin", "distorted_nv16_uv.bin"],
    "input/yuyv":  ["distorted_yuyv.bin"],
    "golden/nv12": ["golden_nv12_y.bin", "golden_nv12_uv.bin"],
    "golden/nv16": ["golden_nv16_y.bin", "golden_nv16_uv.bin"],
    "golden/yuyv": ["golden_yuyv.bin"],
    "golden":       ["golden_y_plane.bin", "golden_u_plane.bin", "golden_v_plane.bin"],
    "verify": [
        "diff_analytic_vs_matlab_bi.png", "diff_analytic_vs_matlab_nn.png",
        "golden_rectified_analytic_bi.tif", "golden_rectified_analytic_nn.tif",
        "reconstructed_mesh_16x12.tif", "reconstructed_mesh_32x24.tif",
    ],
}

# ---- 2. Move files ----
moves = []  # (old_relpath, new_relpath)
for subdir, files in PLAN.items():
    dst_dir = ROOT / subdir
    dst_dir.mkdir(parents=True, exist_ok=True)
    for fname in files:
        src = ROOT / fname
        dst = dst_dir / fname
        if src.exists():
            shutil.move(str(src), str(dst))
            moves.append((fname, str(Path(subdir) / fname)))
            print(f"  {fname}  →  {subdir}/{fname}")

# ---- 3. Update manifest.json ----
manifest_path = ROOT / "manifest.json"
with open(manifest_path, "r", encoding="utf-8") as f:
    m = json.load(f)

# Build a filename → new_path map
path_map = dict(moves)

def fix_path(old):
    """Map an old absolute path ending in filename to new location."""
    if not old:
        return old
    # Extract filename from old path
    fname = os.path.basename(old)
    if fname in path_map:
        return str((ROOT / path_map[fname]).resolve())
    return old

# Fix all paths in manifest
if "yuv_inputs" in m:
    for k, v in m["yuv_inputs"].items():
        m["yuv_inputs"][k] = fix_path(v)
if "golden_reference" in m:
    for k, v in m["golden_reference"].items():
        m["golden_reference"][k] = fix_path(v)
if "mesh_tables" in m:
    for mesh_name, info in m["mesh_tables"].items():
        for k in ["hex_file", "bin64_file", "uv_interleaved_file", "c_header"]:
            if k in info:
                info[k] = fix_path(info[k])
if "input_image" in m:
    m["input_image"] = fix_path(m["input_image"])
if "reference_image" in m:
    m["reference_image"] = fix_path(m["reference_image"])

# Add directory structure metadata
m["directory_structure"] = {
    "source/": "原始标定图像 (Image1.tif 畸变, Image_rect1.tif 矫正)",
    "mesh/16x12/": "AGDC 网格表 16×12 tiles (221节点)",
    "mesh/32x24/": "AGDC 网格表 32×24 tiles (825节点)",
    "input/nv12/": "仿真激励输入 — YUV420SP (NV12)",
    "input/nv16/": "仿真激励输入 — YUV422SP (NV16)",
    "input/yuyv/": "仿真激励输入 — YUV422I (YUYV)",
    "golden/nv12/": "黄金参考 — YUV420SP (NV12)",
    "golden/nv16/": "黄金参考 — YUV422SP (NV16)",
    "golden/yuyv/": "黄金参考 — YUV422I (YUYV)",
    "golden/": "黄金参考 — 独立 Y/U/V 平面",
    "verify/": "验证对比图像 (差异图、重建图、解析法矫正结果)",
}

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
print(f"\n  manifest.json updated")

print("\nDone. New structure:")
for root, dirs, files in os.walk(str(ROOT)):
    level = root.replace(str(ROOT), "").count(os.sep)
    if level == 0:
        continue
    indent = "  " * level
    print(f"{indent}{os.path.basename(root)}/")
    for f in sorted(files):
        print(f"{indent}  {f}")
