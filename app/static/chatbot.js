// 챗봇 상태 관리
const chatbot = {
  isOpen: false,
  sessionId: localStorage.getItem('chatbot_session_id'),
  messages: [],
};

let isSpeaking = false;
const synthesis = window.speechSynthesis;

// 인증 토큰 가져오기 (통합)
function getAuthToken() {
  return (
    localStorage.getItem('access_token') ||
    localStorage.getItem('auth_token') ||
    ''
  ).trim();
}

// 대화 내역 복원
async function restoreChatHistory() {
  const token = getAuthToken();
  if (!token || !chatbot.sessionId) return;

  try {
    const response = await fetch(`/api/v1/chat/history/${chatbot.sessionId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      console.warn('대화 내역 조회 실패:', response.status);

      // 세션이 유효하지 않으면 localStorage도 정리
      if (response.status === 401 || response.status === 404) {
        chatbot.sessionId = null;
        chatbot.messages = [];
        localStorage.removeItem('chatbot_session_id');
      }

      const messagesContainer = document.getElementById('chatbot-messages');
      if (messagesContainer && messagesContainer.children.length === 0) {
        addMessage('assistant', '안녕하세요! 👋 Cloud9 Care 챗봇입니다. 무엇을 도와드릴까요?');
      }
      return;
    }

    const data = await response.json();
    const messagesContainer = document.getElementById('chatbot-messages');
    if (!messagesContainer) return;

    // 기존 메시지 초기화
    messagesContainer.innerHTML = '';
    chatbot.messages = [];

    if (data.messages && data.messages.length > 0) {
      // 이전 대화 복원
      data.messages.forEach((msg) => {
        addMessage(msg.role, msg.content);
        // Emergency 응답 뒤에 응급 알림 복원
        if (msg.role === 'assistant' && msg.risk_level === 'Emergency') {
          addEmergencyAlert();
        }
      });
    } else {
      // 대화 내역이 없으면 환영 메시지
      addMessage('assistant', '안녕하세요! 👋 Cloud9 Care 챗봇입니다. 무엇을 도와드릴까요?');
    }
  } catch (error) {
    console.error('대화 복원 오류:', error);
    // 오류 시 환영 메시지 표시
    const messagesContainer = document.getElementById('chatbot-messages');
    if (messagesContainer && messagesContainer.children.length === 0) {
      addMessage('assistant', '안녕하세요! 👋 Cloud9 Care 챗봇입니다. 무엇을 도와드릴까요?');
    }
  }
}

// 챗봇 초기화
function initChatbot() {
  const button = document.getElementById('chatbot-button');
  const container = document.getElementById('chatbot-container');
  const closeBtn = document.getElementById('chatbot-close');
  const endBtn = document.getElementById('chatbot-end');
  const ttsBtn = document.getElementById('chatbot-tts');
  const sendBtn = document.getElementById('chatbot-send');
  const input = document.getElementById('chatbot-input');

  // 요소가 없으면 초기화 스킵
  if (!button || !container || !closeBtn || !endBtn || !ttsBtn || !sendBtn || !input) {
    console.warn('[Chatbot] Required elements not found, skipping initialization');
    return;
  }

  // 챗봇 열기/닫기
  button.addEventListener('click', () => { toggleChatbot(); });
  closeBtn.addEventListener('click', () => { toggleChatbot(); });

  // 챗 종료
  endBtn.addEventListener('click', endChat);

  // TTS 읽어주기
  ttsBtn.addEventListener('click', readLastMessage);

  // 메시지 전송
  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // 초기 환영 메시지 (세션이 없고 메시지 창이 비어있을 때만)
  if (!chatbot.sessionId) {
    const messagesContainer = document.getElementById('chatbot-messages');
    if (messagesContainer && messagesContainer.children.length === 0) {
      addMessage('assistant', '안녕하세요! 👋 Cloud9 Care 챗봇입니다. 무엇을 도와드릴까요?');
    }
  }
}

// 챗봇 토글
async function toggleChatbot() {
  const container = document.getElementById('chatbot-container');
  if (!container) return;

  chatbot.isOpen = !chatbot.isOpen;

  if (chatbot.isOpen) {
    container.classList.add('open');

    const messagesContainer = document.getElementById('chatbot-messages');
    if (!messagesContainer) return;

    // 화면에 아직 메시지가 없고, 세션이 있으면 복원 시도
    if (chatbot.sessionId && chatbot.messages.length === 0) {
      await restoreChatHistory();
    }

    // 세션도 없고, 화면도 비어 있으면 환영 메시지
    if (!chatbot.sessionId && messagesContainer.children.length === 0) {
      addMessage('assistant', '안녕하세요! 👋 Cloud9 Care 챗봇입니다. 무엇을 도와드릴까요?');
    }
  } else {
    container.classList.remove('open');
  }
}

// 메시지 전송
async function sendMessage() {
  const input = document.getElementById('chatbot-input');
  if (!input) return;

  const message = input.value.trim();

  if (!message) return;

  // 로그인 토큰 확인
  const token = getAuthToken();
  if (!token) {
    addMessage('assistant', '로그인 후 이용할 수 있는 기능입니다.');
    return;
  }

  // TTS 중단
  if (isSpeaking) {
    synthesis.cancel();
    isSpeaking = false;
    const ttsBtn = document.getElementById('chatbot-tts');
    if (ttsBtn) {
      ttsBtn.textContent = '🔊';
      ttsBtn.style.background = 'none';
    }
  }

  // 사용자 메시지 추가
  addMessage('user', message);
  input.value = '';

  // 로딩 표시
  showTypingIndicator();

  try {
    // API 호출
    const response = await fetch('/api/v1/chat/message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        message: message,
        session_id: chatbot.sessionId,
      }),
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('로그인이 필요합니다.');
      }
      throw new Error('메시지 전송 실패');
    }

    const data = await response.json();

    // 세션 ID 저장
    if (data.session_id) {
      chatbot.sessionId = data.session_id;
      localStorage.setItem('chatbot_session_id', data.session_id);
    }

    // 로딩 제거
    hideTypingIndicator();

    // 봇 응답 추가
    addMessage('assistant', data.assistant_message || '응답을 받지 못했습니다.');

    // 응급 상황 처리 (백엔드와 맞춤)
    if (data.risk_level === 'Emergency') {
      addEmergencyAlert();
    }

  } catch (error) {
    console.error('챗봇 오류:', error);
    hideTypingIndicator();

    const errorMessage = error instanceof Error
      ? error.message
      : '죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요.';

    addMessage('assistant', errorMessage);
  }
}

// 메시지 추가
function addMessage(role, content) {
  const messagesContainer = document.getElementById('chatbot-messages');
  if (!messagesContainer) return;

  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = role === 'user' ? '👤' : '🤖';

  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  contentDiv.textContent = content;

  messageDiv.appendChild(avatar);
  messageDiv.appendChild(contentDiv);

  messagesContainer.appendChild(messageDiv);

  // 스크롤을 최하단으로
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  // 메시지 저장
  chatbot.messages.push({ role, content, timestamp: new Date() });
}

// 타이핑 인디케이터 표시
function showTypingIndicator() {
  const messagesContainer = document.getElementById('chatbot-messages');
  if (!messagesContainer) return;

  const typingDiv = document.createElement('div');
  typingDiv.className = 'message assistant';
  typingDiv.id = 'typing-indicator';

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = '🤖';

  const typingContent = document.createElement('div');
  typingContent.className = 'message-content typing-indicator';
  typingContent.innerHTML = `
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
  `;

  typingDiv.appendChild(avatar);
  typingDiv.appendChild(typingContent);
  messagesContainer.appendChild(typingDiv);

  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 타이핑 인디케이터 제거
function hideTypingIndicator() {
  const indicator = document.getElementById('typing-indicator');
  if (indicator) {
    indicator.remove();
  }
}

// 응급 알림 추가 (종료 버튼을 눌러야만 사라짐)
function addEmergencyAlert() {
  const messagesContainer = document.getElementById('chatbot-messages');
  if (!messagesContainer) return;

  const alertDiv = document.createElement('div');
  alertDiv.className = 'emergency-alert';

  alertDiv.innerHTML = `
    <div class="emergency-alert-header">
      <strong>⚠️ 응급 상황 감지</strong>
      <button class="emergency-alert-close" title="닫기">×</button>
    </div>
    <p>
      즉시 가까운 응급실을 방문하시거나<br>
      119에 연락하시기 바랍니다.
    </p>
  `;

  // 닫기 버튼 이벤트
  alertDiv.querySelector('.emergency-alert-close').addEventListener('click', () => {
    alertDiv.remove();
  });

  messagesContainer.appendChild(alertDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 챗 종료 기능
async function endChat() {
  if (!confirm('챗을 종료하시겠습니까? 모든 대화 내용이 삭제됩니다.')) {
    return;
  }

  // 백엔드 세션 종료 API 호출
  try {
    const token = getAuthToken();
    if (chatbot.sessionId && token) {
      await fetch('/api/v1/chat/end', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: chatbot.sessionId,
        }),
      });
    }
  } catch (error) {
    console.error('챗 종료 오류:', error);
  }

  // 프론트 상태 초기화
  chatbot.sessionId = null;
  chatbot.messages = [];
  localStorage.removeItem('chatbot_session_id');

  // 메시지 창 초기화
  const messagesContainer = document.getElementById('chatbot-messages');
  if (messagesContainer) {
    messagesContainer.innerHTML = '';
  }

  // 환영 메시지 다시 표시
  addMessage('assistant', '안녕하세요! 👋 Cloud9 Care 챗봇입니다. 무엇을 도와드릴까요?');

  showAppToast('챗이 종료되었습니다.', 'info', '챗봇');
}

// TTS 토글 (최신 답변만 읽기)
function readLastMessage() {
  const ttsBtn = document.getElementById('chatbot-tts');

  if (isSpeaking) {
    synthesis.cancel();
    isSpeaking = false;
    ttsBtn.textContent = '🔊';
    ttsBtn.style.background = 'none';
    return;
  }

  // 최신 챗봇 답변만 읽기
  const assistantMessages = chatbot.messages.filter(m => m.role === 'assistant');

  if (assistantMessages.length === 0) {
    showAppToast('읽어줄 메시지가 없습니다.', 'info', '음성 안내');
    return;
  }

  const lastMessage = assistantMessages[assistantMessages.length - 1].content;

  isSpeaking = true;
  ttsBtn.textContent = '⏹';
  ttsBtn.style.background = 'rgba(255, 255, 255, 0.2)';

  const utterance = new SpeechSynthesisUtterance(lastMessage);
  utterance.lang = 'ko-KR';
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  utterance.onend = () => {
    isSpeaking = false;
    ttsBtn.textContent = '🔊';
    ttsBtn.style.background = 'none';
  };

  utterance.onerror = () => {
    isSpeaking = false;
    ttsBtn.textContent = '🔊';
    ttsBtn.style.background = 'none';
  };

  synthesis.speak(utterance);
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', initChatbot);
