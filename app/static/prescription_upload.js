/**
 * Prescription Upload and Analysis Logic
 */

window.prescriptionSessionResults = [];

document.addEventListener('DOMContentLoaded', () => {
    if (!window.submitUploadBtn) return;

    window.submitUploadBtn.addEventListener('click', async () => {
        if (window.currentUploadType !== 'prescription') return;
        if (window.selectedFiles.length === 0) return;

        window.loadingOverlay.classList.add('active');
        window.submitUploadBtn.disabled = true;
        window.closeUploadModal.disabled = true;

        try {
            for (const file of window.selectedFiles) {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetchWithAuth('/api/v1/ocr/prescription', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || '처방전 분석 실패');
                }

                const data = await response.json();
                updatePrescriptionUI(data);
                window.addMainPreview('prescription', file);
            }

            setTimeout(() => {
                window.uploadOverlay.classList.remove('show');
                window.finishUpload();

                // 히스토리 리스트 갱신
                if (typeof window.fetchUploadHistory === 'function') {
                    window.fetchUploadHistory();
                }
            }, 500);

        } catch (error) {
            console.error('Prescription Upload Error:', error);
            if (typeof showAppToast === 'function') {
                showAppToast(`오류 발생: ${error.message}`, "warn", "오류");
            }
            window.finishUpload();
        }
    });

    function renderPrescriptionResults() {
        const targetBox = document.getElementById('prescription-analysis-box');
        if (!targetBox) return;

        const resultContainer = targetBox.querySelector('.analysis-result-text');
        if (!resultContainer) return;

        resultContainer.scrollTop = 0;

        if (window.prescriptionSessionResults.length === 0) {
            resultContainer.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 40px 20px;">분석된 처방전이 없습니다.<br>사진을 추가하여 분석을 시작하세요.</div>';
            return;
        }

        const grouped = window.prescriptionSessionResults.reduce((acc, current) => {
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
                const pId = res.prescription_id || (res.hospital ? res.hospital.id : null) || res.id || 'unknown';
                const pDate = res.prescribed_date || '날짜 정보 없음';
                const drugList = res.drugs || [];

                let drugListHtml = drugList.length > 0 ? drugList.map(d => {
                    const name = d.standard_drug_name || d.drug_name || d.name || '알 수 없는 약품';
                    const dosage = d.dosage_amount || d.dosage || '';
                    const frequency = d.daily_frequency || d.frequency || '';
                    const duration = d.duration_days || d.duration || '';

                    return `
                        <div class="pill-candidate-card prescription-drug-item" data-name="${name}" data-prescription-id="${pId}">
                            <div style="display: flex; gap: 12px;">
                                <div style="width: 80px; height: 60px; background: #f1f5f9; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 20px;">💊</div>
                                <div style="flex: 1;">
                                    <div style="display: flex; justify-content: space-between; align-items: start;">
                                        <div style="font-weight: 700; color: #1e293b; font-size: 14px;">${name}</div>
                                        <div style="background: #eef2ff; color: #4f46e5; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700;">${dosage || '1정'}</div>
                                    </div>
                                    <div style="font-size: 11px; color: #64748b; margin-top: 4px;">${frequency ? frequency + '회' : '-'} / ${duration ? duration + '일분' : '-'}</div>
                                    <button class="btn-toggle-sync prescription-sync-btn" data-prescription-id="${pId}" data-name="${name}">
                                        ➕ 복용 정보 등록
                                    </button>
                                </div>
                            </div>
                        </div>`;
                }).join('') : '<div style="color: #95a5a6; padding: 10px; text-align: center;">분석된 약물이 없습니다.</div>';

                return `
                    <div class="prescription-result-block">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 12px; color: #7f8c8d;">
                            <span>📅 처방일: ${pDate}</span>
                        </div>
                        <div class="drug-list-container">${drugListHtml}</div>
                    </div>`;
            }).join('');

            fullHtml += `
                <div class="hospital-group" style="margin-bottom: 20px; border-bottom: 1px solid #f1f5f9; padding-bottom: 15px;">
                    <div class="hospital-info-card" style="background: #f8fafc; border-radius: 8px; padding: 12px; margin-bottom: 12px; border-left: 4px solid #6366f1;">
                        <div style="font-size: 11px; color: #94a3b8; margin-bottom: 2px;">🏥 분석된 병원 정보</div>
                        <div style="font-weight: 700; font-size: 15px; color: #1e293b;">${hospital}</div>
                    </div>
                    <div class="drug-list-header" style="font-size: 13px; font-weight: 700; color: #475569; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;"><span>💊</span> 처방 약물 목록</div>
                    <div class="drug-list-scroll">${hospitalBlocksHtml}</div>
                </div>`;
        }

        resultContainer.innerHTML = fullHtml;

        // Event Listeners for Sync Buttons
        resultContainer.querySelectorAll('.prescription-sync-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const pId = btn.dataset.prescriptionId;
                const name = btn.dataset.name;

                try {
                    const response = await fetchWithAuth('/api/v1/ocr/prescriptions/toggle-sync', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: new URLSearchParams({ prescription_id: pId, drug_name: name })
                    });

                    const result = await response.json();
                    if (response.ok) {
                        if (result.synced) {
                            btn.textContent = '✅ 등록 취소';
                            btn.classList.add('is-synced');
                            window.drug_change_cnt += 1;
                        } else {
                            btn.textContent = '➕ 복용 정보 등록';
                            btn.classList.remove('is-synced');
                            window.drug_change_cnt -= 1;
                        }
                        window.showToast(result.message);
                    }
                } catch (error) {
                    if (typeof showAppToast === 'function') showAppToast(`오류: ${error.message}`, "warn", "오류");
                }
            });
        });
    }

    window.removePrescriptionResult = function(index) {
        if (window.prescriptionSessionResults && window.prescriptionSessionResults[index] !== undefined) {
            window.prescriptionSessionResults.splice(index, 1);
            renderPrescriptionResults();
        }
    };

    function updatePrescriptionUI(data) {
        if (data) {
            if (Array.isArray(data)) {
                window.prescriptionSessionResults.push(...data);
            } else if (typeof data === 'object') {
                window.prescriptionSessionResults.push(data);
            }
            renderPrescriptionResults();

            const syncModal = document.getElementById('prescription-sync-modal');
            if (syncModal) {
                setTimeout(() => { syncModal.style.display = 'block'; }, 100);
            }
        }
    }
});
