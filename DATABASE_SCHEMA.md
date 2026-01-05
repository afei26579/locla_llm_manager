# 数据库表结构说明

本文档描述了应用程序使用的 SQLite 数据库（`data.db`）的完整表结构。

## 数据库概览

- **数据库文件**: `data.db`
- **数据库类型**: SQLite 3
- **管理模块**: `core/database.py`
- **表数量**: 6 个核心表

---

## 表结构详细说明

### 1. conversations（对话表）

存储用户的对话会话信息。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | TEXT | PRIMARY KEY | 对话唯一标识符（UUID） |
| title | TEXT | NOT NULL | 对话标题 |
| persona | TEXT | DEFAULT 'default' | 关联的人格/角色 key |
| created_at | TEXT | NOT NULL | 创建时间（ISO 8601 格式） |
| updated_at | TEXT | NOT NULL | 最后更新时间（ISO 8601 格式） |

**索引**:
- `idx_conversations_updated`: 按 `updated_at DESC` 排序，用于快速获取最近对话

**关系**:
- 一对多关系：一个对话包含多条消息（messages 表）
- 外键关联：`persona` 字段关联 `personas.key`

**使用场景**:
- 对话列表展示
- 对话历史管理
- 按时间排序查询

---

### 2. messages（消息表）

存储对话中的所有消息内容。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 消息自增 ID |
| conversation_id | TEXT | NOT NULL, FOREIGN KEY | 所属对话 ID |
| model | TEXT | NOT NULL | 使用的模型名称 |
| role | TEXT | NOT NULL | 消息角色（user/assistant/system） |
| content | TEXT | NOT NULL | 消息内容 |
| timestamp | TEXT | NOT NULL | 消息时间戳（ISO 8601 格式） |
| completed_at | TEXT | NULL | AI 回复完成时间（可选） |

**索引**:
- `idx_messages_conversation`: 按 `conversation_id` 索引，快速查询对话消息
- `idx_messages_timestamp`: 按 `timestamp` 索引，时间排序查询

**外键约束**:
- `conversation_id` → `conversations(id)` ON DELETE CASCADE（级联删除）

**使用场景**:
- 对话消息展示
- 按模型筛选消息
- 全文搜索消息内容
- 导出对话记录

---

### 3. download_records（下载记录表）

存储已下载的 GGUF 模型文件记录。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| record_key | TEXT | PRIMARY KEY | 记录唯一键（模型名-量化版本） |
| model_name | TEXT | NOT NULL | 模型名称 |
| ollama_name | TEXT | NOT NULL | Ollama 中的模型名称 |
| gguf_path | TEXT | NOT NULL | GGUF 文件本地路径 |
| quantization | TEXT | NULL | 量化版本（Q4_K_M, Q8_0 等） |
| model_id | TEXT | NULL | ModelScope 模型 ID |
| download_time | TEXT | NOT NULL | 下载时间（ISO 8601 格式） |
| file_exists | INTEGER | DEFAULT 1 | 文件是否存在（1=存在, 0=不存在） |

**使用场景**:
- 跟踪已下载的模型
- 避免重复下载
- 模型文件路径查找
- 模型管理和清理

**查询方式**:
- 精确匹配：`record_key`
- 模糊匹配：`model_name` 或 `ollama_name`

---

### 4. personas（人格配置表）

存储 AI 助手和角色的人格配置。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| key | TEXT | PRIMARY KEY | 人格唯一标识符 |
| name | TEXT | NOT NULL | 人格显示名称 |
| icon | TEXT | DEFAULT '🤖' | 图标 emoji |
| icon_path | TEXT | NULL | 自定义图标文件路径 |
| description | TEXT | NULL | 人格描述 |
| system_prompt | TEXT | NULL | 系统提示词 |
| type | TEXT | DEFAULT 'assistant' | 人格类型（assistant/roleplay） |
| background_images | TEXT | DEFAULT '' | 背景图片路径列表（JSON 字符串） |

**人格类型**:
- `assistant`: 功能型助手（如编程助手、翻译助手）
- `roleplay`: 角色扮演（如猫娘、总裁）

**使用场景**:
- 对话人格选择
- 自定义 AI 角色
- 系统提示词管理
- 个性化对话体验

**默认人格**:
- `default`: 默认助手（通用 AI 助手）

---

### 5. models（模型配置表）

存储推荐模型的配置信息。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | TEXT | PRIMARY KEY | 模型唯一 ID（ModelScope ID） |
| category | TEXT | NOT NULL | 模型分类（text/coder/ocr/image/video/audio） |
| subcategory | TEXT | NOT NULL | 子分类（如 general/chat/instruct） |
| name | TEXT | NOT NULL | 模型名称 |
| params | TEXT | NOT NULL | 参数规模（如 "7B", "13B"） |
| params_b | REAL | NOT NULL | 参数规模（十亿为单位，用于计算） |
| ctx | INTEGER | NOT NULL | 上下文长度（token 数） |
| lang | TEXT | NOT NULL | 支持语言（JSON 数组，如 ["zh", "en"]） |
| distilled | INTEGER | DEFAULT 0 | 是否为蒸馏模型（1=是, 0=否） |
| quantizations | TEXT | NOT NULL | 可用量化版本（JSON 数组） |
| file_pattern | TEXT | NOT NULL | 文件名匹配模式（正则表达式） |

**模型分类**:
- `text`: 文本生成模型
- `coder`: 代码生成模型
- `ocr`: 光学字符识别
- `image`: 图像生成
- `video`: 视频处理
- `audio`: 音频处理

**使用场景**:
- 推荐模型列表展示
- 根据硬件配置筛选模型
- 模型下载和管理
- 量化版本选择

**数据格式**:
- `lang`: JSON 数组，如 `["zh", "en"]`
- `quantizations`: JSON 数组，如 `["Q4_K_M", "Q8_0"]`

---

### 6. personal_settings（个人设置表）

存储用户的个人配置和偏好设置。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| key | TEXT | PRIMARY KEY | 设置项键名 |
| value | TEXT | NOT NULL | 设置项值（JSON 字符串） |

**常用设置项**:
- `avatar`: 用户头像路径
- `username`: 用户名称
- `background_images`: 背景图片列表
- `carousel_interval`: 轮播间隔（秒）
- `theme`: 主题设置（存储在 config.json，此处可选）

**使用场景**:
- 个性化设置存储
- 用户偏好管理
- 应用配置持久化

**数据格式**:
- 值以 JSON 字符串存储，支持复杂数据类型
- 读取时自动解析为原始类型

---

## 数据库操作 API

### 获取数据库实例

```python
from core.database import get_database

db = get_database()  # 单例模式
```

### 对话管理

```python
# 创建对话
db.create_conversation(conv_id="uuid", title="新对话", persona="default")

# 更新对话
db.update_conversation(conv_id="uuid", title="新标题")

# 获取对话
conv = db.get_conversation(conv_id="uuid")

# 列出所有对话
conversations = db.list_conversations(limit=100, offset=0)

# 删除对话（级联删除消息）
db.delete_conversation(conv_id="uuid")
```

### 消息管理

```python
# 添加消息
msg_id = db.add_message(
    conv_id="uuid",
    model="qwen2.5:7b",
    role="user",
    content="你好",
    timestamp="2025-12-29T10:00:00"
)

# 获取对话消息
messages = db.get_messages(conv_id="uuid")

# 按模型筛选
messages = db.get_messages_by_model(conv_id="uuid", model="qwen2.5:7b")

# 搜索消息
results = db.search_messages(keyword="Python", limit=50)
```

### 下载记录管理

```python
# 添加下载记录
db.add_download_record(
    record_key="Qwen2.5-7B-Q4_K_M",
    model_name="Qwen2.5-7B",
    ollama_name="qwen2.5:7b-q4",
    gguf_path="/path/to/model.gguf",
    quantization="Q4_K_M",
    model_id="Qwen/Qwen2.5-7B-Instruct-GGUF"
)

# 查找记录
record = db.find_download_record(name="Qwen2.5-7B")

# 列出所有记录
records = db.list_download_records()

# 删除记录
db.delete_download_record(record_key="Qwen2.5-7B-Q4_K_M")
```

### 人格管理

```python
# 添加人格
db.add_persona(
    key="coder",
    name="编程助手",
    icon="💻",
    description="专业的编程助手",
    system_prompt="你是一个专业的编程助手...",
    persona_type="assistant"
)

# 获取人格
persona = db.get_persona(key="coder")

# 列出所有人格
personas = db.list_personas()  # 返回字典 {key: persona_data}

# 删除人格
db.delete_persona(key="coder")
```

### 模型配置管理

```python
# 添加模型
db.add_model(
    model_id="Qwen/Qwen2.5-7B-Instruct-GGUF",
    category="text",
    subcategory="chat",
    name="Qwen2.5-7B",
    params="7B",
    params_b=7.0,
    ctx=32768,
    lang=["zh", "en"],
    distilled=False,
    quantizations=["Q4_K_M", "Q8_0"],
    file_pattern="*q4_k_m*.gguf"
)

# 获取模型
model = db.get_model(model_id="Qwen/Qwen2.5-7B-Instruct-GGUF")

# 列出所有模型（按分类组织）
models = db.list_models()  # 返回嵌套字典

# 删除模型
db.delete_model(model_id="Qwen/Qwen2.5-7B-Instruct-GGUF")
```

### 个人设置管理

```python
# 设置配置
db.set_personal_setting(key="avatar", value="/path/to/avatar.png")
db.set_personal_setting(key="carousel_interval", value=5)

# 获取配置
avatar = db.get_personal_setting(key="avatar", default="")
interval = db.get_personal_setting(key="carousel_interval", default=3)

# 获取所有配置
settings = db.get_all_personal_settings()

# 删除配置
db.delete_personal_setting(key="avatar")
```

---

## 数据迁移

### 从 JSON 迁移到数据库

应用启动时会自动检测并迁移旧的 JSON 数据：

```python
from core.migration import auto_migrate_on_startup

# 在 main.py 中自动调用
auto_migrate_on_startup()
```

**迁移内容**:
1. `history/*.json` → `conversations` + `messages` 表
2. `download_records.json` → `download_records` 表
3. `personas.json` → `personas` 表

**备份位置**: `backup_json/backup_YYYYMMDD_HHMMSS/`

### 手动迁移

```python
from core.migration import DataMigration

migration = DataMigration()

# 检查是否需要迁移
if migration.check_migration_needed():
    success, message = migration.migrate_all()
    print(message)

# 回滚到 JSON（从备份恢复）
success, message = migration.rollback()
```

---

## 数据导出

### 导出对话为 JSON

```python
# 导出单个对话（兼容旧格式）
conv_data = db.export_conversation_to_json(conv_id="uuid")

# 返回格式
{
    "id": "uuid",
    "title": "对话标题",
    "persona": "default",
    "created_at": "2025-12-29T10:00:00",
    "updated_at": "2025-12-29T12:00:00",
    "sessions": [
        {
            "model": "qwen2.5:7b",
            "started_at": "2025-12-29T10:00:00",
            "messages": [
                {
                    "role": "user",
                    "content": "你好",
                    "timestamp": "2025-12-29T10:00:00",
                    "completed_at": ""
                }
            ]
        }
    ]
}
```

---

## 数据库维护

### 关闭连接

```python
db.close()
```

### 数据库文件位置

- **开发环境**: `项目根目录/data.db`
- **打包后**: `exe 所在目录/data.db`

### 备份建议

定期备份 `data.db` 文件，包含所有用户数据：
- 对话历史
- 下载记录
- 人格配置
- 个人设置

---

## 注意事项

1. **线程安全**: 数据库连接使用 `check_same_thread=False`，支持多线程访问
2. **级联删除**: 删除对话时会自动删除关联的所有消息
3. **JSON 字段**: `lang`、`quantizations`、`background_images` 等字段存储为 JSON 字符串
4. **时间格式**: 所有时间字段使用 ISO 8601 格式（`YYYY-MM-DDTHH:MM:SS`）
5. **单例模式**: 使用 `get_database()` 获取全局唯一实例
6. **自动迁移**: 首次启动时自动从 JSON 迁移到数据库

---

## 版本历史

### v1.0（当前版本）
- 初始数据库结构
- 支持对话、消息、下载记录、人格、模型配置、个人设置
- 自动迁移功能
- 数据导出功能

### 迁移记录
- 添加 `personas.type` 字段（assistant/roleplay 分类）
- 添加 `personas.background_images` 字段（背景图片支持）
