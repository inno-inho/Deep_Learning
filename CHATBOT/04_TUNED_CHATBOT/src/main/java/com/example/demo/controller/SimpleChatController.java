package com.example.demo.controller;

/*
============================================================
SimpleChatController.java 파일 전체 용도
============================================================
- 가장 단순한 LLM 호출 데모 컨트롤러.
- 사용자의 질문을 그대로 LLM에 전달하고, 응답을 반환(오류 시 폴백 메시지)합니다.
============================================================
구성요소 및 메서드 개요
============================================================
- 생성자: ChatModel 주입
- chat(): 단일 UserMessage → Prompt 생성 → LLM 호출 → 응답 반환
============================================================
각 라인별 상세 주석은 각 함수 블록 상단/내부에 포함
============================================================
*/

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/simple-chat")
public class SimpleChatController {

    private static final Logger log = LoggerFactory.getLogger(SimpleChatController.class); // 로깅

    private final ChatModel chatModel; // 스프링 AI LLM 모델 의존성

    /*
    ============================================================
    생성자 용도
    ============================================================
    - 외부에서 주입된 ChatModel을 보관합니다.
    ============================================================
    */
    public SimpleChatController(ChatModel chatModel) {
        this.chatModel = chatModel; // 의존성 보관
    }

    /*
    ============================================================
    chat() 메서드 용도
    ============================================================
    - 사용자의 단일 입력을 LLM에 그대로 전달하고 응답을 반환합니다.
    - 예외 발생 시 폴백 메시지로 대체하여 응답합니다.
    ============================================================
    라인별 주석(핵심)
    - 로그: 입력 수신
    - Prompt 생성: UserMessage 기반 최소 프롬프트
    - chatModel.call: LLM 호출
    - 응답 추출 후 반환, 예외 시 폴백
    ============================================================
    */
    @PostMapping
    public ResponseEntity<ChatResponse> chat(@Valid @RequestBody ChatRequest request) {
        log.info("=== 질문 수신: {} ===", request.message()); // 수신 로그

        try {
            // 단순 LLM 호출 - 복잡한 로직 없음
            var prompt = new Prompt(new UserMessage(request.message())); // 사용자 입력을 메시지로 포장
            var result = chatModel.call(prompt); // LLM 호출
            var reply = result.getResult().getOutput().getContent(); // 응답 텍스트 추출

            log.info("LLM 응답 완료"); // 완료 로그
            return ResponseEntity.ok(new ChatResponse(reply)); // 정상 응답

        } catch (Exception ex) {
            log.error("LLM 호출 중 오류 발생", ex); // 예외 로그
            var fallback = "죄송합니다. 현재 응답을 생성할 수 없습니다."; // 폴백 메시지
            return ResponseEntity.ok(new ChatResponse(fallback)); // 폴백 응답
        }
    }

    // 요청/응답 최소 표현 레코드
    public record ChatRequest(@NotBlank String message) {}
    public record ChatResponse(String reply) {}
}


