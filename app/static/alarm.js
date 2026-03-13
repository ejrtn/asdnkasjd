let currentMeds = [];
let alarms = [];
let selectedMedId = null;
let healthAlarms = {};
let alarmHistories = [];
let masterAlarmEnabled = true;

function getMasterDisabledAttr() {
    return !masterAlarmEnabled ? 'disabled' : '';
}

function getMasterBlockedClass() {
    return !masterAlarmEnabled ? 'is-master-disabled' : '';
}

function getToggleAlarmClick(alarmId, isActive) {
    return masterAlarmEnabled ? `onclick="toggleAlarm(${alarmId}, ${isActive})"` : '';
}

function getDeleteAlarmClick(alarmId) {
    return masterAlarmEnabled ? `onclick="deleteAlarm(${alarmId})"` : '';
}

function getAddAlarmClick(medId) {
    return masterAlarmEnabled ? `onclick="addAlarmTime(${medId})"` : '';
}

function getToggleMedClick(medId, isActive) {
    return masterAlarmEnabled
        ? `onclick="event.stopPropagation(); toggleMedAlarms(${medId}, ${isActive})"`
        : '';
}

async function refreshAlarmPageState() {
    await loadMasterAlarmState();
    await Promise.all([loadAlarms(), loadHealthAlarms()]);
    applyHealthAlarmState();
    renderMeds();
}

async function loadMasterAlarmState() {
    try {
        const response = await fetchWithAuth('/api/v1/users/me');
        if (response && response.ok) {
            const user = await response.json();
            masterAlarmEnabled = user.alarm_tf !== false;
        } else {
            masterAlarmEnabled = true;
        }
    } catch (error) {
        console.error('Error loading master alarm state:', error);
        masterAlarmEnabled = true;
    }
}

function checkLoginStatus() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.__BLOCK_ALARM_LOAD__ = true;

        const loginMsg = `
          <div style="text-align: center; padding: 40px 20px; color:#6b7280;">
            <div style="font-size: 48px; margin-bottom: 16px;">🔐</div>
            <h3 style="font-size: 18px; color: #1f2937; margin-bottom: 8px;">로그인이 필요합니다</h3>
            <p style="color: #6b7280; font-size: 14px; margin-bottom: 20px; line-height: 1.6;">알람 설정을 저장하려면 먼저 로그인해주세요.</p>
            <a href="/" class="c9-btn c9-btn-primary" style="display: inline-flex;">로그인 하기</a>
          </div>
        `;

        document.getElementById('tab-med').innerHTML = `<section class="c9-soft-card alarm-card">${loginMsg}</section>`;
        document.getElementById('tab-bp').innerHTML = `<div class="health-layout"><section class="c9-soft-card health-card">${loginMsg}</section></div>`;
        document.getElementById('tab-bs').innerHTML = `<div class="health-layout"><section class="c9-soft-card health-card">${loginMsg}</section></div>`;

        const historyPanel = document.getElementById('alarm-mode-history');
        if (historyPanel) {
            historyPanel.innerHTML = `<section class="c9-soft-card history-card">${loginMsg}</section>`;
        }

        return false;
    }
    return true;
}

function switchTab(tab, el) {
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
    document.querySelectorAll('.alarm-tab').forEach(btn => btn.classList.remove('is-active'));
    document.getElementById('tab-' + tab).classList.add('active');
    if (el) el.classList.add('is-active');
}

function switchAlarmMode(mode, el) {
    document.querySelectorAll('.alarm-mode-panel').forEach(panel => panel.classList.remove('active'));
    document.querySelectorAll('.alarm-mode-tab').forEach(btn => btn.classList.remove('is-active'));

    const target = document.getElementById(`alarm-mode-${mode}`);
    if (target) target.classList.add('active');
    if (el) el.classList.add('is-active');

    if (mode === 'history') {
        loadAlarmHistories();
    }
}

window.addEventListener('DOMContentLoaded', async () => {
    if (!checkLoginStatus()) return;

    await loadMeds();
    await refreshAlarmPageState();
});

// 기록확인 탭 자동 갱신 이벤트 리스너
window.addEventListener('alarm-history-updated', async () => {
    const historyPanel = document.getElementById('alarm-mode-history');
    if (historyPanel && historyPanel.classList.contains('active')) {
        await loadAlarmHistories();
    }
});

// 기록확인 탭 주기적 갱신
setInterval(() => {
    const historyPanel = document.getElementById('alarm-mode-history');
    if (historyPanel && historyPanel.classList.contains('active')) {
        loadAlarmHistories();
    }
}, 30000);

window.addEventListener('pageshow', async () => {
    if (!checkLoginStatus()) return;
    await refreshAlarmPageState();
});

document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState !== 'visible') return;
    if (!checkLoginStatus()) return;
    await refreshAlarmPageState();
});

async function loadHealthAlarms() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    healthAlarms = {};

    const types = ['BP_MORNING', 'BP_EVENING', 'BS_FASTING', 'BS_POSTMEAL', 'BS_BEDTIME'];

    const results = await Promise.all(
        types.map(type =>
            fetchWithAuth(`/api/v1/alarms?alarm_type=${type}`)
                .then(r => r && r.ok ? r.json() : [])
                .then(data => ({ type, data }))
                .catch(() => ({ type, data: [] }))
        )
    );

    results.forEach(({ type, data }) => {
        if (data.length > 0) healthAlarms[type] = data[0];
    });
}

function lockHealthControls() {
    const selectors = [
        '#bp-morning-time', '#bp-evening-time',
        '#bs-fasting-time', '#bs-postmeal-time', '#bs-bedtime-time',
        '#bp-morning-toggle', '#bp-evening-toggle',
        '#bs-fasting-toggle', '#bs-postmeal-toggle', '#bs-bedtime-toggle',
        '#save-bp-alarms-btn', '#save-bs-alarms-btn'
    ];

    selectors.forEach((selector) => {
        const el = document.querySelector(selector);
        if (!el) return;

        if (!masterAlarmEnabled) {
            el.setAttribute('disabled', 'disabled');
            el.classList.add('is-master-disabled');
        } else {
            el.removeAttribute('disabled');
            el.classList.remove('is-master-disabled');
        }
    });

    document.querySelectorAll('.alarm-slot').forEach((slot) => {
        if (!masterAlarmEnabled) slot.classList.add('is-disabled');
        else slot.classList.remove('is-disabled');
    });
}

function applyHealthAlarmState() {
    const map = {
        'BP_MORNING': 'bp-morning',
        'BP_EVENING': 'bp-evening',
        'BS_FASTING': 'bs-fasting',
        'BS_POSTMEAL': 'bs-postmeal',
        'BS_BEDTIME': 'bs-bedtime'
    };

    for (const [type, prefix] of Object.entries(map)) {
        const alarm = healthAlarms[type];
        const timeEl = document.getElementById(prefix + '-time');
        const toggleEl = document.getElementById(prefix + '-toggle');

        if (!timeEl || !toggleEl) continue;

        toggleEl.classList.remove('active');
        toggleEl.disabled = !masterAlarmEnabled;
        timeEl.disabled = !masterAlarmEnabled;

        if (alarm) {
            timeEl.value = alarm.alarm_time;
            const finalActive = masterAlarmEnabled && alarm.is_active;
            if (finalActive) {
                toggleEl.classList.add('active');
            }
        }
    }

    const bpSaveBtn = document.getElementById('save-bp-alarms-btn');
    const bsSaveBtn = document.getElementById('save-bs-alarms-btn');

    if (bpSaveBtn) bpSaveBtn.disabled = !masterAlarmEnabled;
    if (bsSaveBtn) bsSaveBtn.disabled = !masterAlarmEnabled;

    lockHealthControls();
}

async function loadMeds() {
    if (window.__BLOCK_ALARM_LOAD__) return;
    try {
        const response = await fetchWithAuth('/api/v1/current-meds');
        if (!response) return;
        if (response.ok) {
            currentMeds = await response.json();
        } else {
            document.getElementById('med-list').innerHTML =
                '<p style="text-align: center; color: #6b7280;">로그인이 필요합니다</p>';
        }
    } catch (error) {
        console.error('Error loading meds:', error);
    }
}

async function loadAlarms() {
    try {
        const response = await fetchWithAuth('/api/v1/alarms');
        if (!response) return;
        if (response.ok) alarms = await response.json();
    } catch (error) {
        console.error('Error loading alarms:', error);
    }
}

function renderMeds() {
    const medList = document.getElementById('med-list');
    if (!medList) return;

    if (!Array.isArray(currentMeds) || currentMeds.length === 0) {
        medList.innerHTML = '<p style="text-align: center; color: #6b7280;">등록된 약물이 없습니다.</p>';
        const detail = document.getElementById('alarm-detail');
        const title = document.getElementById('detail-title');
        if (title) title.innerHTML = `
          <span class="c9-section-title-icon med-tone-icon">🕰️</span>
          약물을 선택하세요
        `;
        if (detail) {
          detail.innerHTML = '<div class="alarm-detail-empty">등록된 약물이 없습니다.</div>';
        }
        return;
    }

    medList.innerHTML = currentMeds.map(med => {
        const medAlarms = alarms.filter(a => a.current_med_id === med.id);
        const hasActiveAlarm = medAlarms.some(a => a.is_active);
        const finalActive = masterAlarmEnabled && hasActiveAlarm;

        return `
            <div class="med-item ${selectedMedId === med.id ? 'selected' : ''}" onclick="showMedDetail(${med.id})">
                <div class="med-item-main">
                    <div class="med-name">${med.medication_name}</div>
                    <div class="med-meta">알람 ${medAlarms.length}개</div>
                </div>
                <button type="button"
                        class="toggle-switch ${finalActive ? 'active' : ''} ${getMasterBlockedClass()}"
                        ${getToggleMedClick(med.id, !finalActive)}
                        aria-label="${med.medication_name} 알람 전체 켜기 끄기"
                        ${getMasterDisabledAttr()}>
                </button>
            </div>
        `;
    }).join('');

    const targetMedId =
        selectedMedId && currentMeds.some(m => m.id === selectedMedId)
            ? selectedMedId
            : currentMeds[0].id;

    showMedDetail(targetMedId);
}

function showMedDetail(medId) {
    selectedMedId = medId;
    const med = currentMeds.find(m => m.id === medId);
    if (!med) return;

    const medAlarms = alarms.filter(a => a.current_med_id === medId);

    const detailTitle = document.getElementById('detail-title');
    if (detailTitle) {
        detailTitle.innerHTML = `
          <span class="c9-section-title-icon med-tone-icon">🕰️</span>
          ${med.medication_name} 알람 설정
        `;
    }

    const detailHtml = `
        <div class="alarm-time-list">
            ${medAlarms.length === 0
                ? `<div class="alarm-detail-empty" style="min-height: 160px;">등록된 알람이 없습니다.</div>`
                : medAlarms.map(alarm => `
                    <div class="alarm-time-item ${!masterAlarmEnabled ? 'is-disabled' : ''}">
                        <div class="alarm-time-left">
                            <span>🕔</span>
                            <span>${alarm.alarm_time}</span>
                        </div>
                        <div class="alarm-time-right ${!masterAlarmEnabled ? 'is-master-disabled' : ''}">
                            <button type="button"
                                    class="toggle-switch ${(masterAlarmEnabled && alarm.is_active) ? 'active' : ''} ${getMasterBlockedClass()}"
                                    ${getToggleAlarmClick(alarm.id, !(masterAlarmEnabled && alarm.is_active))}
                                    aria-label="알람 켜기 끄기"
                                    ${getMasterDisabledAttr()}>
                            </button>
                            <button
                                type="button"
                                class="btn-delete ${getMasterBlockedClass()}"
                                ${getDeleteAlarmClick(alarm.id)}
                                aria-label="알람 삭제"
                                ${getMasterDisabledAttr()}>
                                ✖
                            </button>
                        </div>
                    </div>
                `).join('')
            }
        </div>

        <div class="alarm-add-box ${!masterAlarmEnabled ? 'is-disabled is-master-disabled' : ''}">
            <div class="alarm-add-title">새 알람 추가</div>
            <input type="time" id="newAlarmTime" value="09:00" ${getMasterDisabledAttr()}>
            <button
                type="button"
                class="btn-add-time ${getMasterBlockedClass()}"
                ${getAddAlarmClick(medId)}
                ${getMasterDisabledAttr()}>
                복약 알람 추가
            </button>
        </div>
    `;

    document.getElementById('alarm-detail').innerHTML = detailHtml;
}

async function toggleMedAlarms(medId, isActive) {
    if (!masterAlarmEnabled) {
        showAppToast('마이페이지에서 전체 알람이 OFF 상태입니다.', 'warn', '복약 알람');
        return;
    }

    const medAlarms = alarms.filter(a => a.current_med_id === medId);

    if (medAlarms.length === 0) {
        showAppToast('설정된 알람이 없습니다.', 'warn', '복약 알람');
        return;
    }

    for (const alarm of medAlarms) {
        try {
            await fetchWithAuth(`/api/v1/alarms/${alarm.id}/toggle`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: isActive })
            });
        } catch (error) {
            console.error('Error toggling alarm:', error);
        }
    }

    await loadAlarms();
    renderMeds();
    showAppToast(`${currentMeds.find(m => m.id === medId)?.medication_name || '약물'} 알람이 ${isActive ? '켜졌' : '꺼졌'}습니다.`, 'success', '복약 알람');
}

async function toggleAlarm(alarmId, isActive, reload = true) {
    if (!masterAlarmEnabled) {
        showAppToast('마이페이지에서 전체 알람이 OFF 상태입니다.', 'warn', '복약 알람');
        return;
    }

    const response = await fetchWithAuth(`/api/v1/alarms/${alarmId}/toggle`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: isActive })
    });

    if (!response) return;

    if (response.ok) {
        await loadAlarms();
        if (reload && selectedMedId) showMedDetail(selectedMedId);
        renderMeds();
    } else {
        console.error('Toggle failed:', response.status);
    }
}

async function deleteAlarm(alarmId) {
    if (!masterAlarmEnabled) {
        showAppToast('마이페이지에서 전체 알람이 OFF 상태입니다.', 'warn', '복약 알람');
        return;
    }

    if (!confirm('정말 삭제하시겠습니까?')) return;

    const response = await fetchWithAuth(`/api/v1/alarms/${alarmId}`, { method: 'DELETE' });
    if (!response) return;

    if (response.ok) {
        await loadAlarms();
        if (selectedMedId) showMedDetail(selectedMedId);
        renderMeds();
        showAppToast('복약 알람이 삭제되었어요.', 'success', '복약 알람');
    } else {
        showAppToast('복약 알람을 삭제할 수 없습니다.', 'warn', '복약 알람');
    }
}

async function toggleHealthAlarm(type, prefix) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        showAppToast('로그인이 필요합니다.', 'warn', '알람');
        return;
    }

    if (!masterAlarmEnabled) {
        showAppToast('마이페이지에서 전체 알람이 OFF 상태입니다.', 'warn', '알람');
        return;
    }

    const el = document.getElementById(prefix + '-toggle');
    const isActive = !el.classList.contains('active');

    if (healthAlarms[type]) {
        const alarmId = healthAlarms[type].id;
        const r = await fetchWithAuth(`/api/v1/alarms/${alarmId}/toggle`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: isActive })
        });

        if (r && r.ok) { 
            healthAlarms[type] = await r.json(); 
            applyHealthAlarmState(); 
        }
    } else {
        const time = document.getElementById(prefix + '-time').value;
        const r = await fetchWithAuth('/api/v1/alarms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ alarm_type: type, alarm_time: time })
        });

        if (r && r.ok) { 
            healthAlarms[type] = await r.json(); 
            applyHealthAlarmState(); 
        }
    }
}

async function saveHealthAlarms(prefixMap, successMessage, titleText) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        showAppToast('로그인이 필요합니다.', 'warn', titleText);
        return;
    }

    if (!masterAlarmEnabled) {
        showAppToast('마이페이지에서 전체 알람이 OFF 상태입니다.', 'warn', titleText);
        return;
    }

    for (const [type, prefix] of Object.entries(prefixMap)) {
        const time = document.getElementById(prefix + '-time').value;
        const isActive = document.getElementById(prefix + '-toggle').classList.contains('active');
        if (healthAlarms[type]) {
            await fetchWithAuth(`/api/v1/alarms/${healthAlarms[type].id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ alarm_time: time, is_active: isActive })
            });
        } else {
            const r = await fetchWithAuth('/api/v1/alarms', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ alarm_type: type, alarm_time: time })
            });
            if (r && r.ok) healthAlarms[type] = await r.json();
        }
    }
    showAppToast(successMessage, 'success', titleText);
}

function toggleBpAlarm(slot) {
    if (!masterAlarmEnabled) {
        applyHealthAlarmState();
        showAppToast('마이페이지에서 전체 알람이 OFF 상태입니다.', 'warn', '혈압 알람');
        return;
    }
    toggleHealthAlarm('BP_' + slot.toUpperCase(), 'bp-' + slot);
}

function toggleBsAlarm(slot) {
    if (!masterAlarmEnabled) {
        applyHealthAlarmState();
        showAppToast('마이페이지에서 전체 알람이 OFF 상태입니다.', 'warn', '혈당 알람');
        return;
    }

    const map = { fasting: 'BS_FASTING', postmeal: 'BS_POSTMEAL', bedtime: 'BS_BEDTIME' };
    toggleHealthAlarm(map[slot], 'bs-' + slot);
}

function saveBpAlarms() {
    if (!masterAlarmEnabled) {
        applyHealthAlarmState();
        showAppToast('마이페이지에서 전체 알람이 OFF 상태입니다.', 'warn', '혈압 알람');
        return;
    }

    saveHealthAlarms(
        { BP_MORNING: 'bp-morning', BP_EVENING: 'bp-evening' },
        '혈압 알람이 저장되었어요.',
        '혈압 알람'
    );
}

function saveBsAlarms() {
    if (!masterAlarmEnabled) {
        applyHealthAlarmState();
        showAppToast('마이페이지에서 전체 알람이 OFF 상태입니다.', 'warn', '혈당 알람');
        return;
    }

    saveHealthAlarms(
        { BS_FASTING: 'bs-fasting', BS_POSTMEAL: 'bs-postmeal', BS_BEDTIME: 'bs-bedtime' },
        '혈당 알람이 저장되었어요.',
        '혈당 알람'
    );
}

async function addAlarmTime(medId) {
    if (!masterAlarmEnabled) {
        showAppToast('마이페이지에서 전체 알람이 OFF 상태입니다.', 'warn', '복약 알람');
        return;
    }

    const time = document.getElementById('newAlarmTime').value;
    if (!time) {
        showAppToast('시간을 선택해주세요.', 'warn', '복약 알람');
        return;
    }

    const response = await fetchWithAuth('/api/v1/alarms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_med_id: medId, alarm_time: time })
    });

    if (!response) return;

    if (response.ok) {
        await loadAlarms();
        showMedDetail(medId);
        renderMeds();
        showAppToast('복약 알람이 추가되었어요.', 'success', '복약 알람');
    } else {
        showAppToast('복약 알람을 추가할 수 없습니다.', 'warn', '복약 알람');
    }
}

async function loadAlarmHistories() {
    const listEl = document.getElementById('alarm-history-list');
    if (!listEl) return;

    listEl.innerHTML = `<div class="history-empty">알람 기록을 불러오는 중입니다.</div>`;

    try {
        const response = await fetchWithAuth('/api/v1/alarms/history?limit=15');
        if (!response) return;

        if (response.ok) {
            alarmHistories = await response.json();
            renderAlarmHistories();
        } else {
            listEl.innerHTML = `<div class="history-empty">알람 기록을 불러올 수 없습니다.</div>`;
        }
    } catch (error) {
        console.error('Error loading alarm histories:', error);
        listEl.innerHTML = `<div class="history-empty">알람 기록을 불러오는 중 문제가 발생했습니다.</div>`;
    }
}

function formatHistorySentAt(isoString) {
    if (!isoString) return '-';

    try {
        const date = new Date(isoString);

        if (Number.isNaN(date.getTime())) {
            return isoString;
        }

        const formatter = new Intl.DateTimeFormat('ko-KR', {
            timeZone: 'Asia/Seoul',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });

        const parts = formatter.formatToParts(date);

        const year = parts.find(p => p.type === 'year')?.value ?? '';
        const month = parts.find(p => p.type === 'month')?.value ?? '';
        const day = parts.find(p => p.type === 'day')?.value ?? '';
        const hour = parts.find(p => p.type === 'hour')?.value ?? '';
        const minute = parts.find(p => p.type === 'minute')?.value ?? '';
        const dayPeriodRaw = parts.find(p => p.type === 'dayPeriod')?.value ?? '';

        let dayPeriod = dayPeriodRaw;
        if (dayPeriodRaw.includes('AM') || dayPeriodRaw.includes('am')) {
            dayPeriod = '오전';
        } else if (dayPeriodRaw.includes('PM') || dayPeriodRaw.includes('pm')) {
            dayPeriod = '오후';
        }

        return `${year}.${month}.${day} ${dayPeriod} ${hour}:${minute}`;
    } catch (error) {
        console.error('Time parsing error:', error);
        return isoString;
    }
}

function renderAlarmHistories() {
    const listEl = document.getElementById('alarm-history-list');
    if (!listEl) return;

    if (!Array.isArray(alarmHistories) || alarmHistories.length === 0) {
        listEl.innerHTML = `<div class="history-empty">아직 기록된 알람 내역이 없습니다.</div>`;
        return;
    }

    listEl.innerHTML = alarmHistories.map(item => `
        <div class="history-item">
            <div class="history-item-left">
                <div class="history-item-title-row">
                    <div class="history-item-title">${item.title}</div>
                    <span class="history-status ${item.is_confirmed ? 'done' : 'pending'}">
                        ${item.is_confirmed ? '확인 완료' : '미확인'}
                    </span>
                </div>

                <div class="history-item-body">${item.body}</div>

                <div class="history-item-meta">
                    <span>🕒 ${formatHistorySentAt(item.sent_at)}</span>
                    <span>•</span>
                    <span>${item.alarm_type}</span>
                </div>
            </div>

            <div class="history-item-right">
                <button
                    type="button"
                    class="history-confirm-btn"
                    onclick="confirmAlarmHistory(${item.history_id})"
                    ${item.is_confirmed ? 'disabled' : ''}>
                    ${item.is_confirmed ? '확인됨' : '확인'}
                </button>
            </div>
        </div>
    `).join('');
}

async function confirmAlarmHistory(historyId) {
    const response = await fetchWithAuth(`/api/v1/alarms/history/${historyId}`, {
        method: 'PATCH'
    });

    if (!response) return;

    if (response.ok) {
        alarmHistories = alarmHistories.map(item =>
            item.history_id === historyId
                ? { ...item, is_confirmed: true }
                : item
        );

        renderAlarmHistories();
        showAppToast('알람 기록을 확인 처리했어요.', 'success', '기록 확인');
    } else {
        showAppToast('알람 기록을 확인 처리할 수 없습니다.', 'warn', '기록 확인');
    }
}