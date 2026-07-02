"""Generate AGDC dataset for VMRImage1_1024x768_RGB888.png (1448x1086)

Format compliance:
  - NV12: 128-bit LSB-first hex (32 chars/line), Y/UV separate, 16B aligned stride
  - Mesh LUT: 9-char hex/line (36-bit {v,u}, row-major), also raw bin64 + uv_fixed + C header
  - Golden: size matches output dimensions
"""
import numpy as np, os, json, shutil, struct
from pathlib import Path
import cv2

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    with open(str(path), 'rb') as f: data = f.read()
    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), flags)

def imwrite_unicode(path, img):
    _, buf = cv2.imencode(os.path.splitext(str(path))[1], img)
    with open(str(path), 'wb') as f: f.write(buf)

def write_hex_file(data, path, bytes_per_line=16):
    """Write binary data as 128-bit LSB-first hex text (32 chars/line)."""
    with open(path, 'w') as f:
        for i in range(0, len(data), bytes_per_line):
            chunk = data[i:i + bytes_per_line]
            if len(chunk) < bytes_per_line:
                chunk = chunk + b'\x00' * (bytes_per_line - len(chunk))
            f.write(chunk.hex() + '\n')

def pad_rows(data, width, stride):
    """Pad each row from width to stride bytes."""
    H = data.shape[0]
    padded = np.zeros((H, stride), dtype=data.dtype)
    padded[:, :width] = data
    return padded

# ============================================================
# Config
# ============================================================
BASE_DIR = Path(r'd:\Clone\CameraCalibration')
SRC_IMAGE = BASE_DIR / 'agdc_test_fisheye_1024x768/source/VMRImage1_1024x768_RGB888.png'
OUT_DIR = BASE_DIR / 'agdc_test_fisheye_1448x1086_RGB'

SS_BASE = np.array([-1.405116937602191e+002, 0.0, 2.716608082380784e-004,
                     5.257341861497706e-006, -1.067888507955045e-009])
XC_BASE, YC_BASE = 512.0, 384.0
CALIB_RADIUS_BASE = 498.0
C, D, E = 1.0, 0.0, 0.0
FC = 4.0
FRAC_BITS = 5
THETA_ORDER = 5

# Load image
img = imread_unicode(SRC_IMAGE)
H_IN, W_IN = img.shape[:2]
scale = W_IN / 1024.0
W_OUT = round(W_IN * 0.625 / 16) * 16
H_OUT = round(H_IN * 0.625 / 12) * 12

# 16B-aligned strides (hardware constraint)
SRC_STRIDE = ((W_IN + 15) // 16) * 16
DST_STRIDE = ((W_OUT + 15) // 16) * 16

print(f'Input: {W_IN}x{H_IN}  Output: {W_OUT}x{H_OUT}  Scale: {scale:.6f}')
print(f'SRC_STRIDE: {SRC_STRIDE} (W={W_IN}, 16B aligned)')
print(f'DST_STRIDE: {DST_STRIDE} (W={W_OUT}, 16B aligned)')

# Setup dirs
for d in ['source', 'mesh/16x12', 'mesh/32x24',
          'input/nv12', 'input/nv16', 'input/yuyv',
          'golden/nv12', 'golden/nv16', 'golden/yuyv', 'verify']:
    (OUT_DIR / d).mkdir(parents=True, exist_ok=True)

# ============================================================
# Calibration parameter scaling
# ============================================================
XC = XC_BASE * scale; YC = YC_BASE * scale
CALIB_RADIUS = CALIB_RADIUS_BASE * scale
SS = SS_BASE.copy()
SS[0] = SS_BASE[0] * scale
SS[1] = SS_BASE[1]
SS[2] = SS_BASE[2] / scale
SS[3] = SS_BASE[3] / (scale ** 2)
SS[4] = SS_BASE[4] / (scale ** 3)
ss_flip = SS[::-1]

# Inverse polynomial fit
rho_samples = np.linspace(0, CALIB_RADIUS, 2000)
z_samples = np.polyval(ss_flip, rho_samples)
theta_samples = np.empty_like(rho_samples)
theta_samples[0] = -np.pi / 2.0
mask = rho_samples[1:] > 0
theta_samples[1:][mask] = np.arctan(z_samples[1:][mask] / rho_samples[1:][mask])
theta_max = theta_samples[-1]

V_mat = np.zeros((len(theta_samples), THETA_ORDER + 1))
for k in range(THETA_ORDER + 1):
    V_mat[:, k] = theta_samples ** k
pol_coeffs, _, _, _ = np.linalg.lstsq(V_mat, rho_samples, rcond=None)
fit_err = np.abs(np.polyval(pol_coeffs[::-1], theta_samples) - rho_samples).max()
print(f'theta_max={np.rad2deg(theta_max):.1f} deg  pol_fit_err={fit_err:.4f} px')

# ============================================================
# Backward mapping
# ============================================================
Nxc, Nyc = H_OUT / 2.0, W_OUT / 2.0
Nz = -W_OUT / FC
u_out_grid, v_out_grid = np.meshgrid(
    np.arange(W_OUT, dtype=np.float64),
    np.arange(H_OUT, dtype=np.float64))

Nx = v_out_grid - Nxc
Ny = u_out_grid - Nyc
NORM_xy = np.maximum(np.sqrt(Nx ** 2 + Ny ** 2), 1e-12)
theta = np.arctan(np.full_like(Nx, Nz) / NORM_xy)
rho = np.polyval(pol_coeffs[::-1], theta)
scale_map = rho / NORM_xy
x_cam = Nx * scale_map
y_cam = Ny * scale_map

u_in = x_cam * C + y_cam * D + XC
v_in = x_cam * E + y_cam + YC
valid_mask = (u_in >= 0) & (u_in < W_IN) & (v_in >= 0) & (v_in < H_IN)
v_in_span = v_in.max(axis=1) - v_in.min(axis=1)
print(f'u_in: [{u_in.min():.1f}, {u_in.max():.1f}]  v_in: [{v_in.min():.1f}, {v_in.max():.1f}]')
print(f'valid: {valid_mask.sum()}/{valid_mask.size} ({100*valid_mask.sum()/valid_mask.size:.1f}%)')
print(f'per-row v_in span: max={v_in_span.max():.1f} px  mean={v_in_span.mean():.1f} px')

# ============================================================
# Golden reference (bilinear interpolation)
# ============================================================
u_in_clip = np.clip(u_in, 0, W_IN - 1)
v_in_clip = np.clip(v_in, 0, H_IN - 1)
u0 = np.floor(u_in_clip).astype(np.int32)
v0 = np.floor(v_in_clip).astype(np.int32)
u1 = np.minimum(u0 + 1, W_IN - 1)
v1 = np.minimum(v0 + 1, H_IN - 1)
wu = (u_in_clip - u0.astype(np.float64)).reshape(H_OUT, W_OUT, 1)
wv = (v_in_clip - v0.astype(np.float64)).reshape(H_OUT, W_OUT, 1)

img_rect = ((1 - wv) * (1 - wu) * img[v0, u0].astype(np.float64) +
             (1 - wv) * wu       * img[v0, u1].astype(np.float64) +
             wv       * (1 - wu) * img[v1, u0].astype(np.float64) +
             wv       * wu       * img[v1, u1].astype(np.float64))
img_rect = np.clip(np.round(img_rect), 0, 255).astype(np.uint8)
img_rect[~valid_mask] = [128, 128, 128]
imwrite_unicode(OUT_DIR / 'verify/golden_rectified_perspective.tif', img_rect)
shutil.copy2(str(SRC_IMAGE), str(OUT_DIR / 'source/VMRImage1_1448x1086_RGB888.png'))

# ============================================================
# YUV conversion functions
# ============================================================
# Three usage scenarios:
#   1. rgb_to_yuv_bt601(): Full-resolution RGB888 → YUV444 planes
#      Input:  BGR image (H, W, 3) uint8
#      Output: Y(H,W), U(H,W), V(H,W) uint8 — pixel-level YUV
#
#   2. pack_nv12/pack_nv16/pack_yuyv(): YUV444 planes → packed YUV formats
#      Input:  Y(H,W), U(H,W), V(H,W) uint8
#      Output: NV12: Y(H,W) + UV(H/2,W) interleaved
#              NV16: Y(H,W) + UV(H,W/2*2) interleaved
#              YUYV: YUYV(H,W*2) packed
#
#   3. pad_rows(): Active data → 16B-aligned stride data
#      Input:  raw pixel buffer (H, W_active)
#      Output: padded buffer (H, STRIDE_ALIGNED)

def rgb_to_yuv_bt601(img_bgr):
    """RGB888 (BGR) → YUV444 planes. BT.601 full-range.
    Usage: Y, U, V = rgb_to_yuv_bt601(bgr_image)"""
    img_f = img_bgr.astype(np.float64)
    B, G, R = img_f[:, :, 0], img_f[:, :, 1], img_f[:, :, 2]
    Y = np.clip(0.299 * R + 0.587 * G + 0.114 * B, 0, 255).astype(np.uint8)
    U = np.clip(-0.169 * R - 0.331 * G + 0.500 * B + 128.0, 0, 255).astype(np.uint8)
    V = np.clip(0.500 * R - 0.419 * G - 0.081 * B + 128.0, 0, 255).astype(np.uint8)
    return Y, U, V

def pack_nv12(Y, U, V):
    """YUV444 planes → NV12 (4:2:0 interleaved UV).
    Usage: Y_out, UV_out = pack_nv12(Y, U, V)"""
    H, W = Y.shape
    Us = ((U[0:H:2, 0:W:2].astype(np.uint16) + U[0:H:2, 1:W:2].astype(np.uint16) +
           U[1:H:2, 0:W:2].astype(np.uint16) + U[1:H:2, 1:W:2].astype(np.uint16) + 2) // 4).astype(np.uint8)
    Vs = ((V[0:H:2, 0:W:2].astype(np.uint16) + V[0:H:2, 1:W:2].astype(np.uint16) +
           V[1:H:2, 0:W:2].astype(np.uint16) + V[1:H:2, 1:W:2].astype(np.uint16) + 2) // 4).astype(np.uint8)
    uv = np.empty((H // 2, W // 2 * 2), dtype=np.uint8)
    uv[:, 0::2], uv[:, 1::2] = Us, Vs
    return Y, uv

def pack_nv16(Y, U, V):
    """YUV444 planes → NV16 (4:2:2 interleaved UV).
    Usage: Y_out, UV_out = pack_nv16(Y, U, V)"""
    H, W = Y.shape
    Us = ((U[:, 0:W:2].astype(np.uint16) + U[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    Vs = ((V[:, 0:W:2].astype(np.uint16) + V[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    uv = np.empty((H, W // 2 * 2), dtype=np.uint8)
    uv[:, 0::2], uv[:, 1::2] = Us, Vs
    return Y, uv

def pack_yuyv(Y, U, V):
    """YUV444 planes → YUYV (4:2:2 packed).
    Usage: yuyv_data = pack_yuyv(Y, U, V)"""
    H, W = Y.shape
    Us = ((U[:, 0:W:2].astype(np.uint16) + U[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    Vs = ((V[:, 0:W:2].astype(np.uint16) + V[:, 1:W:2].astype(np.uint16) + 1) // 2).astype(np.uint8)
    yuyv = np.empty((H, W * 2), dtype=np.uint8)
    for c in range(W // 2):
        yuyv[:, c * 4 + 0] = Y[:, c * 2]
        yuyv[:, c * 4 + 1] = Us[:, c]
        yuyv[:, c * 4 + 2] = Y[:, c * 2 + 1]
        yuyv[:, c * 4 + 3] = Vs[:, c]
    return yuyv

# ============================================================
# Input YUV (fisheye source)
# ============================================================
Yf, Uf, Vf = rgb_to_yuv_bt601(img)
print(f'Source UV: U mean={Uf.mean():.1f} std={Uf.std():.1f}  V mean={Vf.mean():.1f} std={Vf.std():.1f}')

# NV12: pack then pad to 16B-aligned stride
Y_nv12, UV_nv12 = pack_nv12(Yf, Uf, Vf)
Y_padded = pad_rows(Y_nv12, W_IN, SRC_STRIDE)
UV_padded = pad_rows(UV_nv12, W_IN, SRC_STRIDE)  # UV stride = SRC_STRIDE (same as Y)

# Write raw binary (padded)
Y_padded.tofile(str(OUT_DIR / 'input/nv12/distorted_nv12_y.bin'))
UV_padded.tofile(str(OUT_DIR / 'input/nv12/distorted_nv12_uv.bin'))

# Write 128-bit LSB-first hex (32 chars/line)
write_hex_file(Y_padded.tobytes(), str(OUT_DIR / 'input/nv12/distorted_nv12_y.hex'))
write_hex_file(UV_padded.tobytes(), str(OUT_DIR / 'input/nv12/distorted_nv12_uv.hex'))

# NV16
Y_nv16, UV_nv16 = pack_nv16(Yf, Uf, Vf)
Y_p16 = pad_rows(Y_nv16, W_IN, SRC_STRIDE)
UV_p16 = pad_rows(UV_nv16, W_IN, SRC_STRIDE)
Y_p16.tofile(str(OUT_DIR / 'input/nv16/distorted_nv16_y.bin'))
UV_p16.tofile(str(OUT_DIR / 'input/nv16/distorted_nv16_uv.bin'))
write_hex_file(Y_p16.tobytes(), str(OUT_DIR / 'input/nv16/distorted_nv16_y.hex'))
write_hex_file(UV_p16.tobytes(), str(OUT_DIR / 'input/nv16/distorted_nv16_uv.hex'))

# YUYV
YUYV_f = pack_yuyv(Yf, Uf, Vf)
YUYV_padded = pad_rows(YUYV_f, W_IN * 2, SRC_STRIDE * 2)
YUYV_padded.tofile(str(OUT_DIR / 'input/yuyv/distorted_yuyv.bin'))
write_hex_file(YUYV_padded.tobytes(), str(OUT_DIR / 'input/yuyv/distorted_yuyv.hex'))

print(f'Y  padded: {Y_padded.shape} (stride={SRC_STRIDE}), size={Y_padded.nbytes}')
print(f'UV padded: {UV_padded.shape} (stride={SRC_STRIDE}), size={UV_padded.nbytes}')

# ============================================================
# Golden YUV (rectified output)
# ============================================================
Yr, Ur, Vr = rgb_to_yuv_bt601(img_rect)
print(f'Golden UV: U mean={Ur.mean():.1f} std={Ur.std():.1f}  V mean={Vr.mean():.1f} std={Vr.std():.1f}')

Yr_padded = pad_rows(Yr, W_OUT, DST_STRIDE)
Yr_padded.tofile(str(OUT_DIR / 'golden/nv12/golden_nv12_y.bin'))
write_hex_file(Yr_padded.tobytes(), str(OUT_DIR / 'golden/nv12/golden_nv12_y.hex'))

# Golden NV12 UV
_, UVr_nv12 = pack_nv12(Yr, Ur, Vr)
UVr_padded = pad_rows(UVr_nv12, W_OUT, DST_STRIDE)
UVr_padded.tofile(str(OUT_DIR / 'golden/nv12/golden_nv12_uv.bin'))
write_hex_file(UVr_padded.tobytes(), str(OUT_DIR / 'golden/nv12/golden_nv12_uv.hex'))

# Golden NV16
Yr_nv16, UVr_nv16 = pack_nv16(Yr, Ur, Vr)
pad_rows(Yr_nv16, W_OUT, DST_STRIDE).tofile(str(OUT_DIR / 'golden/nv16/golden_nv16_y.bin'))
pad_rows(UVr_nv16, W_OUT, DST_STRIDE).tofile(str(OUT_DIR / 'golden/nv16/golden_nv16_uv.bin'))

# Golden YUYV
YUYV_r = pack_yuyv(Yr, Ur, Vr)
pad_rows(YUYV_r, W_OUT * 2, DST_STRIDE * 2).tofile(str(OUT_DIR / 'golden/yuyv/golden_yuyv.bin'))

# Golden plane files (unpadded, pixel-accurate)
Yr.tofile(str(OUT_DIR / 'golden/golden_y_plane.bin'))
Ur.tofile(str(OUT_DIR / 'golden/golden_u_plane.bin'))
Vr.tofile(str(OUT_DIR / 'golden/golden_v_plane.bin'))

print(f'Golden Y:  {Yr_padded.shape} (stride={DST_STRIDE}), size={Yr_padded.nbytes}')
print(f'Golden UV: {UVr_padded.shape} (stride={DST_STRIDE}), size={UVr_padded.nbytes}')

# ============================================================
# Mesh tables
# ============================================================
def float_to_u12_5(val):
    return np.clip(np.round(val * (1 << FRAC_BITS)).astype(np.int64),
                   -(1 << 17), (1 << 17) - 1).astype(np.int32)

mesh_info = {}
for mesh_name, mesh_cols, mesh_rows in [('16x12', 16, 12), ('32x24', 32, 24)]:
    gc = mesh_cols + 1
    gr = mesh_rows + 1
    nn = gc * gr
    cp = np.linspace(0, W_OUT, gc).astype(np.int32)
    rp = np.linspace(0, H_OUT, gr).astype(np.int32)
    ci = np.clip(cp, 0, W_OUT - 1)
    ri = np.clip(rp, 0, H_OUT - 1)
    mu = u_in[ri[:, None], ci[None, :]]
    mv = v_in[ri[:, None], ci[None, :]]
    muf = float_to_u12_5(mu)
    mvf = float_to_u12_5(mv)
    print(f'Mesh {mesh_name}: tile={W_OUT // mesh_cols}x{H_OUT // mesh_rows}, '
          f'u=[{mu.min():.1f},{mu.max():.1f}], v=[{mv.min():.1f},{mv.max():.1f}]')

    entries = np.zeros(nn, dtype=np.uint64)
    for iy in range(gr):
        for ix in range(gc):
            entries[iy * gc + ix] = ((np.uint64(mvf[iy, ix]) & 0x3FFFF) << 18) | \
                                     (np.uint64(muf[iy, ix]) & 0x3FFFF)

    md = OUT_DIR / 'mesh' / mesh_name

    # 36-bit packed in uint64 LE binary
    entries.tofile(str(md / f'agdc_mesh_{mesh_name}_36bit_in_u64.bin'))

    # 9-char hex per line (36-bit {v,u}, row-major)
    with open(str(md / f'agdc_mesh_{mesh_name}_36bit.hex'), 'w') as f:
        f.write(f'// AGDC Fisheye Mesh: {mesh_name} tiles — {W_IN}x{H_IN} RGB888\n')
        f.write(f'// Nodes: {gc}x{gr} = {nn}, format: 36-bit = {{v[17:0], u[17:0]}}\n')
        f.write(f'// Addressing: addr = iy * {gc} + ix (row-major)\n')
        f.write(f'// SRC_STRIDE={SRC_STRIDE}, DST_STRIDE={DST_STRIDE}\n\n')
        for addr in range(nn):
            iy, ix = addr // gc, addr % gc
            entry = entries[addr]
            f.write(f'@{addr:04X}  // node({ix:02d},{iy:02d})  '
                    f'u=0x{int(muf[iy, ix]) & 0x3FFFF:05X}({mu[iy, ix]:10.2f})  '
                    f'v=0x{int(mvf[iy, ix]) & 0x3FFFF:05X}({mv[iy, ix]:10.2f})  '
                    f'packed=0x{entry:09X}\n')

    # uv_fixed.bin (int32 pairs)
    uv_flat = np.empty(nn * 2, dtype=np.int32)
    uv_flat[0::2] = muf.flatten()
    uv_flat[1::2] = mvf.flatten()
    uv_flat.tofile(str(md / f'agdc_mesh_{mesh_name}_uv_fixed.bin'))

    # C header
    with open(str(md / f'agdc_mesh_{mesh_name}.h'), 'w') as f:
        f.write(f'// AGDC Fisheye Mesh — {mesh_name} tiles — {W_IN}x{H_IN} RGB888\n')
        f.write('#pragma once\n#include <stdint.h>\n\n')
        f.write(f'#define AGDC_MESH_COLS   {gc}\n')
        f.write(f'#define AGDC_MESH_ROWS   {gr}\n')
        f.write(f'#define AGDC_MESH_NODES  {nn}\n')
        f.write(f'#define AGDC_IMG_WIDTH   {W_OUT}\n')
        f.write(f'#define AGDC_IMG_HEIGHT  {H_OUT}\n')
        f.write(f'#define AGDC_FRAC_BITS   {FRAC_BITS}\n\n')
        f.write(f'static const uint64_t agdc_mesh[{nn}] = {{\n')
        for iy in range(gr):
            vals = ', '.join(f'0x{entries[iy * gc + ix]:09X}ULL' for ix in range(gc))
            f.write(f'    {vals},\n')
        f.write('};\n')

    mesh_info[mesh_name] = {
        'grid_cols': gc, 'grid_rows': gr, 'num_nodes': nn,
        'tile_w': W_OUT // mesh_cols, 'tile_h': H_OUT // mesh_rows,
        'u_range_float': [float(mu.min()), float(mu.max())],
        'v_range_float': [float(mv.min()), float(mv.max())],
    }

# ============================================================
# Verification: mesh reconstruction vs golden
# ============================================================
print()
for mesh_name, mesh_cols, mesh_rows in [('16x12', 16, 12), ('32x24', 32, 24)]:
    gc = mesh_cols + 1
    gr = mesh_rows + 1
    cp = np.linspace(0, W_OUT, gc)
    rp = np.linspace(0, H_OUT, gr)
    ci = np.clip(np.round(cp).astype(np.int32), 0, W_OUT - 1)
    ri = np.clip(np.round(rp).astype(np.int32), 0, H_OUT - 1)
    mu = u_in[ri[:, None], ci[None, :]]
    mv = v_in[ri[:, None], ci[None, :]]

    out = np.full((H_OUT, W_OUT, 3), 128, dtype=np.float64)
    for iy in range(H_OUT):
        ry = max(1, min(np.searchsorted(rp, iy), gr - 1))
        y0, y1 = int(rp[ry - 1]), int(rp[ry])
        wy = (iy - y0) / max(y1 - y0, 1e-6)
        for ix in range(W_OUT):
            rx = max(1, min(np.searchsorted(cp, ix), gc - 1))
            x0, x1 = int(cp[rx - 1]), int(cp[rx])
            wx = (ix - x0) / max(x1 - x0, 1e-6)
            x_in = (1 - wy) * ((1 - wx) * mu[ry - 1, rx - 1] + wx * mu[ry - 1, rx]) + \
                   wy * ((1 - wx) * mu[ry, rx - 1] + wx * mu[ry, rx])
            y_in = (1 - wy) * ((1 - wx) * mv[ry - 1, rx - 1] + wx * mv[ry - 1, rx]) + \
                   wy * ((1 - wx) * mv[ry, rx - 1] + wx * mv[ry, rx])
            xi = int(np.clip(np.round(x_in), 0, W_IN - 1))
            yi = int(np.clip(np.round(y_in), 0, H_IN - 1))
            if 0 <= x_in < W_IN and 0 <= y_in < H_IN:
                out[iy, ix, :] = img[yi, xi, :]

    out = out.astype(np.uint8)
    diff = np.abs(out.astype(np.float32) - img_rect.astype(np.float32))
    diff[~valid_mask] = 0
    mae = diff[valid_mask].mean() if valid_mask.any() else 0
    print(f'Verify {mesh_name}: MAE={mae:.4f}  MaxErr={diff.max():.0f}')
    imwrite_unicode(OUT_DIR / 'verify' / f'reconstructed_mesh_{mesh_name}.tif', out)

# ============================================================
# Manifest
# ============================================================
manifest = {
    'description': f'AGDC Fisheye — VMRImage1 {W_IN}x{H_IN} RGB888',
    'model': 'Scaramuzza Omnidirectional Camera Model',
    'scale': float(scale),
    'source_image': str(SRC_IMAGE),
    'note': 'RGB888 color image, 16B-aligned stride, NV12 hex format',
    'parameters': {
        'ss': SS.tolist(), 'xc': float(XC), 'yc': float(YC),
        'c': C, 'd': D, 'e': E, 'calib_radius': float(CALIB_RADIUS),
        'pol_coeffs_fitted': pol_coeffs.tolist(),
        'theta_max_deg': float(np.rad2deg(theta_max)),
    },
    'image': {
        'input_size': [W_IN, H_IN], 'output_size': [W_OUT, H_OUT],
        'src_stride': SRC_STRIDE, 'dst_stride': DST_STRIDE,
        'virtual_fc': FC,
    },
    'hardware_constraints': {
        'per_row_v_in_span_max': float(v_in_span.max()),
        'per_row_v_in_span_mean': float(v_in_span.mean()),
        'line_buf_depth_typical': 70,
        'online_mode_feasible': bool(v_in_span.max() <= 70),
    },
    'format_spec': {
        'nv12': '128-bit LSB-first hex, 32 chars/line, Y/UV separate files',
        'nv12_y_stride': SRC_STRIDE,
        'nv12_uv_stride': SRC_STRIDE,
        'mesh_node_format': '36-bit = {v[17:0], u[17:0]}, 9-char hex/line',
        'mesh_addressing': 'addr = iy * (mesh_cols+1) + ix (row-major)',
        'coordinate_format': 'u12.5 signed, LSB-first byte order',
        'frac_bits': FRAC_BITS,
    },
    'mesh_tables': mesh_info,
}
with open(str(OUT_DIR / 'manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f'\nDone! Output: {OUT_DIR}')
print(f'Format compliance:')
print(f'  NV12: 128-bit LSB-first hex ({SRC_STRIDE*H_IN//16} lines Y, {SRC_STRIDE*H_IN//2//16} lines UV)')
print(f'  Mesh: 9-char hex/line, 36-bit {{v,u}}, row-major')
print(f'  Stride: SRC={SRC_STRIDE} (16B aligned), DST={DST_STRIDE} (16B aligned)')
