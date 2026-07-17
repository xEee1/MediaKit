import pytest
import os
from app.services.convert_service import (
    convert_to_audio,
    convert_to_gif,
    convert_video_format,
    CODEC_MAP,
    QUALITY_DEFAULT,
    _parse_time,
)


# ============== 音频转换 ==============

def test_convert_to_audio_mp3_success(mocker, tmp_path):
    """测试MP3转换成功场景"""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.return_value.returncode = 0

    video_path = tmp_path / 'test_video.mp4'
    video_path.write_text('fake video')
    (tmp_path / 'test_video.mp3').write_text('fake audio')

    result = convert_to_audio(
        video_path=str(video_path),
        output_dir=str(tmp_path),
        format='mp3',
        quality=4,
        task_id='task123',
    )

    assert result.endswith('.mp3')
    assert 'test_video' in result
    mock_subprocess.assert_called_once()


def test_convert_to_audio_wav(mocker, tmp_path):
    """测试WAV格式转换"""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.return_value.returncode = 0

    video_path = tmp_path / 'test.mp4'
    video_path.write_text('fake video')
    (tmp_path / 'test.wav').write_text('fake audio')

    result = convert_to_audio(
        video_path=str(video_path),
        output_dir=str(tmp_path),
        format='wav',
        quality=None,
        task_id='task123',
    )

    assert result.endswith('.wav')


def test_convert_to_audio_m4a(mocker, tmp_path):
    """测试M4A格式转换"""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.return_value.returncode = 0

    video_path = tmp_path / 'video.mp4'
    video_path.write_text('fake video')
    (tmp_path / 'video.m4a').write_text('fake audio')

    result = convert_to_audio(
        video_path=str(video_path),
        output_dir=str(tmp_path),
        format='m4a',
        quality='256k',
        task_id='task456',
    )

    assert result.endswith('.m4a')


def test_convert_to_audio_flac(mocker, tmp_path):
    """测试FLAC格式转换"""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.return_value.returncode = 0

    video_path = tmp_path / 'flac_test.mp4'
    video_path.write_text('fake video')
    (tmp_path / 'flac_test.flac').write_text('fake audio')

    result = convert_to_audio(
        video_path=str(video_path),
        output_dir=str(tmp_path),
        format='flac',
        quality=8,
        task_id='task789',
    )

    assert result.endswith('.flac')


def test_convert_to_audio_unsupported_format(mocker, tmp_path):
    """测试不支持的格式"""
    video_path = tmp_path / 'video.mp4'
    video_path.write_text('fake video')

    with pytest.raises(Exception) as exc_info:
        convert_to_audio(
            video_path=str(video_path),
            output_dir=str(tmp_path),
            format='xyz',
            quality=None,
            task_id='task123',
        )

    assert '不支持的音频格式' in str(exc_info.value)


def test_convert_to_audio_failure(mocker, tmp_path):
    """测试转换失败场景"""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.return_value.returncode = 1
    mock_subprocess.return_value.stderr = 'ffmpeg error'

    video_path = tmp_path / 'video.mp4'
    video_path.write_text('fake video')

    with pytest.raises(Exception) as exc_info:
        convert_to_audio(
            video_path=str(video_path),
            output_dir=str(tmp_path),
            format='mp3',
            quality=4,
            task_id='task123',
        )

    assert '转换失败' in str(exc_info.value)


# ============== GIF 转换 ==============

def test_convert_to_gif_success(mocker, tmp_path):
    """测试 GIF 转换成功（两次 ffmpeg 调用）"""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.return_value.returncode = 0

    video_path = tmp_path / 'video.mp4'
    video_path.write_text('fake video')

    # 预创建 GIF 输出文件（palette png 会被清理）
    (tmp_path / 'video.gif').write_text('fake gif')

    result = convert_to_gif(
        video_path=str(video_path),
        output_dir=str(tmp_path),
        fps=10,
        width=480,
        task_id='gif_task',
    )

    assert result.endswith('.gif')
    # 第一次生成 palette，第二次生成 GIF
    assert mock_subprocess.call_count == 2


def test_convert_to_gif_with_time_range(mocker, tmp_path):
    """测试带起始时间和时长的 GIF 转换"""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.return_value.returncode = 0

    video_path = tmp_path / 'video.mp4'
    video_path.write_text('fake video')
    (tmp_path / 'video.gif').write_text('fake gif')

    result = convert_to_gif(
        video_path=str(video_path),
        output_dir=str(tmp_path),
        fps=15,
        width=320,
        start_time='5',
        duration='3',
        task_id='gif_task2',
    )

    assert result.endswith('.gif')
    # 第一次 ffmpeg 调用应包含 -ss 和 -t
    first_call_args = mock_subprocess.call_args_list[0][0][0]
    assert '-ss' in first_call_args
    assert '5' in first_call_args
    assert '-t' in first_call_args
    assert '3' in first_call_args


def test_convert_to_gif_palette_failure(mocker, tmp_path):
    """测试 palette 生成失败"""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.return_value.returncode = 1
    mock_subprocess.return_value.stderr = 'palette error'

    video_path = tmp_path / 'video.mp4'
    video_path.write_text('fake video')

    with pytest.raises(Exception) as exc_info:
        convert_to_gif(
            video_path=str(video_path),
            output_dir=str(tmp_path),
            task_id='gif_fail',
        )

    assert 'GIF' in str(exc_info.value)


# ============== MOV 转 MP4 ==============

def test_convert_video_format_stream_copy(mocker, tmp_path):
    """测试视频格式转换（流复制快速路径）"""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.return_value.returncode = 0

    video_path = tmp_path / 'input.mov'
    video_path.write_text('fake video')
    (tmp_path / 'input.mp4').write_text('fake mp4')

    result = convert_video_format(
        video_path=str(video_path),
        output_dir=str(tmp_path),
        target_format='mp4',
        task_id='vfmt1',
    )

    assert result.endswith('.mp4')
    # 第一次成功，仅调用一次
    assert mock_subprocess.call_count == 1


def test_convert_video_format_fallback_to_reencode(mocker, tmp_path):
    """测试流复制失败后回退到重新编码"""
    mock_subprocess = mocker.patch('subprocess.run')
    # 第一次失败，第二次成功
    mock_subprocess.side_effect = [
        mocker.Mock(returncode=1, stderr='copy failed'),
        mocker.Mock(returncode=0, stderr=''),
    ]

    video_path = tmp_path / 'input.mov'
    video_path.write_text('fake video')
    (tmp_path / 'input.mp4').write_text('fake mp4')

    result = convert_video_format(
        video_path=str(video_path),
        output_dir=str(tmp_path),
        target_format='mp4',
        task_id='vfmt2',
    )

    assert result.endswith('.mp4')
    assert mock_subprocess.call_count == 2


def test_convert_video_format_both_fail(mocker, tmp_path):
    """测试两种方式都失败"""
    mock_subprocess = mocker.patch('subprocess.run')
    mock_subprocess.side_effect = [
        mocker.Mock(returncode=1, stderr='copy failed'),
        mocker.Mock(returncode=1, stderr='encode failed'),
    ]

    video_path = tmp_path / 'input.mov'
    video_path.write_text('fake video')

    with pytest.raises(Exception) as exc_info:
        convert_video_format(
            video_path=str(video_path),
            output_dir=str(tmp_path),
            target_format='mp4',
            task_id='vfmt3',
        )

    assert '转换失败' in str(exc_info.value)


# ============== 辅助函数 ==============

def test_codec_map_completeness():
    """测试编解码映射包含所有支持的格式"""
    assert 'mp3' in CODEC_MAP
    assert 'wav' in CODEC_MAP
    assert 'm4a' in CODEC_MAP
    assert 'flac' in CODEC_MAP


def test_quality_default_completeness():
    """测试默认质量配置包含所有支持的格式"""
    assert 'mp3' in QUALITY_DEFAULT
    assert 'wav' in QUALITY_DEFAULT
    assert 'm4a' in QUALITY_DEFAULT
    assert 'flac' in QUALITY_DEFAULT


def test_parse_time():
    """测试时间解析"""
    assert _parse_time('5') == '5'
    assert _parse_time('5.5') == '5.5'
    assert _parse_time('00:00:05') == '00:00:05'
    assert _parse_time('1:30') == '1:30'
    assert _parse_time('') is None
    assert _parse_time(None) is None
    assert _parse_time('abc') is None
