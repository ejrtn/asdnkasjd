/**
 * Pill Image Analysis Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    if (!window.submitUploadBtn) return;

    window.submitUploadBtn.addEventListener('click', async () => {
        if (window.currentUploadType !== 'medication') return;
        if (window.selectedFiles.length < 2) {
            if (typeof showAppToast === 'function') {
                showAppToast("알약 분석을 위해 앞면과 뒷면 사진 두 장을 모두 선택해주세요.", "warn", "확인 필요");
            }
            return;
        }

        window.loadingOverlay.classList.add('active');
        window.submitUploadBtn.disabled = true;
        window.closeUploadModal.disabled = true;

        try {
            const formData = new FormData();
            formData.append('files', window.selectedFiles[0]);
            formData.append('files', window.selectedFiles[1]);

            const response = await fetchWithAuth("/api/v1/uploads", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '알약 분석 실패');
            }

            const data = await response.json();
            updatePillUI(data);

            window.addMainPreview('medication', window.selectedFiles[0]);
            window.addMainPreview('medication', window.selectedFiles[1]);

            setTimeout(() => {
                window.uploadOverlay.classList.remove('show');
                window.finishUpload();
            }, 500);

        } catch (error) {
            console.error('Pill Upload Error:', error);
            if (typeof showAppToast === 'function') {
                showAppToast(`오류 발생: ${error.message}`, "warn", "오류");
            }
            window.finishUpload();
        }
    });

    function updatePillUI(data) {
        const targetBox = document.getElementById('medication-analysis-box');
        if (!targetBox) return;

        const resultContainer = targetBox.querySelector('.analysis-result-text');
        if (!resultContainer) return;

        targetBox.style.display = 'block';

        const candidates = Array.isArray(data) ? data : (data.candidates || []);
        const firstItem = candidates[0] || {};
        const aiInfo = firstItem.raw_result ? Object.values(firstItem.raw_result)[0] : (data.ai_extracted ? Object.values(data.ai_extracted)[0] : {});

        const appearance = {
            marking: aiInfo.text || '',
            color: aiInfo.color || '',
            shape: aiInfo.shape || '',
            formulation: aiInfo.formulation || ''
        };

        let candidatesHtml = candidates.length > 0 ? candidates.map(c => {
            const score = c.score !== undefined ? c.score : (c.confidence || 0);
            const confidencePercent = Math.round(score * 100);
            const pillName = c.name || c.pill_name || '알 수 없는 약품';
            const pillInfo = c.efcy_qesitm || c.pill_description || c.medication_info || '정보 없음';
            const pillImg = c.image_path || c.image_url;
            const cid = c.id || '';

            return `
                <div class="pill-candidate-card" style="margin-bottom: 12px; border: 2px solid #e2e8f0; border-radius: 12px; padding: 12px; background: white; transition: all 0.2s;">
                    <div style="display: flex; gap: 12px;">
                        ${pillImg ? `<img src="${pillImg}" style="width: 80px; height: 60px; object-fit: contain; border-radius: 6px; background: #f8fafc; border: 1px solid #eee;">` : `<div style="width: 80px; height: 60px; background: #f1f5f9; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 20px;">💊</div>`}
                        <div style="flex: 1;">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div style="font-weight: 700; color: #1e293b; font-size: 14px;">${pillName}</div>
                                <div style="background: #94a3b8; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700;">${confidencePercent}% 일치</div>
                            </div>
                            <div style="font-size: 11px; color: #64748b; margin-top: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${pillInfo}</div>
                            <button class="btn-toggle-sync" data-id="${cid}" data-name="${pillName}" data-info="${pillInfo}">
                                ➕ 복용 정보 등록
                            </button>
                        </div>
                    </div>
                </div>`;
        }).join('') : '<div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 13px;">일치하는 약품 정보를 찾을 수 없습니다.</div>';

        resultContainer.innerHTML = `
            <div style="background: #f8fafc; border-radius: 12px; padding: 15px; border: 1px solid #e2e8f0;">
                <div style="margin-bottom: 12px; padding: 10px; background: white; border-radius: 10px; border-left: 4px solid #7c3aed; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                    <div style="font-size: 11px; color: #94a3b8; margin-bottom: 2px;">🤖 분석된 검색 조건</div>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">각인: ${appearance.marking || '-'} | 색상: ${appearance.color || '-'} | 모양: ${appearance.shape || '-'} | 제형: ${appearance.formulation || '-'}</div>
                </div>
                <div style="font-size: 14px; font-weight: 700; color: #1e293b; margin-bottom: 10px; display: flex; align-items: center;"><span>🔍</span> 검색 결과 후보</div>
                <div class="pill-candidates-list" style="max-height: 400px; overflow-y: auto; padding-right: 5px;">${candidatesHtml}</div>
            </div>`;

        resultContainer.querySelectorAll('.btn-toggle-sync').forEach(btn => {
            btn.onclick = async () => {
                const id = btn.dataset.id;
                const name = btn.dataset.name;
                const info = btn.dataset.info;

                try {
                    const response = await fetchWithAuth('/api/v1/ocr/pill/toggle-sync', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: new URLSearchParams({ recognition_id: id, pill_name: name, pill_description: info })
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
                } catch (e) { console.error('Pill Sync Toggle Error:', e); }
            };
        });
    }
});
