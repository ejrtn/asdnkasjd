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
async function redirectToDashboardAfterLogin() {
    const token = localStorage.getItem('access_token');
    if (!token || window.location.pathname !== '/login') return;

    try {
        const res = await fetch('/api/v1/users/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            window.location.href = '/dashboard';
        } else {
            localStorage.removeItem('access_token');
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_id');
        }
    } catch {
        // 네트워크 오류 시 무시
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
    if (dropdown && dropdown.classList.contains('show')) {
        dropdown.classList.remove('show');
    }
});

// =====================
// 알람 오디오 및 진동 셋업
// =====================
let __alarmAudio = null;
let __alarmAudioUnlocked = false;

function ensureAlarmAudio() {
    if (!__alarmAudio) {
        __alarmAudio = new Audio('/static/sounds/alarm.mp3?v=2');
        __alarmAudio.preload = 'auto';
        __alarmAudio.volume = 1.0;

        __alarmAudio.addEventListener('canplaythrough', () => {
            console.log('🔊 alarm audio loaded');
        });

        __alarmAudio.addEventListener('error', (e) => {
            console.error('❌ alarm audio load failed:', e, __alarmAudio.currentSrc);
        });
    }
    return __alarmAudio;
}

async function unlockAlarmAudioOnce() {
    if (__alarmAudioUnlocked) return;

    try {
        const audio = ensureAlarmAudio();

        audio.muted = true;
        const p = audio.play();
        if (p && typeof p.then === 'function') {
            await p;
        }

        audio.pause();
        audio.currentTime = 0;
        audio.muted = false;

        __alarmAudioUnlocked = true;
        console.log('🔓 alarm audio unlocked');
    } catch (e) {
        console.warn('🔇 alarm audio unlock failed:', e);
    }
}

async function playAlarmSound() {
    try {
        const audio = ensureAlarmAudio();

        // 이전 재생 흔적 정리
        audio.pause();
        audio.currentTime = 0;

        const playPromise = audio.play();
        if (playPromise && typeof playPromise.then === 'function') {
            await playPromise;
        }
    } catch (e) {
        console.warn('🔇 알림음 재생 실패:', e);
    }
}

function vibrateAlarm() {
    try {
        if ('vibrate' in navigator) {
            navigator.vibrate([250, 120, 250, 120, 400]);
        }
    } catch (e) {
        console.warn('📳 진동 실패:', e);
    }
}

// 사용자 상호작용 때 오디오 언락 준비
window.addEventListener('pointerdown', unlockAlarmAudioOnce, { once: true });
window.addEventListener('keydown', unlockAlarmAudioOnce, { once: true });
window.addEventListener('touchstart', unlockAlarmAudioOnce, { once: true });
window.addEventListener('click', unlockAlarmAudioOnce, { once: true });


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

        const swReg = await navigator.serviceWorker.register('/static/firebase_messaging.js');
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

        const fcmToken = await getToken(messaging, { vapidKey: VAPID_PUBLIC_KEY, serviceWorkerRegistration: swReg });
        console.log('🎫 FCM: 토큰 발급 완료', fcmToken.substring(0, 20) + '...');

        await fetchWithAuth('/api/v1/users/me/fcm-token', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fcm_token: fcmToken }),
        });
        console.log('💾 FCM: 서버에 토큰 저장 완료');

        onMessage(messaging, (payload) => {
            console.log('📱 FCM: 메시지 수신!', payload);

            showAlarmPopup(
                payload.notification.title,
                payload.notification.body,
                payload.data?.alarm_id || null,
                payload.data?.history_id || null,
                payload.data?.snooze_count || 0
            );

            if (Notification.permission === 'granted') {
                new Notification(payload.notification.title, {
                    body: payload.notification.body,
                    icon: '/static/img/pill_front.png',
                    badge: '/static/img/pill_front.png',
                    vibrate: [250, 120, 250, 120, 400],
                    tag: payload.data?.history_id ? `alarm-history-${payload.data.history_id}` : `alarm-${Date.now()}`,
                });
            }
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
let __activePopupHistoryId = null;
let __activePopupHandled = false;
const shownAlarmHistoryIds = new Set();

function showAlarmPopup(title, body, alarmId, historyId = null, snoozeCount = 0) {
    console.log('🎉 알람 팝업 표시:', { title, body, alarmId, historyId, snoozeCount, audioUnlocked: __alarmAudioUnlocked });

    playAlarmSound();
    vibrateAlarm();

    document.getElementById('alarm-popup')?.remove();

    if (__alarmPopupTimer) {
        clearTimeout(__alarmPopupTimer);
        __alarmPopupTimer = null;
    }

    __activePopupHistoryId = historyId ? Number(historyId) : null;
    __activePopupHandled = false;

    const disableSnooze = Number(snoozeCount || 0) >= 1;

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

            <button
                onclick='snoozeAlarm(${JSON.stringify(title)}, ${JSON.stringify(body)}, ${JSON.stringify(alarmId)}, ${JSON.stringify(historyId || "")})'
                ${disableSnooze ? 'disabled' : ''}
                style="
                    flex:1;
                    padding:10px 12px;
                    background:${disableSnooze ? '#e5e7eb' : '#f3f4f6'};
                    color:${disableSnooze ? '#9ca3af' : '#374151'};
                    border:none;
                    border-radius:10px;
                    cursor:${disableSnooze ? 'not-allowed' : 'pointer'};
                    font-weight:700;
                "
            >
                나중에
            </button>
        </div>
    `;

    document.body.appendChild(popup);
    console.log('✅ 알람 팝업이 화면에 추가되었습니다');

    __alarmPopupTimer = setTimeout(async () => {
        document.getElementById('alarm-popup')?.remove();

        if (__activePopupHandled) return;

        // 아무 버튼도 안 눌렀을 때도 10분 뒤 한 번만 다시 알림
        if (historyId && Number(snoozeCount || 0) < 1) {
            try {
                await requestSnooze(historyId, true);
            } catch (error) {
                console.error('자동 재알림 예약 실패:', error);
            }
        }
    }, 60000);
}

async function requestSnooze(historyId, silent = false) {
    const response = await fetchWithAuth(`/api/v1/alarms/history/${historyId}/snooze`, {
        method: 'PATCH'
    });

    if (!response) {
        throw new Error('no response');
    }

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`snooze failed: ${response.status} ${errorText}`);
    }

    shownAlarmHistoryIds.delete(Number(historyId));
    window.dispatchEvent(new CustomEvent('alarm-history-updated'));

    if (!silent) {
        showAppToast('10분 뒤에 다시 알려드릴게요.', 'info', '알람 미루기');
    }
}

async function snoozeAlarm(title, body, alarmId, historyId = null) {
    document.getElementById('alarm-popup')?.remove();

    if (__alarmPopupTimer) {
        clearTimeout(__alarmPopupTimer);
        __alarmPopupTimer = null;
    }

    __activePopupHandled = true;

    if (!historyId) {
        showAppToast('이 알람은 아직 미루기를 지원하지 않습니다.', 'warn', '알람 미루기');
        return;
    }

    try {
        await requestSnooze(historyId, false);
    } catch (error) {
        console.error('알람 미루기 실패:', error);
        showAppToast('알람 미루기에 실패했습니다.', 'warn', '알람 미루기');
    }
}

async function confirmAlarm(alarmId, historyId = null) {
    document.getElementById('alarm-popup')?.remove();

    if (__alarmPopupTimer) {
        clearTimeout(__alarmPopupTimer);
        __alarmPopupTimer = null;
    }

    __activePopupHandled = true;

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

// 알람 폴링 관리 전역 변수 및 함수
let __dueAlarmPollTimer = null;
let __dueAlarmPollStarter = null;

function startDueAlarmPolling() {
    if (__dueAlarmPollTimer) {
        clearInterval(__dueAlarmPollTimer);
        __dueAlarmPollTimer = null;
    }

    if (__dueAlarmPollStarter) {
        clearTimeout(__dueAlarmPollStarter);
        __dueAlarmPollStarter = null;
    }

    pollDueAlarms();

    const now = new Date();
    const msUntilNext10Sec = 10000 - ((now.getSeconds() % 10) * 1000 + now.getMilliseconds());

    __dueAlarmPollStarter = setTimeout(() => {
        pollDueAlarms();
        __dueAlarmPollTimer = setInterval(pollDueAlarms, 10000);
    }, msUntilNext10Sec);
}

// 브라우저 알림 + FCM 초기화 (하단 onload 이벤트에서 통합 호출됨)

let __healthProfilePollInterval = null;

function stopHealthProfilePolling() {
    if (__healthProfilePollInterval) {
        clearInterval(__healthProfilePollInterval);
        __healthProfilePollInterval = null;
    }
}

// 모든 페이지 공통: 가이드 생성 상태 폴링 및 알림
async function checkGlobalGuideStatus() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
        const res = await fetchWithAuth('/api/v1/guides', { method: 'GET' });
        if (!res || !res.ok) return;

        const data = await res.json();

        // 생성 중인 경우 폴링 시작 (이미 시작되어 있으면 중복 방지)
        if (data.activity === true) {
            if (!__healthProfilePollInterval) {
                console.log("📡 AI 가이드 생성 중... 상태 모니터링을 시작합니다.");
                __healthProfilePollInterval = setInterval(checkGlobalGuideStatus, 5000);
            }
        }
        // 생성 완료된 경우
        else if (data.activity === false && __healthProfilePollInterval) {
            console.log("✅ AI 가이드 생성 완료!");
            stopHealthProfilePolling();
            showAppToast("맞춤 건강 가이드가 생성되었습니다! '건강 가이드' 메뉴에서 확인해 보세요.", "success", "가이드 생성 완료");

            // 가이드 페이지라면 페이지 데이터 갱신을 위해 이벤트 발생
            window.dispatchEvent(new CustomEvent('guide-generation-completed'));
        }
    } catch (e) {
        console.error("가이드 상태 체크 실패:", e);
        stopHealthProfilePolling();
    }
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
    }, 8000);
}

document.getElementById('app-toast-close')?.addEventListener('click', () => {
    const toast = document.getElementById('app-toast');
    if (!toast) return;
    toast.classList.remove('show');
    toast.classList.add('hide');
});

// =====================
// 웹 폴링 백업
// =====================
async function pollDueAlarms() {
    if (typeof __sessionExpiredMode !== 'undefined' && __sessionExpiredMode) return;
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

// 페이지 로드 시 상태 체크 및 초기화
window.addEventListener('load', () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    // 1. FCM 초기화
    if ('serviceWorker' in navigator && 'Notification' in window) {
        initFCM();
    }

    // 2. 가이드 생성 상태 체크 (생성 중이면 폴링 시작)
    checkGlobalGuideStatus();

    // 3. 알람 폴링 (FCM 백업)
    startDueAlarmPolling();
});
// =====================
// 화면 노출 시 오디오 리셋 (모바일 백그라운드 전환 등 방지 안정화)
// =====================
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        try {
            const audio = ensureAlarmAudio();
            audio.pause();
            audio.currentTime = 0;
        } catch (e) {
            console.warn('audio reset skipped:', e);
        }
    }
});
