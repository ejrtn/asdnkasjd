/**
 * Upload History Logic
 */

let uploadHistoryData = [];
let currentHistoryFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
    fetchUploadHistory();

    const filterBtns = document.querySelectorAll('.history-filter-btn');
    if (filterBtns) {
        filterBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                filterBtns.forEach(b => b.classList.remove('is-active'));
                this.classList.add('is-active');
                currentHistoryFilter = this.getAttribute('data-filter');
                filterHistory();
            });
        });
    }

    const queryInput = document.getElementById('history-search');
    if (queryInput) {
        queryInput.addEventListener('input', () => filterHistory());
    }
});

async function fetchUploadHistory() {
    const container = document.getElementById('upload-history-list');
    if (!container) return;

    try {
        const response = await fetchWithAuth('/api/v1/uploads/history');
        if (response.ok) {
            const result = await response.json();
            uploadHistoryData = result.content || [];
            filterHistory();
        } else {
            container.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 20px 0;">데이터 로드 실패</div>`;
        }
    } catch (e) {
        console.error("히스토리 Fetch 중 에러: ", e);
        container.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 20px 0;">오류가 발생했습니다.</div>`;
    }
}

function filterHistory() {
    const container = document.getElementById('upload-history-list');
    if (!container) return;

    const queryInput = document.getElementById('history-search');
    const query = queryInput ? queryInput.value.toLowerCase() : '';

    let filtered = uploadHistoryData;

    if (currentHistoryFilter === 'prescription') {
        filtered = filtered.filter(item => item.type === '처방전');
    } else if (currentHistoryFilter === 'pill') {
        filtered = filtered.filter(item => item.type === '알약 분석');
    }

    if (query) {
        filtered = filtered.filter(item =>
            item.type.toLowerCase().includes(query) ||
            (item.date && item.date.toLowerCase().includes(query))
        );
    }

    renderTreeHistory(container, filtered);
}

function renderTreeHistory(container, historyList) {
    if (!historyList || historyList.length === 0) {
        container.innerHTML = `<div style="text-align: center; color: #94a3b8; padding: 60px 0;">검색 결과가 없거나 업로드한 기록이 없습니다.</div>`;
        return;
    }

    const groupedByDate = historyList.reduce((acc, item) => {
        const fullDate = item.date || '';
        const parts = fullDate.split(' ');
        const dateStr = parts[0] || '날짜 미상';
        const timeStr = parts[1] ? parts[1].substring(0, 5) : '--:--';
        const displayType = item.type === '처방전' ? '처방전' : '알약 분석';
        const icon = displayType === '처방전' ? '📄' : '💊';

        if (!acc[dateStr]) acc[dateStr] = [];
        acc[dateStr].push({ ...item, time: timeStr, displayType, icon });
        return acc;
    }, {});

    let html = '';
    const sortedDates = Object.keys(groupedByDate).sort((a, b) => b.localeCompare(a));

    sortedDates.forEach(date => {
        html += `<div class="tree-date-group"><div class="tree-date-header">${date}</div>`;
        const items = groupedByDate[date];
        items.forEach((item, index) => {
            const isLast = (index === items.length - 1);
            const branchSymbol = isLast ? '└' : '├';
            html += `
                <div class="tree-item" onclick="showHistoryAnalysis('${item.id}', this, '${item.displayType}')">
                    <span class="tree-branch">${branchSymbol}</span>
                    <span class="tree-time">${item.time}</span>
                    <span class="tree-icon">${item.icon}</span>
                    <span class="tree-title">${item.displayType} 상세보기</span>
                </div>`;
        });
        html += `</div>`;
    });
    container.innerHTML = html;
}

window.showHistoryAnalysis = async function(uploadId, element, type) {
    document.querySelectorAll('.tree-item').forEach(el => el.classList.remove('is-active'));
    element.classList.add('is-active');

    const detailContainer = document.getElementById('history-detail-content');
    if (!detailContainer) return;

    detailContainer.innerHTML = `<div style="text-align: center; color: #94a3b8; padding: 60px 0;">상세 분석 결과를 불러오는 중입니다...</div>`;

    try {
        const response = await fetchWithAuth(`/api/v1/uploads/${uploadId}/analysis`);
        if (response.ok) {
            const result = await response.json();
            const content = result.content;
            let analysisHtml = type === '처방전' ? generatePrescriptionDetailHtml(content) : generatePillDetailHtml(content);
            const reanalyzeBtnHtml = `<button class="btn-reanalyze" onclick="window.location.reload()"><span>🔄</span> 다시 업로드해서 분석하기</button>`;
            detailContainer.classList.remove('analysis-result-empty');
            detailContainer.innerHTML = analysisHtml + reanalyzeBtnHtml;
        } else {
            detailContainer.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 40px 0;">결과를 불러오지 못했습니다.</div>`;
        }
    } catch (error) {
        console.error("히스토리 상세 Fetch 에러:", error);
        detailContainer.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 40px 0;">오류가 발생했습니다.</div>`;
    }
};

function generatePrescriptionDetailHtml(data) {
    if (!data.candidates || data.candidates.length === 0) return `<div style="color: #64748b; padding: 20px 0;">분석된 처방전 데이터가 없습니다.</div>`;
    let html = '';
    if (data.hospital) {
        html += `
            <div class="hospital-group">
                <div style="margin-bottom: 12px; text-align: center;">
                    <img src="${data.file_path.replace("/app", "")}" style="width: 100%; max-width: 200px; height: auto; border-radius: 8px; border: 1px solid #eee;">
                </div>
                <div class="hospital-info-card">
                    <div style="color: #94a3b8; font-size: 11px; margin-bottom: 2px;">🏥 분석된 병원 정보</div>
                    <div style="font-weight: 700; font-size: 15px; color: #1e293b;">${data.hospital.hospital_name}</div>
                    <div style="font-size: 11px; color: #64748b; margin-top: 4px;">📅 처방일: ${data.hospital.prescription_date || '날짜 정보 없음'}</div>
                </div>
                <div class="drug-list-header"><span>💊</span> 처방 약물 목록</div>
                <div class="drug-list-scroll">`;
    }
    data.candidates.forEach(pill => {
        const name = pill.name || '';
        const dosage = pill.dosage || '';
        const frequency = pill.frequency || '';
        const duration = pill.duration || '';
        html += `
            <div class="pill-candidate-card prescription-drug-item">
                <div style="display: flex; gap: 12px;">
                    <div style="width: 80px; height: 60px; background: #f1f5f9; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 20px;">💊</div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="font-weight: 700; color: #1e293b; font-size: 14px;">${name}</div>
                            <div style="background: #eef2ff; color: #4f46e5; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700;">${dosage || '1정'}</div>
                        </div>
                        <div style="font-size: 11px; color: #64748b; margin-top: 4px;">${frequency ? frequency + '회' : '-'} / ${duration ? duration + '일분' : '-'}</div>
                    </div>
                </div>
            </div>`;
    });
    html += `</div></div>`;
    return html;
}

function generatePillDetailHtml(data) {
    const appearance = {
        'text': (data.ai_extracted.image1.text || '-') + " , " + (data.ai_extracted.image2.text || '-'),
        'color': data.ai_extracted.image1.color + " , " + data.ai_extracted.image2.color,
        'shape': data.ai_extracted.image1.shape,
        'formulation': data.ai_extracted.image1.formulation,
    };
    if (!data.candidates || data.candidates.length === 0) return `<div style="color: #64748b; padding: 20px 0;">분석된 처방전 데이터가 없습니다.</div>`;
    let html = `
        <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;">
            ${data.upload.map(u => `
                <img src="${u.file_path.replace("/app", "")}" 
                     style="width: 100px; height: 100px; object-fit: cover; border-radius: 8px; border: 1px solid #eee; cursor: zoom-in;" 
                     onclick="window.showZoomModal(this.src)">
            `).join('')}
        </div>
        <div style="background: #f8fafc; border-radius: 12px; padding: 15px; border: 1px solid #e2e8f0;">
            <div style="margin-bottom: 12px; padding: 10px; background: white; border-radius: 10px; border-left: 4px solid #7c3aed; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                <div style="font-size: 11px; color: #94a3b8; margin-bottom: 2px;">🤖 분석된 검색 조건</div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">각인: ${appearance.text || '-'} | 색상: ${appearance.color || '-'} | 모양: ${appearance.shape || '-'} | 제형: ${appearance.formulation || '-'}</div>
            </div>
            <div style="font-size: 14px; font-weight: 800; color: #475569; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">🔍 발견된 알약 후보군</div>`;
    data.candidates.forEach(pill => {
        const scoreColor = pill.score > 0.8 ? '#10b981' : (pill.score > 0.6 ? '#f59e0b' : '#ef4444');
        const scorePercent = Math.round(pill.score * 100);
        html += `
            <div class="pill-candidates-list" style="margin-bottom: 15px; padding: 16px; border: 1px solid #e2e8f0; border-radius: 12px; background: white;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div style="font-size: 15px; font-weight: 800; color: #1e293b;">${pill.name}</div>
                    <div style="background: ${scoreColor}15; color: ${scoreColor}; padding: 4px 10px; border-radius: 99px; font-size: 12px; font-weight: 700;">일치도 ${scorePercent}%</div>
                </div>
                <div style="flex: 1; font-size: 13px; color: #475569; line-height: 1.6; background: #f8fafc; padding: 10px; border-radius: 8px;">${pill.efcy_qesitm || '효능/효과 정보가 없습니다.'}</div>
            </div>`;
    });
    html += `</div>`;
    return html;
}

