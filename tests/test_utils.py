import pytest
import os
from app.utils import update_progress, get_progress, clean_progress, generate_task_id


def test_update_progress():
    """测试更新进度"""
    update_progress('task1', 50, '处理中')
    result = get_progress('task1')
    assert result['percent'] == 50
    assert result['message'] == '处理中'
    clean_progress('task1')


def test_get_progress_default():
    """测试获取不存在任务的默认进度"""
    result = get_progress('non_existing_task')
    assert result['percent'] == 0
    assert result['message'] == '未知状态'


def test_clean_progress():
    """测试清理进度"""
    update_progress('task2', 80, '完成')
    clean_progress('task2')
    result = get_progress('task2')
    assert result['percent'] == 0


def test_generate_task_id():
    """测试生成任务ID"""
    task_id = generate_task_id()
    assert isinstance(task_id, str)
    assert len(task_id) == 8


def test_generate_task_id_unique():
    """测试任务ID唯一性"""
    ids = [generate_task_id() for _ in range(100)]
    assert len(set(ids)) == 100
