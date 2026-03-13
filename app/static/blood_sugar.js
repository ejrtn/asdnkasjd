let sugarChart = null;
let selectedSaveMeasureType = "";
let sugarRecords = [];
let activeSugarFilter = "전체";
let activeSugarRecordFilter = "공복";

function switchSugarMode(mode, button) {
  BloodNotebook.switchMode('sugar', mode, button);
}

function selectSaveMeasureType(value, button) {
  selectedSaveMeasureType = value;
  BloodNotebook.selectChip('#save-measure-chip-group .notebook-chip', 'is-active', button);
}

function applySugarFilter(filterValue, button) {
  activeSugarFilter = filterValue;
  BloodNotebook.selectChip('#view-filter-chip-group .notebook-chip', 'is-active', button);
  renderSugarSummary();
  renderSugarChart();
}

function applySugarRecordFilter(filterValue, button) {
  activeSugarRecordFilter = filterValue;
  BloodNotebook.selectChip('#sugar-record-filter-chip-group .notebook-chip', 'is-active', button);
  renderSugarRecordList();
}

function getFilteredSugarRecords() {
  const visibleRecords = sugarRecords.filter(item => item.measure_type !== '임의');
  return BloodNotebook.getFilteredRecords(visibleRecords, activeSugarFilter, 'measure_type', '전체');
}

function getFilteredSugarRecordRecords() {
  const visibleRecords = sugarRecords.filter(item => item.measure_type !== '임의');
  return visibleRecords.filter(item => item.measure_type === activeSugarRecordFilter);
}

function isSameKstDate(dateValue) {
  const target = new Date(dateValue);
  const now = new Date();

  const targetKst = new Date(target.getTime() + 9 * 60 * 60 * 1000);
  const nowKst = new Date(now.getTime() + 9 * 60 * 60 * 1000);

  return (
    targetKst.getUTCFullYear() === nowKst.getUTCFullYear() &&
    targetKst.getUTCMonth() === nowKst.getUTCMonth() &&
    targetKst.getUTCDate() === nowKst.getUTCDate()
  );
}

function setGuideStatus(elementId, isDone) {
  const el = document.getElementById(elementId);
  if (!el) return;

  el.textContent = isDone ? '기록됨' : '미기록';
  el.classList.remove('done', 'pending');
  el.classList.add(isDone ? 'done' : 'pending');
}

function renderSugarTodayStatus() {
  const todayRecords = sugarRecords.filter(item =>
    item.measure_type !== '임의' && isSameKstDate(item.created_at)
  );

  const hasFasting = todayRecords.some(item => item.measure_type === '공복');
  const hasPostmeal = todayRecords.some(item => item.measure_type === '식후 2시간');
  const hasBedtime = todayRecords.some(item => item.measure_type === '취침 전');

  setGuideStatus('guide-fasting', hasFasting);
  setGuideStatus('guide-postmeal', hasPostmeal);
  setGuideStatus('guide-bedtime', hasBedtime);
}

async function submitBloodSugar() {
  BloodNotebook.clearFeedback('sugar-save-feedback');

  const glucoseInput = document.getElementById('glucose-input');
  const glucoseValue = glucoseInput.value.trim();

  if (!glucoseValue) {
    BloodNotebook.showFeedback('sugar-save-feedback', "혈당 수치를 입력해주세요.", "error");
    return;
  }

  if (!selectedSaveMeasureType) {
    BloodNotebook.showFeedback('sugar-save-feedback', "측정 상황을 선택해주세요.", "error");
    return;
  }

  const payload = {
    glucose_mg_dl: Number(glucoseValue),
    measure_type: selectedSaveMeasureType
  };

  const response = await BloodNotebook.fetchWithAuthSafe('/api/v1/health/blood-sugar', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response) return;

  if (response.status === 409) {
    const result = await response.json();
    BloodNotebook.showFeedback('sugar-save-feedback', result.detail || "중복 또는 저장 불가 상태입니다.", "error");
    return;
  }

  if (!response.ok) {
    BloodNotebook.showFeedback('sugar-save-feedback', "혈당 저장 중 오류가 발생했습니다.", "error");
    return;
  }

  glucoseInput.value = '';
  selectedSaveMeasureType = '';

  document.querySelectorAll('#save-measure-chip-group .notebook-chip').forEach(chip => {
    chip.classList.remove('is-active');
  });

  BloodNotebook.showFeedback('sugar-save-feedback', "혈당 기록이 저장되었습니다.", "success");

  await loadBloodSugarRecords();
}

async function loadBloodSugarRecords() {
  const response = await BloodNotebook.fetchWithAuthSafe('/api/v1/health/blood-sugar', {
    method: 'GET'
  });

  if (!response || !response.ok) {
    sugarRecords = [];
    renderSugarSummary();
    renderSugarChart();
    renderSugarRecordList();
    renderSugarTodayStatus();
    return;
  }

  const result = await response.json();
  sugarRecords = Array.isArray(result) ? result : [];
  sugarRecords = sugarRecords.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  renderSugarSummary();
  renderSugarChart();
  renderSugarRecordList();
  renderSugarTodayStatus();
}

function renderSugarSummary() {
  const filtered = getFilteredSugarRecords();

  const latestValueEl = document.getElementById('summary-latest-value');
  const latestMetaEl = document.getElementById('summary-latest-meta');
  const avgValueEl = document.getElementById('summary-average-value');
  const avgMetaEl = document.getElementById('summary-average-meta');
  const filterValueEl = document.getElementById('summary-filter-value');

  filterValueEl.textContent = activeSugarFilter;

  if (!filtered.length) {
    latestValueEl.textContent = '-';
    latestMetaEl.textContent = '최근 기록이 없습니다.';
    avgValueEl.textContent = '-';
    avgMetaEl.textContent = '기록이 없어 평균을 계산할 수 없습니다.';
    return;
  }

  const latest = filtered[0];
  latestValueEl.textContent = `${Number(latest.glucose_mg_dl)} mg/dL`;
  latestMetaEl.textContent = `${latest.measure_type} · ${BloodNotebook.formatDateTime(latest.created_at)}`;

  const avgTarget = filtered.slice(0, 7);
  const avg = avgTarget.reduce((sum, item) => sum + Number(item.glucose_mg_dl), 0) / avgTarget.length;

  avgValueEl.textContent = `${avg.toFixed(1)} mg/dL`;
  avgMetaEl.textContent = `${activeSugarFilter === '전체' ? '전체 기준' : activeSugarFilter + ' 기준'} 최근 ${avgTarget.length}건 평균`;
}

function renderSugarChart() {
  const filtered = getFilteredSugarRecords().slice(0, 15).reverse();
  const ctx = document.getElementById('sugarChart');

  BloodNotebook.destroyChart(sugarChart);
  sugarChart = null;

  if (!filtered.length) {
    sugarChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: '혈당 (mg/dL)',
          data: []
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        }
      }
    });
    return;
  }

  const labels = filtered.map((item, index) => {
    if (index % 4 !== 0 && index !== filtered.length - 1) return '';
    return BloodNotebook.formatDateShort(item.created_at);
  });

  const values = filtered.map(item => Number(item.glucose_mg_dl));

  sugarChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: '혈당 (mg/dL)',
        data: values,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.10)',
        borderWidth: 2,
        tension: 0.32,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top'
        },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.92)',
          padding: 10,
          callbacks: {
            title: function (context) {
              const index = context[0].dataIndex;
              return BloodNotebook.formatDateTime(filtered[index].created_at);
            },
            label: function (context) {
              const index = context.dataIndex;
              const item = filtered[index];
              return ` ${item.measure_type}: ${context.parsed.y} mg/dL`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            autoSkip: false,
            maxRotation: 0
          }
        },
        y: {
          beginAtZero: false,
          suggestedMin: 70,
          grid: {
            color: 'rgba(148, 163, 184, 0.18)'
          }
        }
      }
    }
  });
}

function renderSugarRecordList() {
  const wrap = document.getElementById('sugar-record-list');
  const badge = document.getElementById('record-list-badge');
  const filtered = getFilteredSugarRecordRecords().slice(0, 15);

  if (badge) {
    badge.textContent = `${activeSugarRecordFilter} 보기`;
  }

  if (!filtered.length) {
    wrap.innerHTML = `
      <div class="notebook-empty">
        선택한 조건에 맞는 혈당 기록이 없습니다.
      </div>
    `;
    return;
  }

  wrap.innerHTML = filtered.map(item => `
    <div class="notebook-record-item compact">
      <div class="notebook-record-left">
        <div class="data-del" title="${item.id}">X</div>
        <div class="notebook-record-value-row">
          <span class="notebook-record-value">${Number(item.glucose_mg_dl)} mg/dL</span>
          <span class="notebook-record-badge">${item.measure_type}</span>
        </div>
        <div class="notebook-record-meta">
          <div class="notebook-record-date">${BloodNotebook.formatDateOnly(item.created_at)}</div>
          <div class="notebook-record-clock">${BloodNotebook.formatTimeOnly(item.created_at)}</div>
        </div>
      </div>
    </div>
  `).join('');
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadBloodSugarRecords();

  const recordList = document.querySelector("#sugar-record-list");
  if (!recordList) return;

  recordList.addEventListener("click", async (e) => {
    if (e.target.classList.contains('data-del')) {
      if (confirm("정말 삭제하시겠습니까?")) {
        const response = await BloodNotebook.fetchWithAuthSafe('/api/v1/health/blood-sugar/' + e.target.title, {
          method: 'DELETE',
        });

        if (!response) return;

        const result = await response.json();
        if (result.status === 'success') {
          await loadBloodSugarRecords();
        }
      }
    }
  });
});