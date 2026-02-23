# TUI 模式说明

## 概述

MaiMaiNotePad 后端管理工具 (`manage.sh`) 集成了 TUI（Terminal User Interface）功能，提供更直观的图形化菜单界面。

## TUI vs CLI 模式对比

| 特性 | TUI 模式 | CLI 模式 |
|------|---------|---------|
| 界面 | 图形化菜单 | 文本菜单 |
| 导航 | 方向键 + 回车 | 输入数字 + 回车 |
| 鼠标支持 | 支持（部分终端） | 不支持 |
| 依赖 | 需要 dialog 工具 | 无依赖 |
| 兼容性 | 较好 | 最佳 |
| 视觉效果 | 更美观 | 简洁 |

## 自动模式检测

管理工具会自动检测系统环境并选择合适的模式：

```bash
./manage.sh
```

**检测逻辑**：
1. 如果没有命令行参数（交互式模式）
2. 检查系统是否安装了 `dialog` 工具
3. 如果安装了 → 使用 TUI 模式
4. 如果未安装 → 使用 CLI 模式，并显示安装提示（仅首次）

## dialog 安装提示

如果你的系统没有安装 `dialog`，运行 `./manage.sh` 时会看到一个友好的提示框：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  💡 提示：安装 dialog 获得更好的 TUI 体验
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  当前使用 CLI 模式。安装 dialog 工具后可以使用更直观的 TUI 界面。

  TUI 模式特性：
    • 图形化菜单界面
    • 方向键导航
    • 支持鼠标操作（部分终端）
    • 更直观的用户体验

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  安装方法：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  macOS:
    brew install dialog

  Linux:
    sudo apt-get install dialog

  Windows:
    推荐使用以下方式之一：
    1. WSL (Windows Subsystem for Linux) - 推荐
       wsl --install
       然后在 WSL 中: sudo apt-get install dialog
    2. Git Bash - dialog 支持有限，建议使用 CLI 模式
    3. Cygwin - 安装时选择 dialog 包
    
    注意：Windows 环境建议直接使用 CLI 模式

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  选项：
    y    - 现在安装 dialog（需要管理员权限）
    n    - 继续使用 CLI 模式
    c    - 不再提示（创建标记文件）

请选择 [y/n/c]:
```

**选项说明**：
- **输入 y**：立即安装 dialog（需要管理员权限）
  - macOS: 使用 Homebrew 安装
  - Ubuntu/Debian: 使用 apt-get 安装
  - CentOS/RHEL: 使用 yum 安装
  - Arch Linux: 使用 pacman 安装
  - Windows: 显示安装指南，不提供自动安装
  - 安装成功后脚本会自动退出，请重新运行以使用 TUI 模式
  
- **输入 n**：继续使用 CLI 模式，下次运行时仍会显示此提示

- **输入 c**：不再提示，在 `pyproject.toml` 中设置 `hide_dialog_tip = true`

**Windows 用户特别说明**：
- 系统会显示详细的安装指南
- 不提供自动安装功能
- 只有两个选项：回车（继续）或 c（不再提示）
- 建议直接使用 CLI 模式：`./manage.sh --cli`

**重要提示**：
- 默认情况下，每次运行都会显示此提示
- 只有选择 'c' 才会在 `pyproject.toml` 中设置 `hide_dialog_tip = true`
- 如果想再次看到提示，编辑 `pyproject.toml`，将 `hide_dialog_tip` 改为 `false`

## 强制使用 CLI 模式

如果你想强制使用 CLI 模式（即使安装了 dialog），可以使用 `--cli` 参数：

```bash
./manage.sh --cli
```

**使用场景**：
- 在脚本中调用管理工具
- 终端不兼容 dialog
- 个人偏好文本界面
- 远程 SSH 连接不稳定

## 安装 dialog

### macOS

```bash
brew install dialog
```

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install dialog
```

### CentOS/RHEL

```bash
sudo yum install dialog
```

### Arch Linux

```bash
sudo pacman -S dialog
```

### Windows

Windows 用户推荐使用以下方式之一：

#### 1. WSL (Windows Subsystem for Linux) - 推荐

```bash
# 安装 WSL
wsl --install

# 在 WSL 中安装 dialog
sudo apt-get update
sudo apt-get install dialog
```

**优势**：
- 完整的 Linux 环境
- 最佳兼容性
- 完全支持 TUI 模式

#### 2. Git Bash

下载：https://git-scm.com/download/win

**注意**：
- dialog 支持有限
- 建议使用 CLI 模式
- 适合轻量级使用

#### 3. Cygwin

下载：https://www.cygwin.com/

安装时选择 `dialog` 包。

**建议**：Windows 用户直接使用 CLI 模式获得最佳体验：
```bash
./manage.sh --cli
```

### 验证安装

```bash
dialog --version
```

## TUI 模式操作指南

### 基本操作

- **方向键（↑↓）**：在菜单项之间移动
- **回车键**：选择当前菜单项
- **ESC 键**：返回上级菜单或退出
- **Tab 键**：在按钮之间切换（对话框中）
- **空格键**：选择/取消选择（复选框）

### 菜单导航

1. **主菜单**：5 个主要功能分类
   - 环境管理
   - 服务管理
   - 测试相关
   - 项目维护
   - 高级操作

2. **子菜单**：每个分类下的具体功能
   - 使用方向键选择
   - 按回车键执行
   - 按 ESC 或选择 "0. 返回" 返回上级

3. **对话框**：
   - **信息框**：显示操作结果，按回车继续
   - **确认框**：Yes/No 选择，Tab 切换，回车确认
   - **输入框**：输入文本，回车确认

### 快捷键

- **ESC**：快速返回上级菜单
- **Ctrl+C**：强制退出程序
- **h 或 H**：查看帮助（主菜单中）

## 常见问题

### Q: TUI 界面显示乱码或异常？

**原因**：终端不兼容或 TERM 环境变量设置不正确

**解决方案**：
1. 使用 `--cli` 参数切换到 CLI 模式
2. 检查 TERM 环境变量：
   ```bash
   echo $TERM
   # 应该是 xterm-256color 或类似值
   ```
3. 更新终端模拟器到最新版本

### Q: 鼠标点击无效？

**原因**：部分终端不支持鼠标操作

**解决方案**：
- 使用键盘操作（方向键 + 回车）
- 或切换到支持鼠标的终端（如 iTerm2、GNOME Terminal）

### Q: 如何在脚本中使用管理工具？

**建议**：在脚本中使用直接命令模式，而不是交互式菜单：

```bash
#!/bin/bash
# 不要使用交互式菜单
# ./manage.sh  # ❌

# 使用直接命令
./manage.sh test           # ✅
./manage.sh start-dev      # ✅
./manage.sh cleanup        # ✅
```

### Q: 可以卸载 dialog 吗？

**可以**。卸载 dialog 后，管理工具会自动使用 CLI 模式：

```bash
# macOS
brew uninstall dialog

# Ubuntu/Debian
sudo apt-get remove dialog

# CentOS/RHEL
sudo yum remove dialog
```

## 技术实现

### 核心组件

1. **模式检测**：
   ```bash
   USE_TUI=false
   if [ $# -eq 0 ]; then
       if command -v dialog >/dev/null 2>&1; then
           USE_TUI=true
       fi
   fi
   ```

2. **TUI 菜单函数**：
   - `show_tui_main_menu()` - 主菜单
   - `show_tui_env_menu()` - 环境管理菜单
   - `show_tui_service_menu()` - 服务管理菜单
   - 等等...

3. **对话框函数**：
   - `show_tui_info()` - 信息对话框
   - `show_tui_confirm()` - 确认对话框
   - `show_tui_input()` - 输入对话框
   - `show_tui_progress()` - 进度提示

4. **主程序循环**：
   ```bash
   while true; do
       if [ "$USE_TUI" = true ]; then
           # TUI 模式处理
       else
           # CLI 模式处理
       fi
   done
   ```

### dialog 工具选项

常用的 dialog 选项：

- `--menu`：创建菜单
- `--msgbox`：显示消息框
- `--yesno`：显示确认对话框
- `--inputbox`：显示输入框
- `--textbox`：显示文本文件内容
- `--infobox`：显示信息框（不等待用户输入）
- `--clear`：清屏
- `--title`：设置标题

## 最佳实践

1. **日常使用**：使用 TUI 模式（更直观）
2. **脚本自动化**：使用直接命令模式
3. **远程连接**：根据网络情况选择 CLI 或 TUI
4. **调试问题**：使用 CLI 模式（输出更清晰）
5. **CI/CD 环境**：使用直接命令模式

## 相关文档

- [管理工具使用指南](./管理工具使用指南.md) - 完整功能说明
- [管理工具快速参考](./管理工具快速参考.md) - 命令速查表
- [环境检测功能说明](./环境检测功能说明.md) - 环境检测详解

---

**文档信息**

| 项目 | 内容 |
|------|------|
| 创建日期 | 2026-02-24 |
| 最后更新 | 2026-02-24 |
| 维护者 | cuckoo711 |
| 状态 | ✅ 已完成 |
