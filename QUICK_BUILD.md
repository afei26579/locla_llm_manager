# 快速打包指南

## 🚀 一键打包（推荐）

### Windows 用户

1. **双击运行**：
   ```
   build.bat
   ```

2. **等待完成**，可执行文件会生成在 `dist/` 目录

就这么简单！🎉

---

## 📋 详细步骤

### 1. 安装依赖

```bash
pip install -r requirements_build.txt
```

### 2. 创建启动资源（可选）

```bash
python create_splash.py
```

这会生成：
- `splash.png` - 启动画面
- `icon.ico` - 应用图标

**或者**使用你自己的图片：
- 将启动画面命名为 `splash.png`（推荐 600x400）
- 将图标命名为 `icon.ico`（推荐 256x256）
- 放在项目根目录

### 3. 执行打包

**方法 A：使用批处理脚本（Windows）**
```bash
build.bat
```

**方法 B：使用 Python 脚本**
```bash
python build_config.py
```

**方法 C：使用高级配置**
```bash
pyinstaller build_advanced.spec
```

### 4. 获取可执行文件

打包完成后：
```
dist/本地大模型助手.exe
```

---

## ⚡ 启动速度优化技巧

### 1. 使用虚拟环境打包

```bash
# 创建干净的虚拟环境
python -m venv venv_build
venv_build\Scripts\activate

# 只安装必需的依赖
pip install -r requirements_build.txt

# 执行打包
python build_config.py
```

**效果**：减少 30-50% 的体积和启动时间

### 2. 启用启动画面

启动画面可以：
- 提供视觉反馈
- 让用户知道程序正在启动
- 改善用户体验

已在 `main.py` 中集成，无需额外配置！

### 3. 代码优化

在 `main.py` 中已经添加了启动画面支持：
```python
# 显示启动进度
pyi_splash.update_text('正在初始化...')
pyi_splash.update_text('正在加载配置...')
pyi_splash.update_text('正在启动应用...')
```

---

## 🎨 自定义图标和启动画面

### 使用自己的图片

1. **准备图片**：
   - 启动画面：600x400 或 800x600 PNG
   - 图标：256x256 PNG

2. **转换图标为 ICO**：
   - 在线工具：https://convertio.co/zh/png-ico/
   - 或使用 `create_splash.py` 自动转换

3. **替换文件**：
   ```
   项目根目录/
   ├── splash.png  ← 你的启动画面
   └── icon.ico    ← 你的图标
   ```

4. **重新打包**：
   ```bash
   build.bat
   ```

### 设计建议

**启动画面**：
- 使用项目主题色（#007AFF）
- 包含应用名称
- 背景简洁
- 文字清晰

**图标**：
- 简洁明了
- 在小尺寸下也清晰
- 使用品牌色
- 避免过多细节

---

## 📦 打包配置说明

### 基础配置 (build_config.py)

适合大多数情况，包含：
- ✅ 单文件打包
- ✅ 无控制台窗口
- ✅ 自定义图标
- ✅ 启动画面
- ✅ 代码优化

### 高级配置 (build_advanced.spec)

提供更多控制：
- ✅ 排除不需要的模块
- ✅ UPX 压缩
- ✅ 自定义启动画面文字
- ✅ 版本信息

---

## 🔍 故障排除

### 问题 1：打包失败

**错误**：`ModuleNotFoundError: No module named 'xxx'`

**解决**：
```bash
pip install xxx
```

### 问题 2：启动很慢

**原因**：包含了太多不需要的模块

**解决**：
1. 使用干净的虚拟环境
2. 编辑 `build_advanced.spec`，添加到 `excludes`：
   ```python
   excludes = [
       'tkinter',
       'matplotlib',
       'numpy',
       # ... 其他不需要的模块
   ]
   ```

### 问题 3：图标不显示

**原因**：ICO 文件格式错误

**解决**：
1. 使用标准工具转换
2. 确保包含多个尺寸
3. 重新打包

### 问题 4：启动画面不显示

**原因**：图片路径或格式错误

**解决**：
1. 确保 `splash.png` 在项目根目录
2. 使用 PNG 格式
3. 尺寸不要太大（建议 600x400）

---

## 📊 打包结果对比

| 配置 | 文件大小 | 启动时间 | 适用场景 |
|------|---------|---------|---------|
| 基础配置 | ~150MB | 3-5秒 | 一般使用 |
| 虚拟环境 | ~100MB | 2-3秒 | 推荐 |
| 高级优化 | ~80MB | 1-2秒 | 追求极致 |

---

## ✅ 检查清单

打包前：
- [ ] 安装了 `pyinstaller`
- [ ] 准备了图标和启动画面
- [ ] 应用能正常运行
- [ ] 清理了测试数据

打包后：
- [ ] 可执行文件能启动
- [ ] 图标显示正确
- [ ] 启动画面显示正确
- [ ] 所有功能正常

---

## 🎯 推荐流程

**第一次打包**：
```bash
# 1. 创建资源
python create_splash.py

# 2. 一键打包
build.bat

# 3. 测试
dist\本地大模型助手.exe
```

**优化打包**：
```bash
# 1. 创建虚拟环境
python -m venv venv_build
venv_build\Scripts\activate

# 2. 安装依赖
pip install -r requirements_build.txt

# 3. 高级打包
pyinstaller build_advanced.spec

# 4. 测试
dist\本地大模型助手.exe
```

---

**祝打包顺利！** 🚀

有问题请查看 `BUILD_GUIDE.md` 获取更详细的说明。
