let pressureChart = null;
let selectedSavePressureType = "";
let pressureRecords = [];
let activePressureFilter = "전체";
let activePressureRecordFilter = "아침";

function switchPressureMode(mode, button) {
  BloodNotebook.switchMode('pressure', mode, button);
}

function selectSavePressureType(value, button) {
  selectedSavePressureType = value;
  BloodNotebook.selectChip('#save-pressure-chip-group .notebook-chip', 'is-active', button);
}

function applyPressureFilter(filterValue, button) {
  activePressureFilter = filterValue;
  BloodNotebook.selectChip('#view-pressure-filter-chip-group .notebook-chip', 'is-active', button);
  renderPressureSummary();
  renderPressureChart();
}

function applyPressureRecordFilter(filterValue, button) {
  activePressureRecordFilter = filterValue;
  BloodNotebook.selectChip('#pressure-record-filter-chip-group .notebook-chip', 'is-active', button);
  renderPressureRecordList();
}

function getFilteredPressureRecords() {
  const visibleRecords = pressureRecords.filter(item => item.measure_type !== '임의');
  return BloodNotebook.getFilteredRecords(visibleRecords, activePressureFilter, 'measure_type', '전체');
}

function getFilteredPressureRecordRecords() {
  const visibleRecords = pressureRecords.filter(item => item.measure_type !== '임의');
  return visibleRecords.filter(item => item.measure_type === activePressureRecordFilter);
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

function renderPressureTodayStatus() {
  const todayRecords = pressureRecords.filter(item =>
    item.measure_type !== '임의' && isSameKstDate(item.created_at)
  );

  const hasMorning = todayRecords.some(item => item.measure_type === '아침');
  const hasEvening = todayRecords.some(item => item.measure_type === '저녁');

  setGuideStatus('guide-morning', hasMorning);
  setGuideStatus('guide-evening', hasEvening);
}

async function submitBloodPressure() {
  BloodNotebook.clearFeedback('pressure-save-feedback');

  const systolicInput = document.getElementById('systolic-input');
  const diastolicInput = document.getElementById('diastolic-input');

  const systolicValue = systolicInput.value.trim();
  const diastolicValue = diastolicInput.value.trim();

  if (!systolicValue) {
    BloodNotebook.showFeedback('pressure-save-feedback', "수축기 값을 입력해주세요.", "error");
    return;
  }

  if (!diastolicValue) {
    BloodNotebook.showFeedback('pressure-save-feedback', "이완기 값을 입력해주세요.", "error");
    return;
  }

  if (!selectedSavePressureType) {
    BloodNotebook.showFeedback('pressure-save-feedback', "측정 시각을 선택해주세요.", "error");
    return;
  }

  const payload = {
    systolic: Number(systolicValue),
    diastolic: Number(diastolicValue),
    measure_type: selectedSavePressureType
  };

  const response = await BloodNotebook.fetchWithAuthSafe('/api/v1/health/blood-pressure', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response) return;

  if (response.status === 409) {
    const result = await response.json();
    BloodNotebook.showFeedback('pressure-save-feedback', result.detail || "중복 또는 저장 불가 상태입니다.", "error");
    return;
  }

  if (!response.ok) {
    BloodNotebook.showFeedback('pressure-save-feedback', "혈압 저장 중 오류가 발생했습니다.", "error");
    return;
  }

  systolicInput.value = '';
  diastolicInput.value = '';
  selectedSavePressureType = '';

  document.querySelectorAll('#save-pressure-chip-group .notebook-chip').forEach(chip => {
    chip.classList.remove('is-active');
  });

  BloodNotebook.showFeedback('pressure-save-feedback', "혈압 기록이 저장되었습니다.", "success");

  await loadBloodPressureRecords();
}

async function loadBloodPressureRecords() {
  const response = await BloodNotebook.fetchWithAuthSafe('/api/v1/health/blood-pressure', {
    method: 'GET'
  });

  if (!response || !response.ok) {
    pressureRecords = [];
    renderPressureSummary();
    renderPressureChart();
    renderPressureRecordList();
    renderPressureTodayStatus();
    return;
  }

  const result = await response.json();
  pressureRecords = Array.isArray(result) ? result : [];
  pressureRecords = pressureRecords.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  renderPressureSummary();
  renderPressureChart();
  renderPressureRecordList();
  renderPressureTodayStatus();
}

function renderPressureSummary() {
  const filtered = getFilteredPressureRecords();

  const latestValueEl = document.getElementById('pressure-summary-latest-value');
  const latestMetaEl = document.getElementById('pressure-summary-latest-meta');
  const avgValueEl = document.getElementById('pressure-summary-average-value');
  const avgMetaEl = document.getElementById('pressure-summary-average-meta');
  const filterValueEl = document.getElementById('pressure-summary-filter-value');

  filterValueEl.textContent = activePressureFilter;

  if (!filtered.length) {
    latestValueEl.textContent = '-';
    latestMetaEl.textContent = '최근 기록이 없습니다.';
    avgValueEl.textContent = '-';
    avgMetaEl.textContent = '기록이 없어 평균을 계산할 수 없습니다.';
    return;
  }

  const latest = filtered[0];
  latestValueEl.textContent = `${Number(latest.systolic)} / ${Number(latest.diastolic)}`;
  latestMetaEl.textContent = `${latest.measure_type || '기록'} · ${BloodNotebook.formatDateTime(latest.created_at)}`;

  const avgTarget = filtered.slice(0, 7);
  const systolicAvg = avgTarget.reduce((sum, item) => sum + Number(item.systolic), 0) / avgTarget.length;
  const diastolicAvg = avgTarget.reduce((sum, item) => sum + Number(item.diastolic), 0) / avgTarget.length;

  avgValueEl.textContent = `${Math.round(systolicAvg)} / ${Math.round(diastolicAvg)}`;
  avgMetaEl.textContent = `${activePressureFilter === '전체' ? '전체 기준' : activePressureFilter + ' 기준'} 최근 ${avgTarget.length}건 평균`;
}

function renderPressureChart() {
  const filtered = getFilteredPressureRecords().slice(0, 15).reverse();
  const ctx = document.getElementById('pressureChart');

  BloodNotebook.destroyChart(pressureChart);
  pressureChart = null;

  if (!filtered.length) {
    pressureChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          { label: '수축기', data: [] },
          { label: '이완기', data: [] }
        ]
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

  const systolicValues = filtered.map(item => Number(item.systolic));
  const diastolicValues = filtered.map(item => Number(item.diastolic));

  pressureChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '수축기',
          data: systolicValues,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.08)',
          borderWidth: 2,
          tension: 0.32,
          fill: false,
          pointRadius: 3,
          pointHoverRadius: 5
        },
        {
          label: '이완기',
          data: diastolicValues,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.08)',
          borderWidth: 2,
          tension: 0.32,
          fill: false,
          pointRadius: 3,
          pointHoverRadius: 5
        }
      ]
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
            afterTitle: function (context) {
              const index = context[0].dataIndex;
              return `${filtered[index].measure_type || '기록'}`;
            },
            label: function (context) {
              return ` ${context.dataset.label}: ${context.parsed.y} mmHg`;
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
          suggestedMin: 60,
          suggestedMax: 150,
          grid: {
            color: 'rgba(148, 163, 184, 0.18)'
          }
        }
      }
    }
  });
}

function renderPressureRecordList() {
  const wrap = document.getElementById('pressure-record-list');
  const badge = document.getElementById('pressure-record-list-badge');
  const filtered = getFilteredPressureRecordRecords().slice(0, 15);

  if (badge) {
    badge.textContent = `${activePressureRecordFilter} 보기`;
  }

  if (!filtered.length) {
    wrap.innerHTML = `
      <div class="notebook-empty">
        선택한 조건에 맞는 혈압 기록이 없습니다.
      </div>
    `;
    return;
  }

  wrap.innerHTML = filtered.map(item => `
    <div class="notebook-record-item compact">
      <div class="notebook-record-left">
        <div class="data-del" title="${item.id}">X</div>
        <div class="notebook-record-value-row">
          <span class="notebook-record-value">${Number(item.systolic)} / ${Number(item.diastolic)} mmHg</span>
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
  await loadBloodPressureRecords();
});

document.querySelector("#pressure-record-list").addEventListener("click", async (e) => {
  if (e.target.className == 'data-del') {
    if (confirm("정말 삭제하시겠습니까?")) {
      const response = await BloodNotebook.fetchWithAuthSafe('/api/v1/health/blood-pressure/' + e.target.title, {
        method: 'DELETE',
      });
      const result = await response.json();
      if (result.status == 'success') {
        e.target.parentNode.parentNode.remove()
        loadBloodPressureRecords()
      }
    }

  }
})