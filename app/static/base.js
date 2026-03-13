let __sessionExpiredHandled = false;
let __sessionToastTimer = null;
let __sessionExpiredMode = false;
const PUBLIC_PATHS = ['/', '/login', '/signup', '/find-account'];
let __authGuardRunning = false;

function clearClientSession() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('auth_token');
}

function showSessionToast() {
    const toast = document.getElementById('session-toast');
    if (!toast) return;

    const prog = toast.querySelector('.session-toast-progress > div');
    if (prog) {
        prog.style.animation = 'none';
        void prog.offsetHeight;
        prog.style.animation = '';
    }

    toast.classList.remove('hide');
    toast.classList.add('show');
}

function hideSessionToast() {
    const toast = document.getElementById('session-toast');
    if (!toast) return;

    toast.classList.remove('show');
    toast.classList.add('hide');
}

function handleSessionExpired() {
    if (__sessionExpiredHandled) return;

    __sessionExpiredHandled = true;
    __sessionExpiredMode = true;

    clearClientSession();

    if (PUBLIC_PATHS.includes(window.location.pathname)) {
        window.location.replace('/');
        return;
    }

    showSessionToast();

    __sessionToastTimer = setTimeout(() => {
        window.location.replace('/');
    }, 2500);
}

async function fetchWithAuth(url, options = {}) {
    let accessToken = localStorage.getItem("access_token");

    if (!options.headers) options.headers = {};

    if (accessToken) {
        options.headers["Authorization"] = `Bearer ${accessToken}`;
    }

    let response = await fetch(url, options);

    if (response.status === 401) {
        const refreshResponse = await fetch('/api/v1/auth/token/refresh', {
            method: 'GET',
            credentials: 'include'
        });

        if (refreshResponse.ok) {
            const result = await refreshResponse.json();
            accessToken = result.access_token;
            localStorage.setItem("access_token", accessToken);
            options.headers["Authorization"] = `Bearer ${accessToken}`;
            response = await fetch(url, options);

            if (response.status === 401) {
                handleSessionExpired();
                return null;
            }
        } else {
            handleSessionExpired();
            return null;
        }
    }

    return response;
}

async function authGuard() {
    if (__sessionExpiredMode) return;
    if (__authGuardRunning) return;

    __authGuardRunning = true;

    try {
        const path = window.location.pathname;
        if (PUBLIC_PATHS.includes(path)) return;

        const token = localStorage.getItem('access_token');
        if (!token) {
            handleSessionExpired();
            return;
        }

        const res = await fetchWithAuth('/api/v1/users/me', { method: 'GET' });
        if (!res) return;

        if (!res.ok) {
            handleSessionExpired();
        }
    } finally {
        __authGuardRunning = false;
    }
}

function bindSessionToastEvents() {
    const closeBtn = document.getElementById('session-toast-close');
    const dismissBtn = document.getElementById('session-toast-dismiss');
    const loginBtn = document.getElementById('session-toast-login');

    function goLandingNow() {
        if (__sessionToastTimer) clearTimeout(__sessionToastTimer);
        __sessionToastTimer = null;
        __sessionExpiredMode = true;
        window.location.replace('/');
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            hideSessionToast();
            goLandingNow();
        });
    }

    if (dismissBtn) {
        dismissBtn.addEventListener('click', () => {
            hideSessionToast();
            goLandingNow();
        });
    }

    if (loginBtn) {
        loginBtn.addEventListener('click', () => {
            if (__sessionToastTimer) clearTimeout(__sessionToastTimer);
            __sessionToastTimer = null;
            __sessionExpiredMode = true;
            window.location.replace('/login');
        });
    }
}

function bindUserMenu() {
    const userMenu = document.querySelector('.user-menu');
    const userMenuBtn = document.getElementById('user-menu-btn');
    const userDropdown = document.getElementById('user-dropdown');

    if (!userMenu || !userMenuBtn || !userDropdown) return;

    userMenuBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        userMenu.classList.toggle('open');
    });

    userDropdown.addEventListener('click', function (e) {
        e.stopPropagation();
    });

    document.addEventListener('click', function (e) {
        if (!userMenu.contains(e.target)) {
            userMenu.classList.remove('open');
        }
    });

    document.querySelectorAll('.user-dropdown a').forEach(link => {
        link.addEventListener('click', function () {
            userMenu.classList.remove('open');
        });
    });
}

function bindSearchUI() {
    const searchBtn = document.getElementById('search-btn');
    const searchInput = document.getElementById('search-input');

    if (searchBtn) {
        searchBtn.addEventListener('click', function () {
            const searchTerm = searchInput ? searchInput.value.trim() : '';
            if (searchTerm) {
                alert(`"${searchTerm}" 검색 기능은 추후 추가될 예정입니다.`);
            }
        });
    }

    if (searchInput) {
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (searchBtn) searchBtn.click();
            }
        });
    }
}

function applySavedZoomState() {
    const zoomBtn = document.getElementById('zoom-btn');
    const isZoomed = localStorage.getItem('zoomState') === 'true';

    if (isZoomed) {
        document.body.classList.add('zoom-large');
    }

    if (zoomBtn) {
        zoomBtn.textContent = isZoomed ? '🔎' : '🔍';
        zoomBtn.title = isZoomed ? '글자 크기 축소' : '글자 크기 확대';
    }
}

function bindZoomUI() {
    const zoomBtn = document.getElementById('zoom-btn');
    if (!zoomBtn) return;

    zoomBtn.addEventListener('click', function () {
        const isZoomed = document.body.classList.toggle('zoom-large');
        localStorage.setItem('zoomState', isZoomed ? 'true' : 'false');
        this.textContent = isZoomed ? '🔎' : '🔍';
        this.title = isZoomed ? '글자 크기 축소' : '글자 크기 확대';
    });
}

async function logout() {
    try {
        await fetch('/api/v1/users/logout', {
            method: 'POST',
            credentials: 'include'
        });
    } catch (e) {
        console.error(e);
    }

    clearClientSession();
    window.location.replace('/');
}

window.addEventListener('DOMContentLoaded', authGuard);
window.addEventListener('pageshow', authGuard);
window.addEventListener('focus', authGuard);
setInterval(authGuard, 60 * 1000);

window.addEventListener('DOMContentLoaded', function () {
    applySavedZoomState();
    bindSessionToastEvents();
    bindUserMenu();
    bindSearchUI();
    bindZoomUI();
});