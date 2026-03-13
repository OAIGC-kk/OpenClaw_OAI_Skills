<div align="center">

# 🎨 OAI-SKILL

**强大的 OpenClaw 技能项目 | 图片 · 视频 · 音频 AI 生成**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com)

[English](#english) | [中文文档](#中文文档)

</div>

---

## 中文文档

### 📖 简介

OAI-SKILL 是一个为 [OpenClaw](https://github.com/openclaw) 设计的技能插件，通过 OAI API 实现多种 AI 生成能力。支持 **68 个 AI 模型端点**，涵盖图片生成、视频生成、语音克隆等多种场景。

### ✨ 核心功能

<table>
<tr>
<td width="50%">

#### 🎬 视频生成 (29个模型)

| 类型 | 模型 |
|------|------|
| **文生视频** | Vidu多参、Kling Omni、Veo3、Wan2.6、Grok、Sora2、Luma、Runway、海螺、可灵 |
| **图生视频** | Veo3、Wan2.6、Grok、Sora2、Seedance、Luma、Runway、海螺、可灵、OAI视频、多参视频、首尾帧、首中尾 |
| **视频处理** | 图片对口型、数字人对口型、视频对口型、舞蹈动作迁移、视频动作迁移、视频换人物 |

</td>
<td width="50%">

#### 🎨 图像生成 (48个模型)

| 类型 | 模型 |
|------|------|
| **文生图** | 阿里造相、Flux2-klein、Banana、豆包绘图、4o绘图、即梦3.0、可灵绘图、FLUX编辑、Wan2.2、千问文生图、Flux文生图 |
| **图像编辑** | Banana、豆包绘图、4o绘图、可灵绘图、FLUX编辑、Qwen生图、Qwen编辑、AI反推出图 |
| **图像处理** | AI抠图、AI扩图、AI线稿上色、吉卜力风格 |
| **图像修复** | 面部修复、高清放大、一键修手、老照片修复、智能消除 |
| **创意合成** | AI万物剪纸画、AI局部重绘、一键换衣、人物场景融合、人物姿态迁移等 20+ 模型 |

</td>
</tr>
</table>

#### 🎤 其他功能

- 🔊 **语音克隆** - AI 语音克隆，支持自定义文本
- 💰 **账户查询** - O币余额查询、VIP等级查询

---

### 🚀 快速开始

#### 前置要求

- Python 3.10+
- curl 命令行工具

#### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/OAI-SKILL.git
cd OAI-SKILL

# 2. 配置 API Key（二选一）

# 方式一：环境变量
export OAI_API_KEY="your-api-key-here"

# 方式二：配置文件
mkdir -p ~/.openclaw
echo '{"skills":{"entries":{"oaigc":{"apiKey":"your-api-key-here"}}}}' > ~/.openclaw/openclaw.json
```

#### 获取 API Key

1. 登录 [OAI 平台](https://oaigc.cn)
2. 点击右上角头像 → 个人中心
3. 点击「API令牌」
4. 复制密钥

---

### 📖 使用指南

#### 命令行模式

```bash
# ═══════════════════════════════════════════
# 🔐 账户管理
# ═══════════════════════════════════════════
python3 oaigc/scripts/oaigc.py --check      # 检查 API Key 状态
python3 oaigc/scripts/oaigc.py --balance    # 查询账户余额

# ═══════════════════════════════════════════
# 📋 应用查询
# ═══════════════════════════════════════════
python3 oaigc/scripts/oaigc.py --list                    # 列出所有应用
python3 oaigc/scripts/oaigc.py --list --type image       # 筛选图片类应用
python3 oaigc/scripts/oaigc.py --info z-imagewenshengt   # 查看应用详情

# ═══════════════════════════════════════════
# 🎨 图片生成
# ═══════════════════════════════════════════
# 文生图（默认阿里造相）
python3 oaigc/scripts/oaigc.py \
  --app z-imagewenshengt \
  --prompt "a cute puppy playing in a sunny garden, 4K cinematic" \
  --param aspect_ratio=16:9 \
  -o /tmp/openclaw/oai-output/puppy.png

# 图生图（使用Banana）
python3 oaigc/scripts/oaigc.py \
  --app banana \
  --prompt "transform into oil painting style" \
  --image https://example.com/photo.jpg \
  -o /tmp/openclaw/oai-output/oil_painting.png

# ═══════════════════════════════════════════
# 🎬 视频生成
# ═══════════════════════════════════════════
# 文生视频（Sora2）
python3 oaigc/scripts/oaigc.py \
  --app soraapi \
  --prompt "sweet girl dancing in neon city, MV style, cinematic" \
  --param duration=10 \
  --param aspect_ratio=16:9 \
  -o /tmp/openclaw/oai-output/dance.mp4

# 图生视频
python3 oaigc/scripts/oaigc.py \
  --app tushengshipin \
  --prompt "she starts dancing gracefully" \
  --image https://example.com/photo.png \
  -o /tmp/openclaw/oai-output/dance.mp4

# ═══════════════════════════════════════════
# 🎤 语音克隆
# ═══════════════════════════════════════════
python3 oaigc/scripts/oaigc.py \
  --app yuyinkelong \
  --audio https://example.com/voice.mp3 \
  --param text="你好，欢迎来到OAI平台！" \
  -o /tmp/openclaw/oai-output/speech.mp3
```

#### OpenClaw 集成模式

在 OpenClaw 中配置此技能后，用户可通过自然语言交互：

```
👤 用户: 帮我生成一张可爱的猫咪图片
🤖 AI: 好的！帮你选个绘图模型～
      
      📝 文生图（文字生成）
      1. 🎨 阿里造相 — 文生图，质量稳定
      2. 🔷 Flux2-klein — Flux轻量版
      ...
      
      说个数字或名字都行～

👤 用户: 用第一个
🤖 AI: 来啦！用阿里造相帮你生成的，花了 ¥0.35，等了 25 秒～ 🐱
      [发送生成的图片]
```

---

### ⚙️ 参数说明

| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| `--check` | - | 检查 API Key 状态 | `--check` |
| `--balance` | - | 查询账户余额 | `--balance` |
| `--list` | - | 列出所有应用 | `--list --type image` |
| `--info` | - | 查看应用详情 | `--info z-imagewenshengt` |
| `--app` | `-a` | 指定应用 ID | `--app soraapi` |
| `--task` | `-t` | 自动选择任务类型 | `--task text-to-image` |
| `--prompt` | `-p` | 提示词 | `--prompt "a cute dog"` |
| `--image` | `-i` | 输入图片 URL | `--image https://...` |
| `--video` | - | 输入视频 URL | `--video https://...` |
| `--audio` | - | 输入音频 URL | `--audio https://...` |
| `--param` | - | 额外参数 | `--param duration=10` |
| `--output` | `-o` | 输出文件路径 | `-o /tmp/result.png` |
| `--api-key` | `-k` | API Key | `--api-key sk-xxx` |

---

### 📊 输出格式

脚本执行后会输出以下信息：

```
OUTPUT_FILE:/tmp/openclaw/oai-output/result.png
COST:¥0.35
DURATION:30s
WAIT_TIME:45s
```

| 字段 | 说明 |
|------|------|
| `OUTPUT_FILE` | 生成的文件本地路径 |
| `COST` | O币消耗（API返回） |
| `DURATION` | 任务执行时间（API返回） |
| `WAIT_TIME` | 用户等待时间（轮询耗时） |

---

### 🎯 智能模型选择

#### 视频模型选择规则

| 用户场景 | 推荐模型 |
|----------|----------|
| 只有文字描述 | Vidu多参视频（默认） |
| 图片转视频 | 多参视频 |
| 图片+视频想跳舞 | 舞蹈动作迁移 |
| 视频+音频想对口型 | 视频对口型 |
| 照片+音频做数字人 | 数字人对口型 |
| 指定"Sora" | Sora2 |
| 指定"效果最好" | Sora2 |

#### 绘图模型选择规则

| 用户场景 | 推荐模型 |
|----------|----------|
| 只有文字 | 阿里造相（默认） |
| 编辑图片 | FLUX编辑 |
| 局部修改 | 香蕉局部重绘 |
| 消除水印 | 智能消除 |
| 换背景 | 万物换背景 |
| 抠图 | AI抠图 |
| 高清放大 | 高清放大 |

---

### ⚙️ 配置说明

#### 任务轮询配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 最长等待时间 | 25 分钟 | 超时后放弃 |
| 轮询间隔 | 5 秒 | 每次查询间隔 |
| 失败重试 | 5 次 | 连续失败后放弃 |

#### 特殊端点

| 端点 | 路径 | 说明 |
|------|------|------|
| Banana生图 | `/v1/banbana/generate` | 直接参数格式 |
| 任务查询 | `/v1/task/query/{taskId}` | 查询任务状态 |
| 模型列表 | `/v1/model/list` | 获取可用模型 |
| 账户信息 | `/v1/user/account-info` | 查询余额 |

---

### 📁 项目结构

```
OAI-SKILL/
├── .qoder/                        # Qoder 配置目录
│   ├── agents/
│   └── skills/
├── oaigc/                         # 核心技能目录
│   ├── SKILL.md                   # 技能说明文件（OpenClaw读取）
│   ├── data/
│   │   └── capabilities.json      # API 能力定义（68个端点）
│   └── scripts/
│       └── oaigc.py               # 主脚本（716行）
└── README.md                      # 本文件
```

---

### 📝 API 能力定义

`capabilities.json` 结构：

```json
{
  "version": "2026-03-13",
  "total": 68,
  "api_base_url": "https://oaigc.cn/api",
  "endpoints": [
    {
      "appId": "z-imagewenshengt",
      "name_cn": "阿里造相-文生图",
      "name_en": "Alibaba Text-to-Image",
      "task": "text-to-image",
      "output_type": "image",
      "category": "绘图接口",
      "modes": ["文生图"],
      "params": [...]
    }
  ],
  "special_endpoints": {...}
}
```

---

### 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

### 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

### 🔗 相关链接

| 链接 | 说明 |
|------|------|
| [OAI 平台](https://oaigc.cn) | AI 生成服务平台 |
| [OpenClaw](https://github.com/openclaw) | AI 技能框架 |

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！⭐**

Made with ❤️ by OAI-SKILL Team

</div>

---

<a name="english"></a>
## English

### 📖 Introduction

OAI-SKILL is a skill plugin designed for [OpenClaw](https://github.com/openclaw), providing various AI generation capabilities through the OAI API. It supports **68 AI model endpoints**, covering image generation, video generation, voice cloning, and more.

### ✨ Key Features

- 🎬 **Video Generation** - 29 models (text-to-video, image-to-video, video processing)
- 🎨 **Image Generation** - 48 models (text-to-image, image editing, restoration, creative synthesis)
- 🎤 **Voice Cloning** - AI voice cloning with custom text
- 💰 **Account Query** - Balance and VIP level queries

### 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/OAI-SKILL.git
cd OAI-SKILL

# Set API key
export OAI_API_KEY="your-api-key-here"

# Generate an image
python3 oaigc/scripts/oaigc.py \
  --app z-imagewenshengt \
  --prompt "a cute puppy, 4K cinematic" \
  -o /tmp/output.png

# Generate a video
python3 oaigc/scripts/oaigc.py \
  --app soraapi \
  --prompt "girl dancing in neon city" \
  --param duration=10 \
  -o /tmp/output.mp4
```

### 📄 License

This project is licensed under the MIT License.

---

<div align="center">

**⭐ If this project helps you, please give it a Star! ⭐**

</div>
