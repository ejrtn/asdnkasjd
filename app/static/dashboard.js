// 대시보드 JavaScript

// 전역 변수
let dashboardData = null;

// 현재 날짜 및 시간 업데이트
function updateDateTime() {
    const now = new Date();
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric', 
        weekday: 'short' 
    };
    const dateStr = now.toLocaleDateString('ko-KR', options);
    document.getElementById('current-date').textContent = `📅 ${dateStr}`;
}

// 날씨 정보 (실제로는 API에서 가져와야 함)
function updateWeatherInfo() {
    // 임시 데이터 - 실제로는 날씨 API 연동
    const weatherData = {
        temp: 18,
        condition: '맑음',
        icon: '🌤️',
        tip: '오늘은 가벼운 산책을 하기 좋은 날입니다.'
    };
    
    document.getElementById('weather-info').textContent = 
        `${weatherData.icon} ${weatherData.temp}°C · ${weatherData.condition}`;
    document.getElementById('weather-tip').textContent = weatherData.tip;
}

// 대시보드 데이터 로드
async function loadDashboardData() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        console.log('로그인 토큰이 없습니다.');
        return;
    }

    try {
        const response = await fetch('/api/v1/dashboard/summary', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            dashboardData = await response.json();
            updateDashboardUI();
        } else {
            console.error('대시보드 데이터 로드 실패:', response.status);
        }
    } catch (error) {
        console.error('대시보드 데이터 로드 오류:', error);
    }
}

// 대시보드 UI 업데이트
function updateDashboardUI() {
    if (!dashboardData) return;

    // 건강 점수 업데이트
    const scoreElement = document.querySelector('.score-badge');
    const statusElement = document.querySelector('.score-status');
    if (scoreElement && statusElement) {
        scoreElement.textContent = `건강 점수 ${dashboardData.health_score.score}점`;
        statusElement.textContent = `(${dashboardData.health_score.status})`;
    }

    // 건강 인사이트 업데이트
    const insightItems = document.querySelectorAll('.insight-item');
    dashboardData.insights.forEach((insight, index) => {
        if (insightItems[index]) {
            insightItems[index].textContent = insight;
        }
    });

    // 건강 지표 업데이트
    updateHealthMetrics();
    
    // 복약 정보 업데이트
    updateMedicationInfo();
    
    // 분석 결과 업데이트
    updateAnalysisResult();
    
    // 트렌드 데이터 업데이트
    updateTrendsData();
}

// 건강 지표 업데이트
function updateHealthMetrics() {
    const { health_metrics } = dashboardData;
    
    // 혈압 데이터
    const bpValueElement = document.querySelector('#blood-pressure-data .metric-value');
    const bpStatusElement = document.querySelector('#blood-pressure-data .metric-status');
    if (bpValueElement && bpStatusElement) {
        bpValueElement.textContent = `${health_metrics.blood_pressure.systolic} / ${health_metrics.blood_pressure.diastolic} mmHg`;
        bpStatusElement.textContent = health_metrics.blood_pressure.status;
    }
    
    // 혈당 데이터
    const bsValueElement = document.querySelector('#blood-sugar-data .metric-value');
    const bsStatusElement = document.querySelector('#blood-sugar-data .metric-status');
    if (bsValueElement && bsStatusElement) {
        bsValueElement.textContent = `${health_metrics.blood_sugar.glucose} mg/dL`;
        bsStatusElement.textContent = health_metrics.blood_sugar.status;
    }
}

// 복약 정보 업데이트
function updateMedicationInfo() {
    const { medication } = dashboardData;
    const medicationContainer = document.querySelector('.medication .card-content');
    
    if (!medicationContainer) return;
    
    // 기존 복약 아이템 제거 (next-alarm 제외)
    const existingItems = medicationContainer.querySelectorAll('.medication-item');
    existingItems.forEach(item => item.remove());
    
    // 새 복약 아이템 추가
    medication.medications.forEach(med => {
        const medItem = document.createElement('div');
        medItem.className = 'medication-item';
        medItem.innerHTML = `
            <div class="med-time">${med.time}</div>
            <div class="med-name">${med.name}</div>
            <div class="med-status ${med.is_completed ? 'completed' : 'pending'}">
                ${med.is_completed ? '🟢' : '🔴'}
            </div>
        `;
        medicationContainer.insertBefore(medItem, medicationContainer.querySelector('.next-alarm'));
    });
    
    // 다음 알림 시간 업데이트
    const nextAlarmElement = medicationContainer.querySelector('.next-alarm small');
    if (nextAlarmElement && medication.next_alarm) {
        nextAlarmElement.textContent = `다음 알림까지 ${medication.next_alarm} 남음`;
    }
}

// 분석 결과 업데이트
function updateAnalysisResult() {
    const { analysis } = dashboardData;
    const titleElement = document.querySelector('.analysis-title');
    const resultElement = document.querySelector('.analysis-result');
    
    if (titleElement && resultElement) {
        titleElement.textContent = analysis.title;
        resultElement.textContent = analysis.message;
        resultElement.className = `analysis-result ${analysis.status}`;
    }
}

// 트렌드 데이터 업데이트
function updateTrendsData() {
    const { trends } = dashboardData;
    
    // 수면 데이터
    const sleepValueElement = document.querySelector('#sleep-data .trend-value');
    const sleepChangeElement = document.querySelector('#sleep-data .trend-change');
    if (sleepValueElement && sleepChangeElement) {
        sleepValueElement.textContent = trends.sleep.average;
        sleepChangeElement.textContent = `⬇ 감소 (−${trends.sleep.change_amount})`;
        sleepChangeElement.className = `trend-change ${trends.sleep.change}`;
    }
    
    // 체중 데이터
    const weightValueElement = document.querySelector('#weight-data .trend-value');
    const weightChangeElement = document.querySelector('#weight-data .trend-change');
    if (weightValueElement && weightChangeElement) {
        weightValueElement.textContent = trends.weight.current;
        weightChangeElement.textContent = `➖ ${trends.weight.status}`;
        weightChangeElement.className = `trend-change ${trends.weight.change}`;
    }
}

// 슬라이드 자동 전환
let currentSlide = 1;
let slideInterval;

function showSlide(slideNumber) {
    // 모든 슬라이드 숨기기
    document.querySelectorAll('.slide').forEach(slide => {
        slide.classList.remove('active');
    });
    
    // 모든 인디케이터 비활성화
    document.querySelectorAll('.indicator').forEach(indicator => {
        indicator.classList.remove('active');
    });
    
    // 선택된 슬라이드와 인디케이터 활성화
    document.querySelector(`[data-slide="${slideNumber}"]`).classList.add('active');
    document.querySelector(`.indicator[data-slide="${slideNumber}"]`).classList.add('active');
    
    currentSlide = slideNumber;
}

function nextSlide() {
    const nextSlideNumber = currentSlide === 1 ? 2 : 1;
    showSlide(nextSlideNumber);
}

function startSlideShow() {
    slideInterval = setInterval(nextSlide, 10000); // 10초마다 전환
}

function stopSlideShow() {
    if (slideInterval) {
        clearInterval(slideInterval);
    }
}

// 인디케이터 클릭 이벤트
document.querySelectorAll('.indicator').forEach(indicator => {
    indicator.addEventListener('click', () => {
        const slideNumber = parseInt(indicator.getAttribute('data-slide'));
        showSlide(slideNumber);
        
        // 자동 슬라이드 재시작
        stopSlideShow();
        startSlideShow();
    });
});

// 건강 지표 선택 변경
document.getElementById('health-metric-select').addEventListener('change', function() {
    const selectedMetric = this.value;
    
    // 모든 지표 데이터 숨기기
    document.querySelectorAll('.metric-data').forEach(data => {
        data.classList.remove('active');
    });
    
    // 선택된 지표 데이터 보이기
    document.getElementById(`${selectedMetric}-data`).classList.add('active');
});

// 트렌드 선택 변경
document.getElementById('trend-select').addEventListener('change', function() {
    const selectedTrend = this.value;
    
    // 모든 트렌드 데이터 숨기기
    document.querySelectorAll('.trend-data').forEach(data => {
        data.classList.remove('active');
    });
    
    // 선택된 트렌드 데이터 보이기
    document.getElementById(`${selectedTrend}-data`).classList.add('active');
});

// 마우스 호버 시 슬라이드 일시정지
document.getElementById('hero-slider').addEventListener('mouseenter', stopSlideShow);
document.getElementById('hero-slider').addEventListener('mouseleave', startSlideShow);

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    updateDateTime();
    updateWeatherInfo();
    loadDashboardData();
    startSlideShow();
    
    // 1분마다 시간 업데이트
    setInterval(updateDateTime, 60000);
    
    // 5분마다 대시보드 데이터 업데이트
    setInterval(loadDashboardData, 300000);
});

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', function() {
    stopSlideShow();
});