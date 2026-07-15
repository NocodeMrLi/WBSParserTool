# macOS 打包说明

Mac 版需要在苹果电脑或 macOS 环境里打包，Windows 电脑不能直接生成可运行的 `.app` / `.dmg`。

## 生成 DMG

建议在 Mac 上先安装：

- Python 3.11 或更高版本，推荐使用 python.org 安装包，确保 Tkinter 可用。
- Xcode Command Line Tools：`xcode-select --install`

把整个项目复制到 Mac 后，在终端执行：

```bash
cd /path/to/WBSParserTool
chmod +x build_mac_app.sh build_mac_dmg.sh
./build_mac_dmg.sh
```

生成结果：

```text
dist/WBSParserTool.app
dist/WBSParserTool-mac.dmg
```

把 `dist/WBSParserTool-mac.dmg` 发给 Mac 用户即可。

## 安装方式

用户打开 `WBSParserTool-mac.dmg` 后，把 `WBSParserTool.app` 拖到 `Applications`。

如果 macOS 提示“无法验证开发者”，这是因为应用没有 Apple 开发者签名。内部使用可以右键应用选择“打开”；正式对外分发建议使用 Apple Developer 账号做签名和 notarization。

## 架构说明

Mac 包通常需要在目标架构上构建：

- Apple Silicon Mac 构建出来更适合 M 系列芯片。
- Intel Mac 构建出来更适合 Intel 芯片。

如果要做 Universal 通用包，需要额外配置 Universal Python 和依赖，这套脚本暂时先按当前 Mac 架构打包。

## 在线解析

Mac 版同样不内置 API Key。用户需要在工具里的 `API配置` 中填写自己的接口信息。
