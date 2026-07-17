import os
import re
import time
import mimetypes
import urllib.parse

from flask import (
    Blueprint, render_template, request, jsonify,
    send_from_directory, current_app, abort,
)
from werkzeug.exceptions import NotFound

from app.services.download_service import download_video
from app.services.convert_service import convert_to_audio, convert_to_gif, convert_video_format
from app.services.probe_service import probe_media
from app.utils import update_progress, get_progress, generate_task_id
from config import Config

bp = Blueprint('main', __name__)

ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.webm', '.m4v'}

# 哪些扩展名可以 inline 预览
INLINE_PREVIEW_EXTS = {'.mp4', '.webm', '.m4v', '.mov', '.mp3', '.wav', '.m4a', '.flac', '.ogg'}


def _get_upload_dir():
    upload_folder = current_app.config.get('UPLOAD_FOLDER') or Config.UPLOAD_FOLDER
    return os.path.abspath(upload_folder)


def _allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


def _safe_path(filename):
    """安全地拼接路径，限制在 UPLOAD_FOLDER 内"""
    upload_dir = _get_upload_dir()
    target = os.path.abspath(os.path.join(upload_dir, filename))
    if not target.startswith(upload_dir + os.sep):
        raise NotFound()
    return target


def _make_content_disposition(filename, disposition='attachment'):
    """构造支持中文文件名的 Content-Disposition 头"""
    # RFC 5987 编码用于 UTF-8 文件名
    encoded = urllib.parse.quote(filename, safe='')
    ascii_fallback = filename.encode('ascii', 'ignore').decode('ascii') or 'download'
    return f"{disposition}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/api/convert', methods=['POST'])
def api_convert():
    """统一转换接口"""
    task_id = generate_task_id()
    convert_type = request.form.get('type', 'audio')

    try:
        update_progress(task_id, 0, "准备开始...")

        video_path, custom_name = _resolve_video_source(task_id)

        if convert_type == 'audio':
            format_type = request.form.get('format', 'mp3')
            quality = request.form.get('quality')
            output_path = convert_to_audio(
                video_path=video_path,
                output_dir=_get_upload_dir(),
                format=format_type,
                quality=quality,
                task_id=task_id,
            )
            output_filename = os.path.basename(output_path)
            output_meta = probe_media(output_path)
            result = {
                'success': True,
                'task_id': task_id,
                'type': 'audio',
                'primary': {
                    'filename': output_filename,
                    'label': f'下载音频 ({format_type.upper()})',
                    'mime': mimetypes.guess_type(output_filename)[0] or 'audio/mpeg',
                    'kind': 'audio',
                    'meta': output_meta,
                },
            }

        elif convert_type == 'gif':
            fps = int(request.form.get('fps', 10))
            width = int(request.form.get('width', 480))
            start_time = request.form.get('startTime') or None
            duration = request.form.get('duration') or None
            output_path = convert_to_gif(
                video_path=video_path,
                output_dir=_get_upload_dir(),
                fps=fps,
                width=width,
                start_time=start_time,
                duration=duration,
                task_id=task_id,
            )
            output_filename = os.path.basename(output_path)
            output_meta = probe_media(output_path)
            result = {
                'success': True,
                'task_id': task_id,
                'type': 'gif',
                'primary': {
                    'filename': output_filename,
                    'label': '下载 GIF',
                    'mime': 'image/gif',
                    'kind': 'image',
                    'meta': output_meta,
                },
            }

        elif convert_type == 'mov2mp4':
            output_path = convert_video_format(
                video_path=video_path,
                output_dir=_get_upload_dir(),
                target_format='mp4',
                task_id=task_id,
            )
            output_filename = os.path.basename(output_path)
            output_meta = probe_media(output_path)
            result = {
                'success': True,
                'task_id': task_id,
                'type': 'mov2mp4',
                'primary': {
                    'filename': output_filename,
                    'label': '下载 MP4',
                    'mime': 'video/mp4',
                    'kind': 'video',
                    'meta': output_meta,
                },
            }

        else:
            raise Exception(f"不支持的转换类型: {convert_type}")

        # 如果是URL下载，附带原视频信息
        if request.form.get('source') == 'url':
            source_filename = os.path.basename(video_path)
            source_meta = probe_media(video_path)
            result['secondary'] = {
                'filename': source_filename,
                'label': '下载原视频',
                'mime': mimetypes.guess_type(source_filename)[0] or 'video/mp4',
                'kind': 'video',
                'meta': source_meta,
            }

        result['source_filename'] = custom_name
        update_progress(task_id, 100, "处理完成")
        return jsonify(result)

    except Exception as e:
        update_progress(task_id, -1, str(e))
        return jsonify({'success': False, 'error': str(e), 'task_id': task_id})


def _resolve_video_source(task_id):
    """根据来源解析视频路径，返回 (video_path, custom_name)"""
    source = request.form.get('source', 'url')

    if source == 'url':
        url = (request.form.get('url') or '').strip()
        if not url:
            raise Exception("请输入视频链接")
        custom_filename = (request.form.get('videoFileName') or '').strip() or None
        video_path = download_video(
            url=url,
            output_dir=_get_upload_dir(),
            custom_filename=custom_filename,
            task_id=task_id,
        )
        return video_path, os.path.splitext(os.path.basename(video_path))[0]

    elif source == 'upload':
        if 'file' not in request.files:
            raise Exception("请选择要上传的视频文件")
        f = request.files['file']
        if not f or f.filename == '':
            raise Exception("请选择要上传的视频文件")
        if not _allowed_file(f.filename):
            raise Exception(f"不支持的文件格式，仅支持: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}")

        ext = os.path.splitext(f.filename)[1].lower()
        # 保留中文等 unicode 字符：只剥离路径分隔符
        raw_name = os.path.basename(f.filename)
        safe_name = re.sub(r'[\\/:*?"<>|\r\n\t]', '_', raw_name).strip().strip('.') or f"upload{ext}"
        stored_name = f"{task_id}_{int(time.time())}_{safe_name}"
        save_path = os.path.join(_get_upload_dir(), stored_name)
        os.makedirs(_get_upload_dir(), exist_ok=True)
        f.save(save_path)
        return save_path, os.path.splitext(stored_name)[0]

    else:
        raise Exception(f"不支持的来源类型: {source}")


@bp.route('/api/progress/<task_id>')
def progress(task_id):
    return jsonify(get_progress(task_id))


@bp.route('/api/download/<path:filename>')
def download(filename):
    """下载文件（attachment）"""
    target = _safe_path(filename)
    if not os.path.isfile(target):
        abort(404)
    response = send_from_directory(
        _get_upload_dir(),
        filename,
        as_attachment=True,
        download_name=os.path.basename(target),
    )
    response.headers['Content-Disposition'] = _make_content_disposition(
        os.path.basename(target), disposition='attachment'
    )
    return response


@bp.route('/api/preview/<path:filename>')
def preview(filename):
    """预览文件（inline，支持视频/音频 Range 流式播放）"""
    target = _safe_path(filename)
    if not os.path.isfile(target):
        abort(404)

    ext = os.path.splitext(target)[1].lower()
    if ext not in INLINE_PREVIEW_EXTS:
        abort(403)

    file_size = os.path.getsize(target)
    range_header = request.headers.get('Range', None)

    if range_header:
        byte1, byte2 = None, None
        match = re.search(r'bytes=(\d+)-(\d*)', range_header)
        groups = match.groups()

        if groups[0]:
            byte1 = int(groups[0])
        if groups[1]:
            byte2 = int(groups[1])

        length = file_size
        if byte1 is not None:
            if byte2 is None:
                length = file_size - byte1
            else:
                length = byte2 - byte1 + 1

        with open(target, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)

        response = current_app.response_class(
            data,
            status=206,
            mimetype=mimetypes.guess_type(filename)[0] or 'application/octet-stream',
            direct_passthrough=True,
        )
        response.headers['Content-Range'] = f'bytes {byte1}-{byte1 + length - 1}/{file_size}'
        response.headers['Content-Length'] = str(length)
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Disposition'] = _make_content_disposition(
            os.path.basename(target), disposition='inline'
        )
        return response

    response = send_from_directory(
        _get_upload_dir(),
        filename,
        as_attachment=False,
        download_name=os.path.basename(target),
        conditional=True,
    )
    response.headers['Content-Disposition'] = _make_content_disposition(
        os.path.basename(target), disposition='inline'
    )
    response.headers['Accept-Ranges'] = 'bytes'
    return response
