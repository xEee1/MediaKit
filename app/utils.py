processing_progress = {}


def update_progress(task_id, percent, message):
    processing_progress[task_id] = {
        'percent': percent,
        'message': message
    }


def get_progress(task_id):
    return processing_progress.get(task_id, {'percent': 0, 'message': '未知状态'})


def clean_progress(task_id):
    processing_progress.pop(task_id, None)


def generate_task_id():
    import uuid
    return str(uuid.uuid4())[:8]
