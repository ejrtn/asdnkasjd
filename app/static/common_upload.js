/**
 * Shared state and utilities for Prescription and Medication Upload
 */

// Global state
window.drug_change_cnt = 0;
window.selectedFiles = [];
window.currentUploadType = '';
window.uploadedImages = {
    prescription: [],
    medication: []
};

// UI Elements (Global to be accessed by other scripts)
window.uploadOverlay = null;
window.loadingOverlay = null;
window.submitUploadBtn = null;
window.closeUploadModal = null;
window.zoomOverlay = null;
window.zoomImg = null;

// Pagehide event
window.addEventListener('pagehide', () => {
    if (window.drug_change_cnt != 0) {
        const accessToken = localStorage.getItem("access_token");
        const headers = { "Content-Type": "application/json" };
        if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

        fetch("/api/v1/guides/refresh", {
            method: "POST",
            headers: headers,
            keepalive: true,
        });
        window.drug_change_cnt = 0;
    }
});

document.addEventListener('DOMContentLoaded', () => {
    // Shared Elements Initialization
    window.uploadOverlay = document.getElementById('upload-overlay');
    window.loadingOverlay = document.getElementById('loading-overlay');
    window.submitUploadBtn = document.getElementById('submit-upload');
    window.closeUploadModal = document.getElementById('close-upload-modal');
    window.zoomOverlay = document.getElementById('zoom-overlay');
    window.zoomImg = document.getElementById('zoom-img');
    
    const uploadModalTitle = document.getElementById('upload-modal-title');
    const dropZone = document.getElementById('drop-zone');
    const hiddenFileInput = document.getElementById('hidden-file-input');
    const fileListContainer = document.getElementById('file-list-container');
    const fileList = document.getElementById('file-list');
    const previewGrid = document.getElementById('preview-grid');
    const closeZoomBtn = document.querySelector('.btn-zoom-close');

    // --- Modal Control ---
    document.querySelectorAll('.open-upload-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            window.currentUploadType = btn.getAttribute('data-type');
            uploadModalTitle.textContent = window.currentUploadType === 'prescription'
                ? '처방전 / 약봉투 업로드'
                : '복용약 이미지 업로드';
            window.uploadOverlay.classList.add('show');
            resetUpload();
        });
    });

    if (window.closeUploadModal) {
        window.closeUploadModal.addEventListener('click', () => {
            window.uploadOverlay.classList.remove('show');
        });
    }

    if (window.uploadOverlay) {
        window.uploadOverlay.addEventListener('click', (e) => {
            if (e.target === window.uploadOverlay) {
                window.uploadOverlay.classList.remove('show');
            }
        });
    }

    // --- Zoom Modal Control ---
    if (window.zoomOverlay) {
        window.zoomOverlay.addEventListener('click', (e) => {
            if (e.target === window.zoomOverlay || e.target.classList.contains('btn-zoom-close')) {
                window.zoomOverlay.classList.remove('show');
            }
        });
    }

    if (closeZoomBtn) {
        closeZoomBtn.addEventListener('click', () => {
            window.zoomOverlay.classList.remove('show');
        });
    }

    // --- File Handling ---
    if (dropZone) {
        dropZone.addEventListener('click', () => hiddenFileInput.click());

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                addFiles(files);
            }
        });
    }

    if (hiddenFileInput) {
        hiddenFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                addFiles(e.target.files);
                hiddenFileInput.value = '';
            }
        });
    }

    // Exported helper functions for file handling
    window.addFiles = function(files) {
        const filesArray = Array.from(files);
        filesArray.forEach(file => {
            const isDuplicate = window.selectedFiles.some(f => f.name === file.name && f.size === file.size);
            if (!isDuplicate) {
                window.selectedFiles.push(file);
            }
        });
        renderFiles();
        updateSubmitButton();
    };

    window.removeFile = function(index) {
        window.selectedFiles.splice(index, 1);
        renderFiles();
        updateSubmitButton();
    };

    function renderFiles() {
        fileList.innerHTML = '';
        previewGrid.innerHTML = '';

        if (window.selectedFiles.length === 0) {
            fileListContainer.style.display = 'none';
            previewGrid.style.display = 'none';
            return;
        }

        fileListContainer.style.display = 'block';
        previewGrid.style.display = 'grid';

        window.selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <span>${file.name} (${(file.size / 1024).toFixed(1)} KB)</span>
                <span class="btn-remove" data-index="${index}">x</span>
            `;
            fileList.appendChild(fileItem);

            if (file.type.startsWith('image/') || file.type === 'application/pdf') {
                const previewItem = document.createElement('div');
                previewItem.className = 'preview-item';

                if (file.type.startsWith('image/')) {
                    const img = document.createElement('img');
                    img.style.cursor = 'zoom-in';
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        img.src = e.target.result;
                        img.onclick = (ev) => {
                            ev.stopPropagation();
                            showZoomModal(e.target.result);
                        };
                    };
                    reader.readAsDataURL(file);
                    previewItem.appendChild(img);
                } else {
                    const pdfPlaceholder = document.createElement('div');
                    pdfPlaceholder.className = 'pdf-placeholder';
                    pdfPlaceholder.style.cssText = 'width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#fff1f0; color:#f5222d; font-weight:bold; font-size:12px;';
                    pdfPlaceholder.innerHTML = '<span style="font-size:32px;">📄</span><span>PDF</span>';
                    previewItem.appendChild(pdfPlaceholder);
                }

                const removeBtn = document.createElement('button');
                removeBtn.className = 'btn-remove-preview';
                removeBtn.innerHTML = '×';
                removeBtn.onclick = (e) => {
                    e.stopPropagation();
                    window.removeFile(index);
                };

                previewItem.appendChild(removeBtn);
                previewGrid.appendChild(previewItem);
            }
        });

        fileList.querySelectorAll('.btn-remove').forEach(btn => {
            btn.onclick = () => window.removeFile(parseInt(btn.getAttribute('data-index')));
        });
    }

    function updateSubmitButton() {
        if (window.submitUploadBtn) window.submitUploadBtn.disabled = window.selectedFiles.length === 0;
    }

    function resetUpload() {
        window.selectedFiles = [];
        if (hiddenFileInput) hiddenFileInput.value = '';
        renderFiles();
        updateSubmitButton();
        if (window.loadingOverlay) window.loadingOverlay.classList.remove('active');
    }

    // --- Main View Rendering ---
    window.renderMainPreviews = function() {
        const pBox = document.getElementById('prescription-preview-box');
        const mBox = document.getElementById('medication-preview-box');
        if (pBox) renderBox(pBox, 'prescription');
        if (mBox) renderBox(mBox, 'medication');
    };

    function renderBox(container, type) {
        container.innerHTML = '';
        container.className = 'upload-zone-card has-files';

        const addBtn = document.createElement('div');
        addBtn.className = 'main-upload-add-btn';
        addBtn.innerHTML = `
            <div class="main-upload-add-btn-icon">➕</div>
            <div class="main-upload-add-btn-text">사진 추가</div>
        `;
        addBtn.onclick = (e) => {
            e.stopPropagation();
            window.currentUploadType = type;
            window.uploadOverlay.classList.add('show');
            resetUpload();
        };
        container.appendChild(addBtn);

        window.uploadedImages[type].forEach((imageData, index) => {
            const previewItem = document.createElement('div');
            previewItem.className = 'main-preview-item';

            if (imageData.startsWith('data:image/')) {
                const img = document.createElement('img');
                img.src = imageData;
                img.style.cursor = 'zoom-in';
                img.onclick = (e) => {
                    e.stopPropagation();
                    showZoomModal(imageData);
                };
                previewItem.appendChild(img);
            } else {
                const pdfPlaceholder = document.createElement('div');
                pdfPlaceholder.className = 'pdf-placeholder';
                pdfPlaceholder.style.cssText = 'width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#fff1f0; color:#f5222d; font-weight:bold; font-size:12px;';
                pdfPlaceholder.innerHTML = '<span style="font-size:32px;">📄</span><span>PDF</span>';
                previewItem.appendChild(pdfPlaceholder);
            }

            const removeBtn = document.createElement('button');
            removeBtn.className = 'btn-remove-main';
            removeBtn.innerHTML = '×';
            removeBtn.onclick = (e) => {
                e.stopPropagation();
                window.uploadedImages[type].splice(index, 1);
                window.renderMainPreviews();
            };

            previewItem.appendChild(removeBtn);
            container.appendChild(previewItem);
        });
    }

    window.renderMainPreviews();
});

// Shared Global Functions
window.showZoomModal = function(src) {
    if (window.zoomImg && window.zoomOverlay) {
        window.zoomImg.src = src;
        window.zoomOverlay.classList.add('show');
    }
};

window.showToast = function(message) {
    let toast = document.querySelector('.c9-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'c9-toast';
        document.body.appendChild(toast);
    }
    toast.innerHTML = `<span>✅</span> ${message}`;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
};

window.addMainPreview = function(type, file) {
    if (!file) return;
    if (file.type && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            if (!window.uploadedImages[type].includes(e.target.result)) {
                window.uploadedImages[type].push(e.target.result);
                window.renderMainPreviews();
            }
        };
        reader.readAsDataURL(file);
    } else if (file.type === 'application/pdf') {
        window.uploadedImages[type].push('FILE_TYPE_PDF');
        window.renderMainPreviews();
    }
};

window.finishUpload = function() {
    if (window.loadingOverlay) window.loadingOverlay.classList.remove('active');
    if (window.submitUploadBtn) window.submitUploadBtn.disabled = false;
    if (window.closeUploadModal) window.closeUploadModal.disabled = false;
    window.renderMainPreviews();
};
