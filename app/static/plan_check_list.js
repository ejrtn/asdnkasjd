// 달성률 업데이트 함수
    function updateProgress() {
        const checkboxes = document.querySelectorAll('.plan-item input[type="checkbox"]');
        const total = checkboxes.length;
        if (total === 0) {
            document.getElementById('success-rate').innerText = '0%';
            document.getElementById('progress-fill').style.width = '0%';
            return;
        }

        const checked = Array.from(checkboxes).filter(cb => cb.checked).length;
        const percentage = Math.round((checked / total) * 100);

        document.getElementById('success-rate').innerText = percentage + '%';
        document.getElementById('progress-fill').style.width = percentage + '%';
    }

    // 아이템 목록 로드 함수
    async function loadItems() {
        const response = await fetchWithAuth('/api/v1/plan_check_list');
        if (!response || !response.ok) {
            console.error('Failed to load items');
            return;
        }
        const items = await response.json();
        const list = document.getElementById('plan-list');
        list.innerHTML = '';

        items.forEach(item => {
            const itemHtml = `
            <div class="plan-item" data-id="${item.id}">
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="check-${item.id}" ${item.is_completed ? 'checked' : ''} onchange="toggleItem(${item.id})">
                    <label for="check-${item.id}"></label>
                </div>
                <div class="plan-info">
                    <span class="plan-text" style="${item.is_completed ? 'text-decoration: line-through; color: #aaa;' : ''}">${item.content}</span>
                    <span class="plan-tag">DAILY ACTION</span>
                </div>
                <button class="delete-btn" onclick="deleteItem(this)">×</button>
            </div>
        `;
            list.insertAdjacentHTML('beforeend', itemHtml);
        });
        updateProgress();
    }

    // 아이템 추가 함수
    async function addItem() {
        const input = document.getElementById('new-plan-input');
        const text = input.value.trim();
        if (!text) return;

        const response = await fetchWithAuth('/api/v1/plan_check_list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ "content": text })
        });

        if (!response || !response.ok) {
            console.error('Failed to add item');
            return;
        }

        input.value = '';
        loadItems(); // 목록 새로고침
    }

    // 아이템 삭제 함수
    async function deleteItem(btn) {
        const msg = "정말 삭제하시겠습니까?\n\n(삭제된 항목은 '알람 동기화' 또는 'AI 추천 다시 받기' 버튼으로 다시 불러올 수 있습니다.)";
        showAppConfirm(msg, async () => {
            const itemId = btn.closest('.plan-item').dataset.id;
            const response = await fetchWithAuth('/api/v1/plan_check_list/' + itemId, {
                method: 'DELETE',
            });
            if (!response || !response.ok) {
                console.error('Failed to delete item');
                return;
            }
            btn.closest('.plan-item').remove();
            updateProgress();
        }, null, '미션 삭제');
    }

    // 알람 동기화 함수
    async function syncAlarms() {
        const btn = document.getElementById('sync-alarms-btn');
        btn.classList.add('loading');
        btn.innerHTML = '<span>⏳</span> 동기화 중...';

        try {
            const response = await fetchWithAuth('/api/v1/plan_check_list/sync-alarms', {
                method: 'POST'
            });
            if (response && response.ok) {
                showAppToast('알람 동기화가 완료되었습니다.', 'success', '알람 동기화');
                loadItems();
            } else {
                showAppToast('동기화에 실패했습니다.', 'warn', '알람 동기화');
            }
        } catch (e) {
            console.error(e);
        } finally {
            btn.classList.remove('loading');
            btn.innerHTML = '<span>🔄</span> 알람 동기화';
        }
    }

    // AI 추천 다시 받기 함수
    async function recommendAI() {
        const btn = document.getElementById('recommend-ai-btn');
        btn.classList.add('loading');
        btn.innerHTML = '<span>⏳</span> 생성 중...';

        try {
            const response = await fetchWithAuth('/api/v1/plan_check_list/recommend-ai', {
                method: 'POST'
            });
            if (response && response.ok) {
                showAppToast('AI 추천 플랜이 새롭게 생성되었습니다.', 'success', 'AI 추천');
                loadItems();
            } else {
                showAppToast('추천 플랜 생성에 실패했습니다.', 'warn', 'AI 추천');
            }
        } catch (e) {
            console.error(e);
        } finally {
            btn.classList.remove('loading');
            btn.innerHTML = '<span>✨</span> AI 추천 다시 받기';
        }
    }

    // 아이템 토글 함수
    async function toggleItem(id) {
        const response = await fetchWithAuth(`/api/v1/plan_check_list/${id}/toggle`, {
            method: 'PATCH'
        });
        if (!response || !response.ok) {
            console.error('Failed to toggle item');
            loadItems(); // 상태 복구를 위해 리로드
            return;
        }
        const item = await response.json();
        const itemElement = document.querySelector(`.plan-item[data-id="${id}"]`);
        const textElement = itemElement.querySelector('.plan-text');
        if (item.is_completed) {
            textElement.style.textDecoration = 'line-through';
            textElement.style.color = '#aaa';
        } else {
            textElement.style.textDecoration = 'none';
            textElement.style.color = '#444';
        }
        updateProgress();
    }

    // 엔터키 입력 시 추가
    document.getElementById('new-plan-input')?.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') addItem();
    });

    // 초기 실행
    window.onload = loadItems;