# WBSParserTool

WBSParserTool 是一个桌面端 WBS 任务拆解工具，用于将需求文档解析为工作分解结构和任务清单。

当前项目暂作为私人内部工具维护。

## 功能

- 支持上传 `.pdf`、`.docx`、`.txt` 需求文档。
- 支持本地规则解析，不依赖网络即可生成基础结果。
- 支持在线解析，可配置 OpenAI 兼容的 Chat Completions API。
- 自动生成两份交付文件：
  - `工作分解结构_WBS.docx`
  - `任务清单.xlsx`
- 支持 Windows 桌面安装包。
- 支持 macOS `.dmg` 安装包。
- Windows 和 macOS 都支持将交付文件一键保存到桌面。

## 目录结构

```text
WBSParserTool/
├── app.py                    # 应用入口
├── ui/                       # 桌面 UI
├── core/                     # 文档读取、解析、导出逻辑
├── config/                   # 本地配置管理
├── prompts/                  # 在线解析提示词
├── assets/                   # 图标和图片资源
├── examples/                 # 示例需求文档
├── build_exe.ps1             # Windows 主程序打包脚本
├── build_installer.ps1       # Windows 安装包打包脚本
├── build_mac_app.sh          # macOS app 打包脚本
└── build_mac_dmg.sh          # macOS dmg 打包脚本
```

## 本地运行

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

### macOS

```bash
python3 -m venv .venv-mac
source .venv-mac/bin/activate
pip install -r requirements.txt
python app.py
```

## 打包

### Windows

```powershell
.\build_exe.ps1
.\build_installer.ps1
```

生成结果：

```text
dist\WBSParserTool.exe
dist\WBSParserTool-Setup.exe
```

### macOS

macOS 安装包需要在 macOS 环境中构建：

```bash
chmod +x build_mac_app.sh build_mac_dmg.sh
./build_mac_dmg.sh
```

生成结果：

```text
dist/WBSParserTool.app
dist/WBSParserTool-mac.dmg
```

更详细说明见 [README_MAC.md](README_MAC.md)。

## API 配置

工具不内置任何 API Key。在线解析需要用户在应用内填写自己的接口信息。

配置文件保存到当前用户目录：

- Windows：`%APPDATA%\WBSParserTool\config.json`
- macOS：`~/Library/Application Support/WBSParserTool/config.json`

## 卸载

Windows 项目根目录提供：

```text
Uninstall-WBSParserTool.bat
```

双击该文件会卸载已安装的 WBSParserTool，包括安装目录、桌面快捷方式、开始菜单快捷方式，以及用户目录中的配置和临时文件。

## 注意

- `dist/`、`build/`、虚拟环境和临时输出不会提交到仓库。
- macOS 版本目前未做 Apple Developer 签名和 notarization，内部使用时如遇安全提示，可右键应用选择“打开”。
