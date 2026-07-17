"""download_service 测试（yt-dlp 实现）"""
import os
import pytest
from unittest.mock import MagicMock


def _make_ydl_mock(mocker, output_dir, base_name, ext='mp4'):
    """构造 yt_dlp.YoutubeDL 的 mock 上下文管理器"""
    outtmpl = os.path.join(output_dir, base_name + '.%(ext)s')

    class _FakeYDL:
        def __init__(self, opts):
            self.opts = opts
            self._outtmpl = opts.get('outtmpl') or outtmpl

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=True):
            target = self._outtmpl.replace('%(ext)s', ext)
            os.makedirs(os.path.dirname(target) or '.', exist_ok=True)
            with open(target, 'wb') as f:
                f.write(b'fake video content')
            return {'ext': ext, 'title': base_name}

        def prepare_filename(self, info):
            return self._outtmpl.replace('%(ext)s', info.get('ext', ext))

    mocker.patch('yt_dlp.YoutubeDL', _FakeYDL)
    mocker.patch('imageio_ffmpeg.get_ffmpeg_exe', return_value='ffmpeg')


def test_sanitize_filename():
    """测试文件名清理功能"""
    from app.services.download_service import _sanitize_filename

    assert _sanitize_filename('test/name') == 'test_name'
    assert _sanitize_filename('a*b?c') == 'a_b_c'
    assert _sanitize_filename('..hidden..') == 'hidden'
    assert _sanitize_filename('') == 'video'
    assert _sanitize_filename(None) is None
    assert _sanitize_filename('a:b<c>d|e"f') == 'a_b_c_d_e_f'
    long_name = 'a' * 200
    assert len(_sanitize_filename(long_name)) <= 100


def test_extract_url_from_text():
    """从文本中提取 URL"""
    from app.services.download_service import _extract_url_from_text

    assert _extract_url_from_text('https://example.com/video') == 'https://example.com/video'
    assert _extract_url_from_text('看看 https://www.bilibili.com/video/BV1xx 这个视频') == 'https://www.bilibili.com/video/BV1xx'
    assert _extract_url_from_text('no url here') == 'no url here'


def test_download_video_success(mocker, tmp_path):
    """测试视频下载成功"""
    _make_ydl_mock(mocker, str(tmp_path), 'test_video')

    from app.services.download_service import download_video

    result = download_video(
        url='https://example.com/video',
        output_dir=str(tmp_path),
        custom_filename='test_video',
        task_id='task123',
    )

    assert result is not None
    assert 'test_video' in result
    assert os.path.isfile(result)


def test_download_video_default_filename(mocker, tmp_path):
    """使用 task_id 生成默认文件名"""
    _make_ydl_mock(mocker, str(tmp_path), 'video_task999')

    from app.services.download_service import download_video

    result = download_video(
        url='https://example.com/video',
        output_dir=str(tmp_path),
        task_id='task999',
    )

    assert 'video_task999' in result
    assert os.path.isfile(result)


def test_download_video_creates_output_dir(mocker, tmp_path):
    """下载时自动创建输出目录"""
    _make_ydl_mock(mocker, '', 'myvideo')
    target_dir = tmp_path / 'new_subdir'

    from app.services.download_service import download_video

    result = download_video(
        url='https://example.com/video',
        output_dir=str(target_dir),
        custom_filename='myvideo',
        task_id='task456',
    )

    assert target_dir.exists()
    assert os.path.isfile(result)


def test_download_video_chinese_filename(mocker, tmp_path):
    """中文文件名下载"""
    _make_ydl_mock(mocker, str(tmp_path), '我的视频')

    from app.services.download_service import download_video

    result = download_video(
        url='https://example.com/video',
        output_dir=str(tmp_path),
        custom_filename='我的视频',
        task_id='task789',
    )

    assert '我的视频' in result
    assert os.path.isfile(result)


def test_download_video_failure(mocker, tmp_path):
    """yt-dlp 下载失败"""
    import yt_dlp

    class _FailYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=True):
            raise yt_dlp.utils.DownloadError('Unsupported URL: https://example.com/bad')

    mocker.patch('yt_dlp.YoutubeDL', _FailYDL)
    mocker.patch('imageio_ffmpeg.get_ffmpeg_exe', return_value='ffmpeg')

    from app.services.download_service import download_video

    with pytest.raises(Exception) as exc_info:
        download_video(
            url='https://example.com/bad',
            output_dir=str(tmp_path),
            custom_filename='bad',
            task_id='fail',
        )

    assert '下载失败' in str(exc_info.value)


def test_download_video_douyin_url(mocker, tmp_path):
    """抖音链接会被解析重定向"""
    _make_ydl_mock(mocker, str(tmp_path), 'douyin_video')

    # 模拟 _resolve_douyin_url 不发起真实请求
    mocker.patch('app.services.download_service._resolve_douyin_url',
                 return_value='https://www.douyin.com/real/video')

    from app.services.download_service import download_video

    result = download_video(
        url='https://v.douyin.com/abc123',
        output_dir=str(tmp_path),
        custom_filename='douyin_video',
        task_id='dy1',
    )

    assert os.path.isfile(result)


def test_download_video_no_output_file(mocker, tmp_path):
    """yt-dlp 成功但未生成文件"""
    class _EmptyYDL:
        def __init__(self, opts):
            self._outtmpl = opts.get('outtmpl', '')

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download=True):
            return {'ext': 'mp4'}

        def prepare_filename(self, info):
            return self._outtmpl.replace('%(ext)s', 'mp4')

    mocker.patch('yt_dlp.YoutubeDL', _EmptyYDL)
    mocker.patch('imageio_ffmpeg.get_ffmpeg_exe', return_value='ffmpeg')

    from app.services.download_service import download_video

    with pytest.raises(Exception) as exc_info:
        download_video(
            url='https://example.com/video',
            output_dir=str(tmp_path),
            custom_filename='nonexistent',
            task_id='task000',
        )

    assert '下载失败' in str(exc_info.value)
