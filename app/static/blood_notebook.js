/* =========================
   Blood Notebook Common JS
   혈당/혈압 수첩 공통 유틸
========================= */

window.BloodNotebook = (() => {
  function switchMode(prefix, mode, button) {
    document.querySelectorAll(`.${prefix}-mode-tab, .notebook-mode-tab`).forEach(tab => {
      tab.classList.remove('is-active');
    });

    if (button) {
      button.classList.add('is-active');
    }

    document.querySelectorAll(`.${prefix}-mode-panel, .notebook-mode-panel`).forEach(panel => {
      panel.classList.remove('active');
    });

    const target = document.getElementById(`${prefix}-mode-${mode}`);
    if (target) target.classList.add('active');
  }

  function selectChip(groupSelector, activeClass, button) {
    document.querySelectorAll(groupSelector).forEach(chip => {
      chip.classList.remove(activeClass);
    });

    if (button) {
      button.classList.add(activeClass);
    }
  }

  function formatDateTime(value) {
    const date = new Date(value);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  }

  function formatDateShort(value) {
    const date = new Date(value);
    return new Intl.DateTimeFormat('ko-KR', {
      month: '2-digit',
      day: '2-digit'
    }).format(date);
  }

  function formatDateOnly(value) {
    const date = new Date(value);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  }

  function formatTimeOnly(value) {
    const date = new Date(value);
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  }

  function showFeedback(targetId, message, type = 'success') {
    const box = document.getElementById(targetId);
    if (!box) return;

    box.textContent = message;
    box.className = `notebook-feedback show ${type}`;
  }

  function clearFeedback(targetId) {
    const box = document.getElementById(targetId);
    if (!box) return;

    box.textContent = '';
    box.className = 'notebook-feedback';
  }

  async function fetchWithAuthSafe(url, options = {}) {
    if (typeof fetchWithAuth === 'function') {
      return await fetchWithAuth(url, options);
    }

    let accessToken = localStorage.getItem('access_token');

    if (!options.headers) {
      options.headers = {};
    }

    if (accessToken) {
      options.headers['Authorization'] = `Bearer ${accessToken}`;
    }

    let response = await fetch(url, options);

    if (response.status === 401) {
      const refreshResponse = await fetch('/api/v1/users/token/refresh', { method: 'GET' });

      if (refreshResponse.ok) {
        const result = await refreshResponse.json();
        accessToken = result.access_token;
        localStorage.setItem('access_token', accessToken);
        options.headers['Authorization'] = `Bearer ${accessToken}`;
        response = await fetch(url, options);
      } else {
        alert('세션이 만료되었습니다. 다시 로그인해주세요.');
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_id');
        location.href = '/login';
        return null;
      }
    }

    return response;
  }

  function getFilteredRecords(records, filterValue, key = 'measure_type', allValue = '전체') {
    if (filterValue === allValue) return records;
    return records.filter(item => item[key] === filterValue);
  }

  function renderMiniPreview({
    targetId,
    records,
    emptyMessage,
    formatter
  }) {
    const wrap = document.getElementById(targetId);
    if (!wrap) return;

    if (!records.length) {
      wrap.innerHTML = `
        <div class="notebook-empty sm">
          ${emptyMessage}
        </div>
      `;
      return;
    }

    const recentThree = records.slice(0, 3);
    wrap.innerHTML = recentThree.map(item => formatter(item)).join('');
  }

  function renderRecordList({
    targetId,
    badgeId,
    records,
    filterValue,
    emptyMessage,
    formatter
  }) {
    const wrap = document.getElementById(targetId);
    const badge = document.getElementById(badgeId);

    if (badge) {
      badge.textContent = filterValue === '전체' ? '전체 보기' : `${filterValue} 보기`;
    }

    if (!wrap) return;

    if (!records.length) {
      wrap.innerHTML = `
        <div class="notebook-empty">
          ${emptyMessage}
        </div>
      `;
      return;
    }

    wrap.innerHTML = records.slice(0, 12).map(item => formatter(item)).join('');
  }

  function destroyChart(chartRef) {
    if (chartRef && typeof chartRef.destroy === 'function') {
      chartRef.destroy();
    }
  }

  return {
    switchMode,
    selectChip,
    formatDateTime,
    formatDateShort,
    formatDateOnly,
    formatTimeOnly,
    showFeedback,
    clearFeedback,
    fetchWithAuthSafe,
    getFilteredRecords,
    renderMiniPreview,
    renderRecordList,
    destroyChart
  };
})();
