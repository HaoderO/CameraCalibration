---
name: spec-parser
description: 解析设计文档（PDF/Word/Excel/Markdown/DrawIO），提取模块名、端口、参数、协议、寄存器、时序等关键信息，输出结构化JSON
triggers:
  - 解析规格
  - 提取端口
  - 生成模块定义
  - spec解析
  - 读取PDF
  - 解析文档
  - 提取信息
  - 分析参考手册
  - 文档分析
  - 读取Word
  - 读取Excel
---

# Spec Parser - 规格解析器

解析多种格式的设计文档，提取结构化信息，为后续 RTL 生成和验证提供基础。

## 输入

| 格式 | 说明 |
|---|---|
| PDF | 芯片参考手册 (TRM)、算法论文、协议规范 |
| Word (.docx) | 设计规格书、接口定义文档 |
| Excel (.xlsx/.csv) | 寄存器列表、pinout 表、时序参数表 |
| Markdown (.md) | 设计文档、README、技术笔记 |
| DrawIO (.drawio) | 架构框图、时序图、状态机图 |

## 输出

结构化 JSON，格式如下：

```json
{
  "top_module": "top_name",
  "modules": [
    {
      "name": "mod_a",
      "type": "submodule",
      "ports": [
        {"name": "clk", "direction": "input", "width": 1, "type": "clock"},
        {"name": "rst_n", "direction": "input", "width": 1, "type": "reset"},
        {"name": "data_in", "direction": "input", "width": 32},
        {"name": "data_out", "direction": "output", "width": 32}
      ],
      "parameters": [
        {"name": "DATA_WIDTH", "default": 32}
      ],
      "protocol": "AXI4-Lite",
      "description": "模块功能描述"
    }
  ],
  "registers": [
    {"name": "CTRL", "offset": "0x00", "bits": "[0]", "attr": "RW", "reset": "1'b0", "desc": "模块使能"}
  ],
  "connections": [
    {"from_module": "mod_a", "from_port": "data_out", "to_module": "mod_b", "to_port": "data_in"}
  ],
  "clock_domains": [
    {"name": "clk_sys", "frequency": "100MHz"},
    {"name": "clk_peri", "frequency": "50MHz"}
  ],
  "timing_requirements": [
    {"description": "写操作地址在时钟上升沿前稳定至少2ns"}
  ]
}
```

## 流程

### Step 1: 识别格式并读取文档

| 文档格式 | 首选方法 | 备用方法 |
|---|---|---|
| Markdown (.md) | `Read` 工具直接读取 | — |
| PDF (<10页) | `Read` 工具直接读取 | `pdftotext -layout <file> -` |
| PDF (>10页) | `Read` 工具分页读取（≤20页/次） | `pdftotext -layout <file> -` |
| Word (.docx) | 导出为 PDF 后读取 | 解压 docx 提取 XML |
| Excel (.xlsx/.csv) | `Read` 工具直接读取 | 用 Python pandas 解析 |
| DrawIO (.drawio) | `Read` 工具读取 XML | 提取 mxCell 节点解析层次关系 |

**PDF 读取最佳实践**：
- 使用 `Read` 工具时指定 `pages` 参数分页读取，每次不超过 20 页
- 当 `Read` 工具无法解析 PDF 时，改用 `pdftotext -layout <file> -` 提取纯文本
- 使用 `-layout` 选项保留表格和缩进格式

### Step 2: 提取模块信息

1. 识别顶层模块名称
2. 列出所有子模块及其层级关系
3. 提取每个模块的功能描述

### Step 3: 提取端口信息

1. 端口名称、方向、位宽
2. 端口类型标记（clock / reset / data / control）
3. 接口协议识别（AXI/AHB/APB/TileLink/自定义握手）

### Step 4: 提取参数和寄存器

**参数提取**：
1. parameter / localparam 名称
2. 默认值
3. 参数用途说明

**寄存器提取**：
1. 寄存器名、偏移地址
2. 位域定义、属性 (RW/RO/W1C/W0C)
3. 复位值、功能描述

### Step 5: 分析连接关系

1. 模块间信号连接
2. 顶层端口到子模块的映射
3. 识别跨时钟域连接

### Step 6: 提取时序要求

1. 时钟频率和相位关系
2. 关键路径时序约束
3. 协议时序要求

## 脱敏规则

**输出中禁止出现参考方案的具体型号和公司名称，仅描述技术特征。**

## 示例

**输入**：读取设计规格文档

**输出**：
```json
{
  "modules": [{
    "name": "data_processor",
    "ports": [
      {"name": "clk", "direction": "input", "width": 1, "type": "clock"},
      {"name": "rst_n", "direction": "input", "width": 1, "type": "reset", "active": "low", "async": true},
      {"name": "data_in", "direction": "input", "width": 32},
      {"name": "data_valid", "direction": "input", "width": 1},
      {"name": "result", "direction": "output", "width": 64},
      {"name": "result_valid", "direction": "output", "width": 1}
    ],
    "description": "对输入数据进行乘累加运算"
  }],
  "registers": [
    {"name": "CTRL", "offset": "0x00", "bits": "[0]", "attr": "RW", "reset": "1'b0", "desc": "模块使能"},
    {"name": "CFG", "offset": "0x04", "bits": "[7:0]", "attr": "RW", "reset": "8'h00", "desc": "配置寄存器"}
  ]
}
```

## 下游 Skill

解析结果通常传递给：
- `rtl-generator` — 生成对应的 RTL 代码
- `testplan-gen` — 生成验证计划
- `consistency-check` — 检查设计与文档一致性

## 注意事项

1. 如果文档中有多个模块，确保层级关系正确
2. 位宽缺失时默认为 1
3. 复位类型需要明确（同步/异步、高/低有效）
4. 标注所有跨时钟域信号
5. 输出中避免出现参考方案的具体型号和公司名称，仅描述技术特征
