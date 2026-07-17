import os
import re
import subprocess
import imageio_ffmpeg

from app.utils import update_progress

def _get_ffmpeg_path():
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    local_ffmpeg_dir = os.path.join(project_root, 'ffmpeg')
    local_ffmpeg_exe = os.path.join(local_ffmpeg_dir, 'ffmpeg.exe')
    
    if not os.path.exists(local_ffmpeg_dir):
        os.makedirs(local_ffmpeg_dir)
    
    if not os.path.exists(local_ffmpeg_exe):
        import shutil
        shutil.copy2(ffmpeg_path, local_ffmpeg_exe)
    
    return local_ffmpeg_exe

CODEC_MAP = {
    'mp3': {'codec': 'libmp3lame', 'quality_prefix': '-q:a'},
    'wav': {'codec': 'pcm_s16le', 'quality_prefix': '-b:a'},
    'm4a': {'codec': 'aac', 'quality_prefix': '-b:a'},
    'flac': {'codec': 'flac', 'quality_prefix': '-compression_level'},
    'aac': {'codec': 'aac', 'quality_prefix': '-b:a'},
    'wma': {'codec': 'wmav2', 'quality_prefix': '-q:a'},
    'ogg': {'codec': 'libvorbis', 'quality_prefix': '-q:a'},
}

QUALITY_DEFAULT = {
    'mp3': 4,
    'wav': '1411k',
    'm4a': '192k',
    'flac': 5,
    'aac': '192k',
    'wma': 3,
    'ogg': 4,
}


def _ensure_height_even(value):
    """ffmpeg palette filter 需要 height 为偶数"""
    return value if value % 2 == 0 else value - 1


def _parse_time(value):
    """解析 HH:MM:SS 或秒数字符串"""
    if not value:
        return None
    value = str(value).strip()
    if re.match(r'^\d+(\.\d+)?$', value):
        return value
    if re.match(r'^\d{1,2}:\d{1,2}(:\d{1,2})?$', value):
        return value
    return None


def convert_to_audio(video_path, output_dir, format='mp3', quality=None, task_id=None):
    """视频转音频"""
    if format not in CODEC_MAP:
        raise Exception(f"不支持的音频格式: {format}")

    update_progress(task_id, 60, "开始转换音频...")

    codec_info = CODEC_MAP[format]
    quality_value = quality if quality is not None else QUALITY_DEFAULT[format]

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.{format}")

    cmd = [
        _get_ffmpeg_path(), '-y', '-i', video_path,
        '-vn',
        '-acodec', codec_info['codec'],
        codec_info['quality_prefix'], str(quality_value),
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        error_msg = (result.stderr or '').strip().split('\n')[-1] if result.stderr else 'ffmpeg 执行失败'
        raise Exception(f"音频转换失败: {error_msg}")

    if not os.path.exists(output_path):
        raise Exception("音频转换失败: 输出文件未生成")

    update_progress(task_id, 90, "音频转换完成")
    return output_path


def convert_to_gif(video_path, output_dir, fps=10, width=480, start_time=None, duration=None, task_id=None):
    """视频转 GIF（两阶段 palette 方案，输出质量高）"""
    update_progress(task_id, 55, "正在准备 GIF 调色板...")

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.gif")

    width = int(width) if width else 480
    fps = max(1, min(30, int(fps) if fps else 10))
    height = _ensure_height_even(int(width * 9 // 16))

    scale_filter = f"scale={width}:{height}:flags=lanczos"

    # 通用前置：可选裁剪 + 缩放 + fps
    def pre_args():
        args = []
        s = _parse_time(start_time)
        d = _parse_time(duration)
        if s is not None:
            args += ['-ss', s]
        if d is not None:
            args += ['-t', d]
        return args

    pre = pre_args()

    # 第一阶段：生成调色板
    palette_path = os.path.join(output_dir, f"{base_name}_palette.png")
    palette_filter = f"{scale_filter},palettegen=stats_mode=diff"
    cmd_palette = [
        _get_ffmpeg_path(), '-y', *pre, '-i', video_path,
        '-vf', palette_filter,
        palette_path,
    ]
    result = subprocess.run(cmd_palette, capture_output=True, text=True)
    if result.returncode != 0:
        error_msg = (result.stderr or '').strip().split('\n')[-1] if result.stderr else 'ffmpeg 调色板生成失败'
        raise Exception(f"GIF 调色板生成失败: {error_msg}")

    update_progress(task_id, 75, "正在生成 GIF...")

    # 第二阶段：使用调色板生成 GIF
    gif_filter = f"{scale_filter}[x];[x][1:v]paletteuse=dither=sierra2_4a"
    cmd_gif = [
        _get_ffmpeg_path(), '-y', *pre, '-i', video_path, '-i', palette_path,
        '-lavfi', gif_filter,
        '-loop', '0',
        output_path,
    ]
    result = subprocess.run(cmd_gif, capture_output=True, text=True)
    # 清理调色板临时文件
    try:
        os.remove(palette_path)
    except OSError:
        pass
    if result.returncode != 0:
        error_msg = (result.stderr or '').strip().split('\n')[-1] if result.stderr else 'ffmpeg GIF 生成失败'
        raise Exception(f"GIF 生成失败: {error_msg}")

    if not os.path.exists(output_path):
        raise Exception("GIF 生成失败: 输出文件未生成")

    update_progress(task_id, 90, "GIF 转换完成")
    return output_path


def convert_video_format(video_path, output_dir, target_format='mp4', task_id=None):
    """视频格式转换（如 MOV -> MP4）"""
    update_progress(task_id, 60, f"开始转换为 {target_format.upper()}...")

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.{target_format}")

    # 复制视频/音频流，不重新编码，速度快且无损
    cmd = [
        _get_ffmpeg_path(), '-y', '-i', video_path,
        '-c', 'copy',
        '-movflags', '+faststart',
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 部分容器组合无法 stream copy，回退到重新编码
    if result.returncode != 0:
        update_progress(task_id, 70, "正在重新编码...")
        cmd = [
            _get_ffmpeg_path(), '-y', '-i', video_path,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart',
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            error_msg = (result.stderr or '').strip().split('\n')[-1] if result.stderr else 'ffmpeg 执行失败'
            raise Exception(f"视频格式转换失败: {error_msg}")

    if not os.path.exists(output_path):
        raise Exception("视频格式转换失败: 输出文件未生成")

    update_progress(task_id, 90, "格式转换完成")
    return output_path
