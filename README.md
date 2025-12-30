# 本地大模型助手

一个基于 Ollama 的本地大语言模型管理和对话应用，支持多模型切换、助手与角色扮演、对话历史管理等功能。

## ✨ 主要特性

- 🤖 **多模型支持**：集成 Qwen、GLM、DeepSeek、Llama 等主流开源模型
- 💬 **智能对话**：支持流式输出、上下文记忆、多轮对话
- 🎭 **助手与角色**：区分协作助手（专业工具）和角色扮演（娱乐互动）
- 📚 **对话管理**：基于 SQLite 数据库，自动保存对话历史
- 🎨 **主题切换**：内置深色/浅色主题，界面美观现代
- 📦 **一键下载**：从 ModelScope 自动下载并导入模型到 Ollama
- 🔄 **多模型会话**：同一对话中可切换不同模型，保留各自上下文
- ⚙️ **硬件检测**：自动检测 CPU、GPU、内存信息，推荐合适模型
- 🖼️ **个性化设置**：自定义用户名、头像、聊天背景轮播

## 📋 系统要求

- **操作系统**：Windows 10/11
- **Python**：3.10 或更高版本
- **内存**：建议 8GB 以上（根据模型大小而定）
- **显卡**：可选，支持 NVIDIA GPU 加速

## 🚀 快速开始

### 1. 安装依赖

运行安装脚本：

```bash
install.bat
```

或手动安装：

```bash
pip install -r requirements.txt
```

### 2. 安装 Ollama

**方式一：使用内置 Ollama**

将 `ollama.exe` 放到 `runtime/ollama/` 目录下

**方式二：系统安装**

从 [Ollama 官网](https://ollama.com/download) 下载并安装

### 3. 启动应用

```bash
start.bat
```

或直接运行：

```bash
python main.py
```

## 📖 使用指南

### 下载模型

1. 点击右上角 ⚙️ 进入设置页面
2. 在"模型管理"中选择想要的模型
3. 选择量化版本（推荐 Q4_K_M 或 Q8_0）
4. 点击"下载"按钮，等待下载和导入完成

### 开始对话

1. 点击左侧"＋ 新建对话"
2. 选择助手或角色（协作助手、角色扮演）
3. 在顶部选择模型
4. 输入消息开始对话

### 助手与角色管理

**协作助手**（💼）：专业工具型
- 编程助手、写作助手、翻译助手等
- 图标：🤖 👔 💼 📝 💻 🔧 📊 🎨 🌐 📚 🔬

**角色扮演**（🎭）：娱乐互动型
- 猫娘、霸道总裁、高冷御姐等
- 图标：🐱 🐶 🦊 🐰 🐻 🦄 🧝 👸 🤴 👑 🧙 🦸 ⚔️ 🎭

在设置页面可以添加、编辑、删除助手和角色。

### 个性化设置

1. 进入设置 → 个性化
2. 设置用户名和头像（上传图片或选择颜色）
3. 添加聊天背景图片（支持多张轮播）
4. 设置背景轮播间隔（3-60秒）

## 📁 项目结构

```
.
├── main.py                 # 程序入口
├── install.bat             # 安装脚本
├── start.bat               # 启动脚本
├── requirements.txt        # Python 依赖
├── config.json             # 应用配置
├── models.json             # 模型库配置
├── personal_settings.json  # 个性化设置
├── data.db                 # SQLite 数据库
│
├── core/                   # 核心功能模块
│   ├── chat_db.py          # 对话管理（数据库版本）
│   ├── database.py         # 数据库管理
│   ├── migration.py        # 数据迁移工具
│   ├── model_manager.py    # 模型下载管理
│   ├── ollama_manager.py   # Ollama 服务管理
│   └── hardware.py         # 硬件检测
│
├── ui/                     # 用户界面
│   ├── app.py              # 主窗口
│   ├── chat_page.py        # 对话���面
│   ├── settings_page.py    # 设置页面（单页滚动布局）
│   ├── components.py       # UI 组件
│   └── themes.py           # 主题管理
│
├── models/                 # 模型文件存储目录
├── ollama_models/          # Ollama 模型数据
├── backup_json/            # JSON 备份目录
└── runtime/                # 运行时文件
    └── ollama/             # 内置 Ollama
```

## 🎯 支持的模型

### 文本模型

- **Qwen 系列**：Qwen3-0.6B ~ 32B
- **GLM 系列**：GLM-Edge-4B、GLM-4-9B
- **DeepSeek 系列**：DeepSeek-R1-Distill 1.5B ~ 32B
- **Llama 系列**：Llama-3.2-1B ~ Llama-3-70B
- **其他**：Seed-OSS-36B、GPT-OSS-20B

### 代码模型

- **Qwen2.5-Coder**：0.5B ~ 32B
- **DeepSeek-Coder**：6.7B、V2-Lite-16B

### OCR 模型

- **DeepSeek-OCR**：8B

## ⚙️ 配置说明

### config.json

```json
{
  "app_name": "本地大模型助手",
  "version": "1.0.0",
  "ollama_host": "127.0.0.1",
  "ollama_port": 11434,
  "language": "zh_CN",
  "theme": "dark"
}
```

### personal_settings.json

```json
{
  "user_name": "我",
  "user_avatar_path": null,
  "user_avatar_color": "#007AFF",
  "chat_backgrounds": [],
  "background_interval": 5
}
```

## 🗄️ 数据存储

项目使用 SQLite3 数据库（Python 内置）存储数据：

- **对话历史**：conversations + messages 表
- **下载记录**：download_records 表
- **助手与角色**：personas 表（包含 type 字段区分类型）

数据库会自动创建和迁移，无需手动操作。

## 🎨 界面特性

### 设置页面
- **单页滚动布局**：所有设置项在一个页面中，向下滚动查看
- **智能导航激活**：滚动时自动激活对应的导航项
- **统一卡片样式**：所有设置区块使用统一的外边框和背景色
- **优化滚动条**：10px 宽度，半透明，圆角设计，悬停效果

### 助手与角色
- **双标签页布局**：协作助手和角色扮演分开管理
- **类型标签显示**：卡片上显示类型标签
- **主题色高亮**：角色扮演使用主题色边框
- **自定义图标**：支持上传自定义头像图片

### 个性化
- **用户头像**：支持上传图片或选择纯色背景
- **聊天背景**：支持多张背景图片自动轮播
- **轮播间隔**：可设置 3-60 秒的轮播间隔

## 🔧 常见问题

### Ollama 无法启动

- 检查 `runtime/ollama/ollama.exe` 是否存在
- 或确认系统已安装 Ollama
- 查看端口 11434 是否被占用

### 模型下载失败

- 检查网络连接
- 尝试使用国内镜像源
- 确认磁盘空间充足

### 对话无响应

- 确认 Ollama 服务正在运行
- 检查是否已加载模型
- 查看模型是否与硬件兼容

## 🛠️ 技术栈

- **界面框架**：PySide6 (Qt for Python)
- **模型服务**：Ollama
- **模型下载**：ModelScope
- **HTTP 请求**：requests
- **系统监控**：psutil
- **数据存储**：SQLite3 (Python 内置)

## 📝 开发说明

### 添加新模型

编辑 `models.json`，按照以下格式添加：

```json
{
  "id": "作者/模型ID",
  "name": "模型显示名称",
  "params": "参数量",
  "params_b": 参数量数值,
  "ctx": 上下文长度,
  "lang": ["zh", "en"],
  "distilled": false,
  "quantizations": ["Q4_K_M", "Q8_0"],
  "file_pattern": "文件名-{quant}.gguf"
}
```

### 自定义主题

修改 `ui/themes.py` 中的颜色配置：

```python
DARK_THEME = {
    'name': 'dark',
    'bg': '#1e1e1e',
    'text': '#ffffff',
    'accent': '#007AFF',
    # ...
}
```

### 添加助手或角色

通过设置页面的"助手与角色"区块添加：
- 选择类型：协作助手或角色扮演
- 设置名称、图标、描述
- 配置系统提示词
- 可选：上传自定义头像

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系方式

如有问题或建议，请通过 Issue 反馈。

---

**注意**：使用本应用下载和运行的模型需遵守各模型的开源协议。
