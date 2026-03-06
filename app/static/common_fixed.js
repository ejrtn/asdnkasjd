// 로그인 후 대시보드로 리다이렉트
function redirectToDashboardAfterLogin() {
    const token = localStorage.getItem('access_token');
    if (token && window.location.pathname === '/login') {
        window.location.href = '/dashboard';
    }
}

window.addEventListener('load', redirectToDashboardAfterLogin);

// =====================
// FCM 초기화 및 토큰 등록
// =====================
const VAPID_PUBLIC_KEY = 'BMqfMeyCFrPheF9o7AUnY0hsPZBixyc5tSYo9upqJ_EsWRoHm73-z-N30eXgGc3xO6P8wiqfJfRdPjulDrQrCe0';

async function initFCM() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        console.log('🔐 FCM: 로그인 토큰이 없어서 FCM 초기화를 건너뜁니다');
        return;
    }

    try {
        console.log('🚀 FCM: 초기화 시작');
        
        // Service Worker 등록
        const swReg = await navigator.serviceWorker.register('/static/firebase-messaging-sw.js');
        console.log('✅ FCM: Service Worker 등록 완료');

        // Firebase 초기화
        const { initializeApp } = await import('https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js');
        const { getMessaging, getToken, onMessage } = await import('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging.js');

        const app = initializeApp({
            apiKey: "AIzaSyACrdE8rQvj7i1l8Lnl32xTqY-GVGw556Q",
            authDomain: "cloud9-care.firebaseapp.com",
            projectId: "cloud9-care",
            storageBucket: "cloud9-care.firebasestorage.app",
            messagingSenderId: "879037848068",
            appId: "1:879037848068:web:cc2a4b44d3432c8e7db351",
        });
        console.log('✅ FCM: Firebase 앱 초기화 완료');

        const messaging = getMessaging(app);

        // 알림 권한 요청 및 FCM 토큰 발급
        const permission = await Notification.requestPermission();
        console.log(`🔔 FCM: 알림 권한 상태 - ${permission}`);
        if (permission !== 'granted') {
            console.warn('⚠️ FCM: 알림 권한이 거부되어 FCM을 사용할 수 없습니다');
            return;
        }

        const fcmToken = await getToken(messaging, { vapidKey: VAPID_PUBLIC_KEY, serviceWorkerRegistration: swReg });
        console.log('🎫 FCM: 토큰 발급 완료', fcmToken.substring(0, 20) + '...');

        // 서버에 FCM 토큰 저장
        await fetch('/api/v1/users/me/fcm-token', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ fcm_token: fcmToken }),
        });
        console.log('💾 FCM: 서버에 토큰 저장 완료');

        // 앱이 열려있을 때 인앱 팝업 처리
        onMessage(messaging, (payload) => {
            console.log('📱 FCM: 메시지 수신!', payload);
            showAlarmPopup(
                payload.notification.title, 
                payload.notification.body, 
                payload.data?.alarm_id || null,
                payload.data?.history_id || null
            );
        });
        console.log('👂 FCM: 메시지 리스너 등록 완료');

    } catch (e) {
        console.error('❌ FCM 초기화 실패:', e);
    }
}

// =====================
// 인앱 알람 팝업
// =====================
function showAlarmPopup(title, body, alarmId, historyId = null) {
    console.log('🎉 알람 팝업 표시:', { title, body, alarmId, historyId });

    // 기존 팝업 제거
    document.getElementById('alarm-popup')?.remove();

    const popup = document.createElement('div');
    popup.id = 'alarm-popup';
    popup.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        background: white;
        border-radius: 16px;
        padding: 20px 24px;
        box-shadow: 0 12px 28px rgba(0,0,0,0.16);
        min-width: 320px;
        max-width: 380px;
        border-left: 4px solid #4f46e5;
        animation: slideIn 0.3s ease;
    `;

    popup.innerHTML = `
        <style>
            @keyframes slideIn {
                from { transform: translateX(120%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        </style>
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
            <div style="
                width:36px; height:36px; border-radius:12px;
                display:grid; place-items:center;
                background:#eef2ff; color:#4f46e5; font-size:18px;
                border:1px solid #c7d2fe;
            ">🔔</div>
            <div style="font-weight:800; font-size:15px; color:#111827;">${title}</div>
        </div>

        <div style="color:#475569; font-size:13px; line-height:1.6; margin-bottom:16px;">
            ${body}
        </div>

        <div style="display:flex; gap:8px;">
            <button onclick="confirmAlarm('${alarmId}', '${historyId || ''}')" style="
                flex:1;
                padding:10px 12px;
                background:#4f46e5;
                color:white;
                border:none;
                border-radius:10px;
                cursor:pointer;
                font-weight:700;
            ">
                ✅ 확인
            </button>

            <button onclick='snoozeAlarm(${JSON.stringify(title)}, ${JSON.stringify(body)}, ${JSON.stringify(alarmId)}, ${JSON.stringify(historyId || "")})' style="
                flex:1;
                padding:10px 12px;
                background:#f3f4f6;
                color:#374151;
                border:none;
                border-radius:10px;
                cursor:pointer;
                font-weight:700;
            ">
                나중에
            </button>
        </div>
    `;

    document.body.appendChild(popup);
    console.log('✅ 알람 팝업이 화면에 추가되었습니다');
}

function snoozeAlarm(title, body, alarmId, historyId = null) {
    document.getElementById('alarm-popup')?.remove();

    const snoozeKey = historyId || alarmId;
    if (!snoozeKey) return;

    // 이미 예약된 동일 알람 있으면 제거 후 다시 예약
    if (snoozedAlarmTimers.has(snoozeKey)) {
        clearTimeout(snoozedAlarmTimers.get(snoozeKey));
    }

    showAppToast('10분 뒤에 한 번 더 알려드릴게요.', 'info', '알람 미루기');

    const timerId = setTimeout(() => {
        showAlarmPopup(title, body, alarmId, historyId);
        snoozedAlarmTimers.delete(snoozeKey);
    }, 10 * 60 * 1000); // 10분

    snoozedAlarmTimers.set(snoozeKey, timerId);
}

async function confirmAlarm(alarmId, historyId = null) {
    document.getElementById('alarm-popup')?.remove();

    const snoozeKey = historyId || alarmId;
    if (snoozeKey && snoozedAlarmTimers.has(snoozeKey)) {
        clearTimeout(snoozedAlarmTimers.get(snoozeKey));
        snoozedAlarmTimers.delete(snoozeKey);
    }

    if (!alarmId) return;
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const url = historyId
        ? `/api/v1/alarms/history/${historyId}`
        : `/api/v1/alarms/history/confirm/${alarmId}`;

    try {
        await fetch(url, {
            method: historyId ? 'PATCH' : 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
        });
    } catch (error) {
        console.error('알람 확인 처리 실패:', error);
    }
}

// 브라우저 알림 + FCM 초기화 (로그인 상태일 때만)
if ('serviceWorker' in navigator && 'Notification' in window) {
    window.addEventListener('load', initFCM);
}

// =====================
// 공통 앱 토스트
// =====================
let __appToastTimer = null;

function showAppToast(message, type = 'success', title = '안내') {
    const toast = document.getElementById('app-toast');
    const badge = document.getElementById('app-toast-badge');
    const titleEl = document.getElementById('app-toast-title');
    const messageEl = document.getElementById('app-toast-message');

    if (!toast || !badge || !titleEl || !messageEl) return;

    const config = {
        success: { icon: '✅', title: title || '저장 완료' },
        info: { icon: '🔔', title: title || '안내' },
        alarm: { icon: '⏰', title: title || '알람 시간입니다' },
        warn: { icon: '⚠️', title: title || '확인 필요' }
    };

    const current = config[type] || config.info;

    badge.textContent = current.icon;
    titleEl.textContent = current.title;
    messageEl.textContent = message;

    toast.classList.remove('hide');
    toast.classList.add('show');

    if (__appToastTimer) clearTimeout(__appToastTimer);
    __appToastTimer = setTimeout(() => {
        toast.classList.remove('show');
        toast.classList.add('hide');
    }, 2400);
}

document.getElementById('app-toast-close')?.addEventListener('click', () => {
    const toast = document.getElementById('app-toast');
    if (!toast) return;
    toast.classList.remove('show');
    toast.classList.add('hide');
});

// =====================
// 웹 폴링 백업 (FCM 누락 대비)
// =====================
const shownAlarmHistoryIds = new Set();
const snoozedAlarmTimers = new Map();

async function pollDueAlarms() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
        const response = await fetch('/api/v1/alarms/due', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) return;

        const items = await response.json();
        if (!Array.isArray(items) || items.length === 0) return;

        items.forEach(item => {
            if (shownAlarmHistoryIds.has(item.history_id)) return;
            shownAlarmHistoryIds.add(item.history_id);

            showAlarmPopup(item.title, item.body, item.alarm_id, item.history_id);
        });
    } catch (error) {
        console.error('❌ due alarm polling 실패:', error);
    }
}

window.addEventListener('load', () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    pollDueAlarms();
    setInterval(pollDueAlarms, 30000);
});