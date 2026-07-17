"""路由层测试"""
import os
import io
import pytest
from app import create_app
from config import Config


@pytest.fixture
def app(tmp_path, mocker):
    # 让上传/下载落到 tmp_path
    class TestConfig(Config):
        UPLOAD_FOLDER = str(tmp_path)
        TESTING = True
    flask_app = create_app(TestConfig)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_route(client):
    """首页正常返回"""
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'<!DOCTYPE html>' in resp.data
    assert b'\xe5\xa4\x9a\xe5\xaa\x92\xe4\xbd\x93' in resp.data  # "多媒体" GBK 不可，UTF-8 检查
    # 确认包含页面特征
    assert b'convertForm' in resp.data or b'convert-form' in resp.data or b'\xe5\xa4\x9a\xe5\xaa\x92\xe4\xbd\x93' in resp.data


def test_progress_route(client):
    """进度查询"""
    resp = client.get('/api/progress/nonexistent')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {'percent': 0, 'message': '未知状态'}


def test_download_nonexistent_file(client):
    """下载不存在的文件返回 404"""
    resp = client.get('/api/download/notexist.mp4')
    assert resp.status_code == 404


def test_preview_disallowed_extension(tmp_path, client):
    """不允许的扩展名预览返回 403"""
    f = tmp_path / 'test.txt'
    f.write_text('hello')
    resp = client.get('/api/preview/test.txt')
    # 文本文件既不在 INLINE_PREVIEW_EXTS 也不在 ALLOWED_VIDEO_EXTENSIONS
    # _safe_path 会放行（因为没有路径穿越），但 preview 内部 403
    assert resp.status_code in (403, 404)


def test_download_existing_file(app, client, tmp_path):
    """下载存在的文件"""
    f = tmp_path / 'video.mp4'
    f.write_bytes(b'fake video content')
    resp = client.get('/api/download/video.mp4')
    assert resp.status_code == 200
    assert b'fake video content' in resp.data
    cd = resp.headers.get('Content-Disposition', '')
    assert 'attachment' in cd
    assert 'video.mp4' in cd


def test_download_chinese_filename(app, client, tmp_path):
    """下载中文文件名"""
    f = tmp_path / '我的视频.mp4'
    f.write_bytes(b'fake')
    resp = client.get('/api/download/' + '%E6%88%91%E7%9A%84%E8%A7%86%E9%A2%91.mp4')
    assert resp.status_code == 200
    cd = resp.headers.get('Content-Disposition', '')
    assert 'attachment' in cd
    # 包含 RFC 5987 编码
    assert 'UTF-8' in cd or "filename*=" in cd


def test_preview_video(app, client, tmp_path):
    """预览视频文件"""
    f = tmp_path / 'clip.mp4'
    f.write_bytes(b'fake video data')
    resp = client.get('/api/preview/clip.mp4')
    assert resp.status_code == 200
    assert b'fake video data' in resp.data
    cd = resp.headers.get('Content-Disposition', '')
    assert 'inline' in cd


def test_preview_audio(app, client, tmp_path):
    """预览音频文件"""
    f = tmp_path / 'song.mp3'
    f.write_bytes(b'fake audio')
    resp = client.get('/api/preview/song.mp3')
    assert resp.status_code == 200
    assert b'fake audio' in resp.data


def test_preview_path_traversal_blocked(app, client, tmp_path):
    """路径穿越被阻止"""
    resp = client.get('/api/preview/..%2F..%2Fetc%2Fpasswd')
    # Flask 默认 path: 会 URL 解码，所以可能是 404 或 403
    assert resp.status_code in (404, 403, 308)


def test_convert_url_missing(client):
    """URL 模式缺少链接时返回错误"""
    resp = client.post('/api/convert', data={'type': 'audio', 'source': 'url'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is False
    assert '请输入视频链接' in data['error']


def test_convert_upload_missing_file(client):
    """上传模式缺少文件时返回错误"""
    resp = client.post('/api/convert', data={'type': 'audio', 'source': 'upload'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is False


def test_convert_upload_disallowed_format(client):
    """上传不允许的格式"""
    data = {
        'type': 'audio', 'source': 'upload',
        'file': (io.BytesIO(b'fake'), 'test.txt'),
    }
    resp = client.post('/api/convert', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    resp_json = resp.get_json()
    assert resp_json['success'] is False
    assert '不支持' in resp_json['error']


def test_convert_unsupported_type(client):
    """不支持的转换类型"""
    data = {
        'type': 'unknown', 'source': 'url',
        'url': 'https://example.com',
    }
    resp = client.post('/api/convert', data=data)
    # 因为 source=url 也会先尝试 download，download 会失败
    assert resp.status_code == 200
    data_json = resp.get_json()
    assert data_json['success'] is False
