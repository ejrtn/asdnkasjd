// Slide Navigation
let currentSlide = 0; // 0-based
let slideInterval;
const SLIDE_DURATION = 10000; // 10초마다 슬라이드 변경

function getSlides() {
  return Array.from(document.querySelectorAll('.slide'));
}

function getIndicators() {
  return Array.from(document.querySelectorAll('.indicator'));
}

function showSlideByIndex(index) {
  const slides = getSlides();
  const indicators = getIndicators();
  if (slides.length === 0) return;

  slides.forEach(s => s.classList.remove('active'));
  indicators.forEach(i => i.classList.remove('active'));

  const safeIndex = ((index % slides.length) + slides.length) % slides.length;
  slides[safeIndex].classList.add('active');
  if (indicators[safeIndex]) indicators[safeIndex].classList.add('active');

  currentSlide = safeIndex;
}

function nextSlide() {
  showSlideByIndex(currentSlide + 1);
}

function startSlideTimer() {
  stopSlideTimer();
  slideInterval = setInterval(nextSlide, SLIDE_DURATION);
}

function stopSlideTimer() {
  if (slideInterval) clearInterval(slideInterval);
  slideInterval = null;
}

function resetSlideTimer() {
  startSlideTimer();
}

// Dashboard Summary
async function loadDashboardSummary() {
  const token = localStorage.getItem('access_token');
  if (!token) return;

  try {
    const response = await fetch('/api/v1/dashboard/summary', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      console.error('[Dashboard Summary] Failed:', response.status, response.statusText);
      return;
    }

    const data = await response.json();

    const sleepData = document.getElementById('sleep-data');
    const weightData = document.getElementById('weight-data');

    if (sleepData && data.sleep) {
      sleepData.innerHTML = `
        <div class="trend-value">${data.sleep.value ?? '-'}</div>
        <div class="trend-label">${data.sleep.label ?? '평균 수면 시간'}</div>
        <div class="trend-change ${getTrendClass(data.sleep.change)}">${data.sleep.change ?? '➖ 정보 없음'}</div>
      `;
    }

    if (weightData && data.weight) {
      weightData.innerHTML = `
        <div class="trend-value">${data.weight.value ?? '-'}</div>
        <div class="trend-label">${data.weight.label ?? '현재 체중'}</div>
        <div class="trend-change ${getTrendClass(data.weight.change)}">${data.weight.change ?? '➖ 정보 없음'}</div>
      `;
    }
  } catch (error) {
    console.error('[Dashboard Summary] Error:', error);
  }
}

function getTrendClass(changeText = '') {
  if (changeText.includes('감소')) return 'decrease';
  if (changeText.includes('증가')) return 'increase';
  return 'stable';
}

// Dashboard Health Metric Summary
async function loadDashboardHealthMetricSummary() {
  const token = localStorage.getItem('access_token');
  if (!token) return;

  try {
    const response = await fetch('/api/v1/dashboard/health-metric-summary', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      console.error('[Dashboard Health Metric Summary] Failed:', response.status, response.statusText);
      return;
    }

    const data = await response.json();

    renderMetricSummaryGroup('dashboard-bp-list', data.blood_pressure);
    renderMetricSummaryGroup('dashboard-bs-list', data.blood_sugar);
  } catch (error) {
    console.error('[Dashboard Health Metric Summary] Error:', error);
  }
}

function renderMetricSummaryGroup(listId, group) {
  const listEl = document.getElementById(listId);

  if (!listEl || !group) return;

  const items = Array.isArray(group.items) ? group.items : [];

  listEl.innerHTML = items.map(item => {
    const accentClass =
      item.label === '저녁' || item.label === '식후 2시간'
        ? 'accent'
        : '';

    return `
      <div class="metric-stream-item">
        <div class="metric-stream-main">
          <div class="metric-stream-badge ${accentClass}">
            ${item.label}
          </div>
          <div class="metric-stream-value ${item.value_class || item.status}">
            ${item.value}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

document.addEventListener('DOMContentLoaded', () => {
  // indicator 클릭 연결
  getIndicators().forEach((indicator, idx) => {
    indicator.addEventListener('click', () => {
      showSlideByIndex(idx);
      resetSlideTimer();
    });
  });

  // 첫 슬라이드 보장
  showSlideByIndex(0);
  startSlideTimer();
  loadDashboardAlarmSummary();
  loadDashboardSummary();
  loadDashboardHealthMetricSummary();
});

// 탭 숨김이면 멈췄다가 돌아오면 재시작
document.addEventListener('visibilitychange', () => {
  if (document.hidden) stopSlideTimer();
  else startSlideTimer();
});

// Health Metric Toggle
const healthMetricSelect = document.getElementById('health-metric-select');
if (healthMetricSelect) {
  healthMetricSelect.addEventListener('change', (e) => {
    const value = e.target.value;
    document.querySelectorAll('.metric-data').forEach(el => {
      el.classList.remove('active');
    });
    document.getElementById(`${value}-data`).classList.add('active');
  });
}

// Trend Toggle
const trendSelect = document.getElementById('trend-select');
if (trendSelect) {
  trendSelect.addEventListener('change', (e) => {
    const value = e.target.value;
    document.querySelectorAll('.trend-data').forEach(el => {
      el.classList.remove('active');
    });
    document.getElementById(`${value}-data`).classList.add('active');
  });
}

// Zoom functionality
function toggleZoom() {
  document.body.classList.toggle('zoom-large');
}

// Check login status
function checkLoginStatus() {
  const token = localStorage.getItem('access_token');
  if (!token) {
    window.location.href = '/';
  }
}

// Dashboard Alarm Summary
async function loadDashboardAlarmSummary() {
  const token = localStorage.getItem('access_token');
  const container = document.getElementById('dashboard-alarm-summary');
  if (!container) return;

  if (!token) {
    container.innerHTML = `
      <div class="next-alarm">
        <small>로그인 후 오늘의 알림을 확인할 수 있어요.</small>
      </div>
    `;
    return;
  }

  try {
    const response = await fetch('/api/v1/alarms/dashboard-summary', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      container.innerHTML = `
        <div class="next-alarm">
          <small>오늘의 알림 정보를 불러오지 못했어요.</small>
        </div>
      `;
      return;
    }

    const data = await response.json();

    const previousAlarm = data.previous_alarm;
    const nextAlarm = data.next_alarm;
    const remainingText = data.remaining_text || '예정된 다음 알림이 없습니다.';

    container.innerHTML = `
      ${
        previousAlarm
          ? `
          <div class="medication-item">
            <div class="med-main">
              <div class="med-badge previous">이전 알림</div>
              <div class="med-row">
                <div class="med-time">${previousAlarm.time}</div>
                <div class="med-name">${previousAlarm.label}</div>
              </div>
            </div>
            <div class="med-status ${previousAlarm.is_confirmed ? 'completed' : 'pending'}">
              ${previousAlarm.is_confirmed ? '🟢' : '🔴'}
            </div>
          </div>
        `
          : `
          <div class="medication-item medication-empty">
            <div class="med-main">
              <div class="med-badge previous">이전 알림</div>
              <div class="med-row">
                <div class="med-name">오늘 지난 알림이 없습니다.</div>
              </div>
            </div>
          </div>
        `
      }
      ${
        nextAlarm
          ? `
          <div class="medication-item">
            <div class="med-main">
              <div class="med-badge next">다음 알림</div>
              <div class="med-row">
                <div class="med-time">${nextAlarm.time}</div>
                <div class="med-name">${nextAlarm.label}</div>
              </div>
            </div>
            <div class="med-status pending">🔴</div>
          </div>
        `
          : `
          <div class="medication-item medication-empty">
            <div class="med-main">
              <div class="med-badge next">다음 알림</div>
              <div class="med-row">
                <div class="med-name">예정된 다음 알림이 없습니다.</div>
              </div>
            </div>
          </div>
        `
      }
      <div class="next-alarm">
        <small>${remainingText}</small>
      </div>
    `;
  } catch (error) {
    console.error('[Dashboard Alarm Summary] Failed to load:', error);
    container.innerHTML = `
      <div class="next-alarm">
        <small>오늘의 알림 정보를 불러오지 못했어요.</small>
      </div>
    `;
  }
}
