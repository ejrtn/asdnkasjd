/**
 * Prescription and Medication Upload Logic
 * Handles multiple file selection, previews, deletion, and simulated upload.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const uploadOverlay = document.getElementById('upload-overlay');
    const uploadModalTitle = document.getElementById('upload-modal-title');
    const dropZone = document.getElementById('drop-zone');
    const hiddenFileInput = document.getElementById('hidden-file-input');
    const closeUploadModal = document.getElementById('close-upload-modal');
    const submitUploadBtn = document.getElementById('submit-upload');
    const loadingOverlay = document.getElementById('loading-overlay');

    const fileListContainer = document.getElementById('file-list-container');
    const fileList = document.getElementById('file-list');
    const previewGrid = document.getElementById('preview-grid');

    // State
    let selectedFiles = [];
    let currentUploadType = '';

    // Persistent state for main view (uploaded images)
    let uploadedImages = {
        prescription: [],
        medication: []
    };

    // --- Modal Control ---

    document.querySelectorAll('.open-upload-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentUploadType = btn.getAttribute('data-type');
            uploadModalTitle.textContent = currentUploadType === 'prescription'
                ? '처방전 / 약봉투 업로드'
                : '복용약 이미지 업로드';
            uploadOverlay.classList.add('show');
            resetUpload();
        });
    });

    closeUploadModal.addEventListener('click', () => {
        uploadOverlay.classList.remove('show');
    });

    uploadOverlay.addEventListener('click', (e) => {
        if (e.target === uploadOverlay) {
            uploadOverlay.classList.remove('show');
        }
    });

    function resetUpload() {
        selectedFiles = [];
        hiddenFileInput.value = '';
        renderFiles();
        updateSubmitButton();
        loadingOverlay.classList.remove('active');
    }

    // --- File Handling ---

    dropZone.addEventListener('click', () => hiddenFileInput.click());

    hiddenFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            addFiles(e.target.files);
            // Reset input so the same file can be selected again if removed
            hiddenFileInput.value = '';
        }
    });

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

    function addFiles(files) {
        const filesArray = Array.from(files);

        filesArray.forEach(file => {
            // Check for duplicates (by name and size)
            const isDuplicate = selectedFiles.some(f => f.name === file.name && f.size === file.size);
            if (!isDuplicate) {
                selectedFiles.push(file);
            }
        });

        renderFiles();
        updateSubmitButton();
    }

    function removeFile(index) {
        selectedFiles.splice(index, 1);
        renderFiles();
        updateSubmitButton();
    }

    // --- Rendering (Modal) ---

    function renderFiles() {
        // Clear previous
        fileList.innerHTML = '';
        previewGrid.innerHTML = '';

        if (selectedFiles.length === 0) {
            fileListContainer.style.display = 'none';
            previewGrid.style.display = 'none';
            return;
        }

        fileListContainer.style.display = 'block';
        previewGrid.style.display = 'grid';

        selectedFiles.forEach((file, index) => {
            // 1. Add to Text List
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <span>${file.name} (${(file.size / 1024).toFixed(1)} KB)</span>
                <span class="btn-remove" data-index="${index}">x</span>
            `;
            fileList.appendChild(fileItem);

            // 2. Add to Preview Grid (Image or PDF)
            if (file.type.startsWith('image/') || file.type === 'application/pdf') {
                const previewItem = document.createElement('div');
                previewItem.className = 'preview-item';

                if (file.type.startsWith('image/')) {
                    const img = document.createElement('img');
                    const reader = new FileReader();
                    reader.onload = (e) => { img.src = e.target.result; };
                    reader.readAsDataURL(file);
                    previewItem.appendChild(img);
                } else {
                    // PDF Placeholder
                    const pdfPlaceholder = document.createElement('div');
                    pdfPlaceholder.className = 'pdf-placeholder';
                    pdfPlaceholder.style.cssText = 'width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#fff1f0; color:#f5222d; font-weight:bold; font-size:12px;';
                    pdfPlaceholder.innerHTML = '<span style="font-size:32px;">📄</span><span>PDF</span>';
                    previewItem.appendChild(pdfPlaceholder);
                }

                const removeBtn = document.createElement('button');
                removeBtn.className = 'btn-remove-preview';
                removeBtn.innerHTML = '×';
                removeBtn.title = '삭제';
                removeBtn.onclick = (e) => {
                    e.stopPropagation();
                    removeFile(index);
                };

                previewItem.appendChild(removeBtn);
                previewGrid.appendChild(previewItem);
            }
        });

        // Add event listeners for text list remove buttons
        fileList.querySelectorAll('.btn-remove').forEach(btn => {
            btn.onclick = () => removeFile(parseInt(btn.getAttribute('data-index')));
        });
    }

    function updateSubmitButton() {
        submitUploadBtn.disabled = selectedFiles.length === 0;
    }

    // --- Rendering (Main View) ---

    function renderMainPreviews() {
        const pBox = document.getElementById('prescription-preview-box');
        const mBox = document.getElementById('medication-preview-box');

        if (pBox) renderBox(pBox, 'prescription');
        if (mBox) renderBox(mBox, 'medication');
    }

    function renderBox(container, type) {
        if (uploadedImages[type].length === 0) {
            container.classList.add('empty-state');
            container.innerHTML = `
                <div class="drop-zone-icon">📁</div>
                <div class="drop-zone-text">파일 업로드</div>
                <div class="drop-zone-subtext">지원 형식: JPG, PNG, PDF (최대 10MB, 다중 선택 가능)</div>
            `;
            return;
        }

        container.classList.remove('empty-state');
        container.innerHTML = '';
        uploadedImages[type].forEach((imageData, index) => {
            const previewItem = document.createElement('div');
            previewItem.className = 'main-preview-item';

            if (imageData.startsWith('data:image/')) {
                const img = document.createElement('img');
                img.src = imageData;
                previewItem.appendChild(img);
            } else {
                // PDF Placeholder for main view
                const pdfPlaceholder = document.createElement('div');
                pdfPlaceholder.className = 'pdf-placeholder';
                pdfPlaceholder.style.cssText = 'width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#fff1f0; color:#f5222d; font-weight:bold; font-size:12px;';
                pdfPlaceholder.innerHTML = '<span style="font-size:32px;">📄</span><span>PDF</span>';
                previewItem.appendChild(pdfPlaceholder);
            }

            const removeBtn = document.createElement('button');
            removeBtn.className = 'btn-remove-main';
            removeBtn.innerHTML = '×';
            removeBtn.title = '삭제';
            removeBtn.onclick = (e) => {
                e.stopPropagation(); // Prevent opening upload modal
                uploadedImages[type].splice(index, 1);
                renderMainPreviews();
            };

            previewItem.appendChild(removeBtn);
            container.appendChild(previewItem);
        });
    }

    // Initialize main view
    renderMainPreviews();

    // --- Upload Action ---

    submitUploadBtn.addEventListener('click', () => {
        if (selectedFiles.length === 0) return;

        // Show loading
        loadingOverlay.classList.add('active');
        submitUploadBtn.disabled = true;
        closeUploadModal.disabled = true;

        // Process files for OCR and main view
        const filesToUpload = selectedFiles
            .filter(file => file.type.startsWith('image/') || file.type === 'application/pdf');

        if (filesToUpload.length === 0) {
            finishUpload();
            return;
        }

        const uploadPromises = filesToUpload.map(async (file) => {
            const formData = new FormData();
            formData.append('file', file);

            try {
                // OCR API 호출
                const response = await fetch('/api/v1/ocr', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                const rawText = data.raw_text || "분석된 텍스트가 없습니다.";

                // 화면에 결과 표시 (처방전 또는 복용약)
                const targetBoxId = currentUploadType === 'prescription'
                    ? 'prescription-analysis-box'
                    : 'medication-analysis-box';

                const targetBox = document.getElementById(targetBoxId);
                if (targetBox) {
                    const resultContainer = targetBox.querySelector('.analysis-result-text') || targetBox.querySelector('p');
                    if (resultContainer) {
                        resultContainer.textContent = rawText;
                        resultContainer.style.color = '#333';
                    }
                }

                // 이미지인 경우 미리보기를 위해 push
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    return new Promise((resolve) => {
                        reader.onload = (e) => {
                            uploadedImages[currentUploadType].push(e.target.result);
                            resolve();
                        };
                        reader.readAsDataURL(file);
                    });
                } else {
                    uploadedImages[currentUploadType].push('FILE_TYPE_PDF');
                }
            } catch (error) {
                console.error('OCR Error:', error);
                alert(`${file.name} 분석 중 오류가 발생했습니다.`);
            }
        });

        Promise.all(uploadPromises).then(() => {
            finishUpload();
        });

        function finishUpload() {
            loadingOverlay.classList.remove('active');
            uploadOverlay.classList.remove('show');
            submitUploadBtn.disabled = false;
            closeUploadModal.disabled = false;
            renderMainPreviews();
        }
    });
});
