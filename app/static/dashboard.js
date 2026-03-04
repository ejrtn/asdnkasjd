// Slide Navigation
document.querySelectorAll('.indicator').forEach(indicator => {
  indicator.addEventListener('click', () => {
    const slideNum = indicator.dataset.slide;
    showSlide(slideNum);
  });
});

function showSlide(slideNum) {
  document.querySelectorAll('.slide').forEach(slide => {
    slide.classList.remove('active');
  });
  document.querySelectorAll('.indicator').forEach(ind => {
    ind.classList.remove('active');
  });

  document.querySelector(`[data-slide="${slideNum}"]`).classList.add('active');
  document.querySelector(`.indicator[data-slide="${slideNum}"]`).classList.add('active');
}

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
  const token = localStorage.getItem('auth_token');
  const cardsContainer = document.getElementById('dashboard-cards');
  
  if (!token) {
    cardsContainer.innerHTML = `
      <div class="login-required-message">
        <div>🔐</div>
        <h3>로그인이 필요합니다</h3>
        <p>상단 우측의 사람 아이콘을 클릭하여 로그인하세요.</p>
      </div>
    `;
  }
}
