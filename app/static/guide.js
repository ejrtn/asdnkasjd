document.addEventListener('DOMContentLoaded', () => {
    initGuide();
});

let currentStatus = { diseases: [], allergies: [], meds: [], profile: null, bp_records: [], bs_records: [] };
let guideData = null;
let guideCreatedAt = null;
let isSpeaking2 = false;
const synthesis2 = window.speechSynthesis;

async function initGuide() {
    // 1. 프로필 정보와 가이드 정보를 병렬로 가져옴
    Promise.all([
        fetchHealthProfile(),
        generateNewGuide()
    ]);
    setupGuideEventListeners();
}

async function fetchHealthProfile() {
    const token = localStorage.getItem("access_token");
    if (!token) {
        showLoginRequired();
        return;
    }

    try {
        const healthRes = await fetchWithAuth(`/api/v1/health`, { method: 'GET' });

        if (!healthRes || !healthRes.ok) throw new Error("Fetch failed");
        const health = await healthRes.json();

        currentStatus.diseases = health.chronic_diseases || [];
        currentStatus.allergies = health.allergies || [];
        currentStatus.meds = health.current_meds || [];
        currentStatus.profile = health.health_profile || null;
        currentStatus.bp_records = health.blood_pressure_records || [];
        currentStatus.bs_records = health.blood_sugar_records || [];

        renderHealthProfile();
    } catch (err) {
        console.error("Profile Load Error:", err);
        currentStatus.diseases = [];
        currentStatus.allergies = [];
        currentStatus.meds = [];
        currentStatus.profile = null;
        renderHealthProfile();
    }
}

function showLoginRequired() {
    const container = document.getElementById('guide-container');
    container.innerHTML = `
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; padding:40px 20px;">
            <div style="font-size:64px; margin-bottom:24px;">🔐</div>
            <h3 style="font-size:20px; color:#333; margin-bottom:12px; font-weight:bold;">로그인이 필요합니다</h3>
            <p style="color:#999; font-size:14px; margin-bottom:32px; text-align:center;">상단 우측의 사람 아이콘을 클릭하여 로그인하세요.</p>
            <a href="/" style="display:inline-block; padding:12px 32px; background:#4f46e5; color:white; text-decoration:none; border-radius:8px; font-weight:bold; font-size:14px;">로그인 하기</a>
        </div>
    `;
}

async function generateNewGuide(isPolling = false) {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const loadingState = document.getElementById('guide-loading-state');
    const content = document.getElementById('guide-sections');
    const loadingNote = document.getElementById('guide-loading-note');

    // 처음 로드할 때만 로딩 상태 표시
    if (!isPolling) {
        if (loadingState) loadingState.classList.remove('hidden');
        if (content) {
            content.classList.add('hidden');
            content.style.display = 'none';
        }
    }

    try {
        const res = await fetchWithAuth('/api/v1/guides', { method: 'GET' });
        if (!res || !res.ok) throw new Error("Guide request failed");

        const data = await res.json();

        // activity가 true이면 생성 중인 상태
        if (data.activity === true) {
            console.log("Currently generating... checking again in 3s.");
            if (loadingNote) {
                loadingNote.innerHTML = `
                    <span>⏳</span>
                    <span>AI가 건강 정보를 분석하여 맞춤 가이드를 생성 중입니다...</span>
                `;
            }
            // 가이드 생성 중이면 3초 뒤에 다시 체크 (isPolling = true)
            setTimeout(() => generateNewGuide(true), 3000);
            return;
        }

        if (data.generated_content) {
            guideData = data.generated_content;
            guideCreatedAt = data.created_at || null;
            renderGuide();
            renderGuideTimestamp();

            if (loadingState) loadingState.classList.add('hidden');
            if (content) {
                content.classList.remove('hidden');
                content.style.display = 'flex';
            }
        }
    } catch (err) {
        console.error("Guide Gen Error:", err);
        // 에러 발생 시 처음 로드 상태면 재시도
        if (!isPolling) {
            setTimeout(() => generateNewGuide(false), 5000);
        }
    }
}

function renderGuideTimestamp() {
    const el = document.getElementById('guide-updated-at');
    if (!el) return;
    if (!guideCreatedAt) {
        el.innerText = '';
        return;
    }
    try {
        const d = new Date(guideCreatedAt);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hour = String(d.getHours()).padStart(2, '0');
        const min = String(d.getMinutes()).padStart(2, '0');
        el.innerHTML = `
        <span style="display:block;margin-left:45px;">
        <span class="guide-updated-at-dot"></span> 최근 건강 정보 반영 &nbsp; ${year}.${month}.${day} ${hour}:${min}
        </span>
        `;
    } catch (e) {
        el.innerText = '';
    }
}

function renderHealthProfile() {
    const diseaseList = document.getElementById('chronic-disease-list');
    diseaseList.innerHTML =
        currentStatus.diseases.length > 0
            ? currentStatus.diseases.map(d => `<li class="c9-chip c9-chip-blue">${d.disease_name}</li>`).join('')
            : '<li class="c9-muted">등록된 질환이 없습니다.</li>';

    const allergyList = document.getElementById('allergy-list');
    allergyList.innerHTML =
        currentStatus.allergies.length > 0
            ? currentStatus.allergies.map(a => `<li class="c9-chip c9-chip-amber">${a.allergy_name}</li>`).join('')
            : '<li class="c9-muted">등록된 알레르기가 없습니다.</li>';

    const bpText = document.getElementById('recent-bp-text');
    const bsText = document.getElementById('recent-bs-text');

    if (currentStatus.bp_records.length > 0) {
        const latestBP = currentStatus.bp_records[0];
        bpText.innerHTML = `
            <span style="font-size:11px;font-weight:600;color:#6366f1;background:#eef2ff;border-radius:6px;padding:1px 6px;margin-left:4px;">
                ${latestBP.measure_type || ''}
            </span><br>
            ${latestBP.systolic}/${latestBP.diastolic}mmHg
        `;
    } else {
        bpText.innerText = '기록 없음';
    }

    if (currentStatus.bs_records.length > 0) {
        const latestBS = currentStatus.bs_records[0];
        bsText.innerHTML = `
            <span style="font-size:11px;font-weight:600;color:#6366f1;background:#eef2ff;border-radius:6px;padding:1px 6px;margin-left:4px;">
                ${latestBS.measure_type || ''}
            </span><br>
            ${latestBS.glucose_mg_dl}mg/dL
        `;
    } else {
        bsText.innerText = '기록 없음';
    }

    const medList = document.getElementById('medication-list');
    medList.innerHTML =
        currentStatus.meds.length > 0
            ? currentStatus.meds.map(m => `
                <div class="guide-med-item">
                    <span class="guide-med-name">${m.medication_name}</span>
                    <span class="guide-med-date">${m.start_date || '기록없음'}</span>
                </div>
            `).join('')
            : '<p class="c9-muted text-center py-2">등록된 약물이 없습니다.</p>';

    const prof = currentStatus.profile;
    if (prof) {
        document.getElementById('height-weight-text').innerText =
            (prof.height_cm && prof.weight_kg) ? `${prof.height_cm}cm / ${prof.weight_kg}kg` : '-';

        const bmiText = document.getElementById('bmi-text');
        if (prof.height_cm && prof.weight_kg) {
            const bmi = (prof.weight_kg / ((prof.height_cm / 100) ** 2)).toFixed(1);
            let status = '';
            if (bmi < 18.5) status = '(저체중)';
            else if (bmi < 23) status = '(정상)';
            else if (bmi < 25) status = '(과체중)';
            else status = '(비만)';
            bmiText.innerHTML = `${bmi} <span class="text-[10px] font-normal">${status}</span>`;
        } else {
            bmiText.innerText = '-';
        }

        document.getElementById('sleep-text').innerText =
            prof.sleep_hours ? `${prof.sleep_hours}시간/일 (${prof.sleep_change || '변화없음'})` : '-';

        document.getElementById('smoking-text').innerText = prof.smoking_status || '-';
        document.getElementById('drinking-text').innerText = prof.drinking_status || '-';
        document.getElementById('exercise-text').innerText = prof.exercise_frequency || '-';
        document.getElementById('diet-text').innerText = prof.diet_type || '-';
    }
}

function renderGuide() {

    if (!guideData) return;

    // --- Section 1: 복약 안전성 ---
    const s1 = guideData.section1;
    const section1 = document.getElementById('section-1');
    const statusTag = document.getElementById('safety-status-tag');
    const safetyContent = document.getElementById('safety-content');
    const safetyCautions = document.getElementById('general-cautions-list');

    statusTag.innerText = s1.status;
    section1.className = 'guide-section-card line-blue'; // Fixed color

    if (s1.status.includes('위험')) {
        statusTag.className = 'c9-badge c9-badge-danger';
    } else if (s1.status.includes('주의')) {
        statusTag.className = 'c9-badge c9-badge-warn';
    } else {
        statusTag.className = 'c9-badge c9-badge-success';
    }

    // 약물이 없을 때의 문구 처리 (LLM이 준 content를 우선하되, 비어있으면 기본 문구)
    safetyContent.innerHTML = (currentStatus.meds.length === 0 && (!s1.content || s1.content.length < 5))
        ? `<div>현재 복용 중인 약물이 없어 상호작용 위험이 없습니다.</div><div class="mt-1">건강한 상태를 잘 유지하고 계시네요!</div>`
        : s1.content.replace(/\n/g, '<br>');

    const safetyNotesBox = document.getElementById('safety-notes-box');
    const cautionsArray = s1.general_cautions || [];
    // 일반 주의사항은 LLM 데이터 기준으로 표시 (프로필 로딩 race condition 방지)
    // status가 '상호작용 없음'이거나 약물이 없을 때만 상태 뱃지와 노트박스를 숨김
    const hasNoMeds = s1.status && s1.status.includes('상호작용 없음') && cautionsArray.length === 0;
    if (hasNoMeds) {
        statusTag.classList.add('hidden');
        if (safetyNotesBox) safetyNotesBox.classList.add('hidden');
    } else {
        statusTag.classList.remove('hidden');
        if (safetyNotesBox) safetyNotesBox.classList.remove('hidden');
        safetyCautions.innerHTML = cautionsArray.length > 0
            ? cautionsArray.map(c => `<li>${c}</li>`).join('')
            : '<li>특별한 주의사항이 없습니다.</li>';
    }

    // --- Section 2: 질환 기반 생활습관 가이드 ---
    const s2 = guideData.section2;
    const diseaseGuidesContent = document.getElementById('disease-guides-content');
    const integratedPoint = document.getElementById('integrated-point');
    const integratedBox = document.querySelector('#section-2 .guide-integrated-box');
    const diseaseReferenceFooter = document.getElementById('disease-reference-footer');

    if (s2.disease_guides && s2.disease_guides.length > 0) {
        integratedBox.classList.remove('hidden');
        if (diseaseReferenceFooter) diseaseReferenceFooter.classList.remove('hidden');
        diseaseGuidesContent.innerHTML = `
            <div class="guide-disease-grid">
                ${s2.disease_guides.map(dg => `
                    <div class="guide-disease-card">
                        <div class="guide-disease-title">
                            <span>${dg.name}</span>
                            <span class="c9-badge c9-badge-primary">CARE</span>
                        </div>
                        <div class="guide-disease-list">
                            ${dg.tips.map(tip => `
                                <div class="guide-disease-item">
                                    <span class="guide-disease-dot">•</span>
                                    <span>${tip}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        integratedPoint.innerText = s2.integrated_point || "";
    } else {
        integratedBox.classList.add('hidden');
        if (diseaseReferenceFooter) diseaseReferenceFooter.classList.add('hidden');
        diseaseGuidesContent.innerHTML = `
            <div>등록된 질환이 없어 별도의 생활습관 가이드가 필요하지 않습니다.</div>
            <div class="mt-1">아주 건강하시네요!</div>
        `;
    }


    // --- Section 3: 건강 관리 수칙 ---
    const s3 = guideData.section3;
    const section3Title = document.querySelector('#section-3 .guide-plan-title');
    const checklistContainer = document.getElementById('checklist-container');

    section3Title.innerText = "③ 오늘의 건강 관리 수칙";

    // 4대 필수 카테고리 기본 가이드 (백엔드 보정이 놓친 경우 프론트에서 최후 방어)
    const REQUIRED_CATEGORIES = [
        { name: '운동', tip: '주 3회, 30분 이상 가벼운 걷기 등 자신에게 맞는 운동을 꾸준히 실천해 보세요.' },
        { name: '식단', tip: '규칙적인 식사와 균형 잡힌 영양 섭취가 면역력 유지에 도움이 됩니다.' },
        { name: '수면', tip: '하루 7~8시간의 충분한 수면으로 몸의 피로를 풀어주세요.' },
        { name: '흡연/음주', tip: '금연과 절주는 모든 대사 질환 예방의 첫걸음입니다.' }
    ];

    // health_guides를 우선 사용, 없으면 checklist 팁들을 공통 hints로 변환
    let healthGuides = s3.health_guides || [];
    if (healthGuides.length === 0 && s3.checklist && s3.checklist.length > 0) {
        // 체크리스트 형식 → 4대 카테고리로 분배 (항목을 나눠서 할당)
        const tips = s3.checklist;
        const chunkSize = Math.ceil(tips.length / 4);
        healthGuides = REQUIRED_CATEGORIES.map((cat, i) => ({
            name: cat.name,
            tips: tips.slice(i * chunkSize, (i + 1) * chunkSize).length > 0
                ? tips.slice(i * chunkSize, (i + 1) * chunkSize)
                : [cat.tip]
        }));
    }

    // 4대 카테고리 누락 보정 (프론트 최후 방어선)
    if (healthGuides.length > 0) {
        const existingNames = new Set(healthGuides.map(hg => hg.name));
        for (const cat of REQUIRED_CATEGORIES) {
            if (!existingNames.has(cat.name)) {
                healthGuides.push({ name: cat.name, tips: [cat.tip] });
            }
        }
    } else {
        // 완전히 빈 경우 기본값으로 채우기
        healthGuides = REQUIRED_CATEGORIES.map(cat => ({ name: cat.name, tips: [cat.tip] }));
    }

    if (healthGuides.length > 0) {
        checklistContainer.innerHTML = healthGuides.map(hg => `
            <div class="guide-disease-card">
                <div class="guide-disease-title">
                    <span>${hg.name}</span>
                    <span class="c9-badge c9-badge-primary">HEALTH</span>
                </div>
                <div class="guide-disease-list">
                    ${(hg.tips || []).map(tip => `
                        <div class="guide-disease-item">
                            <span class="guide-disease-dot">•</span>
                            <span>${tip}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    } else {
        checklistContainer.innerHTML = `
            <div class="guide-section-body text-gray-600" style="grid-column: span 2;">
                수집된 건강 데이터를 바탕으로 생성된 맞춤 수칙이 없습니다.
            </div>
        `;
    }

    // Disclaimer
    const disclaimerText = document.getElementById('disclaimer-text');
    if (disclaimerText && guideData.disclaimer) {
        disclaimerText.innerText = guideData.disclaimer;
    }
}


function toggleAccordion(id) {
    document.getElementById(id).classList.toggle('accordion-active');
}

function switchGuideMode(mode, buttonEl) {
    const tabs = document.querySelectorAll('.guide-mode-tab');
    const panels = document.querySelectorAll('.guide-mode-panel');

    tabs.forEach(tab => tab.classList.remove('is-active'));
    panels.forEach(panel => panel.classList.remove('active'));

    if (buttonEl) {
        buttonEl.classList.add('is-active');
    }

    const target = document.getElementById(`guide-mode-${mode}`);
    if (target) {
        target.classList.add('active');
    }
}

function setupGuideEventListeners() {
    const ttsBtn = document.getElementById('tts-btn');

    if (ttsBtn) {
        ttsBtn.addEventListener('click', toggleTTS);
    }

    // 전역 완료 이벤트 리스너 추가 (common.js에서 발생)
    window.addEventListener('guide-generation-completed', () => {
        console.log("🔔 가이드 생성 완료 이벤트 수신 - 데이터를 갱신합니다.");
        generateNewGuide();
    });
}

function toggleTTS() {
    if (!guideData) return;

    const btnText = document.getElementById('tts-text');
    const btnIcon = document.getElementById('tts-icon');

    if (isSpeaking2) {
        synthesis2.cancel();
        isSpeaking2 = false;
        btnText.innerText = '가이드 읽어주기';
        btnIcon.innerText = '📢';
        return;
    }

    const s1 = guideData.section1;
    const s2 = guideData.section2;
    const s3 = guideData.section3;

    const diseaseText = (s2.disease_guides || [])
        .map(d => `${d.name} 관리 방법입니다. ${(d.tips || []).join(', ')}`)
        .join('. ');

    let healthGuidesText = "";
    if (s3.health_guides && s3.health_guides.length > 0) {
        healthGuidesText = s3.health_guides.map(h => `${h.name} 관리법입니다. ${(h.tips || []).join(', ')}`).join('. ');
    } else if (s3.checklist && s3.checklist.length > 0) {
        healthGuidesText = s3.checklist.join(', ');
    }

    const fullText = `
        현재 등록된 질환, 복용 중인 약, 생활습관 등 건강 정보를 바탕으로 맞춤 생활 가이드를 안내드립니다.

        먼저 질환 기반 생활습관 가이드입니다.
        ${diseaseText || "등록된 질환이 없습니다."}

        다음은 복약 안전성 안내입니다.
        현재 상태는 ${s1.status || "정보 없음"} 입니다. ${s1.content || ""}.

        오늘의 건강 관리 수칙입니다.
        ${healthGuidesText || "특별한 수칙이 없습니다."}
    `;

    const utterance = new SpeechSynthesisUtterance(fullText);
    utterance.lang = 'ko-KR';

    utterance.onstart = () => {
        isSpeaking2 = true;
        btnText.innerText = '읽기 중지';
        btnIcon.innerText = '⏹';
    };

    utterance.onend = () => {
        isSpeaking2 = false;
        btnText.innerText = '가이드 읽어주기';
        btnIcon.innerText = '📢';
    };

    synthesis2.speak(utterance);
}