# Camera Calibration Tutorial Illustrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the tutorial's ASCII illustrations and supplement its formulas, algorithms, stereo geometry, and hardware pipeline with a consistent set of white-background, black-structure SVG diagrams.

**Architecture:** Store every diagram as a standalone, dependency-free SVG under `assets/camera-calibration/`. Integrate them through relative Markdown image links while retaining copyable formulas and pseudocode. Validate the SVG files structurally, audit all Markdown references, and render representative diagrams before completion.

**Tech Stack:** SVG 1.1/XML, Markdown, PowerShell validation, browser or image renderer for visual inspection.

---

## File map

**Create:**

- `assets/camera-calibration/01-pinhole-camera.svg` — pinhole projection and inverted image
- `assets/camera-calibration/02-four-coordinate-systems.svg` — world-to-pixel transformation
- `assets/camera-calibration/03-intrinsic-extrinsic.svg` — intrinsic/extrinsic comparison
- `assets/camera-calibration/04-intrinsic-matrix.svg` — matrix layout and variable meanings
- `assets/camera-calibration/05-homogeneous-coordinate.svg` — unified affine transformation
- `assets/camera-calibration/06-lens-distortion.svg` — normal/barrel/pincushion grids
- `assets/camera-calibration/07-undistortion-mapping.svg` — reverse mapping
- `assets/camera-calibration/08-projection-models.svg` — five projection models
- `assets/camera-calibration/09-checkerboard-principle.svg` — checkerboard corner constraints
- `assets/camera-calibration/10-capture-poses.svg` — recommended image coverage
- `assets/camera-calibration/11-zhang-calibration-flow.svg` — Zhang calibration pipeline
- `assets/camera-calibration/12-reprojection-optimization.svg` — reprojection error minimization
- `assets/camera-calibration/13-lm-step-control.svg` — LM damping logic
- `assets/camera-calibration/14-stereo-depth.svg` — disparity-to-depth geometry
- `assets/camera-calibration/15-epipolar-rectification.svg` — epipolar geometry and rectification
- `assets/camera-calibration/16-code-workflows.svg` — three sample program workflows
- `assets/camera-calibration/17-remap-hardware-pipeline.svg` — S0–S4 and line buffers
- `assets/camera-calibration/18-parameter-hardware-bridge.svg` — calibration-to-register bridge
- `assets/camera-calibration/README.md` — palette, typography, line, arrow, and naming conventions

**Modify:**

- `相机标定零基础入门教程.md` — replace ASCII diagrams and insert all SVG references and captions

## Task 1: Establish the visual system

- [ ] **Step 1: Create the asset directory**

Run:

```powershell
New-Item -ItemType Directory -Force -Path 'assets\camera-calibration'
```

Expected: directory `assets/camera-calibration` exists.

- [ ] **Step 2: Create `assets/camera-calibration/README.md`**

Record these fixed rules:

```markdown
# Camera calibration illustration system

- Canvas: 1200 px wide; default height 700 px
- Background: #FFFFFF
- Primary structure/text/data flow: #111827
- Secondary grid/divider: #D1D5DB
- Projection/helper: #2563EB
- Key point/current step: #F59E0B
- Correct/ideal: #16A34A
- Error/distortion: #DC2626
- Chinese font fallback: Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif
- Main stroke: 3 px; helper stroke: 2 px; dashed helper: 8 6
- Minimum body label: 24 px; title: 32 px
- Every SVG has a white background rect, viewBox, title, desc, and arrow markers.
- Color never carries meaning alone; pair it with labels, shapes, or line styles.
```

- [ ] **Step 3: Verify the convention file**

Run:

```powershell
Select-String -LiteralPath 'assets\camera-calibration\README.md' -Pattern '#FFFFFF','#111827','Color never'
```

Expected: all three rules are returned.

## Task 2: Draw the imaging and parameter foundations

**Files:** SVG 01–05.

- [ ] **Step 1: Draw `01-pinhole-camera.svg`**

Show an upright object, two principal rays crossing at the optical center, an image plane, and the inverted image. Label `物体`, `光心 O`, `焦距 f`, and `倒立影像`.

- [ ] **Step 2: Draw `02-four-coordinate-systems.svg`**

Use four numbered panels: `世界坐标系 → 相机坐标系 → 图像坐标系 → 像素坐标系`. Include `[R|t]`, perspective division, and `K` on the three connecting arrows.

- [ ] **Step 3: Draw `03-intrinsic-extrinsic.svg`**

Split the canvas into `内参：相机自身` and `外参：相机在哪里、朝哪里`. Include `fx, fy, cx, cy` on the left and `R, t` on the right.

- [ ] **Step 4: Draw `04-intrinsic-matrix.svg`**

Present the 3×3 matrix in the center, with leader lines from `fx/fy` to focal-length diagrams and from `cx/cy` to the principal point on a sensor grid.

- [ ] **Step 5: Draw `05-homogeneous-coordinate.svg`**

Contrast separate `旋转/缩放用乘法 + 平移用加法` with a single 4×4 homogeneous multiplication. Highlight the appended `1`.

- [ ] **Step 6: Parse all five SVG files**

Run:

```powershell
Get-ChildItem 'assets\camera-calibration\0[1-5]-*.svg' | ForEach-Object { [xml](Get-Content -Raw -LiteralPath $_.FullName) | Out-Null; $_.Name }
```

Expected: five filenames and no XML exception.

## Task 3: Draw distortion, projection, and calibration capture

**Files:** SVG 06–10.

- [ ] **Step 1: Draw `06-lens-distortion.svg`**

Use three equal grids labeled `正常`, `桶形畸变`, and `枕形畸变`. Keep identical control points so curvature is directly comparable.

- [ ] **Step 2: Draw `07-undistortion-mapping.svg`**

Show an output pixel tracing backward through the distortion model to a subpixel source coordinate, followed by four-neighbor bilinear interpolation.

- [ ] **Step 3: Draw `08-projection-models.svg`**

Use five compact panels for perspective, equidistant, equisolid-angle, stereographic, and orthographic projection. Show ray angle `θ`, image radius `r`, and the corresponding relation without long derivations.

- [ ] **Step 4: Draw `09-checkerboard-principle.svg`**

Show detected inner corners, known square size, row/column indexing, and the planar constraint `Z=0`.

- [ ] **Step 5: Draw `10-capture-poses.svg`**

Show six good checkerboard poses covering center, edges, tilt, distance, and rotation. Add a separate crossed-out row for blur, tiny board, repeated pose, and cropped corners.

- [ ] **Step 6: Parse all five SVG files**

Run:

```powershell
Get-ChildItem 'assets\camera-calibration\0[6-9]-*.svg','assets\camera-calibration\10-*.svg' | ForEach-Object { [xml](Get-Content -Raw -LiteralPath $_.FullName) | Out-Null; $_.Name }
```

Expected: five filenames and no XML exception.

## Task 4: Draw calibration, optimization, and stereo geometry

**Files:** SVG 11–15.

- [ ] **Step 1: Draw `11-zhang-calibration-flow.svg`**

Create a single directional flow: images → corners → homographies → initial intrinsics → per-image extrinsics → distortion → nonlinear refinement → result and reprojection error.

- [ ] **Step 2: Draw `12-reprojection-optimization.svg`**

Show observed corner `p`, projected corner `p̂`, residual vector, summed squared residuals, and an iteration loop that reduces total error.

- [ ] **Step 3: Draw `13-lm-step-control.svg`**

Show the damping parameter `λ`: failed trial increases `λ` and makes a cautious gradient-like step; successful trial decreases `λ` and permits a Gauss–Newton-like step.

- [ ] **Step 4: Draw `14-stereo-depth.svg`**

Show two cameras separated by baseline `B`, focal length `f`, left/right image coordinates, disparity `d = xL - xR`, and depth `Z = fB/d`.

- [ ] **Step 5: Draw `15-epipolar-rectification.svg`**

Use a before/after split. Before: epipolar lines converge through epipoles. After: scanlines are horizontal and corresponding points share the same row.

- [ ] **Step 6: Parse all five SVG files**

Run:

```powershell
Get-ChildItem 'assets\camera-calibration\1[1-5]-*.svg' | ForEach-Object { [xml](Get-Content -Raw -LiteralPath $_.FullName) | Out-Null; $_.Name }
```

Expected: five filenames and no XML exception.

## Task 5: Draw software and hardware workflows

**Files:** SVG 16–18.

- [ ] **Step 1: Draw `16-code-workflows.svg`**

Use three stacked lanes titled `单目标定`, `虚拟广告牌`, and `双目标定`. Each lane must include inputs, core OpenCV operations, outputs, and one diagnostic result.

- [ ] **Step 2: Draw `17-remap-hardware-pipeline.svg`**

Show S0 coordinate generation, S1 mesh lookup, S2 interpolation, S3 source addressing, and S4 pixel interpolation. Place line buffers beneath S3–S4 and distinguish coordinate flow from pixel flow.

- [ ] **Step 3: Draw `18-parameter-hardware-bridge.svg`**

Show `K/dist → OpenCV map generation → quantization/mesh compression → memory/register packing → FPGA configuration → corrected stream`, including host and hardware boundaries.

- [ ] **Step 4: Parse all three SVG files**

Run:

```powershell
Get-ChildItem 'assets\camera-calibration\1[6-8]-*.svg' | ForEach-Object { [xml](Get-Content -Raw -LiteralPath $_.FullName) | Out-Null; $_.Name }
```

Expected: three filenames and no XML exception.

## Task 6: Integrate diagrams into the tutorial

**File:** `相机标定零基础入门教程.md`.

- [ ] **Step 1: Replace the world-coordinate ASCII diagram**

At the current diagram near line 78, replace the fenced ASCII block with:

```markdown
![从世界坐标到像素坐标的四个坐标系](assets/camera-calibration/02-four-coordinate-systems.svg)

*图 2：一个三维点依次经过外参、透视投影和内参，最终成为图像中的像素。*
```

- [ ] **Step 2: Replace the distortion ASCII grids**

At the current diagram near line 218, replace the fenced ASCII block with:

```markdown
![正常网格、桶形畸变与枕形畸变对比](assets/camera-calibration/06-lens-distortion.svg)

*图 6：桶形畸变使直线向外鼓起，枕形畸变使直线向内收缩。*
```

- [ ] **Step 3: Replace the calibration ASCII flow**

At the current diagram near line 389, replace the fenced ASCII flow with the reference to `11-zhang-calibration-flow.svg` and a caption explaining initial estimation followed by nonlinear refinement.

- [ ] **Step 4: Replace the hardware bridge ASCII flow**

At the current diagram near line 842, replace the fenced ASCII flow with the reference to `18-parameter-hardware-bridge.svg` and a caption explaining the software/hardware boundary.

- [ ] **Step 5: Insert the remaining diagrams**

Place each remaining SVG immediately after the first complete prose explanation of its topic. Preserve matrix, equation, pseudocode, and API code blocks at current locations.

- [ ] **Step 6: Audit the Markdown image references**

Run:

```powershell
$md = Get-Content -Raw -Encoding utf8 -LiteralPath '相机标定零基础入门教程.md'
[regex]::Matches($md, '!\[[^\]]+\]\((assets/camera-calibration/[^)]+\.svg)\)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
```

Expected: 18 unique SVG paths.

## Task 7: Validate and visually inspect the complete set

- [ ] **Step 1: Run structural validation**

Run:

```powershell
$files = Get-ChildItem 'assets\camera-calibration\*.svg'
if ($files.Count -ne 18) { throw "Expected 18 SVG files, found $($files.Count)" }
foreach ($f in $files) {
  [xml]$xml = Get-Content -Raw -LiteralPath $f.FullName
  if (-not $xml.svg.viewBox) { throw "$($f.Name) has no viewBox" }
  if (-not $xml.svg.title) { throw "$($f.Name) has no title" }
  if (-not $xml.svg.desc) { throw "$($f.Name) has no desc" }
}
'18 SVG files passed XML and metadata validation'
```

Expected: `18 SVG files passed XML and metadata validation`.

- [ ] **Step 2: Check every Markdown target**

Run:

```powershell
$md = Get-Content -Raw -Encoding utf8 -LiteralPath '相机标定零基础入门教程.md'
$refs = [regex]::Matches($md, '!\[[^\]]+\]\((assets/camera-calibration/[^)]+\.svg)\)')
foreach ($ref in $refs) {
  if (-not (Test-Path -LiteralPath $ref.Groups[1].Value)) { throw "Missing $($ref.Groups[1].Value)" }
}
"$($refs.Count) Markdown image references exist"
```

Expected: `18 Markdown image references exist`.

- [ ] **Step 3: Check that explanatory ASCII art is gone**

Run:

```powershell
Select-String -LiteralPath '相机标定零基础入门教程.md' -Encoding utf8 -Pattern '正常网格','桶形畸变 \(线条','开始\s*$'
```

Expected: no matches inside fenced ASCII diagrams.

- [ ] **Step 4: Render and inspect representative diagrams**

Render SVG 01, 06, 11, 15, 17, and 18. For each one verify:

- no clipped or overlapping Chinese labels;
- black remains the dominant structural color;
- colored elements remain understandable in grayscale;
- arrow direction is unambiguous;
- labels remain readable at 50% scale.

- [ ] **Step 5: Review the final diff manually**

Confirm that no tutorial prose, formulas, code samples, or headings were accidentally removed. Because this workspace is not a Git repository, compare the edited Markdown against a temporary pre-edit copy or use the editor's local history.

