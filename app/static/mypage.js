function mypageToast(type, message) {
  const config = {
    success: { title: "완료", icon: "✅" },
    error: { title: "오류", icon: "⚠️" },
    info: { title: "안내", icon: "ℹ️" },
    warn: { title: "주의", icon: "⚠️" }
  };

  const toast = config[type] || config.info;

  const toastEl = document.getElementById('app-toast');
  const badgeEl = document.getElementById('app-toast-badge');
  const titleEl = document.getElementById('app-toast-title');
  const messageEl = document.getElementById('app-toast-message');
  const closeBtn = document.getElementById('app-toast-close');

  if (!toastEl || !badgeEl || !titleEl || !messageEl) {
    alert(message);
    return;
  }

  badgeEl.textContent = toast.icon;
  titleEl.textContent = toast.title;
  messageEl.textContent = message;

  toastEl.classList.remove('hide');
  toastEl.classList.add('show');

  if (toastEl.__hideTimer) {
    clearTimeout(toastEl.__hideTimer);
  }

  toastEl.__hideTimer = setTimeout(() => {
    toastEl.classList.remove('show');
    toastEl.classList.add('hide');
  }, 2600);

  if (closeBtn && !closeBtn.__mypageToastBound) {
    closeBtn.addEventListener('click', () => {
      if (toastEl.__hideTimer) clearTimeout(toastEl.__hideTimer);
      toastEl.classList.remove('show');
      toastEl.classList.add('hide');
    });
    closeBtn.__mypageToastBound = true;
  }
}

function syncAlarmToggleUI() {
  const checkbox = document.getElementById("alarm_tf_checkbox");
  const toggleBtn = document.getElementById("alarm-toggle-btn");
  const statusText = document.getElementById("alarm-toggle-status");

  if (!checkbox || !toggleBtn || !statusText) return;

  const isOn = checkbox.checked;
  toggleBtn.classList.toggle("is-on", isOn);
  toggleBtn.setAttribute("aria-pressed", isOn ? "true" : "false");
  statusText.textContent = isOn ? "ON" : "OFF";
  statusText.style.color = isOn ? "#4f46e5" : "#94a3b8";
}

function bindAlarmToggle() {
  const checkbox = document.getElementById("alarm_tf_checkbox");
  const toggleBtn = document.getElementById("alarm-toggle-btn");

  if (!checkbox || !toggleBtn || toggleBtn.dataset.bound === "true") return;

  toggleBtn.addEventListener("click", async () => {
    const prevValue = checkbox.checked;
    const newValue = !prevValue;

    checkbox.checked = newValue;
    syncAlarmToggleUI();

    try {
      const response = await fetchWithAuth('/api/v1/users/me/alarm-toggle', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alarm_tf: newValue })
      });

      if (!response || !response.ok) {
        const errorText = response ? await response.text() : '';
        console.error('alarm toggle failed:', response?.status, errorText);

        checkbox.checked = prevValue;
        syncAlarmToggleUI();
        mypageToast('error', '알람 전체 설정 변경에 실패했습니다.');
        return;
      }

      const result = await response.json().catch(() => null);

      if (result && typeof result.alarm_tf === 'boolean') {
        checkbox.checked = result.alarm_tf;
      } else {
        checkbox.checked = newValue;
      }

      syncAlarmToggleUI();
      mypageToast(
        'success',
        checkbox.checked ? '전체 알람이 활성화되었습니다.' : '전체 알람이 비활성화되었습니다.'
      );
    } catch (error) {
      console.error(error);
      checkbox.checked = prevValue;
      syncAlarmToggleUI();
      mypageToast('error', '알람 전체 설정 변경 중 문제가 발생했습니다.');
    }
  });

  toggleBtn.dataset.bound = "true";
}

function setMyPageMode(mode) {
  const mainPanel = document.querySelector(".mypage_container .mypage");
  const passwordPanel = document.querySelector(".mypage_container .password-chenge");
  const withdrawPanel = document.querySelector(".mypage_container .user-drop");

  const mainTab = document.querySelector(".mypage-mode-main");
  const passwordTabs = document.querySelectorAll(".password-chenge-move");
  const withdrawTabs = document.querySelectorAll(".user-drop-move");

  const headerAccount = document.getElementById("mypage-header-account");
  const headerSecurity = document.getElementById("mypage-header-security");

  [mainTab, ...passwordTabs, ...withdrawTabs].forEach((btn) => {
    if (btn && btn.classList.contains("mypage-mode-tab")) {
      btn.classList.remove("is-active");
    }
  });

  if (headerAccount) headerAccount.classList.remove("is-active");
  if (headerSecurity) headerSecurity.classList.remove("is-active");

  mainPanel.classList.remove("open");
  passwordPanel.classList.remove("open");
  withdrawPanel.classList.remove("open");

  if (mode === "main") {
    mainPanel.classList.add("open");
    if (mainTab) mainTab.classList.add("is-active");
    if (headerAccount) headerAccount.classList.add("is-active");
  } else if (mode === "password") {
    passwordPanel.classList.add("open");
    passwordTabs.forEach((btn) => {
      if (btn.classList.contains("mypage-mode-tab")) btn.classList.add("is-active");
    });
    if (headerSecurity) headerSecurity.classList.add("is-active");
  } else if (mode === "withdraw") {
    withdrawPanel.classList.add("open");
    withdrawTabs.forEach((btn) => {
      if (btn.classList.contains("mypage-mode-tab")) btn.classList.add("is-active");
    });
    if (headerSecurity) headerSecurity.classList.add("is-active");
  }
}

window.onload = async () => {
  try {
    const response = await fetchWithAuth(`/api/v1/users/me`, {
      method: 'GET'
    });
    if (!response || !response.ok) throw new Error("Fetch failed");
    const user = await response.json();

    document.querySelector('.mypage_container .id').value = user.id;
    document.querySelector('.mypage_container .name').value = user.name;
    document.querySelector('.mypage_container .nickname').value = user.nickname;
    document.querySelector('.mypage_container .phone_number').value = user.phone_number;
    document.querySelector('.mypage_container .birthday').value = user.birthday;
    document.querySelector('.mypage_container .gender').value = user.gender;
    document.getElementById('alarm_tf_checkbox').checked = user.alarm_tf !== false;

    document.querySelector('.mypage_container .is_terms_agreed').checked = user.is_terms_agreed;
    document.querySelector('.mypage_container .is_privacy_agreed').checked = user.is_privacy_agreed;
    document.querySelector('.mypage_container .is_marketing_agreed').checked = user.is_marketing_agreed;
    document.querySelector('.mypage_container .is_alarm_agreed').checked = user.is_alarm_agreed;

    syncAlarmToggleUI();
    bindAlarmToggle();
    setMyPageMode('main');
  } catch (e) {
    console.error(e);
  }
};

document.getElementById('profileForm').onsubmit = async (e) => {
  e.preventDefault();
  const data = {
    nickname: document.getElementById('nickname').value,
    phone_number: document.getElementById('phone_number').value,
    birthday: document.getElementById('birthday').value,
    gender: document.getElementById('gender').value,
    alarm_tf: document.getElementById('alarm_tf_checkbox').checked,
    is_marketing_agreed: document.getElementById('is_marketing_agreed').checked,
    is_alarm_agreed: document.getElementById('is_alarm_agreed').checked,
  };

  const response = await fetchWithAuth('/api/v1/users/me', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  if (response && response.ok) mypageToast("success", "회원 정보가 수정되었습니다.");
  else if (response) mypageToast("error", "회원 정보 수정에 실패했습니다.");
};

async function changePassword() {
  const oldPassword = document.getElementById('old_password').value;
  const newPassword = document.getElementById('new_password').value;
  const id = document.getElementById('id').value;

  if (!oldPassword || !newPassword) {
    mypageToast("info", "비밀번호를 모두 입력해주세요.");
    return;
  }

  const response = await fetchWithAuth('/api/v1/users/me/password', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      old_password: oldPassword,
      new_password: newPassword,
      id: id
    })
  });

  if (response && response.ok) {
    mypageToast("success", "비밀번호가 변경되었습니다.");
    document.getElementById('old_password').value = "";
    document.getElementById('new_password').value = "";
    setMyPageMode('main');
  } else if (response) {
    const err = await response.json();
    mypageToast("error", "변경 실패: " + (err.detail || "정보를 확인해주세요."));
  }
}

async function withdraw() {
  const password = document.getElementById('delete_password').value;
  if (!password) {
    mypageToast("info", "비밀번호를 입력해주세요.");
    return;
  }

  if (confirm("정말로 탈퇴하시겠습니까? 데이터는 복구되지 않습니다.")) {
    const response = await fetchWithAuth('/api/v1/users/me', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password })
    });

    if (response && response.ok) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_id");
      mypageToast("success", "회원 탈퇴가 완료되었습니다.");
      setTimeout(() => {
        location.href = "/";
      }, 700);
    } else if (response) {
      mypageToast("error", "비밀번호가 올바르지 않습니다.");
    }
  }
}

document.querySelectorAll(".mypage_container .mypage-move").forEach((item) => {
  item.addEventListener("click", () => setMyPageMode('main'));
});

document.querySelectorAll(".password-chenge-move").forEach((item) => {
  item.addEventListener("click", () => setMyPageMode('password'));
});

document.querySelectorAll(".user-drop-move").forEach((item) => {
  item.addEventListener("click", () => setMyPageMode('withdraw'));
});

document.querySelector(".mypage-mode-main").addEventListener("click", () => {
  setMyPageMode('main');
});
