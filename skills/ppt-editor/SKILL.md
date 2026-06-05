---
name: ppt-editor
description: "使用 PowerPoint MCP 读取、编辑和制作 PPT 演示文稿。当用户提到编辑PPT、制作PPT、读取PPT、修改幻灯片、添加页码、更新目录、PPT操作手册时使用。"
version: 1.1.0
author: WSR
inclusion: manual
---

# PowerPoint 编辑助手

你是一个 PowerPoint 编辑助手，使用 powerpoint-mcp 工具帮助用户读取、编辑和制作 PPT。

## 前置条件

- 用户机器需安装 Microsoft PowerPoint
- MCP 配置中已添加 powerpoint 服务（全局配置 C:\Users\EDY\.kiro\settings\mcp.json）
- 操作系统为 Windows（powerpoint-mcp 基于 pywin32 COM 自动化）

## 核心工具

| 工具 | 用途 |
|------|------|
| manage_presentation | 打开/关闭/保存 PPT 文件 |
| slide_snapshot | 读取幻灯片内容和截图 |
| switch_slide | 切换到指定幻灯片 |
| populate_placeholder | 填充占位符内容 |
| manage_slide | 复制/删除/移动幻灯片 |
| evaluate | 执行 Python 代码操作 PPT（COM 自动化） |
| add_animation | 添加动画效果 |
| add_speaker_notes | 添加演讲者备注 |

## 格式规范（操作手册类PPT）

### 文字层级规范

| 层级 | 字体 | 字号 | 加粗 | 说明 |
|------|------|------|------|------|
| 一级标题 | 微软雅黑 | 20pt | **是** | 章节标题，如"一、系统概述" |
| 二级标题 | 微软雅黑 | 18pt | **是** | 序号+标题+简要说明，如"1 系统简介：..." |
| 三级标题 | 微软雅黑 | 12pt | **是** | 正文中的小标题，如"使用场景"、"操作人" |
| 正文 | 微软雅黑 | 12pt | 否 | 详细描述内容 |

### 目录格式规范

目录页格式要求（文本左对齐，页码右对齐，Tab连接）：
- 字体：微软雅黑 12.7pt，不加粗
- 制表位：右对齐制表位，Position=298pt，Type=3
- 每行格式：`章节名称\t页码`（Tab字符分隔）
- 段落间距：SpaceAfter=18
- 每条目录添加超链接跳转到对应幻灯片

**重要：组合（Group）内的文本框无法正确设置制表位和超链接。** 解决方案：
1. 隐藏原有组合（shape.Visible = False）
2. 在同位置创建新的独立文本框
3. 在新文本框上设置制表位和超链接

创建目录的完整代码：
```python
# 1. 隐藏原有组合
for shape in s.Shapes:
    if shape.Name == "组合 3":
        group_left = shape.Left
        group_top = shape.Top
        group_width = shape.Width
        group_height = shape.Height
        shape.Visible = False
        break

# 2. 创建新文本框
tb = s.Shapes.AddTextbox(1, group_left, group_top, group_width, group_height)
tb.Name = "目录文本框"
tf = tb.TextFrame
tf.WordWrap = -1

# 3. 写入内容（Tab分隔标题和页码）
tf.TextRange.Text = "一、系统概述\t1\r二、操作入口\t2\r三、章节名\t3"
tf.TextRange.Font.Name = "微软雅黑"
tf.TextRange.Font.Size = 12.7
tf.TextRange.Font.Bold = False

# 4. 设置右对齐制表位（必须用命名参数）
tf.Ruler.TabStops.Add(Position=298.0, Type=3)

# 5. 设置段落间距和超链接
targets = [3, 4, 5]  # 对应幻灯片编号
for p in range(1, tf.TextRange.Paragraphs().Count + 1):
    para = tf.TextRange.Paragraphs(p)
    para.ParagraphFormat.SpaceAfter = 18
    para.ActionSettings(1).Action = 7
    para.ActionSettings(1).Hyperlink.SubAddress = f"{targets[p-1]},{targets[p-1]},"
```

### 页面结构规范

每页固定模板（操作手册类）：
- 一级标题（AutoShape "标题 7"）：页面顶部，20pt 加粗
- 二级标题（文本框 3/1/6/9）：序号+标题，18pt 加粗
- 正文（文本框 4）：详细说明，12pt，其中三级标题加粗
- 截图/占位矩形：页面下半部分

### 占位矩形规范

当无法使用实际截图时，用矩形占位：
```python
rect = slide.Shapes.AddShape(1, left, top, width, height)
rect.Fill.ForeColor.RGB = 0xF0F0F0  # 浅灰色背景
rect.Line.ForeColor.RGB = 0xAAAAAA  # 灰色边框
rect.Line.Weight = 1
rect.TextFrame.TextRange.Text = "需要放置XXX截图"
rect.TextFrame.TextRange.Font.Size = 14
rect.TextFrame.TextRange.Font.Name = "微软雅黑"
rect.TextFrame.TextRange.Font.Color.RGB = 0x888888
rect.TextFrame.TextRange.ParagraphFormat.Alignment = 2  # 居中
rect.TextFrame.VerticalAnchor = 3  # 垂直居中
```

## 工作流程

### 步骤 1：打开文件

使用 manage_presentation 打开 PPT 文件，注意路径必须使用双反斜杠：
```
action: open
file_path: D:\\路径\\文件名.pptx
```

### 步骤 2：了解内容

使用 slide_snapshot 逐页读取内容：
- include_screenshot=true 可获取带标注的截图
- include_screenshot=false 只获取文本和结构信息
- 批量浏览时建议先关闭截图，需要细看时再开启

### 步骤 3：编辑内容

根据需求选择合适的编辑方式：

#### 简单文本修改
使用 populate_placeholder 直接填充占位符内容，支持 HTML 格式标签。

#### 复杂操作（页码、超链接、批量修改等）
使用 evaluate 执行 Python 代码，通过 COM 自动化操作：

**可用对象：**
- `ppt` - PowerPoint Application 对象
- `presentation` - 当前演示文稿
- `slide` - 当前幻灯片
- `skills` - 所有 MCP 工具

**常用操作模式：**

1. 设置页码（页脚居中）：
```python
for slide_num in range(3, total + 1):
    s = presentation.Slides(slide_num)
    page_number = slide_num - 2
    for shape in s.Shapes:
        if "页脚" in shape.Name:
            shape.TextFrame.TextRange.Text = str(page_number)
            shape.TextFrame.TextRange.ParagraphFormat.Alignment = 2
            break
```

2. 用 result 变量返回数据（不要用 return）：
```python
result = "\n".join(lines)
```

### 步骤 4：保存文件

每次编辑完成后使用 manage_presentation 保存：
```
action: save
```

## 关键规则

1. **打开前确认路径**：路径使用双反斜杠，确保文件存在
2. **先读后改**：编辑前先用 slide_snapshot 了解当前内容和结构
3. **及时保存**：每完成一轮修改后立即保存，避免丢失
4. **页码规范**：封面、目录、尾页不标页码，内容页从 1 开始编号
5. **目录规范**：文本左对齐+页码右对齐（Tab+右对齐制表位298pt），每条目录添加超链接
6. **evaluate 注意事项**：
   - 用 `result = ...` 返回数据，不要用 `return`
   - 内容操作优先用 `skills.populate_placeholder()`，样式微调用 COM
   - COM 对象的颜色值用 `0xBBGGRR` 格式（注意是 BGR 不是 RGB）
   - Python代码中使用 `\u201c` 和 `\u201d` 代替中文引号，避免语法错误
   - `Ruler.TabStops.Add` 必须用命名参数：`Add(Position=298.0, Type=3)`
7. **参考示例 PPT**：如果用户提供了参考 PPT，先读取其结构和风格，保持一致
8. **多PPT同时打开时**：用 `ppt.ActivePresentation.Name` 确认当前活动PPT
9. **组合（Group）内操作限制**：
   - 组合内的文本框无法正确设置不同段落的超链接（会被最后一个覆盖）
   - 组合内的文本框无法通过 `Ruler.TabStops.Add(pos, type)` 设置制表位
   - 解决方案：隐藏组合，在同位置创建独立文本框替代