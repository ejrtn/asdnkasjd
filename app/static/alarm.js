let currentMeds = [];
let alarms = [];
let selectedMedId = null;

window.onload = async () => {
    await loadMeds();
    await loadAlarms();
};

async function loadMeds() {
    const token = localStorage.getItem("access_token");
    console.log('Loading meds with token:', token);
    
    try {
        const response = await fetch('/api/v1/current-meds', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        console.log('Meds response status:', response.status);
        
        if (response.ok) {
            currentMeds = await response.json();
            console.log('Current meds loaded:', currentMeds);
            console.log('Is array?', Array.isArray(currentMeds));
            renderMeds();
        } else {
            const errorText = await response.text();
            console.error('Meds load failed:', response.status, errorText);
            document.getElementById('med-list').innerHTML = 
                '<p style="text-align: center; color: #f59e0b;">로그인이 필요합니다. <a href="/login">로그인 하기</a></p>';
        }
    } catch (error) {
        console.error('Error loading meds:', error);
        document.getElementById('med-list').innerHTML = 
            '<p style="text-align: center; color: #ef4444;">약물을 불러오는 중 오류가 발생했습니다.</p>';
    }
}

async function loadAlarms() {
    const token = localStorage.getItem("access_token");
    try {
        const response = await fetch('/api/v1/alarms', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            alarms = await response.json();
            if (selectedMedId) {
                showMedDetail(selectedMedId);
            }
        }
    } catch (error) {
        console.error('Error loading alarms:', error);
    }
}

function renderMeds() {
    const medList = document.getElementById('med-list');
    
    console.log('renderMeds called, currentMeds:', currentMeds);
    console.log('currentMeds type:', typeof currentMeds);
    console.log('Is array?', Array.isArray(currentMeds));
    
    if (!Array.isArray(currentMeds) || currentMeds.length === 0) {
        medList.innerHTML = '<p style="text-align: center; color: #6b7280;">등록된 약물이 없습니다.</p>';
        return;
    }

    medList.innerHTML = currentMeds.map(med => {
        const medAlarms = alarms.filter(a => a.current_med_id === med.id);
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
    renderMeds();
}

async function toggleMedAlarms(medId, isActive) {
    const medAlarms = alarms.filter(a => a.current_med_id === medId);
    
    for (const alarm of medAlarms) {
        await toggleAlarm(alarm.id, isActive, false);
    }
    
    await loadAlarms();
    renderMeds();
}

async function toggleAlarm(alarmId, isActive, reload = true) {
    const token = localStorage.getItem('access_token');
    console.log(`Toggling alarm ${alarmId} to ${isActive}`);
    
    try {
        const response = await fetch(`/api/v1/alarms/${alarmId}/toggle`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ is_active: isActive })
        });

        console.log('Toggle response:', response.status);
        
        if (response.ok) {
            await loadAlarms();
            if (reload && selectedMedId) {
                showMedDetail(selectedMedId);
            }
            renderMeds();
        } else {
            const error = await response.json();
            console.error('Toggle failed:', error);
            alert('알람 설정을 변경할 수 없습니다.');
        }
    } catch (error) {
        console.error('Toggle alarm error:', error);
        alert('오류가 발생했습니다.');
    }
}

async function deleteAlarm(alarmId) {
    if (!confirm('정말 삭제하시겠습니까?')) return;

    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch(`/api/v1/alarms/${alarmId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            await loadAlarms();
            if (selectedMedId) {
                showMedDetail(selectedMedId);
            }
            renderMeds();
        } else {
            alert('알람을 삭제할 수 없습니다.');
        }
    } catch (error) {
        console.error('Delete alarm error:', error);
        alert('오류가 발생했습니다.');
    }
}

async function addAlarmTime(medId) {
    const time = document.getElementById('newAlarmTime').value;
    if (!time) {
        alert('시간을 선택해주세요.');
        return;
    }

    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch('/api/v1/alarms', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                current_med_id: medId,
                alarm_time: time
            })
        });

        if (response.ok) {
            await loadAlarms();
            showMedDetail(medId);
            renderMeds();
        } else {
            const error = await response.json();
            alert('알람을 추가할 수 없습니다: ' + (error.detail || ''));
        }
    } catch (error) {
        console.error('Create alarm error:', error);
        alert('오류가 발생했습니다.');
    }
}
