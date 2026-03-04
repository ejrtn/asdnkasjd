let currentMeds = [];
let alarms = [];
let selectedMedId = null;

async function fetchWithAuth(url, options = {}) {
    let token = localStorage.getItem("access_token");
    if (!options.headers) options.headers = {};
    if (token) options.headers["Authorization"] = `Bearer ${token}`;

    let response = await fetch(url, options);

    if (response.status === 401) {
        const refresh = await fetch('/api/v1/users/token/refresh', { method: 'GET' });
        if (refresh.ok) {
            const result = await refresh.json();
            token = result.access_token;
            localStorage.setItem("access_token", token);
            options.headers["Authorization"] = `Bearer ${token}`;
            response = await fetch(url, options);
        } else {
            alert("세션이 만료되었습니다. 다시 로그인해주세요.");
            localStorage.removeItem("access_token");
            localStorage.removeItem("user_id");
            location.href = "/login";
            return null;
        }
    }
    return response;
}

window.onload = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
        document.getElementById('med-list').innerHTML =
            '<p style="text-align: center; color: #f59e0b;">로그인이 필요합니다. <a href="/login">로그인 하기</a></p>';
        return;
    }
    await Promise.all([loadMeds(), loadAlarms()]);
    renderMeds();
};

async function loadMeds() {
    try {
        const response = await fetchWithAuth('/api/v1/current-meds');
        if (!response) return;
        if (response.ok) {
            currentMeds = await response.json();
        } else {
            document.getElementById('med-list').innerHTML =
                '<p style="text-align: center; color: #f59e0b;">로그인이 필요합니다. <a href="/login">로그인 하기</a></p>';
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

    if (!Array.isArray(currentMeds) || currentMeds.length === 0) {
        medList.innerHTML = '<p style="text-align: center; color: #6b7280;">등록된 약물이 없습니다.</p>';
        return;
    }

    medList.innerHTML = currentMeds.map(med => {
        const medAlarms = alarms.filter(a => a.current_med_id === med.id);
        console.log(medAlarms);
        const hasActiveAlarm = medAlarms.some(a => a.is_active);

        return `
            <div class="med-item ${selectedMedId === med.id ? 'selected' : ''}" onclick="showMedDetail(${med.id})">
                <div>
                    <div style="font-weight: bold;">${med.medication_name}</div>
                    <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">
                        알람 ${medAlarms.length}개
                    </div>
                </div>
                <div class="toggle-switch ${hasActiveAlarm ? 'active' : ''}"
                     onclick="event.stopPropagation(); toggleMedAlarms(${med.id}, ${!hasActiveAlarm})">
                </div>
            </div>
        `;
    }).join('');
    showMedDetail(currentMeds[0].id)
}

function showMedDetail(medId) {
    selectedMedId = medId;
    const med = currentMeds.find(m => m.id === medId);
    if (!med) return;

    const medAlarms = alarms.filter(a => a.current_med_id === medId);

    document.getElementById('detail-title').textContent = med.medication_name + ' 알람 설정';

    const detailHtml = `
        <div style="padding: 10px;">
            ${medAlarms.length === 0 ?
                '<p style="text-align: center; color: #6b7280; padding: 20px;">등록된 알람이 없습니다.</p>' :
                medAlarms.map(alarm => `
                    <div class="alarm-time-item">
                        <div>
                            <div style="font-size: 18px; font-weight: bold;">🕔 ${alarm.alarm_time}</div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div class="toggle-switch ${alarm.is_active ? 'active' : ''}"
                                 onclick="toggleAlarm(${alarm.id}, ${!alarm.is_active})">
                            </div>
                            <button class="btn-delete" onclick="deleteAlarm(${alarm.id})">✖</button>
                        </div>
                    </div>
                `).join('')
            }
            <div style="margin-top: 20px; padding: 15px; background: #f9fafb; border-radius: 6px;">
                <label style="display: block; margin-bottom: 8px; font-weight: bold;">새 알람 추가</label>
                <input type="time" id="newAlarmTime" value="09:00"
                       style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 4px; margin-bottom: 10px;">
                <button class="btn-add-time" onclick="addAlarmTime(${medId})">+ 알람 추가</button>
            </div>
        </div>
    `;

    document.getElementById('alarm-detail').innerHTML = detailHtml;
}

async function toggleMedAlarms(medId, isActive) {
    const medAlarms = alarms.filter(a => a.current_med_id === medId);

    if (medAlarms.length === 0) {
        alert('설정된 알람이 없습니다.');
        return;
    }

    for (const alarm of medAlarms) {
        await toggleAlarm(alarm.id, isActive, false);
    }
    await loadAlarms();
    renderMeds();
    if (selectedMedId) showMedDetail(selectedMedId);
}

async function toggleAlarm(alarmId, isActive, reload = true) {
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
    if (!confirm('정말 삭제하시겠습니까?')) return;

    const response = await fetchWithAuth(`/api/v1/alarms/${alarmId}`, { method: 'DELETE' });
    if (!response) return;

    if (response.ok) {
        await loadAlarms();
        if (selectedMedId) showMedDetail(selectedMedId);
        renderMeds();
    } else {
        alert('알람을 삭제할 수 없습니다.');
    }
}

async function addAlarmTime(medId) {
    const time = document.getElementById('newAlarmTime').value;
    if (!time) { alert('시간을 선택해주세요.'); return; }

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
    } else {
        const error = await response.json();
        alert('알람을 추가할 수 없습니다: ' + (error.detail || ''));
    }
}
