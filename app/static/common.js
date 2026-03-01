// 사용자 메뉴 드롭다운 토글
document.getElementById('user-menu-btn').addEventListener('click', function(e) {
    e.stopPropagation();
    document.getElementById('user-dropdown').classList.toggle('show');
});

// 외부 클릭 시 드롭다운 닫기
document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown.classList.contains('show')) {
        dropdown.classList.remove('show');
    }
});
