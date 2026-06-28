
```yaml
name: drawio
description: 统一处理所有绘图、制图、图表设计需求，原生基于 draw.io (diagrams.net) 实现，生成标准 mxGraphModel 格式 .drawio 文件。支持流程图、架构图、ER 图、时序图、网络图、原型图等通用图表；**识别硬件/芯片相关关键词时，自动应用工业级硬件架构图专属视觉风格**。支持导出 PNG/SVG/PDF/JPG、生成在线编辑 URL，兼容 Windows / WSL2 / macOS / Linux 全平台。
```

---

## 1. 触发规则

满足以下任意条件，立即启用本技能，**禁止使用 Mermaid、CSV 等其他绘图格式**。

### 1.1 通用绘图触发（必启用）

1. 动作关键词：`create` / `generate` / `draw` / `design`（创建、生成、绘制、设计）
2. 图表类型：流程图、架构图、ER 图、时序图、类图、网络图、原型图、线框图、UI 草图
3. 工具/文件关键词：`drawio` / `draw.io` / `drawoi` / `.drawio` 文件
4. 导出诉求：要求将图表导出为 PNG / SVG / PDF

### 1.2 硬件架构专属触发（自动加载硬件风格）

出现以下硬件相关词汇，**强制套用硬件架构视觉规范**：
硬件架构、芯片架构、SoC、FPGA、IP 核、总线、模块框图、硬件拓扑、外设、接口、寄存器、片上系统、处理器核、视频引擎、图形引擎。

---

## 2. 整体执行流程

全程遵循固定四步流水线，**仅在「生成 XML」环节注入硬件样式，其余流程完全不变**，顺序不可颠倒。

1. **生成标准 XML**
   基于 `mxGraphModel` 编写图表 XML；硬件类图表强制嵌入硬件架构专属样式属性。
2. **写入本地文件**
   通过文件工具将 XML 保存为 `.drawio` 文件至当前工作目录。
3. **按输出格式分支处理**
   根据用户指定格式，分别执行导出、生成 URL、保留原文件逻辑。
4. **打开结果/输出路径**
   调用系统命令自动打开文件/网页；打开失败则打印完整路径，引导用户手动操作。

---

## 3. 全局 XML 基础约束（所有图表强制遵守）

`.drawio` 文件为原生 mxGraphModel XML，所有图表必须满足以下硬性规则：

1. 必须保留基础骨架：包含 `<mxCell id="0"/>`、`<mxCell id="1" parent="0"/>` 根节点，缺失会导致图表空白。
2. **严禁添加 XML 注释 `<!-- -->`**，避免解析异常。
3. 特殊字符必须转义：`&amp;`、`&lt;`、`&gt;`、`&quot;`。
4. 所有 `<mxCell>` 标签使用**全局唯一 ID**。
5. 所有连线（edge）必须携带子节点：`<mxGeometry relative="1" as="geometry" />`，否则连线无法渲染。

### 基础 XML 骨架（通用）

```xml
<mxGraphModel adaptiveColors="auto">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <!-- 图表元素、模块、连线全部写在此处，parent="1" -->
  </root>
</mxGraphModel>
```

---

## 4. 视觉样式规范（硬件架构图专用）

识别硬件相关关键词时，全局启用本套扁平化工业风格，**无圆角、无阴影、无渐变、无3D效果**。

### 4.1 全局画布配置

关闭网格、辅助线，固定背景色，XML 根标签配置如下：

```xml
<mxGraphModel adaptiveColors="auto" grid="0" guides="0" tooltips="0" connect="0">
```

- 画布背景色：`#FFF5E6`（浅米黄色纯色）
- 功能说明：`grid=0` 关闭网格，`guides=0` 关闭对齐辅助线

### 4.2 功能模块样式

所有模块为**纯直角矩形**，统一 1px 深灰色实线边框，按功能分为三类：

| 模块分类         | 适用对象                              | 填充色              | 完整 style 属性                                                                                                                                                             |
| ---------------- | ------------------------------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 计算/控制类      | ARM核、DSP、视频引擎、计算IP、控制器  | `#C6E2FF`（淡蓝） | `rounded=0;shadow=0;gradient=none;fillColor=#C6E2FF;strokeColor=#333333;strokeWidth=1;align=center;verticalAlign=middle;whiteSpace=wrap;html=0;`                          |
| 总线/外设/接口类 | AHB/APB总线、GPIO、I2S、RGB、各类外设 | `#FFE0B2`（浅橙） | `rounded=0;shadow=0;gradient=none;fillColor=#FFE0B2;strokeColor=#333333;strokeWidth=1;align=center;verticalAlign=middle;whiteSpace=wrap;html=0;`                          |
| 核心IP高亮分区   | GPU、专用加速核、核心IP模块           | `#FFE0E0`（淡粉） | `rounded=0;shadow=0;gradient=none;fillColor=#FFE0E0;strokeColor=#FF0000;strokeWidth=1;dashed=1;dashPattern=4 4;align=center;verticalAlign=middle;whiteSpace=wrap;html=0;` |

> 补充：模块内子模块继承父模块样式，尺寸缩小，文字可左对齐。

### 4.3 分区虚线框（区域划分）

用于圈选子系统/IP组，**无填充、红色虚线边框**，样式如下：

```
rounded=0;shadow=0;gradient=none;fillColor=none;strokeColor=#FF0000;strokeWidth=1;dashed=1;dashPattern=4 4;align=center;verticalAlign=middle;html=0;
```

- 标注规则：分区名称写在虚线框下方，使用小号黑色字体。

### 4.4 连线与箭头样式

**强制直角走线**（`orthogonal=1`），禁止斜线、曲线；统一 1px 线宽、实心箭头，按信号类型分色：

| 信号类型          | 线条/箭头色值         | 完整 edge 样式                                                                               | 适用场景                         |
| ----------------- | --------------------- | -------------------------------------------------------------------------------------------- | -------------------------------- |
| 控制/配置信号     | `#E63946`（红色）   | `orthogonal=1;strokeColor=#E63946;strokeWidth=1;endArrow=block;arrowColor=#E63946;html=0;` | 寄存器配置、复位、中断、控制指令 |
| 高速数据/总线信号 | `#2A9D8F`（青绿色） | `orthogonal=1;strokeColor=#2A9D8F;strokeWidth=1;endArrow=block;arrowColor=#2A9D8F;html=0;` | 数据流、高速总线、图像数据       |
| 外部接口信号      | `#F4A261`（橙黄色） | `orthogonal=1;strokeColor=#F4A261;strokeWidth=1;endArrow=block;arrowColor=#F4A261;html=0;` | RGB、RSDS、I2S、UART 对外接口    |
| 辅助/时钟信号     | `#6C757D`（灰色）   | `orthogonal=1;strokeColor=#6C757D;strokeWidth=1;endArrow=block;arrowColor=#6C757D;html=0;` | 时钟、电源、状态信号             |

### 4.5 文字与字体规范

全图文字为**纯黑色**，无彩色字体；字体统一为 Arial 无衬线字体，按层级区分字号：

- 全局文字基础样式：`fontColor=#000000;fontName=Arial;`
- 核心模块/总线名称：`fontSize=14`
- 子模块、频率、带宽参数：`fontSize=11`
- 外部接口、辅助标注：`fontSize=9`
- 对齐规则：模块内文字居中，接口标注与箭头平行。

---

## 5. 布局规范（硬件架构图专属）

1. 功能分区：按控制区、总线区、计算区、接口区水平/垂直划分，模块无重叠。
2. 总线排布：高速总线在上，低速总线在下，长条总线水平贯穿画布。
3. 连接点位：模块与总线的连线，对接模块边缘中心位置，排布整齐。
4. 外部接口：箭头延伸至画布边缘，接口名称标注在箭头外侧。
5. 疏密要求：紧凑排布，适配工业文档使用场景，无大面积空白。

---

## 6. 文件命名规范

### 6.1 通用规则

1. 全部使用**小写英文**，多单词用连字符 `-` 分隔。
2. 原生文件：`名称.drawio`
3. 导出文件：双后缀格式 `名称.drawio.格式`（标识内嵌可编辑XML）。
4. 文件名贴合图表业务内容，简洁易懂。

### 6.2 硬件场景命名示例

| 用户请求             | 输出格式 | 最终文件名                  |
| -------------------- | -------- | --------------------------- |
| 绘制SoC整体架构图    | 无格式   | `soc-architecture.drawio` |
| 芯片架构导出PNG      | png      | `chip-frame.drawio.png`   |
| 总线架构生成SVG      | svg      | `bus-topology.drawio.svg` |
| FPGA模块框图在线打开 | url      | `fpga-module.drawio`      |
| 处理器IP架构导出PDF  | pdf      | `processor-ip.drawio.pdf` |

### 6.3 文件生命周期

1. PNG/SVG/PDF 导出成功：**删除原始 `.drawio` 文件**（导出文件已内嵌完整XML）。
2. URL 在线模式：保留本地 `.drawio` 文件作为持久化副本。
3. 仅原生文件输出：保留 `.drawio` 文件。

---

## 7. 输出分支处理

根据用户指定格式，分为三大执行分支，依赖 draw.io 桌面版 CLI 实现文件导出。

### 7.1 支持的导出格式能力

| 格式 | 内嵌XML | 特性说明                       |
| ---- | ------- | ------------------------------ |
| PNG  | 支持    | 通用图片，可回编，推荐透明背景 |
| SVG  | 支持    | 矢量图，无限放大不失真，可回编 |
| PDF  | 支持    | 适合打印、文档嵌入，可回编     |
| JPG  | 不支持  | 有损压缩，导出后无法二次编辑   |

### 7.2 CLI 工具路径探测（跨平台）

优先通过 `which`/`where` 检测环境变量，未命中则使用系统默认路径：

1. Windows(MSYS2/Git Bash)：`/d/software/drawio/draw.io/drawio.exe`
2. WSL2：`/mnt/c/Program Files/draw.io/draw.io.exe`
   备选路径：`/mnt/c/Users/$WIN_USER/AppData/Local/Programs/draw.io/draw.io.exe`
3. macOS：`/Applications/draw.io.app/Contents/MacOS/draw.io`
4. 原生 Linux：直接使用命令 `drawio`
5. 原生 Windows：`"C:\Program Files\draw.io\draw.io.exe"`

### 7.3 标准导出命令（硬件图优化版）

基础参数说明：

- `-x`：启用导出模式（必填）
- `-f`：指定导出格式（必填）
- `-e`：内嵌原始XML（必加，保证可编辑）
- `-b 15`：边距15px（硬件图纸专用，留白更大）
- `-t`：PNG专用，开启透明背景

#### 常用命令示例

```bash
# 导出透明背景PNG（推荐）
$DRAWIO_CMD -x -f png -e -b 15 -t -o soc-arch.drawio.png soc-arch.drawio

# 导出矢量SVG
$DRAWIO_CMD -x -f svg -e -b 15 -o bus.drawio.svg bus.drawio

# 导出打印用PDF
$DRAWIO_CMD -x -f pdf -e -b 15 -o fpga.drawio.pdf fpga.drawio
```

### 7.4 分支1：导出 PNG / SVG / PDF / JPG

1. 探测 draw.io CLI 可执行文件。
2. 执行导出命令，生成目标格式文件。
3. 导出成功：删除原始 `.drawio` 文件，调用系统命令打开导出文件。
4. 未找到 CLI：保留 `.drawio` 文件，提示用户：安装 draw.io 桌面端、改用 URL 模式、手动打开文件。

### 7.5 分支2：URL 在线编辑模式

无需本地客户端，生成 `app.diagrams.net` 在线编辑链接。

#### 7.5.1 URL 生成逻辑

1. 保留本地 `.drawio` 文件。
2. 读取XML → Node.js `zlib.deflateRawSync` 压缩 → Base64 编码。
3. 拼接为在线链接：`https://app.diagrams.net/?grid=0&pv=0&border=10&edit=_blank#create=编码数据`

#### 7.5.2 一键生成脚本

```bash
URL=$(node -e '
const fs = require("fs");
const zlib = require("zlib");
const xml = fs.readFileSync(process.argv[1], "utf8");
const compressed = zlib.deflateRawSync(encodeURIComponent(xml)).toString("base64");
const payload = encodeURIComponent(JSON.stringify({ type: "xml", compressed: true, data: compressed }));
console.log("https://app.diagrams.net/?grid=0&pv=0&border=10&edit=_blank#create=" + payload);
' DIAGRAM.drawio)
```

#### 7.5.3 跨平台打开方式

- macOS：`open "$URL"`
- 原生 Linux：`xdg-open "$URL"`
- Windows / WSL2：**禁止直接调用URL**（cmd 会截断 `#` 后数据），创建临时 `.url` 快捷文件打开
  - WSL2 示例：
    ```bash
    TMPFILE=$(mktemp --suffix=.url)
    printf '[InternetShortcut]\r\nURL=%s\r\n' "$URL" > "$TMPFILE"
    cmd.exe /c start "" "$(wslpath -w "$TMPFILE")"
    ```
  - 原生 Windows 示例：
    ```cmd
    echo [InternetShortcut] > %TEMP%\drawio.url
    echo URL=%URL% >> %TEMP%\drawio.url
    start "" "%TEMP%\drawio.url"
    ```

#### 7.5.4 降级规则（硬件大图专用）

浏览器 URL 长度上限约 32KB ~ 2MB，**超大型硬件架构图**触发上限时：

1. 停止生成 URL。
2. 仅交付本地 `.drawio` 文件，并提示：`图表体量较大，已生成本地可编辑文件，请使用 draw.io 客户端打开`。

#### 7.5.5 输出文案

```
Opened in browser: <完整URL>
Local file: <文件路径>.drawio
```

### 7.6 分支3：无指定输出格式

仅生成并保留 `.drawio` 原生文件，调用系统命令打开；打开失败则输出文件路径。

### 7.7 跨平台文件打开通用命令

| 环境         | 打开命令                                       |
| ------------ | ---------------------------------------------- |
| macOS        | `open 文件名`                                |
| 原生 Linux   | `xdg-open 文件名`                            |
| WSL2         | `cmd.exe /c start "" "$(wslpath -w 文件名)"` |
| 原生 Windows | `start 文件名`                               |

---

## 8. 硬件架构图标准 XML 模板（可直接复用）

```xml
<mxGraphModel adaptiveColors="auto" grid="0" guides="0" tooltips="0" connect="0">
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>

    <!-- 计算类模块 - 淡蓝色 -->
    <mxCell id="2" value="ARM Core" style="rounded=0;shadow=0;gradient=none;fillColor=#C6E2FF;strokeColor=#333333;strokeWidth=1;align=center;verticalAlign=middle;whiteSpace=wrap;html=0;fontColor=#000000;fontName=Arial;fontSize=14;" vertex="1" parent="1">
      <mxGeometry x="80" y="60" width="120" height="80" as="geometry"/>
    </mxCell>

    <!-- 总线模块 - 浅橙色 -->
    <mxCell id="3" value="AHB Bus (100MHz)" style="rounded=0;shadow=0;gradient=none;fillColor=#FFE0B2;strokeColor=#333333;strokeWidth=1;align=center;verticalAlign=middle;whiteSpace=wrap;html=0;fontColor=#000000;fontName=Arial;fontSize=14;" vertex="1" parent="1">
      <mxGeometry x="50" y="180" width="350" height="40" as="geometry"/>
    </mxCell>

    <!-- 外设模块 - 浅橙色 -->
    <mxCell id="4" value="I2S 接口" style="rounded=0;shadow=0;gradient=none;fillColor=#FFE0B2;strokeColor=#333333;strokeWidth=1;align=center;verticalAlign=middle;whiteSpace=wrap;html=0;fontColor=#000000;fontName=Arial;fontSize=14;" vertex="1" parent="1">
      <mxGeometry x="320" y="60" width="100" height="80" as="geometry"/>
    </mxCell>

    <!-- 高速数据连线 - 青绿色 直角走线 -->
    <mxCell id="5" value="" style="orthogonal=1;strokeColor=#2A9D8F;strokeWidth=1;endArrow=block;arrowColor=#2A9D8F;html=0;" edge="1" parent="1" source="2" target="3">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>

    <!-- 控制信号连线 - 红色 直角走线 -->
    <mxCell id="6" value="" style="orthogonal=1;strokeColor=#E63946;strokeWidth=1;endArrow=block;arrowColor=#E63946;html=0;" edge="1" parent="1" source="4" target="3">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

---

## 9. 故障排查表

| 故障现象                         | 根因                                          | 解决方案                                               |
| -------------------------------- | --------------------------------------------- | ------------------------------------------------------ |
| 找不到 draw.io CLI               | 未安装桌面端或未配置环境变量                  | 保留 `.drawio` 文件，引导用户安装客户端、改用URL模式 |
| 导出文件为空/损坏                | XML 格式非法、特殊字符未转义、存在注释        | 校验XML合法性，删除注释，转义特殊符号                  |
| 图表打开空白                     | 缺失 `id="0"` / `id="1"` 根节点           | 补全基础XML骨架                                        |
| 连线不渲染                       | 连线缺少 `<mxGeometry>` 子节点              | 为所有edge补充几何节点                                 |
| 连线为曲线/斜线                  | 未添加 `orthogonal=1`                       | 所有连线强制开启直角走线                               |
| 模块出现圆角/阴影/渐变           | 样式缺少 `rounded=0;shadow=0;gradient=none` | 补全硬件标准样式前缀                                   |
| 分区框显示为实线                 | 缺少 `dashed=1;dashPattern=4 4`             | 补充虚线样式参数                                       |
| URL 打开后页面空白(Windows/WSL2) | cmd 截断URL中 `#` 后的数据                  | 使用临时 `.url` 快捷文件方案                         |
| URL 生成失败/超长                | 图表过大，超出浏览器长度限制                  | 放弃URL模式，仅交付本地 `.drawio` 文件               |
| 文件无法打开                     | 路径错误、文件关联异常                        | 输出文件绝对路径，引导手动打开                         |

---

## 10. 补充说明

1. 本技能**完全兼容 draw.io 官方标准**，所有生成文件可在任意版本 draw.io 客户端/网页端正常编辑。
2. 通用图表默认使用 draw.io 原生样式；仅命中硬件关键词时，自动加载硬件架构视觉规范。
3. 所有样式参数、色值、路由规则固定，保证多轮生成的硬件架构图风格统一。
4. 如需扩展样式（新增模块类型、信号类型），仅在「视觉样式规范」章节补充对应 style 属性即可。
