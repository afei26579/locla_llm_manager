# 主题系统说明

## 目录结构

```
themes/
  ├── dark.json          # 深色主题
  ├── light.json         # 浅色主题
  ├── custom/            # 自定义主题目录
  │   └── my_theme.json  # 用户自定义主题
  └── README.md          # 本文档
```

## 主题配置格式

每个主题文件是一个 JSON 文件，包含以下部分：

### 1. 元数据 (meta)

```json
{
  "meta": {
    "name": "dark",                    // 主题唯一标识
    "display_name": "深色",            // 显示名称
    "version": "1.0.0",                // 版本号
    "author": "System",                // 作者
    "description": "默认深色主题",     // 描述
    "base": null                       // 基础主题（继承用）
  }
}
```

### 2. 颜色配置 (colors)

#### 背景色 (background)
- `primary`: 主背景色
- `secondary`: 次级背景色
- `tertiary`: 第三级背景色

#### 表面色 (surface)
- `card`: 卡片背景色
- `input`: 输入框背景色
- `hover`: 悬停状态背景色
- `active`: 激活状态背景色

#### 边框色 (border)
- `default`: 默认边框色
- `focus`: 聚焦边框色

#### 强调色 (accent)
- `primary`: 主强调色
- `hover`: 悬停强调色
- `light`: 浅色强调色

#### 文字色 (text)
- `primary`: 主文字色
- `secondary`: 次级文字色
- `dim`: 暗淡文字色

#### 语义色 (semantic)
- `success`: 成功色
- `warning`: 警告色
- `error`: 错误色
- `info`: 信息色

#### 聊天气泡 (chat)
- `user_bubble`: 用户消息气泡色
- `ai_bubble`: AI 消息气泡色

#### 滚动条 (scrollbar)
- `track`: 滚动条轨道色
- `thumb`: 滚动条滑块色
- `thumb_hover`: 滚动条滑块悬停色

#### 其他组件
- `sidebar.background`: 侧边栏背景色
- `notification.background`: 通知栏背景色
- `settings.nav_bg`: 设置导航背景色
- `settings.nav_active`: 设置导航激活色
- `progress.background`: 进度条背景色
- `progress.fill`: 进度条填充色
- `info_row.background`: 信息行背景色

### 3. 字体配置 (typography)

```json
{
  "typography": {
    "font_family": "Microsoft YaHei UI, sans-serif",
    "font_size": {
      "small": 10,
      "normal": 13,
      "medium": 14,
      "large": 16,
      "xlarge": 20
    },
    "font_weight": {
      "normal": 400,
      "medium": 500,
      "semibold": 600,
      "bold": 700
    }
  }
}
```

### 4. 间距配置 (spacing)

```json
{
  "spacing": {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xxl": 32
  }
}
```

### 5. 圆角配置 (radius)

```json
{
  "radius": {
    "small": 6,
    "medium": 10,
    "large": 16,
    "xlarge": 20,
    "round": 9999
  }
}
```

## 创建自定义主题

### 方法 1: 从头创建

1. 在 `themes/custom/` 目录下创建新的 JSON 文件
2. 按照上述格式填写完整配置
3. 在应用中选择该主题

### 方法 2: 基于现有主题扩展

```json
{
  "meta": {
    "name": "my_dark",
    "display_name": "我的深色主题",
    "base": "dark"
  },
  "colors": {
    "accent": {
      "primary": "#FF6B6B"
    }
  }
}
```

只需指定 `base` 字段和要覆盖的配置即可。

## 支持的 UI 组件样式

新主题系统支持以下组件的完整样式定制：

### 基础组件
- ✅ 按钮 (QPushButton)
- ✅ 输入框 (QLineEdit, QTextEdit, QPlainTextEdit)
- ✅ 下拉框 (QComboBox)
- ✅ 复选框 (QCheckBox)
- ✅ 单选框 (QRadioButton)
- ✅ 滑块 (QSlider)
- ✅ 进度条 (QProgressBar)
- ✅ 数字输入框 (QSpinBox, QDoubleSpinBox)

### 容器组件
- ✅ 标签页 (QTabWidget, QTabBar)
- ✅ 滚动区域 (QScrollArea)
- ✅ 滚动条 (QScrollBar)
- ✅ 分组框 (QGroupBox)
- ✅ 分隔线 (QFrame)

### 视图组件
- ✅ 列表视图 (QListView)
- ✅ 树形视图 (QTreeView)
- ✅ 表格视图 (QTableView)

### 其他组件
- ✅ 菜单 (QMenu)
- ✅ 工具提示 (QToolTip)
- ✅ 对话框 (QDialog, QMessageBox)
- ✅ 状态栏 (QStatusBar)
- ✅ 工具栏 (QToolBar)
- ✅ 停靠窗口 (QDockWidget)
- ✅ 日期时间选择器 (QDateEdit, QTimeEdit, QDateTimeEdit)

## 使用示例

### Python 代码中使用

```python
from core.theme import get_theme_manager

# 获取主题管理器
theme = get_theme_manager()

# 切换主题
theme.set_theme('light')

# 获取当前主题颜色
colors = theme.colors
print(colors['accent'])  # 访问强调色

# 获取样式表
stylesheet = theme.get_stylesheet()
widget.setStyleSheet(stylesheet)

# 监听主题变更
theme.theme_changed.connect(on_theme_changed)
```

### 兼容旧代码

旧代码无需修改，自动使用新主题系统：

```python
from ui.themes import get_theme_manager, THEMES

theme = get_theme_manager()
colors = theme.colors  # 自动转换为扁平结构
```

## 颜色格式

支持以下颜色格式：

- 十六进制: `#RRGGBB` 或 `#RRGGBBAA`
- RGB: `rgb(255, 255, 255)`
- RGBA: `rgba(255, 255, 255, 0.5)`
- 透明: `transparent`

## 主题验证

主题加载时会自动验证：

1. 必需字段检查
2. 颜色格式验证
3. 配置完整性检查

验证失败的主题不会被加载，并在控制台输出错误信息。

## 最佳实践

1. **命名规范**: 使用小写字母和下划线，如 `my_custom_theme`
2. **颜色对比度**: 确保文字和背景有足够的对比度
3. **一致性**: 保持同类元素的视觉一致性
4. **测试**: 在不同场景下测试主题效果
5. **文档**: 为自定义主题添加说明文档

## 故障排除

### 主题未加载

1. 检查 JSON 格式是否正确
2. 确认文件位置正确
3. 查看控制台错误信息

### 颜色显示异常

1. 验证颜色格式是否正确
2. 检查是否缺少必需的颜色字段
3. 尝试使用基础主题继承

### 样式未生效

1. 确认已调用 `setStyleSheet()`
2. 检查是否有其他样式覆盖
3. 尝试重启应用

## 技术支持

如有问题，请查看：
- 项目文档
- 示例主题文件
- 源代码注释
