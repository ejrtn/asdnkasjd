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
    let prescriptionSessionResults = []; // Store multiple analysis results for the current session

    // Persistent state for main view (uploaded images)
    let uploadedImages = {
        prescription: [],
        medication: []
    };


    // --- Sync Elements ---
    const syncModal = document.getElementById('prescription-sync-modal');
    const btnSync = document.getElementById('btn-sync-prescription');
    const btnCancelSync = document.getElementById('btn-cancel-sync');

    // --- Zoom Elements ---
    const zoomOverlay = document.getElementById('zoom-overlay');
    const zoomImg = document.getElementById('zoom-img');
    const closeZoomBtn = document.querySelector('.btn-zoom-close');

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

    // --- Zoom Modal Control ---
    function showZoomModal(src) {
        zoomImg.src = src;
        zoomOverlay.classList.add('show');
    }

    if (zoomOverlay) {
        zoomOverlay.addEventListener('click', (e) => {
            if (e.target === zoomOverlay || e.target.classList.contains('btn-zoom-close')) {
                zoomOverlay.classList.remove('show');
            }
        });
    }

    if (closeZoomBtn) {
        closeZoomBtn.addEventListener('click', () => {
            zoomOverlay.classList.remove('show');
        });
    }

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
        container.innerHTML = '';
        container.className = 'upload-zone-card has-files'; // Always use has-files to enable flex layout

        // Always show the "Add" button as a square thumbnail
        const addBtn = document.createElement('div');
        addBtn.className = 'main-upload-add-btn';
        addBtn.innerHTML = `
            <div class="main-upload-add-btn-icon">➕</div>
            <div class="main-upload-add-btn-text">사진 추가</div>
        `;
        addBtn.onclick = (e) => {
            e.stopPropagation();
            currentUploadType = type;
            uploadOverlay.classList.add('show');
            resetUpload();
        };
        container.appendChild(addBtn);

        // Render existing images
        uploadedImages[type].forEach((imageData, index) => {
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
            removeBtn.title = '삭제';
            removeBtn.onclick = (e) => {
                e.stopPropagation();
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
                    const response = await fetchWithAuth('/api/v1/ocr/prescription', {
                        method: 'POST',
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
                formData.append('files', selectedFiles[0]);
                formData.append('files', selectedFiles[1]);

                const response = await fetchWithAuth("/api/v1/uploads", {
                    method: "POST",
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || '알약 분석 실패');
                }

                const data = await response.json();
                updateAnalysisUI('medication', data);

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

        // 새로운 결과 렌더링 시 상단으로 스크롤 고정
        resultContainer.scrollTop = 0;

        // 1. 처방전(Prescription) 구조화 데이터 처리
        if (type === 'prescription' && data) {
            // Flatten current result if it's an array and add to session results
            if (Array.isArray(data)) {
                prescriptionSessionResults.push(...data);
            } else if (typeof data === 'object') {
                prescriptionSessionResults.push(data);
            }

            // Group by hospital name (Ensure flat grouping)
            const grouped = prescriptionSessionResults.reduce((acc, current) => {
                // 병원명이 없거나 빈 공백인 경우 처리
                const hospital = (current.hospital_name && current.hospital_name.trim())
                    ? current.hospital_name.trim()
                    : '병원명 미확인';

                if (!acc[hospital]) acc[hospital] = [];
                acc[hospital].push(current);
                return acc;
            }, {});

            let fullHtml = '';

            for (const hospital in grouped) {
                const results = grouped[hospital];

                let hospitalBlocksHtml = results.map(res => {
                    const pId = res.prescription_id || res.id || 'unknown';
                    const pDate = res.prescribed_date || '날짜 정보 없음';
                    const drugList = res.drugs || [];

                    let drugListHtml = '';
                    if (drugList.length > 0) {
                        drugListHtml = drugList.map(d => {
                            const name = d.standard_drug_name || d.drug_name || d.name || '알 수 없는 약품';
                            const dosage = d.dosage_amount || d.dosage || '';
                            const frequency = d.daily_frequency || d.frequency || '';
                            const duration = d.duration_days || d.duration || '';

                            return `
                                <div class="prescription-drug-item" 
                                     data-name="${name}"
                                     data-prescription-id="${pId}"
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
                    } else {
                        drugListHtml = '<div style="color: #95a5a6; padding: 10px; text-align: center;">분석된 약물이 없습니다.</div>';
                    }

                    return `
                        <div class="prescription-result-block" style="margin-bottom: 15px; padding-bottom: 10px; ${results.length > 1 ? 'border-bottom: 1px dashed #eef2f7;' : ''}">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 12px; color: #7f8c8d;">
                                <span>📅 처방일: ${pDate}</span>
                            </div>
                            <div class="drug-list-container">
                                ${drugListHtml}
                            </div>
                        </div>
                    `;
                }).join('');

                fullHtml += `
                    <div class="hospital-group" style="background: #f8fbff; padding: 15px; border-radius: 12px; border: 1px solid #e1f0ff; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 20px; width: 100%;">
                        <div style="margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #007bff;">
                            <div style="color: #666; font-size: 11px; margin-bottom: 2px;">🏥 병원명</div>
                            <div style="font-weight: 700; font-size: 16px; color: #007bff;">${hospital}</div>
                        </div>
                        <div>
                            ${hospitalBlocksHtml}
                        </div>
                    </div>
                `;
            }

            resultContainer.innerHTML = fullHtml;

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

            // 연동 모달 표시: 모든 렌더링이 완료된 후 하단에 나타나도록 함
            if (syncModal) {
                // 부드러운 노출을 위해 display 제어 (자동 스크롤 제거)
                setTimeout(() => {
                    syncModal.style.display = 'block';
                }, 100);
            }
        }
        // 2. 알약(Medication/Pill) 데이터 처리
        else if (type === 'medication' && (Array.isArray(data) || typeof data === 'object')) {
            targetBox.style.display = 'block';
            console.log(data);

            // 새로운 배열 구조 또는 기존 객체 구조 대응
            const candidates = Array.isArray(data) ? data : (data.candidates || []);
            const firstItem = candidates[0] || {};
            
            // 시각 분석 정보 추출 (첫 번째 후보의 raw_result 또는 data.ai_extracted 사용)
            const aiInfo = firstItem.raw_result ? Object.values(firstItem.raw_result)[0] : (data.ai_extracted ? Object.values(data.ai_extracted)[0] : {});
            
            const displayText = firstItem.pill_name || data.display_text || '';
            const appearance = {
                marking: aiInfo.text || '',
                color: aiInfo.color || '',
                shape: aiInfo.shape || '',
                formulation: aiInfo.formulation || ''
            };

            let candidatesHtml = '';
            if (candidates.length > 0) {
                candidatesHtml = candidates.map((c, index) => {
                    const score = c.score !== undefined ? c.score : (c.confidence || 0);
                    const confidencePercent = Math.round(score * 100);
                    const pillName = c.name || c.pill_name || '알 수 없는 약품';
                    const pillInfo = c.efcy_qesitm || c.pill_description || c.medication_info || '정보 없음';
                    const pillImg = c.image_path || c.image_url;
                    // 각 후보별 고유 ID 사용
                    const cid = c.id || '';

                    return `
                        <div class="pill-candidate-card" style="margin-bottom: 12px; border: 2px solid #e2e8f0; border-radius: 12px; padding: 12px; background: white; transition: all 0.2s;">
                            <div style="display: flex; gap: 12px;">
                                ${pillImg ?
                            `<img src="${pillImg}" style="width: 80px; height: 60px; object-fit: contain; border-radius: 6px; background: #f8fafc; border: 1px solid #eee;">` :
                            `<div style="width: 80px; height: 60px; background: #f1f5f9; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 20px;">💊</div>`
                        }
                                <div style="flex: 1;">
                                    <div style="display: flex; justify-content: space-between; align-items: start;">
                                        <div style="font-weight: 700; color: #1e293b; font-size: 14px;">${pillName}</div>
                                        <div style="background: #94a3b8; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700;">
                                            ${confidencePercent}% 일치
                                        </div>
                                    </div>
                                    <div style="font-size: 11px; color: #64748b; margin-top: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                                        ${pillInfo}
                                    </div>
                                    <button class="btn-toggle-sync" 
                                            data-id="${cid}" 
                                            data-name="${pillName}" 
                                            data-info="${pillInfo}"
                                            style="margin-top: 8px; width: 100%; border: 2px solid #7c3aed; background: white; color: #7c3aed; padding: 6px; border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s;">
                                        ➕ 복용 정보 등록
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
                        <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">각인: ${appearance.marking || '-'} | 색상: ${appearance.color || '-'} | 모양: ${appearance.shape || '-'} | 제형: ${appearance.formulation || '-'}</div>
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
            resultContainer.querySelectorAll('.btn-toggle-sync').forEach(btn => {
                btn.onclick = async () => {
                    const id = btn.dataset.id;
                    const name = btn.dataset.name;
                    const info = btn.dataset.info;

                    try {
                        if (!id) {
                            console.error('Missing recognition_id');
                            alert('식별 정보가 누락되었습니다. 다시 시도해 주세요.');
                            return;
                        }

                        const response = await fetchWithAuth('/api/v1/ocr/pill/toggle-sync', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                            body: new URLSearchParams({
                                recognition_id: id,
                                pill_name: name,
                                pill_description: info
                            })
                        });

                        const result = await response.json();

                        if (response.ok) {
                            if (result.synced) {
                                // 등록됨 상태
                                btn.textContent = '✅ 등록 취소';
                                btn.style.background = '#7c3aed';
                                btn.style.color = 'white';
                                btn.closest('.pill-candidate-card').style.borderColor = '#7c3aed';
                                btn.closest('.pill-candidate-card').style.background = '#f5f3ff';
                            } else {
                                // 미등록 상태로 원복
                                btn.textContent = '➕ 복용 정보 등록';
                                btn.style.background = 'white';
                                btn.style.color = '#7c3aed';
                                btn.closest('.pill-candidate-card').style.borderColor = '#e2e8f0';
                                btn.closest('.pill-candidate-card').style.background = 'white';
                            }
                            
                            if (typeof showToast === 'function') {
                                showToast(result.message);
                            } else {
                                console.log(result.message);
                            }
                        }
                    } catch (e) {
                        console.error('Pill Sync Toggle Error:', e);
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

    // --- Toast Notification ---
    function showToast(message) {
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
    }

    // --- Sync Action (Prescription -> CurrentMed) ---
    if (btnSync) {
        btnSync.addEventListener('click', async () => {
            // 선택된 약물들 수집 (데이터-처방전-ID 필요)
            const selectedItems = document.querySelectorAll('.prescription-drug-item.selected');
            if (selectedItems.length === 0) {
                alert('연동할 알약을 하나 이상 선택해 주세요.');
                return;
            }

            // Group drug names by prescription ID
            const syncGroups = {};
            selectedItems.forEach(item => {
                const pId = item.dataset.prescriptionId;
                const name = item.dataset.name;
                if (!syncGroups[pId]) syncGroups[pId] = [];
                syncGroups[pId].push(name);
            });

            try {
                const token = localStorage.getItem('access_token');
                let totalSynced = 0;

                // Call sync API for each prescription group
                for (const pId in syncGroups) {
                    if (pId === 'unknown') continue;

                    const response = await fetchWithAuth(`/api/v1/ocr/prescriptions/${pId}/sync`, {
                        method: 'POST',
                        body: JSON.stringify({ drug_names: syncGroups[pId] })
                    });

                    if (!response.ok) throw new Error(`처방전(ID: ${pId}) 연동 실패`);
                    const data = await response.json();
                    totalSynced += data.count;
                }

                // 성공 피드백: 알럿 대신 토스트 사용 및 창 유지
                showToast(`${totalSynced}개의 약물이 복용 명단에 추가되었습니다.`);

                // 선택된 약물들의 스타일 초기화 및 선택 해제 (창은 닫지 않음)
                selectedItems.forEach(item => {
                    item.classList.remove('selected');
                    item.style.background = '#fff';
                    item.style.borderColor = '#e1e8f0';
                });
            } catch (error) {
                alert(`오류: ${error.message}`);
            }
        });
    }

    if (btnCancelSync) {
        btnCancelSync.addEventListener('click', () => {
            // "나중에" 버튼을 눌러도 창이 닫히지 않도록 수정되었습니다.
            // 필요시 선택 해제 등의 다른 로직을 추가할 수 있습니다.
            console.log('Sync postponed, but window remains open.');
        });
    }
});

// 업로드 히스토리 불러오기
async function fetchUploadHistory() {
    const list1 = document.getElementById('upload-history-list-prescription');
    const list2 = document.getElementById('upload-history-list-pill');

    // 두 컨테이너 중 하나라도 없으면 여기서 에러표시를 할 필요는 없지만,
    // 둘 다 없다면 굳이 페치할 필요 없음.
    if (!list1 && !list2) return;

    try {
        const response = await fetchWithAuth('/api/v1/uploads/history');
        if (response.ok) {
            const result = await response.json();
            const data = result.content || [];
            console.log(data)
            if (list1) renderUploadHistory(list1, data);
            if (list2) renderUploadHistory(list2, data);
        } else {
            console.error("히스토리 데이터를 불러오지 못했습니다.");
            const errorHtml = `<div style="text-align: center; color: #ef4444; padding: 20px 0;">히스토리를 불러오는 중 오류가 발생했습니다.</div>`;
            if (list1) list1.innerHTML = errorHtml;
            if (list2) list2.innerHTML = errorHtml;
        }
    } catch (e) {
        console.error("히스토리 Fetch 중 에러: ", e);
        const errorHtml = `<div style="text-align: center; color: #ef4444; padding: 20px 0;">히스토리를 불러오는 중 오류가 발생했습니다.</div>`;
        if (list1) list1.innerHTML = errorHtml;
        if (list2) list2.innerHTML = errorHtml;
    }
}

// 업로드 히스토리 렌더링
function renderUploadHistory(container, historyList) {
    if (!container) return;

    if (!historyList || historyList.length === 0) {
        container.innerHTML = `<div style="text-align: center; color: #94a3b8; padding: 20px 0;">아직 업로드한 기록이 없습니다.</div>`;
        return;
    }

    let html = '';
    historyList.forEach((item, index) => {
        const icon = item.type === '처방전' ? '📄' : '💊';
        const dateStr = item.date;
        const uniqueId = `history-images-${container.id}-${index}`;

        // 이미지 목록 서브 HTML 생성
        let imagesHtml = '';
        if (item.images && item.images.length > 0) {
            item.images.forEach(img => {
                imagesHtml += `
                    <div class="history-image-item" data-url="${img.url}" style="padding: 8px 10px; margin-top: 5px; background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px; color: #475569; transition: background 0.2s;">
                        <span>🖼️</span>
                        <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${img.name}</span>
                    </div>
                `;
            });
        } else {
            imagesHtml = `<div style="font-size: 13px; color: #94a3b8; padding: 5px;">이미지가 없습니다.</div>`;
        }

        html += `
            <div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">
                <!-- 타이틀 (클릭 시 아코디언 토글) + X 버튼 -->
                <div class="history-title-row" style="display: flex; align-items: center; justify-content: space-between; padding: 10px 5px; cursor: pointer;">
                    <div style="display: flex; align-items: center; font-size: 16px; font-weight: 500; color: #334155; flex: 1;">
                        <span style="font-size: 20px; margin-right: 12px; opacity: 0.8;">${icon}</span>
                        <span>${dateStr} ${item.type}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div class="history-arrow" style="font-size: 16px; color: #94a3b8; transition: transform 0.3s;">▼</div>
                        <button class="history-delete-btn" data-id="${item.id}" title="삭제"
                            style="background: none; border: none; cursor: pointer; font-size: 16px; color: #cbd5e1; padding: 4px 6px; border-radius: 4px; line-height: 1; transition: color 0.2s;"
                            onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='#cbd5e1'">✕</button>
                    </div>
                </div>
                <!-- 확장 영역 (이미지 목록) -->
                <div id="${uniqueId}" style="display: none; padding-left: 35px; padding-right: 10px; flex-direction: column; gap: 5px; margin-top: 5px;">
                    ${imagesHtml}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;

    // 이벤트 리스너 바인딩 (아코디언 토글)
    const titleRows = container.querySelectorAll('.history-title-row');
    titleRows.forEach(row => {
        row.addEventListener('click', function () {
            const arrow = this.querySelector('.history-arrow');
            const expandArea = this.nextElementSibling;
            if (expandArea.style.display === 'none') {
                expandArea.style.display = 'flex';
                arrow.style.transform = 'rotate(180deg)';
            } else {
                expandArea.style.display = 'none';
                arrow.style.transform = 'rotate(0deg)';
            }
        });
    });

    // 이벤트 리스너 바인딩 (X 삭제 버튼)
    const deleteBtns = container.querySelectorAll('.history-delete-btn');
    deleteBtns.forEach(btn => {
        btn.addEventListener('click', async function (e) {
            e.stopPropagation(); // 아코디언 토글 방지
            const uploadId = this.getAttribute('data-id');
            if (!uploadId) return;

            if (!confirm('이 업로드 기록을 삭제하시겠습니까?')) return;

            try {
                const response = await fetchWithAuth(`/api/v1/uploads/${uploadId}`, {
                    method: 'DELETE',
                });
                if (response.ok) {
                    // 성공 시 히스토리 새로고침
                    fetchUploadHistory();
                } else {
                    alert('삭제 중 오류가 발생했습니다. 다시 시도해 주세요.');
                }
            } catch (err) {
                console.error('삭제 에러:', err);
                alert('삭제 중 오류가 발생했습니다.');
            }
        });
    });

    // 이벤트 리스너 바인딩 (이미지 이름 클릭 시 줌 모달 띄우기)
    const imageItems = container.querySelectorAll('.history-image-item');
    imageItems.forEach(item => {
        item.addEventListener('click', function (e) {
            e.stopPropagation(); // 부모 토글 이벤트 방지
            const url = this.getAttribute('data-url');
            if (url && typeof showZoomModal === 'function') {
                showZoomModal(url);
            } else {
                // fall back logic
                const zoomOverlay = document.getElementById('zoom-overlay');
                const zoomImg = document.getElementById('zoom-img');
                if (zoomOverlay && zoomImg) {
                    zoomImg.src = url;
                    zoomOverlay.classList.add('show');
                } else {
                    window.open(url, '_blank');
                }
            }
        });
    });
}

// 최초 로딩 시 데이터 패치
document.addEventListener('DOMContentLoaded', () => {
    fetchUploadHistory();
});
