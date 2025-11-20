package com.example.demo.chat;

//============================================================
//ChatbotConfig.java 전체 용도
//============================================================
//- Spring Boot 환경에서 "OpenAPI 기본 정보(제목, 버전, 설명)를 제공"하는 설정 클래스.
//- SpringDoc(OpenAPI) 문서 기능이 활성화된 경우에만 OpenAPI Bean을 생성.
//- @EnableScheduling을 통해 스케줄링 기능(@Scheduled)을 사용할 수 있도록 전체 애플리케이션에서 활성화시킴.
//- 결과적으로 Spring AI 기반 챗봇이 API 문서를 활용할 수 있도록 OpenAPI 인스턴스를 제공하는 초기 설정 역할 수행.
//
//
//============================================================
//각 라인별 상세 주석 포함 코드
//============================================================

import java.util.Optional;                            // Optional 사용을 위한 import

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;   // 조건부 빈 등록을 위한 어노테이션
import org.springframework.context.annotation.Bean;    // Bean 등록 어노테이션
import org.springframework.context.annotation.Configuration; // 설정 클래스 정의 어노테이션
import org.springframework.scheduling.annotation.EnableScheduling; // 스케줄링 기능 활성화

import io.swagger.v3.oas.models.OpenAPI;              // OpenAPI 객체
import io.swagger.v3.oas.models.info.Info;            // API 문서 정보 객체

@Configuration                                        // Spring 설정 클래스임을 명시
@EnableScheduling                                     // 스케줄링 기능 활성화
public class ChatbotConfig {

    @Bean                                             // Spring Bean 등록
    // 특정 프로퍼티 활성화 시에만 Bean 생성
    @ConditionalOnProperty(name = "springdoc.api-docs.enabled", havingValue = "true", matchIfMissing = true)

    public Optional<OpenAPI> customOpenAPI() {        // OpenAPI Bean 생성 메서드
        OpenAPI openAPI = new OpenAPI();              // OpenAPI 객체 생성

        openAPI.setInfo(new Info()                    // API 문서 정보 설정
                .title("홈쇼핑 API")                 // API 제목
                .version("v1.0")                      // API 버전
                .description("Spring AI 챗봇과 연동된 홈쇼핑 데모 API") // API 설명
        );

        return Optional.of(openAPI);                  // Optional로 감싸서 반환
    }
}
