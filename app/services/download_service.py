import os
import re
import requests
import yt_dlp
import imageio_ffmpeg
from app.utils import update_progress


def _sanitize_filename(name):
    if name is None:
        return None
    sanitized = re.sub(r'[\\/:*?"<>|\r\n\t]', '_', str(name))
    sanitized = sanitized.strip().strip('.')[:100]
    return sanitized or 'video'


def _resolve_douyin_url(url):
    if 'douyin.com' not in url:
        return url
    try:
        response = requests.head(url, allow_redirects=True, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36'
        })
        return response.url
    except Exception:
        return url


def _extract_url_from_text(text):
    url_pattern = re.compile(r'https?://[^\s]+')
    matches = url_pattern.findall(text)
    if matches:
        return matches[0]
    return text


def download_video(url, output_dir, custom_filename=None, task_id=None):
    os.makedirs(output_dir, exist_ok=True)

    base_name = _sanitize_filename(custom_filename) if custom_filename else f"video_{task_id}"

    update_progress(task_id, 5, "解析视频链接...")

    url = _extract_url_from_text(url)

    if 'douyin.com' in url or 'v.douyin.com' in url:
        url = _resolve_douyin_url(url)
        update_progress(task_id, 10, f"解析完成: {url[:50]}...")

    update_progress(task_id, 15, "开始下载视频...")

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    local_ffmpeg_dir = os.path.join(project_root, 'ffmpeg')
    local_ffmpeg_exe = os.path.join(local_ffmpeg_dir, 'ffmpeg.exe')
    
    if not os.path.exists(local_ffmpeg_dir):
        os.makedirs(local_ffmpeg_dir)
    
    if not os.path.exists(local_ffmpeg_exe):
        import shutil
        shutil.copy2(ffmpeg_path, local_ffmpeg_exe)
    
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, base_name + '.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36',
        'ffmpeg_location': local_ffmpeg_dir,
    }

    cookies_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'cookies.txt')
    if os.path.exists(cookies_file):
        ydl_opts['cookiefile'] = cookies_file
        update_progress(task_id, 12, "检测到cookies文件，使用登录态下载...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            
            if os.path.exists(filename):
                update_progress(task_id, 40, "视频下载完成")
                return filename
            else:
                files = [f for f in os.listdir(output_dir) if f.startswith(base_name)]
                if files:
                    update_progress(task_id, 40, "视频下载完成")
                    return os.path.join(output_dir, files[0])
                raise Exception("视频下载失败: 未找到下载文件")
    except yt_dlp.DownloadError as e:
        error_msg = str(e)
        if "Fresh cookies" in error_msg or "fresh cookies" in error_msg:
            error_msg = (
                "需要抖音登录态才能下载此视频。\n"
                "解决方法：\n"
                "1. 在浏览器中登录抖音官网 (https://www.douyin.com)\n"
                "2. 使用浏览器插件导出cookies为Netscape格式\n"
                "3. 将文件保存为项目根目录下的 'cookies.txt'\n"
                "4. 刷新页面重新尝试"
            )
        elif "Unsupported URL" in error_msg or "unsupported URL" in error_msg:
            error_msg = f"无法解析该视频链接，请确认链接是否有效。原始错误: {error_msg[:100]}"
        raise Exception(f"视频下载失败: {error_msg}")
    except Exception as e:
        raise Exception(f"视频下载失败: {str(e)[:200]}")
