# TRG - Terminal Rhythm Game

一个在终端中运行的节奏游戏，支持键盘操作和自定义谱面。

## 功能特性

- 在终端中运行的节奏游戏
- 支持自定义谱面
- 键盘控制（默认D, F, J, K）
- 可配置的游戏设置

## 安装

### 要求

- Python 3.6+
- 所需依赖包见 `requirements.txt`

### 安装步骤
* 其实更建议直接使用Release中的可执行文件，而不是直接运行源代码，它通常更稳定，也更方便

1. 克隆仓库
```bash
git clone [仓库URL]
cd TRG_release
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

### 运行游戏
* 直接运行可执行文件
```bash
./Terminal_Rhythm_game
```
* 或者使用Python运行
```bash
python main_ansi.py
```

### 控制键位

游戏中的控制键位可在 `game_config.json` 中配置，默认包括：
- D, F, J, K 进行游戏
- 空格键暂停游戏

### 自定义谱面

1. 使用谱面编辑器创建或编辑谱面
```bash
python chart_editor.py
```

2. 将创建的谱面文件保存到 `charts/` 目录

3. 将音频文件放入 `audio/` 目录

## 项目结构

- `main_ansi.py` - 主程序入口
- `game_engine.py` - 游戏引擎核心
- `ansi_renderer.py` - 终端渲染器
- `audio_manager.py` - 音频管理
- `chart_parser.py` - 谱面解析器
- `config_manager.py` - 配置管理
- `saves/` - 游戏存档
- `charts/` - 谱面文件
- `audio/` - 音频文件

## 配置

游戏配置文件位于 `game_config.json`，可自定义以下内容：
- 音量设置
- 按键映射
- 游戏参数

## 许可证

本项目采用 MIT 许可证 - 详见 LICENSE 文件

## 开发

### 构建可执行文件

可以使用 PyInstaller 构建可执行文件：

```bash
pyinstaller --onefile Terminal_Rhythm_game.spec
```

生成的可执行文件将位于 `dist/` 目录中。