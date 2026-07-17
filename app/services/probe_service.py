"""媒体文件元信息获取服务（基于 ffprobe）"""
import os
import json
import subprocess
import re


def _humanize_bytes(size):
    if size is None:
        return None
    try:
        size = float(size)
    except (TypeError, ValueError):
        return None
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != 'B' else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def _humanize_duration(seconds):
    if seconds is None:
        return None
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    if h > 0:
        return f"{h}:{m:02d}:{s:05.2f}"
    return f"{m}:{s:05.2f}"


def probe_media(file_path):
    """使用 ffprobe 获取媒体文件元信息

    返回 dict：{ duration, width, height, size, size_human, duration_human, format_name, vcodec, acodec }
    失败时返回包含 file_size 的最小字典
    """
    result = {
        'duration': None,
        'width': None,
        'height': None,
        'size': None,
        'size_human': None,
        'duration_human': None,
        'format_name': None,
        'vcodec': None,
        'acodec': None,
    }

    if not file_path or not os.path.exists(file_path):
        return result

    try:
        size = os.path.getsize(file_path)
        result['size'] = size
        result['size_human'] = _humanize_bytes(size)
    except OSError:
        pass

    try:
        proc = subprocess.run(
            [
                'ffprobe', '-v', 'error',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                file_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            return result

        data = json.loads(proc.stdout)
        fmt = data.get('format') or {}
        if 'duration' in fmt:
            try:
                result['duration'] = float(fmt['duration'])
            except (TypeError, ValueError):
                pass

        result['format_name'] = fmt.get('format_name')

        for stream in data.get('streams') or []:
            codec_type = stream.get('codec_type')
            if codec_type == 'video' and result['width'] is None:
                result['width'] = stream.get('width')
                result['height'] = stream.get('height')
                result['vcodec'] = stream.get('codec_name')
            elif codec_type == 'audio' and result['acodec'] is None:
                result['acodec'] = stream.get('codec_name')

        result['duration_human'] = _humanize_duration(result['duration'])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass

    return result
