let selectedDiseases = [];
let allergyIndex = 0;
let medIndex = 0;
let chronicList = [];
let toastTimer = null;
let health_change_cnt = 0;

function showToast(message, type = "info") {
  const toast = document.getElementById("health-toast");
  if (!toast) return;

  toast.textContent = message;
  toast.className = `health-toast ${type} show`;

  if (toastTimer) clearTimeout(toastTimer);

  toastTimer = setTimeout(() => {
    toast.className = "health-toast";
  }, 2200);
}

function openConfirmModal(message = "건강정보를 저장하시겠습니까?") {
  return window.showAppConfirm(message, null, null, "건강정보 저장");
}

// 탭 전환 함수
function switchHealthTab(tabName, element) {
  document.querySelectorAll('.health-tab').forEach(tab => {
    tab.classList.remove('is-active');
  });

  document.querySelectorAll('.health-panel').forEach(panel => {
    panel.classList.remove('active');
  });

  element.classList.add('is-active');
  document.getElementById(`health-tab-${tabName}`).classList.add('active');

  const guideBox = document.querySelector('.med-guide-box');
  if (guideBox) {
    if (tabName === 'medication') {
      guideBox.classList.add('open');
    } else {
      guideBox.classList.remove('open');
    }
  }
}

// 공통 API 요청 함수
async function fetchWithAuth(url, options = {}) {
  let accessToken = localStorage.getItem("access_token");

  if (!options.headers) options.headers = {};

  if (accessToken) {
    options.headers["Authorization"] = `Bearer ${accessToken}`;
  }

  let response = await fetch(url, options);

  if (response.status === 401) {
    console.log("액세스 토큰 만료, 갱신 시도 중...");
    const refreshResponse = await fetch('/api/v1/auth/token/refresh', { method: 'GET' });

    if (refreshResponse.ok) {
      const result = await refreshResponse.json();
      accessToken = result.access_token;
      localStorage.setItem("access_token", accessToken);
      options.headers["Authorization"] = `Bearer ${accessToken}`;
      response = await fetch(url, options);
    } else {
      showToast("세션이 만료되었습니다. 다시 로그인해주세요.", "error");
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_id");
      location.href = "/login";
      return null;
    }
  }

  return response;
}

// 흡연/음주 필드 토글
function toggleSmokingFields() {
  const smokingStatus = document.querySelector("[name='smoking_status']")?.value;
  const smokingYears = document.querySelector("[name='smoking_years']");
  const smokingPerWeek = document.querySelector("[name='smoking_per_week']");
  const isDisabled = smokingStatus === "비흡연";

  if (smokingYears) {
    smokingYears.disabled = isDisabled;
    if (isDisabled) smokingYears.value = "";
  }

  if (smokingPerWeek) {
    smokingPerWeek.disabled = isDisabled;
    if (isDisabled) smokingPerWeek.value = "";
  }
}

function markHealthChanged() {
  health_change_cnt++;
}

function toggleDrinkingFields() {
  const drinkingStatus = document.querySelector("[name='drinking_status']")?.value;
  const drinkingYears = document.querySelector("[name='drinking_years']");
  const drinkingPerWeek = document.querySelector("[name='drinking_per_week']");
  const isDisabled = drinkingStatus === "비음주";

  if (drinkingYears) {
    drinkingYears.disabled = isDisabled;
    if (isDisabled) drinkingYears.value = "";
  }

  if (drinkingPerWeek) {
    drinkingPerWeek.disabled = isDisabled;
    if (isDisabled) drinkingPerWeek.value = "";
  }
}

// 탭 이동 헬퍼
function activateHealthTab(tabName) {
  const targetTab = document.querySelector(`.health-tab[data-tab="${tabName}"]`);
  if (targetTab) {
    switchHealthTab(tabName, targetTab);
    targetTab.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

// 공통 테이블 행 삭제
function removeTableRow(button) {
  const row = button.closest('tr');
  if (row) {
    row.remove();
    markHealthChanged();
  }
}

// 데이터 렌더링
function renderChronicDiseases(list) {
  list.forEach(item => {
    chronicList.push({
      name: item.disease_name,
      when_to_diagnose: item.when_to_diagnose
    });
  });
  renderChronic();
}

function renderAllergies(list) {
  const tbody = document.getElementById("allergy-tbody");
  if (!tbody) return;

  list.forEach(item => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>
        <select class="allergie_type" name="allergies[${allergyIndex}][category]">
          <option style="display:none;">종류 선택</option>
          <option ${item.allergy_type == '약물' ? 'selected' : ''}>약물</option>
          <option ${item.allergy_type == '음식' ? 'selected' : ''}>음식</option>
          <option ${item.allergy_type == '기타' ? 'selected' : ''}>기타</option>
        </select>
      </td>
      <td>
        <input type="text" class="allergie_name" name="allergies[${allergyIndex}][allergy_name]" placeholder="예: 아스피린, 복숭아" value="${item.allergy_name || ''}">
      </td>
      <td>
        <input type="text" class="allergie_status" name="allergies[${allergyIndex}][symptom]" placeholder="예: 두드러기, 호흡곤란" value="${item.symptom || ''}">
      </td>
      <td>
        <button type="button" class="delete-btn" onclick="removeTableRow(this)">×</button>
      </td>
    `;

    tbody.appendChild(tr);
    allergyIndex++;
  });
}

function renderMedications(list) {
  const container = document.querySelector("#med-container tbody");
  if (!container) return;

  list.forEach(med => {
    let t = '';
    t += '<tr>';
    t += `<td><input type="text" class="med_name" placeholder="약물이름" value="${med.medication_name || ''}"></td>`;
    t += `<td><input type="text" class="med_dose" placeholder="500mg" value="${med.one_dose_amount || ''}"></td>`;
    t += `<td><input type="text" class="med_count" placeholder="1정" value="${med.one_dose_count || ''}"></td>`;
    t += `<td><input type="text" class="med_days" placeholder="3일" value="${med.total_days || ''}"></td>`;
    t += `<td><input type="text" class="med_instructions" placeholder="식후 30분" value="${med.instructions || ''}"></td>`;
    t += '<td><button type="button" class="delete-btn">×</button></td>';
    t += '</tr>';

    container.insertAdjacentHTML('beforeend', t);

    const newRow = container.lastElementChild;
    newRow.querySelector(".delete-btn").addEventListener("click", (e) => {
      e.target.closest('tr').remove();
      markHealthChanged();
    });
  });
}

function renderHealthProfile(data) {
  const profile = data.health_profile;

  chronicList = [];
  const selectedDiseasesEl = document.getElementById("selected-diseases");
  const allergyTbody = document.getElementById("allergy-tbody");
  const medTbody = document.querySelector("#med-container tbody");

  if (selectedDiseasesEl) selectedDiseasesEl.innerHTML = "";
  if (allergyTbody) allergyTbody.innerHTML = "";
  if (medTbody) medTbody.innerHTML = "";

  allergyIndex = 0;

  if (profile) {
    document.querySelector("[name='family_history']").value = profile.family_history ?? "";
    document.querySelector("[name='family_history_note']").value = profile.family_history_note ?? "";
    document.querySelector("[name='height_cm']").value = profile.height_cm ?? "";
    document.querySelector("[name='weight_kg']").value = profile.weight_kg ?? "";
    document.querySelector("[name='weight_change']").value = profile.weight_change ?? "";
    document.querySelector("[name='sleep_change']").value = profile.sleep_change ?? "";
    document.querySelector("[name='sleep_hours']").value = profile.sleep_hours ?? "";
    document.querySelector("[name='smoking_status']").value = profile.smoking_status ?? "";
    document.querySelector("[name='smoking_years']").value = profile.smoking_years ?? "";
    document.querySelector("[name='smoking_per_week']").value = profile.smoking_per_week ?? "";
    document.querySelector("[name='drinking_status']").value = profile.drinking_status ?? "";
    document.querySelector("[name='drinking_years']").value = profile.drinking_years ?? "";
    document.querySelector("[name='drinking_per_week']").value = profile.drinking_per_week ?? "";
    document.querySelector("[name='exercise_frequency']").value = profile.exercise_frequency ?? "";
    document.querySelector("[name='diet_type']").value = profile.diet_type ?? "";
  }

  renderChronicDiseases(data.chronic_diseases || []);
  renderAllergies(data.allergies || []);
  renderMedications(data.current_meds || []);

  toggleSmokingFields();
  toggleDrinkingFields();
}

// 만성질환
function renderChronic() {
  const selectedContainer = document.getElementById("selected-diseases");
  const hiddenInput = document.getElementById("chronic-hidden");
  if (!selectedContainer || !hiddenInput) return;

  selectedContainer.innerHTML = "";

  chronicList.forEach((item, index) => {
    const tag = document.createElement("div");
    tag.className = "selected-tag";
    tag.innerHTML = `
      <span>${item.name}</span>
      <select onchange="updateDiagnose(${index}, this.value)">
        <option style="display:none;">진단시기 선택</option>
        <option ${item.when_to_diagnose == "1년 이내" ? 'selected' : ''}>1년 이내</option>
        <option ${item.when_to_diagnose == "5년 이내" ? 'selected' : ''}>5년 이내</option>
        <option ${item.when_to_diagnose == "10년 이상" ? 'selected' : ''}>10년 이상</option>
        <option ${item.when_to_diagnose == "알수없음" ? 'selected' : ''}>알수없음</option>
      </select>
      <span class="remove-btn" onclick="removeChronic(${index})">×</span>
    `;
    selectedContainer.appendChild(tag);
  });

  hiddenInput.value = JSON.stringify(chronicList);
}

function addChronic(name) {
  if (chronicList.some(item => item.name === name)) return;
  chronicList.push({ name, when_to_diagnose: "" });
  renderChronic();
}

function removeChronic(index) {
  chronicList.splice(index, 1);
  renderChronic();
  markHealthChanged();
}

function updateDiagnose(index, value) {
  chronicList[index].when_to_diagnose = value;
  const hiddenInput = document.getElementById("chronic-hidden");
  if (hiddenInput) {
    hiddenInput.value = JSON.stringify(chronicList);
    markHealthChanged();
  }
}

// 알레르기 추가
function addAllergy() {
  const tbody = document.getElementById("allergy-tbody");
  if (!tbody) return;

  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>
      <select class="allergie_type" name="allergies[${allergyIndex}][category]">
        <option style="display:none;">종류 선택</option>
        <option>약물</option>
        <option>음식</option>
        <option>기타</option>
      </select>
    </td>
    <td>
      <input type="text" class="allergie_name" name="allergies[${allergyIndex}][allergy_name]" placeholder="예: 아스피린, 복숭아">
    </td>
    <td>
      <input type="text" class="allergie_status" name="allergies[${allergyIndex}][symptom]" placeholder="예: 두드러기, 호흡곤란">
    </td>
    <td>
      <button type="button" class="delete-btn" onclick="removeTableRow(this)">×</button>
    </td>
  `;

  tbody.appendChild(tr);
  allergyIndex++;
  markHealthChanged();
}

// 약 추가
function addMed() {
  const container = document.querySelector("#med-container tbody");
  if (!container) return;

  let t = '';
  t += '<tr>';
  t += '<td><input type="text" class="med_name" placeholder="약물이름"></td>';
  t += '<td><input type="text" class="med_dose" placeholder="500mg"></td>';
  t += '<td><input type="text" class="med_count" placeholder="1정"></td>';
  t += '<td><input type="text" class="med_days" placeholder="3일"></td>';
  t += '<td><input type="text" class="med_instructions" placeholder="식후 30분"></td>';
  t += '<td><button type="button" class="delete-btn">×</button></td>';
  t += '</tr>';

  container.insertAdjacentHTML('beforeend', t);

  const newRow = container.lastElementChild;
  newRow.querySelector(".delete-btn").addEventListener("click", (e) => {
    e.target.closest('tr').remove();
    markHealthChanged();
  });
  markHealthChanged();
}

// 검증
function validateAllergies() {
  const rows = document.querySelectorAll("#allergy-tbody tr");

  for (const tr of rows) {
    const type = tr.querySelector(".allergie_type")?.value;
    const name = tr.querySelector(".allergie_name")?.value?.trim();
    const symptom = tr.querySelector(".allergie_status")?.value?.trim();

    const hasAnyValue = !!(
      (type && type !== "종류 선택") ||
      (name && name.length > 0) ||
      symptom
    );

    if (hasAnyValue) {
      if (!type || type === "종류 선택") {
        activateHealthTab("allergy");
        showToast("알레르기 분류를 선택해주세요.", "error");
        return false;
      }

      if (!name) {
        activateHealthTab("allergy");
        showToast("알레르기 성분/명칭을 입력해주세요.", "error");
        return false;
      }
    }
  }

  return true;
}

function validateChronicDiseases() {
  for (const item of chronicList) {
    if (!item.when_to_diagnose) {
      activateHealthTab("allergy");
      showToast(`질환 "${item.name}"의 진단시기를 선택해주세요.`, "error");
      return false;
    }
  }
  return true;
}

function validateMedications() {
  const rows = document.querySelectorAll("#med-container tbody tr");

  for (const tr of rows) {
    const name = tr.querySelector(".med_name")?.value?.trim();
    const dose = tr.querySelector(".med_dose")?.value?.trim();
    const doseCount = tr.querySelector(".med_count")?.value?.trim();
    const days = tr.querySelector(".med_days")?.value?.trim();
    const instructions = tr.querySelector(".med_instructions")?.value?.trim();

    const hasAnyValue = !!(name || dose || doseCount || days || instructions);

    if (hasAnyValue && !name) {
      activateHealthTab("medication");
      showToast("약물명을 입력해주세요.", "error");
      return false;
    }
  }

  return true;
}

// 저장
async function handleSaveHealthProfile() {
  const familyHistory = document.querySelector("[name='family_history']").value;
  const height = document.querySelector("[name='height_cm']").value;
  const weight = document.querySelector("[name='weight_kg']").value;
  const weightChange = document.querySelector("[name='weight_change']").value;
  const sleepHours = document.querySelector("[name='sleep_hours']").value;
  const sleepChange = document.querySelector("[name='sleep_change']").value;
  const smokingStatus = document.querySelector("[name='smoking_status']").value;
  const drinkingStatus = document.querySelector("[name='drinking_status']").value;
  const exercise = document.querySelector("[name='exercise_frequency']").value;
  const diet = document.querySelector("[name='diet_type']").value;

  if (familyHistory !== "없음" && familyHistory !== "모름") {
    const familyHistoryNote = document.querySelector("[name='family_history_note']").value.trim();
    if (!familyHistoryNote) {
      activateHealthTab("profile");
      showToast("가족력이 있을 경우 내용을 입력해주세요.", "error");
      return;
    }
  }

  if (!height) {
    activateHealthTab("profile");
    showToast("신장 (cm)을 입력해주세요.", "error");
    return;
  }

  if (!sleepHours) {
    activateHealthTab("profile");
    showToast("수면 시간(시간)을 입력해주세요.", "error");
    return;
  }

  if (!weight) {
    activateHealthTab("profile");
    showToast("체중 (kg)을 입력해주세요.", "error");
    return;
  }

  const requiredFields = [
    { value: weightChange, message: "최근 체중 변화를 선택해주세요." },
    { value: sleepChange, message: "최근 수면 시간 변화를 선택해주세요." },
    { value: smokingStatus, message: "흡연 상태를 선택해주세요." },
    { value: drinkingStatus, message: "음주 상태를 선택해주세요." },
    { value: exercise, message: "운동 빈도를 선택해주세요." },
    { value: diet, message: "식습관을 선택해주세요." }
  ];

  for (const field of requiredFields) {
    if (!field.value || field.value.includes("선택")) {
      activateHealthTab("profile");
      showToast(field.message, "error");
      return;
    }
  }

  if (!validateAllergies()) return;
  if (!validateChronicDiseases()) return;
  if (!validateMedications()) return;

  const finalConfirm = await openConfirmModal("건강정보를 저장하시겠습니까?");
  if (!finalConfirm) return;

  const allergies = [];
  document.querySelectorAll("#allergy-tbody tr").forEach(tr => {
    const type = tr.querySelector(".allergie_type").value;
    const name = tr.querySelector(".allergie_name").value.trim();
    const symptom = tr.querySelector(".allergie_status").value.trim();

    if (type && type !== "종류 선택" && name) {
      allergies.push({
        allergy_type: type,
        allergy_name: name,
        symptom: symptom || null
      });
    }
  });

  const medications = [];
  document.querySelectorAll("#med-container tbody tr").forEach(tr => {
    const name = tr.querySelector(".med_name").value.trim();
    const oneDose = tr.querySelector(".med_dose").value.trim();
    const oneDoseCount = tr.querySelector(".med_count").value.trim();
    const days = tr.querySelector(".med_days").value.trim();
    const instructions = tr.querySelector(".med_instructions").value.trim();

    if (name) {
      medications.push({
        medication_name: name,
        one_dose_amount: oneDose || null,
        one_dose_count: oneDoseCount || null,
        total_days: days || null,
        instructions: instructions || null
      });
    }
  });

  const safeParseFloat = (selector) => {
    const val = document.querySelector(selector)?.value;
    return (val !== undefined && val !== "") ? parseFloat(val) : null;
  };

  const safeParseInt = (selector) => {
    const val = document.querySelector(selector)?.value;
    return (val !== undefined && val !== "") ? parseInt(val) : null;
  };

  const data = {
    family_history: familyHistory,
    family_history_note: document.querySelector("[name='family_history_note']").value.trim() || null,
    height_cm: safeParseFloat("[name='height_cm']"),
    weight_kg: safeParseFloat("[name='weight_kg']"),
    weight_change: weightChange,
    sleep_change: sleepChange,
    sleep_hours: safeParseFloat("[name='sleep_hours']"),
    smoking_status: smokingStatus,
    smoking_years: safeParseInt("[name='smoking_years']"),
    smoking_per_week: safeParseFloat("[name='smoking_per_week']"),
    drinking_status: drinkingStatus,
    drinking_years: safeParseInt("[name='drinking_years']"),
    drinking_per_week: safeParseFloat("[name='drinking_per_week']"),
    exercise_frequency: exercise,
    diet_type: diet,
    allergies,
    chronic_diseases: chronicList,
    medications
  };

  const response = await fetchWithAuth("/api/v1/health", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });

  if (!response) return;

  if (response.ok) {
    showToast("건강정보가 저장되었습니다.", "success");
    health_change_cnt = 0; // Reset after manual save
  } else {
    const errorText = await response.text();
    console.error("건강정보 저장 실패:", errorText);
    showToast("건강정보 저장에 실패했습니다.", "error");
  }
}

// 초기화
document.addEventListener("DOMContentLoaded", async () => {
  const customInput = document.getElementById("custom-disease-input");
  const saveBtn = document.querySelector(".save-btn");

  document.querySelectorAll(".disease-option").forEach(option => {
    option.addEventListener("click", () => {
      addChronic(option.dataset.value);
    });
  });

  if (customInput) {
    customInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        const value = this.value.trim();
        if (value) {
          addChronic(value);
          this.value = "";
        }
      }
    });
  }

  document.querySelector("[name='family_history']")?.addEventListener("change", (e) => {
    if (e.target.value === '없음' || e.target.value === '모름') {
      document.querySelector("[name='family_history_note']").value = '';
    }
  });

  document.querySelector("[name='smoking_status']")?.addEventListener("change", () => {
    toggleSmokingFields();
  });

  document.querySelector("[name='drinking_status']")?.addEventListener("change", () => {
    toggleDrinkingFields();
  });

  if (saveBtn) {
    saveBtn.addEventListener("click", handleSaveHealthProfile);
  }

  const token = localStorage.getItem("access_token");
  if (token) {
    try {
      const healthRes = await fetchWithAuth(`/api/v1/health`, { method: 'GET' });
      if (!healthRes || !healthRes.ok) throw new Error("Fetch failed");
      const health = await healthRes.json();
      renderHealthProfile(health);
    } catch (err) {
      console.error('건강 데이터 로드 실패:', err);
    }
  }

  toggleSmokingFields();
  toggleDrinkingFields();

  // Track all input changes
  document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('change', markHealthChanged);
  });
});

window.addEventListener('pagehide', () => {
    if (health_change_cnt > 0) {
        const accessToken = localStorage.getItem("access_token");
        const headers = { "Content-Type": "application/json" };
        if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

        fetch("/api/v1/guides/refresh", {
            method: "POST",
            headers: headers,
            keepalive: true
        });
        health_change_cnt = 0;
    }
});
