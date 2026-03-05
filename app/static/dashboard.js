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
