import pytest
import os
import json
from app.services.probe_service import probe_media, _humanize_bytes, _humanize_duration


def test_humanize_bytes():
    assert _humanize_bytes(0) == '0 B'
    assert _humanize_bytes(500) == '500 B'
    assert _humanize_bytes(1024) == '1.0 KB'
    assert _humanize_bytes(1024 * 1024) == '1.0 MB'
    assert _humanize_bytes(1024 * 1024 * 1024) == '1.0 GB'
    assert _humanize_bytes(None) is None
    assert _humanize_bytes('invalid') is None


def test_humanize_duration():
    assert _humanize_duration(0) == '0:00.00'
    assert _humanize_duration(5) == '0:05.00'
    assert _humanize_duration(65) == '1:05.00'
    assert _humanize_duration(3661) == '1:01:01.00'
    assert _humanize_duration(None) is None
    assert _humanize_duration('abc') is None
    assert _humanize_duration(-1) is None


def test_probe_nonexistent_file():
    """测试不存在的文件"""
    result = probe_media('/nonexistent/file.mp4')
    assert result['size'] is None
    assert result['size_human'] is None
    assert result['duration'] is None


def test_probe_empty_path():
    """测试空路径"""
    result = probe_media('')
    assert result['size'] is None
    assert result['duration'] is None


def test_probe_file_size_only(mocker, tmp_path):
    """当 ffprobe 不可用时，文件大小仍可获取"""
    mocker.patch('subprocess.run', side_effect=FileNotFoundError('ffprobe not found'))

    f = tmp_path / 'test.mp4'
    f.write_text('x' * 1024)

    result = probe_media(str(f))
    assert result['size'] == 1024
    assert result['size_human'] == '1.0 KB'
    # ffprobe 失败则其他字段为 None
    assert result['duration'] is None
    assert result['width'] is None


def test_probe_with_ffmpeg_data(mocker, tmp_path):
    """ffprobe 正常返回时的解析"""
    ffprobe_output = {
        'format': {
            'duration': '65.5',
            'format_name': 'mov,mp4,m4a,3gp,3g2,mj2',
        },
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264', 'width': 1920, 'height': 1080},
            {'codec_type': 'audio', 'codec_name': 'aac'},
        ],
    }
    mock_proc = mocker.Mock()
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps(ffprobe_output)
    mock_proc.stderr = ''
    mocker.patch('subprocess.run', return_value=mock_proc)

    f = tmp_path / 'test.mp4'
    f.write_text('x' * (10 * 1024 * 1024))  # 10 MB

    result = probe_media(str(f))
    assert result['duration'] == 65.5
    assert result['duration_human'] == '1:05.50'
    assert result['width'] == 1920
    assert result['height'] == 1080
    assert result['vcodec'] == 'h264'
    assert result['acodec'] == 'aac'
    assert result['size'] == 10 * 1024 * 1024
    assert result['size_human'] == '10.0 MB'


def test_probe_ffprobe_error(mocker, tmp_path):
    """ffprobe 返回非 0 退出码"""
    mock_proc = mocker.Mock()
    mock_proc.returncode = 1
    mock_proc.stdout = ''
    mock_proc.stderr = 'Invalid data found'
    mocker.patch('subprocess.run', return_value=mock_proc)

    f = tmp_path / 'broken.mp4'
    f.write_text('not a video')

    result = probe_media(str(f))
    # 至少能拿到文件大小
    assert result['size'] is not None
    assert result['duration'] is None


def test_probe_json_decode_error(mocker, tmp_path):
    """ffprobe 输出不是有效 JSON"""
    mock_proc = mocker.Mock()
    mock_proc.returncode = 0
    mock_proc.stdout = 'not json'
    mock_proc.stderr = ''
    mocker.patch('subprocess.run', return_value=mock_proc)

    f = tmp_path / 'x.mp4'
    f.write_text('x')

    result = probe_media(str(f))
    assert result['duration'] is None
    assert result['size'] == 1
