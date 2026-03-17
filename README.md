# AstrBot 上下文统计插件 (Context Stat Plugin)

一个用于统计当前会话上下文长度的 AstrBot 插件，支持自动检测模型名称并显示 Token 使用情况。

## 功能特性

- 📊 自动检测当前使用的 AI 模型
- 💬 统计当前会话的消息数量
- 📝 计算字符数和 Token 数
- 💡 可视化进度条显示 Token 使用率
- ⚡ 支持手动设置 Token 上限

## 支持的模型

插件内置了 100+ 种模型的上下文长度配置，包括：

| 平台 | 模型示例 |
|------|---------|
| OpenAI | gpt-4o, gpt-4, gpt-3.5-turbo |
| Moonshot | kimi-k2.5, moonshot-v1-200k |
| Claude | claude-3-7-sonnet, claude-3-opus |
| DeepSeek | deepseek-chat, deepseek-reasoner |
| Gemini | gemini-2.5-pro, gemini-1.5-pro |
| 通义千问 | qwen-max, qwen-long |
| 智谱 AI | glm-4, glm-4-plus |
| Meta | llama-3.3-70b, llama-3.1-405b |

## 安装方法

### 方法一：通过命令行安装

```bash
# 进入 AstrBot 插件目录
cd <AstrBot安装路径>/data/plugins

# 克隆本仓库
git clone https://github.com/Wan-LaiQiu/astrbot_content_info.git

# 重启 AstrBot
```

### 方法二：手动安装

1. 下载本仓库代码
2. 将文件复制到 `AstrBot/data/plugins/astrbot_content_info/` 目录下
3. 重启 AstrBot

## 依赖安装

```bash
pip install tiktoken
```

或在 AstrBot 目录下运行：

```bash
pip install -r requirements.txt
```

## 使用说明

### 查看上下文统计

在会话中发送指令：

```
/context
```

返回示例：

```
📊 **上下文统计**
--------------------
🤖 模型：gpt-4o
💬 消息：12 条
📝 字符：3,456 字
当前使用: 892 tokens / 128000 tokens
███░░░░░░░░  约 0.7%
--------------------
```

### 手动设置 Token 上限

如果插件无法自动检测模型，或你想覆盖默认设置：

```
/context_limit 128000 gpt-4o
```

参数说明：
- `第一个参数`：Token 上限数值（必填）
- `第二个参数`：模型名称（可选）

例子：
```
/context_limit 128000                    # 只设置上限
/context_limit 256000 kimi-k2.5          # 设置上限并绑定模型名
```

## 常见问题

### 1. 显示"未知模型"

这表示插件无法自动检测到模型名称。你可以：

1. 使用 `/context_limit` 手动指定模型名
2. 确保使用的模型名包含常见关键词（如 gpt、claude、kimi 等）

### 2. Token 计算显示"依赖未安装"

运行以下命令安装依赖：

```bash
pip install tiktoken
```

### 3. 插件加载失败

检查 AstrBot 日志，确保：
1. 插件文件放置在正确的目录
2. 所有文件完整（main.py、models.json、requirements.txt）
3. Python 版本 >= 3.8

## 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | 插件主代码 |
| `models.json` | 模型上下文长度配置表 |
| `requirements.txt` | Python 依赖列表 |

## 技术细节

### 模型检测逻辑

插件按以下顺序尝试检测模型名：

1. 检查 `event` 对象及其 `provider` 属性
2. 检查 `conversation` 对象
3. 检查 `provider_manager` 中的 providers
4. 检查 `context` 中的 provider

### Token 计算方法

使用 OpenAI 的 `tiktoken` 库，采用 `cl100k_base` 编码进行计算。注意：不同模型的实际 Token 计算方式可能略有差异，本插件提供的数值仅供参考。

## 贡献与反馈

如果遇到问题或有建议，欢迎提交 Issue 或 Pull Request。

## 授权协议

MIT License
