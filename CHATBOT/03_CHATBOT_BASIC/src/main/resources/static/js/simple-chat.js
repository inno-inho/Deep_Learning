// ============================================================
// 단순 대화 챗봇 (SIMPLE)
// - 기능: 간단한 LLM 질의/응답
// - 의존성 분리: 전역 유틸이 없을 때를 대비해 지역 fallback을 포함
// ============================================================
(function () {
	//-------------------------------
	// 함수용도: 화면 요소 캐시
	// - 입력: 없음
	// - 출력: 없음
	// - 비고: DOMContentLoaded 시점 이후 스크립트 로드 전제
	// 실행되는 순서 : 1 (초기 실행 시 상수 바인딩)
	//-------------------------------
	const simpleLauncher = document.getElementById('simpleChatLauncher');
	const simplePanel = document.getElementById('simpleChatPanel');
	const simpleCloseBtn = document.getElementById('simpleChatClose');
	const simpleChatBody = simplePanel.querySelector('.chat-body');
	const simpleInput = document.getElementById('simpleChatInput');
	const simpleSendButton = document.getElementById('simpleChatSend');

	//-------------------------------
	// 함수용도: 로딩 인디케이터 참조를 보관하는 상태
	// - 입력: 없음
	// - 출력: 없음
	// - 비고: setLoading에서 사용
	// 실행되는 순서 : 1
	//-------------------------------
	const state = { loadingIndicator: null };

	// 유틸 존재하지 않을 경우 지역 구현(fallback)
	//-------------------------------
	// 함수용도: 패널 열기/닫기 토글 (전역 toggleChatPanel 없을 때 대체)
	// - 입력: panel(Element), input(Element)
	// - 출력: 없음
	// - 비고: 열릴 때 입력 포커스 지연 부여
	// 실행되는 순서 : 필요 시 호출
	//-------------------------------
	const doTogglePanel = typeof toggleChatPanel === 'function'
		? toggleChatPanel
		: function(panel, input) {
			panel.classList.toggle('visible');
			if (panel.classList.contains('visible')) {
				setTimeout(() => input && input.focus && input.focus(), 200);
			}
		};

	//-------------------------------
	// 함수용도: 채팅 메시지 추가 (전역 appendChatMessage 없을 때 대체)
	// - 입력: chatBody(Element), role('user'|'bot'), payload(string)
	// - 출력: 생성된 메시지(Element)
	// - 비고: bot일 때 배지 출력
	// 실행되는 순서 : 필요 시 호출
	//-------------------------------
	const append = typeof appendChatMessage === 'function'
		? appendChatMessage
		: function(chatBody, role, payload) {
			const message = document.createElement('div');
			message.classList.add('chat-message', role);
			if (role === 'bot') {
				const badge = document.createElement('span');
				badge.className = 'bot-badge';
				badge.textContent = 'AI 상담';
				message.appendChild(badge);
			}
			const textNode = document.createTextNode(payload);
			message.appendChild(textNode);
			chatBody.appendChild(message);
			chatBody.scrollTop = chatBody.scrollHeight;
			return message;
		};

	//-------------------------------
	// 함수용도: 로딩 상태 제어 (전역 setChatLoading 없을 때 대체)
	// - 입력: isLoading(boolean), sendButton, input, chatBody, st(state)
	// - 출력: 없음
	// - 비고: 로딩 시작 시 봇 메시지로 간단한 안내 표시
	// 실행되는 순서 : 필요 시 호출
	//-------------------------------
	const setLoading = typeof setChatLoading === 'function'
		? setChatLoading
		: function(isLoading, sendButton, input, chatBody, st) {
			if (isLoading) {
				if (sendButton) sendButton.disabled = true;
				if (input) input.disabled = true;
				if (chatBody) {
					st.loadingIndicator = append(chatBody, 'bot', '처리 중...');
				}
			} else {
				if (sendButton) sendButton.disabled = false;
				if (input) input.disabled = false;
				if (st && st.loadingIndicator && st.loadingIndicator.parentNode) {
					st.loadingIndicator.parentNode.removeChild(st.loadingIndicator);
					st.loadingIndicator = null;
				}
				if (input && input.focus) input.focus();
			}
		};

	//-------------------------------
	// 함수용도: Enter(Shift 미포함)로 전송 콜백 실행 (전역 유틸 fallback)
	// - 입력: input(Element), sendCallback(Function)
	// - 출력: 없음
	// - 비고: 기본 채팅 UX
	// 실행되는 순서 : 이벤트 바인딩 시
	//-------------------------------
	const ensureEnterHandler = typeof setupEnterKeyHandler === 'function'
		? setupEnterKeyHandler
		: function(input, sendCallback) {
			input.addEventListener('keydown', (event) => {
				if (event.key === 'Enter' && !event.shiftKey) {
					event.preventDefault();
					sendCallback();
				}
			});
		};

	//-------------------------------
	// 함수용도: ESC로 패널 닫기 (전역 유틸 fallback)
	// - 입력: panel(Element)
	// - 출력: 없음
	// - 비고: 문서 전역 keydown 리스너
	// 실행되는 순서 : 이벤트 바인딩 시
	//-------------------------------
	const ensureEscapeHandler = typeof setupEscapeKeyHandler === 'function'
		? setupEscapeKeyHandler
		: function(panel) {
			document.addEventListener('keydown', (event) => {
				if (event.key === 'Escape' && panel.classList.contains('visible')) {
					panel.classList.remove('visible');
				}
			});
		};

	//-------------------------------
	// 함수용도: fetch 타임아웃 처리 (전역 fetchWithTimeout 없을 때 대체)
	// - 입력: url(string), options(RequestInit), timeout(ms)
	// - 출력: Response
	// - 비고: AbortController 사용
	// 실행되는 순서 : API 호출 시
	//-------------------------------
	const doFetchWithTimeout = typeof fetchWithTimeout === 'function'
		? fetchWithTimeout
		: async function(url, options, timeout = 35000) {
			const controller = new AbortController();
			const timeoutId = setTimeout(() => controller.abort(), timeout);
			try {
				const response = await fetch(url, { ...options, signal: controller.signal });
				clearTimeout(timeoutId);
				return response;
			} catch (e) {
				clearTimeout(timeoutId);
				throw e;
			}
		};

	//-------------------------------
	// 함수용도: 에러 메시지 변환 (전역 getChatErrorMessage 없을 때 대체)
	// - 입력: error(Error)
	// - 출력: 사용자용 메시지(string)
	// - 비고: 공통 정책에 맞춘 문구
	// 실행되는 순서 : 에러 처리 시
	//-------------------------------
	const toErrorMessage = typeof getChatErrorMessage === 'function'
		? getChatErrorMessage
		: function(error) {
			let errorMessage = '죄송합니다. ';
			if (error && error.name === 'AbortError') {
				errorMessage += '응답 시간이 초과되었습니다. 다시 시도해주세요.';
			} else if (error && String(error.message || '').includes('status: 500')) {
				errorMessage += 'AI 서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
			} else if (error && String(error.message || '').includes('status: 404')) {
				errorMessage += '챗봇 API를 찾을 수 없습니다. 관리자에게 문의하세요.';
			} else {
				errorMessage += '현재 상담이 지연되고 있습니다. 잠시 후 다시 시도해주세요.';
			}
			return errorMessage;
		};

	// 메시지 전송 (단순 LLM 직접 호출)
	//-------------------------------
	// 함수용도: 입력값을 서버에 전송하고 응답을 채팅창에 표시
	// - 입력: 없음(내부에서 요소 접근)
	// - 출력: 없음
	// - 비고: 로딩 상태/에러 메시지 처리 포함
	// 실행되는 순서 : 전송 이벤트 발생 시
	//-------------------------------
	const sendSimpleMessage = async () => {
		const text = simpleInput.value.trim();
		if (!text || simpleSendButton.disabled) {
			return;
		}

		append(simpleChatBody, 'user', text);
		simpleInput.value = '';
		setLoading(true, simpleSendButton, simpleInput, simpleChatBody, state);

		try {
			const response = await doFetchWithTimeout('/api/v1/simple-chat', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					message: text
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const data = await response.json();

			// AI 응답 표시
			if (data.reply) {
				append(simpleChatBody, 'bot', data.reply);
			}

		} catch (error) {
			console.error('단순 챗봇 API 호출 중 오류:', error);
			const errorMessage = toErrorMessage(error);
			append(simpleChatBody, 'bot', errorMessage);
		} finally {
			setLoading(false, simpleSendButton, simpleInput, simpleChatBody, state);
		}
	};

	// 이벤트 바인딩
	//-------------------------------
	// 함수용도: 런처/닫기/전송/키보드 핸들러 바인딩
	// - 입력: 없음
	// - 출력: 없음
	// - 비고: 초기화 시 1회 실행
	// 실행되는 순서 : 2
	//-------------------------------
	simpleLauncher.addEventListener('click', () => doTogglePanel(simplePanel, simpleInput));
	simpleCloseBtn.addEventListener('click', () => doTogglePanel(simplePanel, simpleInput));
	simpleSendButton.addEventListener('click', sendSimpleMessage);
	ensureEnterHandler(simpleInput, sendSimpleMessage);
	ensureEscapeHandler(simplePanel);
})();

/*
실행 순서(주요 흐름):
1) 상수/상태 초기화
   - 역할: DOM 요소 캐시 및 상태 준비
   - 시점: 스크립트 로드 즉시

2) 이벤트 바인딩
   - 역할: 버튼(열기/닫기/전송), 키보드(Enter/ESC) 핸들러 연결
   - 결과: 사용자의 인터랙션을 처리할 준비 완료

3) sendSimpleMessage
   - 역할: 사용자의 입력을 간단 챗 API에 전송 후 응답 출력
   - 세부: 로딩 표시 → /api/v1/simple-chat POST → 응답/에러 메시지 표시 → 로딩 해제
*/

