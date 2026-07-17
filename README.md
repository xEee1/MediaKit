# MediaKit - 多媒体在线转换工具

一个基于 Flask 的在线多媒体转换工具，支持视频转音频、视频转 GIF、MOV 转 MP4，以及多平台视频下载。

## ✨ 功能特性

- 🎵 **视频转音频**（MP3 / WAV / M4A / FLAC / AAC / WMA / OGG）
- 🎞️ **视频转 GIF**（高质量 palette 方案，可裁剪时间区间）
- 🔁 **MOV 转 MP4**（流复制快速转换，自动回退 H.264 重新编码）
- 📥 **多平台视频下载**（B站、YouTube、抖音、微博、小红书等）
- 📤 **本地文件上传**（拖拽上传，最大 5GB）
- 🎚️ **音质档位可调**（无损 / 320kbps / 190kbps / 128kbps / 64kbps）
- 📱 **响应式界面**，适配手机和电脑

## 🚀 快速开始

### 1. 安装依赖

```bash
cd MediaKit
pip install -r requirements.txt
```

### 2. 启动应用

```bash
python wsgi.py
```

访问 http://127.0.0.1:5000

### 3. 抖音视频下载（可选）

抖音部分视频需要登录态才能下载，如需下载抖音视频，你需要添加自己的 cookies 文件：

1. 在浏览器中登录抖音官网 `https://www.douyin.com`
2. 使用浏览器插件（如 **EditThisCookie**）导出 cookies
3. 选择导出格式为 **Netscape 格式**，保存到项目根目录下，文件名为 `cookies.txt`
4. 重新启动应用

> **重要说明**：
> - `cookies.txt` 文件包含你的个人登录信息，请妥善保管
> - 该文件已添加到 `.gitignore`，不会被提交到 GitHub，确保你的隐私安全
> - 如果不添加 `cookies.txt`，抖音部分视频可能无法下载，但不影响其他平台（B站、YouTube等）的使用

## 📁 项目结构

```
MediaKit/
├── app/                    # 应用核心
│   ├── routes.py           # 路由和 API
│   └── services/           # 业务服务
├── static/                 # 前端资源
├── templates/              # HTML 模板
├── tests/                  # 单元测试
├── config.py               # 配置管理
├── wsgi.py                 # 启动入口
└── requirements.txt        # 依赖列表
```

## ❓ 常见问题

### 无法下载抖音视频？
抖音部分视频需要登录态，请参考上方"抖音视频下载"说明添加 `cookies.txt`。

### 转换失败？
检查视频文件完整性，确保磁盘有足够空间。

### 端口被占用？
通过环境变量 `FLASK_RUN_PORT` 修改端口：
```bash
set FLASK_RUN_PORT=5001
python wsgi.py
```

## 📄 许可证

MIT License
