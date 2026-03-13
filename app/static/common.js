// 쿠키에서 특정 이름의 값을 가져오는 헬퍼 함수
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// 쿠키에서 토큰을 읽어 localStorage에 저장하는 함수 (소셜 로그인용)
function syncTokensFromCookies() {
    const accessToken = getCookie('access_token');
    const userId = getCookie('user_id');

    if (accessToken) {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('auth_token', accessToken);
        document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:01 GMT; path=/;';
    }

    if (userId) {
        localStorage.setItem('user_id', userId);
        document.cookie = 'user_id=; expires=Thu, 01 Jan 1970 00:00:01 GMT; path=/;';
    }
}

// 스크립트 로드 시 즉시 동기화 실행
syncTokensFromCookies();

// 로그인 후 대시보드로 리다이렉트
function redirectToDashboardAfterLogin() {
    const token = localStorage.getItem('access_token');
    if (token && window.location.pathname === '/login') {
        window.location.href = '/dashboard';
    }
}

window.addEventListener('load', () => {
    syncTokensFromCookies();
    redirectToDashboardAfterLogin();
});

// 사용자 메뉴 드롭다운 토글
document.getElementById('user-menu-btn')?.addEventListener('click', function (e) {
    e.stopPropagation();
    document.getElementById('user-dropdown')?.classList.toggle('show');
});

document.addEventListener('click', function () {
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown?.classList.contains('show')) {
        dropdown.classList.remove('show');
    }
});

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

        const swReg = await navigator.serviceWorker.register('/static/firebase-messaging-sw.js');
        console.log('✅ FCM: Service Worker 등록 완료');

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

        const permission = await Notification.requestPermission();
        console.log(`🔔 FCM: 알림 권한 상태 - ${permission}`);
        if (permission !== 'granted') {
            console.warn('⚠️ FCM: 알림 권한이 거부되어 FCM을 사용할 수 없습니다');
            return;
        }

        const fcmToken = await getToken(messaging, {
            vapidKey: VAPID_PUBLIC_KEY,
            serviceWorkerRegistration: swReg
        });
        console.log('🎫 FCM: 토큰 발급 완료', fcmToken.substring(0, 20) + '...');

        const saveRes = await fetchWithAuth('/api/v1/users/me/fcm-token', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fcm_token: fcmToken }),
        });

        if (saveRes && saveRes.ok) {
            console.log('💾 FCM: 서버에 토큰 저장 완료');
        } else {
            console.warn('⚠️ FCM: 서버에 토큰 저장 실패');
        }

        onMessage(messaging, (payload) => {
            console.log('📱 FCM: 메시지 수신!', payload);
            showAlarmPopup(
                payload.notification?.title || '알람',
                payload.notification?.body || '알람 시간이 되었습니다.',
                payload.data?.alarm_id || null,
                payload.data?.history_id || null,
                Number(payload.data?.snooze_count || 0)
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
let __alarmPopupTimer = null;

function clearAlarmPopupTimer() {
    if (__alarmPopupTimer) {
        clearTimeout(__alarmPopupTimer);
        __alarmPopupTimer = null;
    }
}

function showAlarmPopup(title, body, alarmId, historyId = null, snoozeCount = 0) {
    console.log('🎉 알람 팝업 표시:', { title, body, alarmId, historyId, snoozeCount });

    document.getElementById('alarm-popup')?.remove();
    clearAlarmPopupTimer();

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

    const snoozeDisabled = Number(snoozeCount) >= 1;

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

            <button
                ${snoozeDisabled ? 'disabled' : `onclick='snoozeAlarm(${JSON.stringify(title)}, ${JSON.stringify(body)}, ${JSON.stringify(alarmId)}, ${JSON.stringify(historyId || "")})'`}
                style="
                    flex:1;
                    padding:10px 12px;
                    background:${snoozeDisabled ? '#e5e7eb' : '#f3f4f6'};
                    color:#374151;
                    border:none;
                    border-radius:10px;
                    cursor:${snoozeDisabled ? 'not-allowed' : 'pointer'};
                    font-weight:700;
                    opacity:${snoozeDisabled ? '0.6' : '1'};
                "
            >
                나중에
            </button>
        </div>
    `;

    document.body.appendChild(popup);

    __alarmPopupTimer = setTimeout(() => {
        document.getElementById('alarm-popup')?.remove();
        __alarmPopupTimer = null;
    }, 60000);

    console.log('✅ 알람 팝업이 화면에 추가되었습니다');
}

async function snoozeAlarm(title, body, alarmId, historyId = null) {
    document.getElementById('alarm-popup')?.remove();
    clearAlarmPopupTimer();

    if (!historyId) {
        showAppToast('이 알람은 아직 미루기를 지원하지 않습니다.', 'warn', '알람 미루기');
        return;
    }

    try {
        const response = await fetchWithAuth(`/api/v1/alarms/history/${historyId}/snooze`, {
            method: 'PATCH'
        });

        if (!response) return;

        if (!response.ok) {
            const errorText = await response.text();
            console.error('snooze failed:', response.status, errorText);
            throw new Error(`snooze failed: ${response.status} ${errorText}`);
        }

        shownAlarmHistoryIds.delete(Number(historyId));
        window.dispatchEvent(new CustomEvent('alarm-history-updated'));
        showAppToast('10분 뒤에 다시 알려드릴게요.', 'info', '알람 미루기');
    } catch (error) {
        console.error('알람 미루기 실패:', error);
        showAppToast('알람 미루기에 실패했습니다.', 'warn', '알람 미루기');
    }
}

async function confirmAlarm(alarmId, historyId = null) {
    document.getElementById('alarm-popup')?.remove();
    clearAlarmPopupTimer();

    if (!alarmId) return;

    try {
        let response = null;

        if (historyId) {
            response = await fetchWithAuth(`/api/v1/alarms/history/${historyId}`, {
                method: 'PATCH',
            });
        }

        if (!response || !response.ok) {
            response = await fetchWithAuth(`/api/v1/alarms/history/confirm/${alarmId}`, {
                method: 'POST',
            });
        }

        if (!response) return;

        if (!response.ok) {
            throw new Error(`confirm failed: ${response.status}`);
        }

        if (historyId) {
            shownAlarmHistoryIds.add(Number(historyId));
        }

        window.dispatchEvent(new CustomEvent('alarm-history-updated'));
        showAppToast('알람을 확인 처리했어요.', 'success', '알람 확인');
    } catch (error) {
        console.error('알람 확인 처리 실패:', error);
        showAppToast('알람 확인 처리에 실패했습니다.', 'warn', '알람 확인');
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

async function pollDueAlarms() {
    try {
        const response = await fetchWithAuth('/api/v1/alarms/due', {
            method: 'GET',
        });

        if (!response) return;
        if (!response.ok) return;

        const items = await response.json();
        if (!Array.isArray(items) || items.length === 0) return;

        items.forEach(item => {
            if (shownAlarmHistoryIds.has(item.history_id)) return;

            shownAlarmHistoryIds.add(item.history_id);
            showAlarmPopup(
                item.title,
                item.body,
                item.alarm_id,
                item.history_id,
                item.snooze_count || 0
            );
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