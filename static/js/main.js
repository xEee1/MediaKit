(function () {
    'use strict';

    const dom = {
        form: document.getElementById('convertForm'),
        convertBtn: document.getElementById('convertBtn'),
        btnText: document.querySelector('#convertBtn .btn-text'),
        btnIcon: document.getElementById('btnIcon'),
        convertType: document.getElementById('convertType'),
        sourceType: document.getElementById('sourceType'),

        // Tabs
        tabButtons: document.querySelectorAll('.tab-item'),

        // Source panels
        urlPanel: document.getElementById('urlPanel'),
        uploadPanel: document.getElementById('uploadPanel'),
        sourceButtons: document.querySelectorAll('.switch-btn'),

        // URL inputs
        urlInput: document.getElementById('url'),
        videoFileNameInput: document.getElementById('videoFileName'),

        // Upload
        dropzone: document.getElementById('dropzone'),
        fileInput: document.getElementById('fileInput'),
        browseBtn: document.getElementById('browseBtn'),
        fileInfo: document.getElementById('fileInfo'),
        fileName: document.getElementById('fileName'),
        fileSize: document.getElementById('fileSize'),
        removeFileBtn: document.getElementById('removeFileBtn'),

        // Audio params
        formatSelect: document.getElementById('format'),
        qualitySelect: document.getElementById('quality'),

        // GIF params
        gifFps: document.getElementById('gifFps'),
        gifWidth: document.getElementById('gifWidth'),
        gifStart: document.getElementById('gifStart'),
        gifDuration: document.getElementById('gifDuration'),

        // UI states
        progressCard: document.getElementById('progressCard'),
        progressBar: document.getElementById('progressBar'),
        progressPercent: document.getElementById('progressPercent'),
        progressText: document.getElementById('progressText'),
        errorBox: document.getElementById('errorBox'),
        errorText: document.getElementById('errorText'),
        errorClose: document.getElementById('errorClose'),
        resultCard: document.getElementById('resultCard'),
        resultInfo: document.getElementById('resultInfo'),
        resultActions: document.getElementById('resultActions'),
        previewArea: document.getElementById('previewArea'),
        previewTabs: document.getElementById('previewTabs'),
        previewContent: document.getElementById('previewContent'),
    };

    let currentFile = null;
    let pollInterval = null;
    let previewList = [];
    let currentPreviewIndex = 0;

    /* ==================== Tab 切换 ==================== */
    function switchConvertType(type) {
        dom.convertType.value = type;
        dom.tabButtons.forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.type === type);
        });
        document.querySelectorAll('.type-panel').forEach((panel) => {
            panel.hidden = panel.dataset.type !== type;
        });
        hideError();
        hideResult();
    }

    dom.tabButtons.forEach((btn) => {
        btn.addEventListener('click', () => switchConvertType(btn.dataset.type));
    });

    /* ==================== 来源切换 ==================== */
    function switchSource(source) {
        dom.sourceType.value = source;
        dom.sourceButtons.forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.source === source);
        });
        dom.urlPanel.hidden = source !== 'url';
        dom.uploadPanel.hidden = source !== 'upload';
        hideError();
    }

    dom.sourceButtons.forEach((btn) => {
        btn.addEventListener('click', () => switchSource(btn.dataset.source));
    });

    /* ==================== 文件上传（拖拽 + 点击） ==================== */
    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB';
        return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB';
    }

    function setFile(file) {
        if (!file) return;
        const maxSize = 200 * 1024 * 1024;
        if (file.size > maxSize) {
            showError('文件大小超过 200MB 限制');
            return;
        }
        if (!/^video\//.test(file.type) && !/\.(mp4|mov|avi|mkv|flv|webm|m4v)$/i.test(file.name)) {
            showError('请选择视频文件');
            return;
        }
        currentFile = file;
        dom.fileName.textContent = file.name;
        dom.fileSize.textContent = formatBytes(file.size);
        dom.fileInfo.hidden = false;
        dom.dropzone.hidden = true;
        hideError();
    }

    function clearFile() {
        currentFile = null;
        dom.fileInput.value = '';
        dom.fileInfo.hidden = true;
        dom.dropzone.hidden = false;
    }

    dom.browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dom.fileInput.click();
    });

    dom.dropzone.addEventListener('click', () => dom.fileInput.click());

    dom.fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    });

    dom.removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        clearFile();
    });

    ['dragenter', 'dragover'].forEach((event) => {
        dom.dropzone.addEventListener(event, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dom.dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach((event) => {
        dom.dropzone.addEventListener(event, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dom.dropzone.classList.remove('dragover');
        });
    });

    dom.dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files && files[0]) {
            setFile(files[0]);
        }
    });

    /* ==================== 提交 ==================== */
    dom.form.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideError();
        hideResult();

        const convertType = dom.convertType.value;
        const source = dom.sourceType.value;

        if (source === 'url') {
            const url = dom.urlInput.value.trim();
            if (!url) {
                showError('请输入视频链接');
                dom.urlInput.focus();
                return;
            }
        } else if (source === 'upload') {
            if (!currentFile) {
                showError('请选择要上传的视频文件');
                return;
            }
        }

        const formData = new FormData();
        formData.append('type', convertType);
        formData.append('source', source);
        if (source === 'url') {
            formData.append('url', dom.urlInput.value.trim());
            const customName = dom.videoFileNameInput.value.trim();
            if (customName) formData.append('videoFileName', customName);
        } else {
            formData.append('file', currentFile);
        }

        if (convertType === 'audio') {
            formData.append('format', dom.formatSelect.value);
            formData.append('quality', dom.qualitySelect.value);
        } else if (convertType === 'gif') {
            formData.append('fps', dom.gifFps.value);
            formData.append('width', dom.gifWidth.value);
            if (dom.gifStart.value.trim()) formData.append('startTime', dom.gifStart.value.trim());
            if (dom.gifDuration.value.trim()) formData.append('duration', dom.gifDuration.value.trim());
        }

        setBusy(true);
        showProgress();
        updateProgressUI(0, '准备开始...');

        try {
            const response = await fetch('/api/convert', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.success) {
                startPolling(data.task_id, data);
            } else {
                showError(data.error || '处理失败');
                hideProgress();
            }
        } catch (err) {
            showError('网络请求失败：' + err.message);
            hideProgress();
        } finally {
            setBusy(false);
        }
    });

    /* ==================== 进度轮询 ==================== */
    function startPolling(taskId, resultData) {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/progress/' + encodeURIComponent(taskId));
                const data = await res.json();
                updateProgressUI(data.percent, data.message);

                if (data.percent >= 100) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    showResult(resultData);
                } else if (data.percent === -1) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    showError(data.message || '处理失败');
                    hideProgress();
                }
            } catch (err) {
                console.error('进度查询失败', err);
            }
        }, 1000);
    }

    /* ==================== UI 辅助 ==================== */
    function setBusy(busy) {
        dom.convertBtn.disabled = busy;
        if (busy) {
            dom.btnText.textContent = '处理中…';
            dom.btnIcon.className = 'fa fa-refresh spin';
        } else {
            dom.btnText.textContent = '开始转换';
            dom.btnIcon.className = 'fa fa-arrow-circle-right';
        }
    }

    function updateProgressUI(percent, message) {
        const safe = Math.max(0, Math.min(100, percent || 0));
        dom.progressBar.style.width = safe + '%';
        dom.progressPercent.textContent = safe + '%';
        dom.progressText.textContent = message || '';
    }

    function showProgress() { dom.progressCard.hidden = false; }
    function hideProgress() { dom.progressCard.hidden = true; }

    function showError(msg) {
        dom.errorText.textContent = msg;
        dom.errorBox.hidden = false;
    }
    function hideError() { dom.errorBox.hidden = true; }
    dom.errorClose.addEventListener('click', hideError);

    function hideResult() {
        dom.resultCard.hidden = true;
        dom.previewArea.hidden = true;
        // 清理播放器
        stopAllMedia();
    }

    function stopAllMedia() {
        dom.previewContent.querySelectorAll('video, audio').forEach((el) => {
            try { el.pause(); } catch (e) { /* noop */ }
            el.removeAttribute('src');
            el.load();
        });
    }

    /* ==================== 渲染结果 ==================== */
    function showResult(data) {
        hideProgress();
        renderInfo(data);
        renderPreview(data);
        renderActions(data);
        dom.resultCard.hidden = false;
        dom.resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function renderInfo(data) {
        const typeText = {
            audio: '音频提取',
            gif: 'GIF 生成',
            mov2mp4: '格式转换',
        }[data.type] || '转换';

        const rows = [['任务类型', typeText]];

        const primaryMeta = data.primary.meta || {};
        const primaryInfo = formatFileInfo(data.primary.filename, primaryMeta);
        rows.push(['输出文件', primaryInfo]);

        if (data.secondary) {
            const secMeta = data.secondary.meta || {};
            const secInfo = formatFileInfo(data.secondary.filename, secMeta);
            rows.push(['源视频', secInfo]);
        }

        dom.resultInfo.innerHTML = rows
            .map(([k, v]) =>
                `<div class="info-row"><span class="info-label">${k}</span><span class="info-value">${escapeHtml(v)}</span></div>`
            )
            .join('');
    }

    function formatFileInfo(filename, meta) {
        const parts = [filename];
        const detail = [];
        if (meta.duration_human) detail.push(`时长 ${meta.duration_human}`);
        if (meta.width && meta.height) detail.push(`${meta.width}×${meta.height}`);
        if (meta.size_human) detail.push(`大小 ${meta.size_human}`);
        if (detail.length) parts.push(' · ' + detail.join(' · '));
        return parts.join('');
    }

    /* ==================== 预览渲染 ==================== */
    function renderPreview(data) {
        stopAllMedia();
        previewList = [];

        const primary = buildPreviewItem(data.primary, true);
        if (primary) previewList.push(primary);

        if (data.secondary) {
            const sec = buildPreviewItem(data.secondary, false);
            if (sec) previewList.push(sec);
        }

        if (previewList.length === 0) {
            dom.previewArea.hidden = true;
            return;
        }

        dom.previewArea.hidden = false;

        // 渲染 tab
        dom.previewTabs.innerHTML = previewList
            .map((item, idx) => `
                <button type="button" class="preview-tab ${idx === 0 ? 'active' : ''}" data-index="${idx}">
                    <i class="fa ${item.icon}"></i> ${escapeHtml(item.label)}
                </button>
            `).join('');

        dom.previewTabs.querySelectorAll('.preview-tab').forEach((tab) => {
            tab.addEventListener('click', () => {
                const idx = parseInt(tab.dataset.index, 10);
                showPreview(idx);
            });
        });

        showPreview(0);
    }

    function buildPreviewItem(item, isPrimary) {
        const filename = item.filename;
        const ext = (filename.split('.').pop() || '').toLowerCase();
        const mime = item.mime || '';
        const meta = item.meta || {};

        // 仅对可播放类型构建预览项
        const videoExts = ['mp4', 'webm', 'm4v', 'mov'];
        const audioExts = ['mp3', 'wav', 'm4a', 'flac', 'ogg'];

        if (videoExts.includes(ext) || mime.startsWith('video/')) {
            return {
                kind: 'video',
                label: isPrimary ? '播放视频' : '播放原视频',
                icon: 'fa-play-circle',
                filename: filename,
                mime: mime || 'video/mp4',
            };
        }
        if (audioExts.includes(ext) || mime.startsWith('audio/')) {
            return {
                kind: 'audio',
                label: isPrimary ? '播放音频' : '播放音频',
                icon: 'fa-music',
                filename: filename,
                mime: mime || 'audio/mpeg',
            };
        }
        if (ext === 'gif' || mime === 'image/gif') {
            return {
                kind: 'image',
                label: isPrimary ? '查看 GIF' : '查看 GIF',
                icon: 'fa-image',
                filename: filename,
                mime: 'image/gif',
            };
        }
        return null;
    }

    function showPreview(index) {
        if (index < 0 || index >= previewList.length) return;
        currentPreviewIndex = index;
        const item = previewList[index];

        // 更新 tab 高亮
        dom.previewTabs.querySelectorAll('.preview-tab').forEach((tab) => {
            tab.classList.toggle('active', parseInt(tab.dataset.index, 10) === index);
        });

        stopAllMedia();
        dom.previewContent.innerHTML = '';

        const previewUrl = '/api/preview/' + encodeURIComponent(item.filename);

        let el;
        if (item.kind === 'video') {
            el = document.createElement('video');
            el.controls = true;
            el.preload = 'metadata';
            el.src = previewUrl;
            el.addEventListener('error', () => onMediaError(item));
        } else if (item.kind === 'audio') {
            el = document.createElement('audio');
            el.controls = true;
            el.preload = 'metadata';
            el.src = previewUrl;
            el.addEventListener('error', () => onMediaError(item));
        } else if (item.kind === 'image') {
            el = document.createElement('img');
            el.src = previewUrl;
            el.alt = item.filename;
            el.addEventListener('error', () => onMediaError(item));
        }
        if (el) dom.previewContent.appendChild(el);
    }

    function onMediaError(item) {
        dom.previewContent.innerHTML = `
            <div class="preview-error">
                <i class="fa fa-exclamation-circle" style="font-size:24px;display:block;margin-bottom:8px;"></i>
                浏览器无法直接预览此文件（${escapeHtml(item.filename)}），请使用下载按钮获取。
            </div>
        `;
    }

    /* ==================== 下载按钮 ==================== */
    function renderActions(data) {
        dom.resultActions.innerHTML = '';

        appendDownloadButton(data.primary, true);

        if (data.secondary) {
            appendDownloadButton(data.secondary, false);
        }
    }

    function appendDownloadButton(item, isPrimary) {
        const btn = document.createElement('a');
        btn.className = isPrimary ? 'btn btn-download' : 'btn btn-secondary';
        btn.href = '/api/download/' + encodeURIComponent(item.filename);
        btn.setAttribute('download', item.filename);
        const icon = isPrimary ? 'fa-download' : 'fa-download';
        btn.innerHTML = `<i class="fa ${icon}"></i> ${escapeHtml(item.label)}`;
        dom.resultActions.appendChild(btn);
    }

    function escapeHtml(str) {
        if (str == null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
})();
