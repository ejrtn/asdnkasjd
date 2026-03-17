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
    }, 5000);
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
    bindZoomUI();
    bindMobileSidebar();
    bindMobileExpandBtns();
});

/* ===== Mobile Sidebar Toggle ===== */
function closeAllMobilePanels() {
    document.querySelectorAll('.nav-item.mobile-open').forEach(item => {
        item.classList.remove('mobile-open');
    });
    document.querySelectorAll('.mobile-expand-btn').forEach(btn => {
        btn.setAttribute('aria-expanded', 'false');
    });
}

function bindMobileSidebar() {
    var menuBtn = document.getElementById('mobile-menu-btn');
    var backdrop = document.getElementById('mobile-sidebar-backdrop');
    var sidebar = document.querySelector('.sidebar');

    if (!menuBtn || !backdrop || !sidebar) return;

    var navigating = false;

    function closeSidebar() {
        document.body.classList.remove('sidebar-open');
        menuBtn.setAttribute('aria-expanded', 'false');
        closeAllMobilePanels();
    }

    function moveToHref(href) {
        if (!href || href.startsWith('javascript:')) return;
        if (navigating) return;

        navigating = true;
        closeSidebar();

        setTimeout(function () {
            window.location.href = href;
        }, 120);
    }

    menuBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();

        var userMenu = document.querySelector('.user-menu');
        if (userMenu) userMenu.classList.remove('open');

        var isOpen = document.body.classList.toggle('sidebar-open');
        menuBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    backdrop.addEventListener('click', closeSidebar);

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeSidebar();
    });

    /* 1) 사이드바 메뉴 링크 직접 바인딩 */
    sidebar.querySelectorAll('.sidebar-link').forEach(function (link) {
        link.addEventListener('click', function (e) {
            if (window.innerWidth > 768) return;

            var href = this.getAttribute('href');
            if (!href || href.startsWith('javascript:')) return;

            e.preventDefault();
            e.stopPropagation();
            moveToHref(href);
        });
    });

    /* 2) 메가패널 카드 링크 직접 바인딩 */
    sidebar.querySelectorAll('.mega-card-link').forEach(function (link) {
        link.addEventListener('click', function (e) {
            if (window.innerWidth > 768) return;

            var href = this.getAttribute('href');
            if (!href || href.startsWith('javascript:')) return;

            e.preventDefault();
            e.stopPropagation();
            moveToHref(href);
        });
    });

    /* 3) 메가패널 설명영역 클릭 시 대표 페이지 이동 */
    sidebar.querySelectorAll('.nav-item').forEach(function (item) {
        var mainLink = item.querySelector('.sidebar-link');
        var panel = item.querySelector('.mega-panel');

        if (!mainLink || !panel) return;

        panel.addEventListener('click', function (e) {
            if (window.innerWidth > 768) return;

            if (e.target.closest('.mega-card-link')) return;
            if (e.target.closest('a')) return;
            if (e.target.closest('button')) return;

            var href = mainLink.getAttribute('href');
            if (!href || href.startsWith('javascript:')) return;

            e.preventDefault();
            e.stopPropagation();
            moveToHref(href);
        });
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth > 768) {
            navigating = false;
            closeSidebar();
            closeAllMobilePanels();
        }
    });
}

/* ===== Mobile Mega-Panel Accordion ===== */
function bindMobileExpandBtns() {
    document.querySelectorAll('.mobile-expand-btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            if (window.innerWidth > 768) return;

            const navItem = this.closest('.nav-item');
            if (!navItem) return;

            const wasOpen = navItem.classList.contains('mobile-open');

            closeAllMobilePanels();

            if (!wasOpen) {
                navItem.classList.add('mobile-open');
                this.setAttribute('aria-expanded', 'true');
            } else {
                this.setAttribute('aria-expanded', 'false');
            }
        });
    });
}