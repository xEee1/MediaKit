# 多媒体在线转换工具

一个基于 Flask 的在线多媒体转换工具，支持：

- 🎵 **视频转音频**（MP3 / WAV / M4A / FLAC / AAC / WMA / OGG）
- 🎞️ **视频转 GIF**（高质量 palette 方案，可裁剪时间区间）
- 🔁 **MOV 转 MP4**（流复制快速转换，自动回退 H.264 重新编码）

支持两种视频来源：
- **视频链接**：B 站、YouTube、抖音、微博、小红书等（基于 yt-dlp）
- **本地文件上传**：拖拽或点击上传，最大 200MB

## 功能特性

- 多平台视频下载（B 站、YouTube、抖音、微博、小红书等数百个平台）
- 多格式输出（MP3、WAV、M4A、FLAC、AAC、WMA、OGG、GIF、MP4）
- 音质档位可调（无损 / 320kbps / 190kbps / 128kbps / 64kbps）
- 自定义文件名，支持中文和特殊字符
- 实时进度条 + 状态文字
- 拖拽上传 + 文件类型校验
- 响应式界面，适配手机和电脑
- 清晰的错误提示
- 浏览器内音频/视频预览

## 技术栈

- 后端：Python Flask
- 前端：HTML5 + Bootstrap 5 + Font Awesome
- 视频下载：yt-dlp
- 音视频处理：ffmpeg（通过 imageio-ffmpeg 自动安装）

## 快速开始

### 1. 安装依赖

```bash
cd video_converter
pip install -r requirements.txt
```

### 2. 启动应用

```bash
python wsgi.py
```

访问 http://127.0.0.1:5000

### 3. 抖音视频下载（可选）

抖音部分视频需要登录态才能下载，如需下载抖音视频：

1. 在浏览器中登录抖音官网 `https://www.douyin.com`
2. 使用浏览器插件（如 EditThisCookie）导出 cookies
3. 导出为 **Netscape 格式**，保存到项目根目录下的 `cookies.txt`
4. 重新启动应用

**注意**：`cookies.txt` 已添加到 `.gitignore`，不会提交到 GitHub

## 项目结构

```
video_converter/
├── app/                        # 应用核心
│   ├── __init__.py             # 应用工厂
│   ├── routes.py               # 路由和 API
│   ├── utils.py                # 进度跟踪、任务 ID 生成
│   └── services/
│       ├── download_service.py # yt-dlp 视频下载
│       ├── convert_service.py  # ffmpeg 转换（音频/GIF/格式）
│       └── probe_service.py    # 媒体信息探测
├── static/
│   ├── css/style.css           # 自定义样式
│   └── js/main.js              # 前端交互
├── templates/index.html        # 主页面
├── tmp/                        # 临时文件（已忽略）
├── tests/                      # 单元测试
├── config.py                   # 配置管理
├── wsgi.py                     # 启动入口
├── requirements.txt
├── .env.example                # 环境变量示例
├── .gitignore
└── README.md
```

## API 接口

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回首页 |
| `/api/convert` | POST | 统一转换接口（FormData） |
| `/api/progress/<task_id>` | GET | 查询任务进度 |
| `/api/download/<path:filename>` | GET | 下载结果文件 |
| `/api/preview/<path:filename>` | GET | 预览文件（支持 Range 请求） |

### POST /api/convert

**FormData 字段**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `type` | 是 | `audio` / `gif` / `mov2mp4` |
| `source` | 是 | `url` / `upload` |
| `url` | url 模式必填 | 视频链接 |
| `videoFileName` | 否 | 自定义文件名（仅 url 模式） |
| `file` | upload 模式必填 | 上传的视频文件 |
| `format` | audio 模式 | `mp3` / `wav` / `m4a` / `flac` / `aac` / `wma` / `ogg` |
| `quality` | audio 模式 | `0` (无损) ~ `9` (经济) |
| `fps` | gif 模式 | 帧率 |
| `width` | gif 模式 | 输出宽度（px） |
| `startTime` | 否 | GIF 起始时间（秒数或 `HH:MM:SS`） |
| `duration` | 否 | GIF 持续时长 |

**响应示例**：

```json
{
  "success": true,
  "task_id": "abc12345",
  "type": "audio",
  "primary": { "filename": "myvideo.mp3", "label": "下载音频 (MP3)" },
  "secondary": { "filename": "myvideo.mp4", "label": "下载原视频" },
  "source_filename": "myvideo"
}
```

## 运行测试

```bash
python -m pytest tests/ -v
```

## 常见问题

### yt-dlp 问题
- 无法下载特定平台：检查 yt-dlp 版本，更新至最新
- 抖音需要 cookies：参考上方"抖音视频下载"说明

### ffmpeg 问题
- 命令未找到：ffmpeg 通过 imageio-ffmpeg 自动安装，无需手动配置
- 转换失败：检查视频文件完整性

### 端口占用
通过环境变量 `FLASK_RUN_PORT` 修改端口。

## 许可证

MIT License