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

    let lastPrescriptionId = null;

    // --- Sync Elements ---
    const syncModal = document.getElementById('prescription-sync-modal');
    const btnSync = document.getElementById('btn-sync-prescription');
    const btnCancelSync = document.getElementById('btn-cancel-sync');

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
        // 이미지가 없으면 빈 상태(업로드 안내) 표시
        if (uploadedImages[type].length === 0) {
            container.classList.add('empty-state');
            container.innerHTML = `
                <div style="font-size: 48px; margin-bottom: 10px;">📁</div>
                <div style="font-weight: 700; color: #475569; font-size: 16px;">파일 업로드</div>
                <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">지원 형식: JPG, PNG, PDF (최대 10MB, 다중 선택 가능)</div>
            `;
            return;
        }

        // 이미지가 있으면 리스트 렌더링
        container.classList.remove('empty-state');
        container.innerHTML = '';

        // 업로드 버튼 역할을 할 빈 박스 하나 추가 (다시 업로드 가능하도록)
        const addBtn = document.createElement('div');
        addBtn.className = 'main-preview-item add-more-btn';
        addBtn.style.cssText = 'border: 2px dashed #3b82f6; display: flex; align-items: center; justify-content: center; font-size: 24px; color: #3b82f6; cursor: pointer; background: #f8fbff;';
        addBtn.innerHTML = '+';
        addBtn.onclick = (e) => {
            e.stopPropagation();
            currentUploadType = type;
            uploadOverlay.classList.add('show');
            resetUpload();
        };
        container.appendChild(addBtn);

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
    submitUploadBtn.addEventListener('click', async () => {
        if (selectedFiles.length === 0) return;

        // Show loading
        loadingOverlay.classList.add('active');
        submitUploadBtn.disabled = true;
        closeUploadModal.disabled = true;

        try {
            if (currentUploadType === 'prescription') {
                // --- [Case 1] 처방전: 각 파일을 개별적으로 순차 전송 ---
                for (const file of selectedFiles) {
                    const formData = new FormData();
                    formData.append('file', file);

                    const token = localStorage.getItem('access_token');
                    const response = await fetch('/api/v1/ocr/prescription', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`
                        },
                        body: formData
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || '처방전 분석 실패');
                    }

                    const data = await response.json();
                    updateAnalysisUI('prescription', data);

                    // 파일 메인 뷰에 추가 (기존 selectedFiles가 아닌 서버 성공 시점에 추가되도록 보장)
                    addMainPreview('prescription', file);
                }
            } else {
                // --- [Case 2] 알약: 앞/뒷면 두 장을 한 번에 전송 ---
                if (selectedFiles.length < 2) {
                    alert("알약 분석을 위해 앞면과 뒷면 사진 두 장을 모두 선택해주세요.");
                    loadingOverlay.classList.remove('active');
                    submitUploadBtn.disabled = false;
                    closeUploadModal.disabled = false;
                    return;
                }

                const formData = new FormData();
                formData.append('front_file', selectedFiles[0]);
                formData.append('back_file', selectedFiles[1]);

                const token = localStorage.getItem('access_token');
                const response = await fetch('/api/v1/ocr/pill', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });


                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || '알약 분석 실패');
                }

                const data = await response.json();
                updateAnalysisUI('medication', data.preview_text);

                // 두 파일 모두 메인 뷰에 추가
                addMainPreview('medication', selectedFiles[0]);
                addMainPreview('medication', selectedFiles[1]);
            }

            // 전송 완료 후 모달 닫기
            setTimeout(() => {
                uploadOverlay.classList.remove('show');
                finishUpload();
            }, 500);

        } catch (error) {
            console.error('Upload Error:', error);
            alert(`오류 발생: ${error.message}`);
            finishUpload();
        }
    });

    /**
     * 분석 결과 UI 업데이트 (처방전/약봉투 또는 알약)
     * @param {string} type - 'prescription' 또는 'medication'
     * @param {object|string} data - 필터링된 API 응답 데이터
     */
    function updateAnalysisUI(type, data) {
        const targetBoxId = type === 'prescription' ? 'prescription-analysis-box' : 'medication-analysis-box';
        const targetBox = document.getElementById(targetBoxId);
        if (!targetBox) return;

        const resultContainer = targetBox.querySelector('.analysis-result-text');
        if (!resultContainer) return;

        // 1. 처방전(Prescription) 구조화 데이터 처리
        if (type === 'prescription' && typeof data === 'object') {
            const hospitalName = data.hospital_name || '미확인 병원';
            const prescribedDate = data.prescribed_date || '날짜 정보 없음';

            // 약물 리스트 생성
            let drugListHtml = '';
            const drugList = data.drugs || [];

            if (drugList.length > 0) {
                drugListHtml = drugList.map(d => {
                    const name = d.standard_drug_name || d.drug_name || d.name || '알 수 없는 약품';
                    const dosage = d.dosage_amount || d.dosage || '';
                    const frequency = d.daily_frequency || d.frequency || '';
                    const duration = d.duration_days || d.duration || '';

                    return `
                        <div class="prescription-drug-item" 
                             data-name="${name}"
                             style="margin-bottom: 8px; padding: 12px 15px; background: #fff; border-radius: 10px; border: 1px solid #e1e8f0; border-left: 5px solid #007bff; box-shadow: 0 2px 5px rgba(0,0,0,0.04); display: flex; align-items: center; justify-content: space-between; cursor: pointer; transition: all 0.2s;">
                            <div style="display: flex; align-items: center; flex: 1;">
                                <span style="font-size: 18px; margin-right: 10px;">💊</span>
                                <span style="font-weight: 600; color: #2c3e50; line-height: 1.2;">${name}</span>
                            </div>
                            <div style="text-align: right; font-size: 11px; color: #7f8c8d; min-width: 80px;">
                                <span style="display: inline-block; background: #f8f9fa; padding: 2px 6px; border-radius: 4px; margin-bottom: 2px;">${dosage || '1정'}</span>
                                <br>
                                <span>${frequency ? frequency + '회' : '-'} / ${duration ? duration + '일분' : '-'}</span>
                            </div>
                        </div>
                    `;
                }).join('');
            } else if (data.drug_names && data.drug_names.length > 0) {
                drugListHtml = data.drug_names.map(name => `
                    <div class="prescription-drug-item" 
                         data-name="${name}"
                         style="margin-bottom: 8px; padding: 12px 15px; background: #fff; border-radius: 10px; border: 1px solid #e1e8f0; border-left: 5px solid #007bff; font-weight: 600; font-size: 15px; color: #2c3e50; box-shadow: 0 2px 5px rgba(0,0,0,0.04); cursor: pointer; transition: all 0.2s;">
                        <span style="font-size: 18px; margin-right: 10px;">💊</span> ${name}
                    </div>
                `).join('');
            } else {
                drugListHtml = '<div style="color: #95a5a6; padding: 20px; text-align: center; background: #f8f9fa; border-radius: 10px;">분석된 약물 성분이 없습니다.</div>';
            }

            // 전체 레이아웃 렌더링
            resultContainer.innerHTML = `
                <div style="background: #f8fbff; padding: 15px; border-radius: 12px; border: 1px solid #e1f0ff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #eef2f7;">
                        <div>
                            <div style="color: #666; font-size: 11px; margin-bottom: 2px;">🏥 병원명</div>
                            <div style="font-weight: 600; font-size: 14px; color: #333;">${hospitalName}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #666; font-size: 11px; margin-bottom: 2px;">📅 처방일</div>
                            <div style="font-weight: 500; font-size: 14px; color: #333;">${prescribedDate}</div>
                        </div>
                    </div>
                    <div>
                        <div style="color: #666; font-size: 11px; margin-bottom: 8px;">💊 분석된 약물 리스트 (클릭하여 선택)</div>
                        <div style="max-height: 250px; overflow-y: auto; padding-right: 5px;" class="custom-scrollbar">
                            ${drugListHtml}
                        </div>
                    </div>
                </div>
            `;

            // 클릭 이벤트 리스너 등록
            resultContainer.querySelectorAll('.prescription-drug-item').forEach(item => {
                item.addEventListener('click', () => {
                    item.classList.toggle('selected');
                    if (item.classList.contains('selected')) {
                        item.style.background = '#e0f2fe';
                        item.style.borderColor = '#7dd3fc';
                    } else {
                        item.style.background = '#fff';
                        item.style.borderColor = '#e1e8f0';
                    }
                });
            });

            // 전역 변수에 ID 저장 및 연동 모달 표시
            if (data.prescription_id || data.id) {
                lastPrescriptionId = data.prescription_id || data.id;
                if (syncModal) syncModal.style.display = 'block';
            }
        }
        // 2. 알약(Medication/Pill) 데이터 처리
        else if (type === 'medication' && typeof data === 'object') {
            targetBox.style.display = 'block';

            const recognitionId = data.id;
            const candidates = data.candidates || [];
            const displayText = data.display_text || '';
            const appearance = data.appearance || {};

            let candidatesHtml = '';
            if (candidates.length > 0) {
                candidatesHtml = candidates.map((c, index) => {
                    const confidencePercent = Math.round(c.confidence * 100);
                    const isTop = index === 0;

                    return `
                        <div class="pill-candidate-card" style="margin-bottom: 12px; border: 2px solid ${isTop ? '#7c3aed' : '#e2e8f0'}; border-radius: 12px; padding: 12px; background: white; transition: all 0.2s;">
                            <div style="display: flex; gap: 12px;">
                                ${c.image_url ?
                            `<img src="${c.image_url}" style="width: 80px; height: 60px; object-fit: contain; border-radius: 6px; background: #f8fafc; border: 1px solid #eee;">` :
                            `<div style="width: 80px; height: 60px; background: #f1f5f9; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 20px;">💊</div>`
                        }
                                <div style="flex: 1;">
                                    <div style="display: flex; justify-content: space-between; align-items: start;">
                                        <div style="font-weight: 700; color: #1e293b; font-size: 14px;">${c.pill_name}</div>
                                        <div style="background: ${isTop ? '#7c3aed' : '#94a3b8'}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700;">
                                            ${confidencePercent}% 일치
                                        </div>
                                    </div>
                                    <div style="font-size: 11px; color: #64748b; margin-top: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                                        ${c.medication_info || '정보 없음'}
                                    </div>
                                    <button class="btn-select-pill" 
                                            data-id="${recognitionId}" 
                                            data-name="${c.pill_name}" 
                                            data-info="${c.medication_info}"
                                            style="margin-top: 8px; width: 100%; border: none; background: ${isTop ? '#7c3aed' : '#f1f5f9'}; color: ${isTop ? 'white' : '#475569'}; padding: 6px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;">
                                        ${isTop ? '이 약이 맞아요' : '선택하기'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                candidatesHtml = '<div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 13px;">일치하는 약품 정보를 찾을 수 없습니다.</div>';
            }

            resultContainer.innerHTML = `
                <div style="background: #f8fafc; border-radius: 12px; padding: 15px; border: 1px solid #e2e8f0;">
                    <div style="margin-bottom: 12px; padding: 10px; background: white; border-radius: 10px; border-left: 4px solid #7c3aed; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                        <div style="font-size: 11px; color: #94a3b8; margin-bottom: 2px;">🤖 분석된 검색 조건</div>
                        <div style="font-size: 13px; font-weight: 600; color: #475569;">${displayText}</div>
                        <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">각인: ${appearance.marking || '-'} | 색상: ${appearance.color || '-'} | 모양: ${appearance.shape || '-'}</div>
                    </div>
                    
                    <div style="font-size: 14px; font-weight: 700; color: #1e293b; margin-bottom: 10px; display: flex; align-items: center;">
                        <span style="margin-right: 6px;">🔍</span> 검색 결과 후보
                    </div>
                    
                    <div class="pill-candidates-list" style="max-height: 400px; overflow-y: auto; padding-right: 5px;">
                        ${candidatesHtml}
                    </div>
                </div>
            `;

            // 이벤트 리스너 등록
            resultContainer.querySelectorAll('.btn-select-pill').forEach(btn => {
                btn.onclick = async () => {
                    const id = btn.dataset.id;
                    const name = btn.dataset.name;
                    const info = btn.dataset.info;

                    try {
                        const response = await fetch('/api/v1/ocr/pill/select', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                            body: new URLSearchParams({
                                recognition_id: id,
                                pill_name: name,
                                pill_description: info
                            })
                        });

                        if (response.ok) {
                            alert(`'${name}'(으)로 최종 선택되었습니다.`);
                            // UI 업데이트 (선택된 상태 표시)
                            resultContainer.querySelectorAll('.pill-candidate-card').forEach(card => {
                                card.style.opacity = '0.5';
                                card.style.border = '2px solid #e2e8f0';
                            });
                            btn.closest('.pill-candidate-card').style.opacity = '1';
                            btn.closest('.pill-candidate-card').style.border = '2px solid #10b981';
                            btn.textContent = '선택됨 ✅';
                            btn.style.background = '#10b981';
                            btn.style.color = 'white';
                            btn.disabled = true;
                        }
                    } catch (e) {
                        console.error('Pill Selection Error:', e);
                    }
                };
            });
        }
        // 3. 기타 예외 처리
        else {
            if (type === 'medication') targetBox.style.display = 'block';
            const text = typeof data === 'object' ? (data.preview_text || data.message || "분석 완료") : data;
            resultContainer.textContent = text;
            resultContainer.style.color = '#333';
            resultContainer.style.background = '#fff';
            resultContainer.style.padding = '10px';
            resultContainer.style.borderRadius = '8px';
            resultContainer.style.border = '1px solid #eee';
        }
    }
    function addMainPreview(type, file) {
        if (!file) return;

        if (file.type && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                // 중복 추가 방지 (같은 데이터가 이미 있으면 추가 안함 - 선택적)
                if (!uploadedImages[type].includes(e.target.result)) {
                    uploadedImages[type].push(e.target.result);
                    renderMainPreviews();
                }
            };
            reader.onerror = (err) => console.error("FileReader Error:", err);
            reader.readAsDataURL(file);
        } else if (file.type === 'application/pdf') {
            uploadedImages[type].push('FILE_TYPE_PDF');
            renderMainPreviews();
        } else {
            // 타입이 명확하지 않을 경우 확장자로 판단 시도
            const fileName = (file.name || '').toLowerCase();
            if (fileName.endsWith('.jpg') || fileName.endsWith('.jpeg') || fileName.endsWith('.png')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    if (!uploadedImages[type].includes(e.target.result)) {
                        uploadedImages[type].push(e.target.result);
                        renderMainPreviews();
                    }
                };
                reader.readAsDataURL(file);
            } else {
                uploadedImages[type].push('FILE_TYPE_UNKNOWN');
                renderMainPreviews();
            }
        }
    }

    function finishUpload() {
        loadingOverlay.classList.remove('active');
        submitUploadBtn.disabled = false;
        closeUploadModal.disabled = false;
        renderMainPreviews();
    }

    // --- Sync Action (Prescription -> CurrentMed) ---
    if (btnSync) {
        btnSync.addEventListener('click', async () => {
            if (!lastPrescriptionId) return;

            // 선택된 약물 이름들 수집
            const selectedItems = document.querySelectorAll('.prescription-drug-item.selected');
            const selectedDrugNames = Array.from(selectedItems).map(item => item.dataset.name);

            if (selectedDrugNames.length === 0) {
                alert('연동할 약물을 하나 이상 선택해 주세요.');
                return;
            }

            try {
                const token = localStorage.getItem('access_token');
                const response = await fetch(`/api/v1/ocr/prescriptions/${lastPrescriptionId}/sync`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ drug_names: selectedDrugNames })
                });

                if (!response.ok) throw new Error('연동 실패');

                const data = await response.json();
                alert(`${data.count}개의 약물이 성공적으로 연동되었습니다.`);
                if (syncModal) syncModal.style.display = 'none';
            } catch (error) {
                alert(`오류: ${error.message}`);
            }
        });
    }

    if (btnCancelSync) {
        btnCancelSync.addEventListener('click', () => {
            if (syncModal) syncModal.style.display = 'none';
        });
    }
});