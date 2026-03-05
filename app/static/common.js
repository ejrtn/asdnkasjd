// 로그인 후 대시보드로 리다이렉트
function redirectToDashboardAfterLogin() {
    const token = localStorage.getItem('access_token');
    if (token && window.location.pathname === '/login') {
        window.location.href = '/dashboard';
    }
}

window.addEventListener('load', redirectToDashboardAfterLogin);

// 사용자 메뉴 드롭다운 토글
document.getElementById('user-menu-btn').addEventListener('click', function(e) {
    e.stopPropagation();
    document.getElementById('user-dropdown').classList.toggle('show');
});

document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown.classList.contains('show')) {
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
            showAlarmPopup(payload.notification.title, payload.notification.body, payload.data?.alarm_id);
        });
        console.log('👂 FCM: 메시지 리스너 등록 완료');

    } catch (e) {
        console.error('❌ FCM 초기화 실패:', e);
    }
}

// =====================
// 인앱 알람 팝업
// =====================
function showAlarmPopup(title, body, alarmId) {
    console.log('🎉 알람 팝업 표시:', { title, body, alarmId });
    
    // 기존 팝업 제거
    document.getElementById('alarm-popup')?.remove();

    const popup = document.createElement('div');
    popup.id = 'alarm-popup';
    popup.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 9999;
        background: white; border-radius: 12px; padding: 20px 24px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.15); min-width: 300px;
        border-left: 4px solid #4f46e5; animation: slideIn 0.3s ease;
    `;
    popup.innerHTML = `
        <style>
            @keyframes slideIn { from { transform: translateX(120%); } to { transform: translateX(0); } }
        </style>
        <div style="font-weight:bold; font-size:15px; margin-bottom:6px;">🔔 ${title}</div>
        <div style="color:#6b7280; font-size:13px; margin-bottom:14px;">${body}</div>
        <div style="display:flex; gap:8px;">
            <button onclick="confirmAlarm('${alarmId}')" style="
                flex:1; padding:8px; background:#4f46e5; color:white;
                border:none; border-radius:8px; cursor:pointer; font-weight:bold;">
                ✅ 확인
            </button>
            <button onclick="document.getElementById('alarm-popup').remove()" style="
                flex:1; padding:8px; background:#f3f4f6; color:#374151;
                border:none; border-radius:8px; cursor:pointer;">
                나중에
            </button>
        </div>
    `;
    document.body.appendChild(popup);
    console.log('✅ 알람 팝업이 화면에 추가되었습니다');

    // 30초 후 자동 닫기
    setTimeout(() => {
        popup.remove();
        console.log('⏰ 알람 팝업이 30초 후 자동으로 닫혔습니다');
    }, 30000);
}

async function confirmAlarm(alarmId) {
    document.getElementById('alarm-popup')?.remove();
    if (!alarmId) return;
    const token = localStorage.getItem('access_token');
    await fetch(`/api/v1/alarms/history/confirm/${alarmId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
    });
}

// 브라우저 알림 + FCM 초기화 (로그인 상태일 때만)
if ('serviceWorker' in navigator && 'Notification' in window) {
    window.addEventListener('load', initFCM);
}
