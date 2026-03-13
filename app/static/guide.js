document.addEventListener('DOMContentLoaded', () => {
    initGuide();
});

let currentStatus = { diseases: [], allergies: [], meds: [], profile: null, bp_records: [], bs_records: [] };
let guideData = null;
let isSpeaking2 = false;
const synthesis2 = window.speechSynthesis;

async function initGuide() {
    await fetchHealthProfile();
    await generateNewGuide();
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

async function generateNewGuide() {
    const token = localStorage.getItem("access_token");
    if (!token) {
        showLoginRequired();
        return;
    }

    const loadingState = document.getElementById('guide-loading-state');
    const content = document.getElementById('guide-sections');
    const loadingNote = document.getElementById('guide-loading-note');

    if (loadingState) {
        loadingState.classList.remove('hidden');
    }

    if (content) {
        content.classList.add('hidden');
        content.style.display = 'none';
    }

    if (loadingNote) {
        loadingNote.innerHTML = `
            <span>⏳</span>
            <span>AI 맞춤 가이드를 새로 생성 중입니다. 잠시만 기다려주세요.</span>
        `;
    }

    try {
        const res = await fetchWithAuth('/api/v1/guides', {
            method: 'GET',
        });

        if (!res || !res.ok) {
            throw new Error("Guide request failed");
        }

        const data = await res.json();
        console.log("Guide API Data:", data);

        if (data.activity === true) {
            console.log("Currently generating... checking again in 5s.");
            setTimeout(initGuide, 5000);
            return;
        }

        if (data.generated_content) {
            guideData = data.generated_content;
            renderGuide();

            if (loadingState) {
                loadingState.classList.add('hidden');
            }

            if (content) {
                content.classList.remove('hidden');
                content.style.display = 'flex';
            }
        }
    } catch (err) {
        console.error("Guide Gen Error:", err);
        if (loadingNote) {
            loadingNote.innerHTML = `
                <span>⚠️</span>
                <span>가이드를 불러오는 중 문제가 발생했습니다. 잠시 후 자동으로 다시 시도합니다.</span>
            `;
        }
        setTimeout(initGuide, 5000);
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
        bpText.innerText = `${latestBP.systolic}/${latestBP.diastolic}`;
    } else {
        bpText.innerText = '기록 없음';
    }

    if (currentStatus.bs_records.length > 0) {
        const latestBS = currentStatus.bs_records[0];
        bsText.innerText = `${latestBS.glucose_mg_dl}mg/dL`;
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
    section1.className = 'guide-section-card line-blue'; // Default color

    if (s1.status.includes('위험')) {
        statusTag.className = 'c9-badge c9-badge-danger';
        section1.className = 'guide-section-card line-red';
    } else if (s1.status.includes('주의')) {
        statusTag.className = 'c9-badge c9-badge-warn';
        section1.className = 'guide-section-card line-amber';
    } else {
        statusTag.className = 'c9-badge c9-badge-success';
        section1.className = 'guide-section-card line-indigo';
    }

    // 약물이 없을 때의 문구 처리 (LLM이 준 content를 우선하되, 비어있으면 기본 문구)
    safetyContent.innerHTML = (currentStatus.meds.length === 0 && (!s1.content || s1.content.length < 5))
        ? `<div>현재 복용 중인 약물이 없어 상호작용 위험이 없습니다.</div><div class="mt-1">건강한 상태를 잘 유지하고 계시네요!</div>`
        : s1.content.replace(/\n/g, '<br>');

    const safetyNotesBox = document.getElementById('safety-notes-box');
    if (currentStatus.meds.length === 0) {
        statusTag.classList.add('hidden');
        if (safetyNotesBox) safetyNotesBox.classList.add('hidden');
    } else {
        statusTag.classList.remove('hidden');
        if (safetyNotesBox) safetyNotesBox.classList.remove('hidden');
        safetyCautions.innerHTML = s1.general_cautions.length > 0
            ? s1.general_cautions.map(c => `<li>${c}</li>`).join('')
            : '<li>특별한 주의사항이 없습니다.</li>';
    }

    // --- Section 1: 질환 기반 생활습관 가이드 ---
    const s2 = guideData.section2;
    const diseaseGuidesContent = document.getElementById('disease-guides-content');
    const integratedPoint = document.getElementById('integrated-point');
    const integratedBox = document.querySelector('#section-2 .guide-integrated-box');

    if (currentStatus.diseases.length > 0 && s2.disease_guides && s2.disease_guides.length > 0) {
        integratedBox.classList.remove('hidden');
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
        diseaseGuidesContent.innerHTML = `
            <div>등록된 질환이 없어 별도의 생활습관 가이드가 필요하지 않습니다.</div>
            <div class="mt-1">아주 건강하시네요!</div>
        `;
    }

    // --- Section 3: 건강 관리 수칙 ---
    const s3 = guideData.section3;
    const section3Title = document.querySelector('#section-3 .guide-plan-title');
    const checklistContainer = document.getElementById('checklist-container');

    section3Title.innerText = "3) 오늘의 건강 관리 수칙";

    // Support both new 'health_guides' and old 'checklist' format
    let healthGuides = s3.health_guides || [];
    if (healthGuides.length === 0 && s3.checklist && s3.checklist.length > 0) {
        healthGuides = [{
            name: "공통 관리 수칙",
            tips: s3.checklist
        }];
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