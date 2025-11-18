package com.example.demo.controller;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;

@Validated
@RestController
@RequestMapping("/api/v1/demo")
@Tag(name = "Demo API", description = "Swagger UI 연결을 위한 임시 데모 엔드포인트 모음")
public class SwaggerDemoController {

    @Operation(summary = "서버 상태 확인", description = "서버의 헬스체크 용도로 사용합니다.")
    @ApiResponse(responseCode = "200", description = "서버 동작 중")
    @GetMapping("/ping")
    public ResponseEntity<Map<String, Object>> ping() {
        return ResponseEntity.ok(Map.of("status", "OK", "timestamp", LocalDate.now()));
    }

    @Operation(summary = "사용자 목록 조회", description = """
		검색어와 페이지 정보를 사용해 사용자 목록을 조회합니다.
		이동 경로 예시: 홈 > 상단 메뉴 '고객센터' > '회원 관리' > '회원 목록 조회' 탭 선택
		""")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "조회 성공"),
            @ApiResponse(responseCode = "400", description = "잘못된 요청", content = @Content)
    })
    @GetMapping("/users")
    public ResponseEntity<Map<String, Object>> getUsers(
            @Parameter(description = "이름 검색 키워드", example = "kim") @RequestParam(required = false) String keyword,
            @Parameter(description = "페이지 번호", example = "0") @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "페이지 크기", example = "10") @RequestParam(defaultValue = "10") int size
    ) {
        return ResponseEntity.ok(Map.of(
                "keyword", keyword,
                "page", page,
                "size", size,
                "users", List.of(Map.of("id", 1, "name", "홍길동"))
        ));
    }

    @Operation(summary = "사용자 단건 조회", description = """
		경로 변수로 사용자 ID를 전달해 단건 정보를 조회합니다.
		이동 경로 예시: 홈 > 고객센터 > 회원 관리 > '회원 상세 조회'에서 회원 ID 입력
		""")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "조회 성공"),
            @ApiResponse(responseCode = "404", description = "사용자를 찾을 수 없음", content = @Content)
    })
    @GetMapping("/users/{userId}")
    public ResponseEntity<Map<String, Object>> getUser(
            @Parameter(description = "조회할 사용자 ID", example = "42") @PathVariable Long userId
    ) {
        return ResponseEntity.ok(Map.of("id", userId, "name", "테스트 사용자", "email", "user@example.com"));
    }

    @Operation(summary = "사용자 생성 (회원가입)", description = """
		새로운 사용자를 등록합니다. 회원가입 시 사용하세요.
		이동 경로 예시: 홈 > 우측 상단 '회원가입' 버튼 > 가입 정보 입력 > '가입 완료' 제출
		""")
    @ApiResponses({
            @ApiResponse(responseCode = "201", description = "생성 성공"),
            @ApiResponse(responseCode = "400", description = "요청 본문 검증 실패", content = @Content)
    })
    @PostMapping("/users")
    public ResponseEntity<Map<String, Object>> createUser(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(description = "생성할 사용자 정보", required = true,
                    content = @Content(schema = @Schema(implementation = CreateUserRequest.class)))
            @RequestBody CreateUserRequest request
    ) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(Map.of("id", 100L, "name", request.name(), "email", request.email()));
    }

    @Operation(summary = "사용자 전체 정보 수정", description = """
		사용자의 이름과 이메일을 모두 수정합니다.
		이동 경로 예시: 홈 > 고객센터 > 회원 관리 > 회원 상세 > '정보 수정' 버튼 클릭 후 저장
		""")
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "수정 성공"),
            @ApiResponse(responseCode = "404", description = "사용자를 찾을 수 없음", content = @Content)
    })
    @PutMapping("/users/{userId}")
    public ResponseEntity<Map<String, Object>> updateUser(
            @Parameter(description = "수정할 사용자 ID", example = "42") @PathVariable Long userId,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(description = "수정할 사용자 정보", required = true,
                    content = @Content(schema = @Schema(implementation = UpdateUserRequest.class)))
            @RequestBody UpdateUserRequest request
    )
    {
        return ResponseEntity.ok(Map.of(
                "id", userId,
                "name", request.name(),
                "email", request.email(),
                "message", "사용자 정보가 수정되었습니다."
        ));
    }

    @Operation(summary = "사용자 이메일만 수정", description = """
		사용자의 이메일 주소만 선택적으로 수정합니다.
		이동 경로 예시: 홈 > 고객센터 > 회원 관리 > 회원 상세 > 연락처 섹션의 '이메일 수정' 선택
		""")
    @ApiResponse(responseCode = "200", description = "수정 성공")
    @PatchMapping("/users/{userId}/email")
    public ResponseEntity<Map<String, Object>> updateUserEmail(
            @Parameter(description = "수정할 사용자 ID", example = "42") @PathVariable Long userId,
            @io.swagger.v3.oas.annotations.parameters.RequestBody(description = "새로운 이메일 정보", required = true,
                    content = @Content(schema = @Schema(implementation = UpdateEmailRequest.class)))
            @RequestBody UpdateEmailRequest request
    ) {
        return ResponseEntity.ok(Map.of(
                "id", userId,
                "email", request.email(),
                "message", "이메일이 업데이트되었습니다."
        ));
    }

    @Operation(summary = "사용자 삭제", description = """
		ID에 해당하는 사용자를 비활성화 또는 삭제합니다.
		이동 경로 예시: 홈 > 고객센터 > 회원 관리 > 회원 상세 > 하단 '회원 탈퇴 처리' 버튼
		""")
    @ApiResponses({
            @ApiResponse(responseCode = "204", description = "삭제 성공"),
            @ApiResponse(responseCode = "404", description = "사용자를 찾을 수 없음", content = @Content)
    })
    @DeleteMapping("/users/{userId}")
    public ResponseEntity<Void> deleteUser(
            @Parameter(description = "삭제할 사용자 ID", example = "42") @PathVariable Long userId
    ) {
        return ResponseEntity.noContent().build();
    }

    @Operation(summary = "주문 목록 조회", description = """
		주문 상태로 주문 목록을 필터링합니다.
		이동 경로 예시: 홈 > 상단 메뉴 '주문/배송' > '주문 내역 조회' > 필터 조건 선택
		""")
    @GetMapping("/orders")
    public ResponseEntity<Map<String, Object>> getOrders(
            @Parameter(description = "조회할 주문 상태", example = "READY") @RequestParam(required = false) String status
    ) {
        return ResponseEntity.ok(Map.of(
                "status", status,
                "orders", List.of(Map.of("orderId", 9001, "status", status != null ? status : "READY"))
        ));
    }

    @Operation(summary = "주문 생성", description = """
		장바구니 정보로 주문을 생성합니다.
		이동 경로 예시: 홈 > 상품 상세 페이지 > '장바구니 담기' > 장바구니 > '주문하기'
		""")
    @PostMapping("/orders")
    public ResponseEntity<Map<String, Object>> createOrder(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(description = "생성할 주문 정보", required = true,
                    content = @Content(schema = @Schema(implementation = CreateOrderRequest.class)))
            @RequestBody CreateOrderRequest request
    ) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(Map.of("orderId", 9999, "items", request.productIds(), "message", "주문이 접수되었습니다."));
    }

    @Operation(summary = "주문 단건 조회", description = """
		주문 ID로 단건 주문을 조회합니다.
		이동 경로 예시: 홈 > 주문/배송 > 주문 내역 > 조회할 주문 선택
		""")
    @GetMapping("/orders/{orderId}")
    public ResponseEntity<Map<String, Object>> getOrder(
            @Parameter(description = "조회할 주문 ID", example = "9999") @PathVariable Long orderId
    ) {
        return ResponseEntity.ok(Map.of("orderId", orderId, "status", "READY", "totalPrice", 12345));
    }

    @Operation(summary = "파일 업로드 시뮬레이션", description = """
		Swagger에서 멀티파트 요청 예시를 보여주기 위한 엔드포인트입니다.
		이동 경로 예시: 홈 > 고객지원 > 자료실 > '파일 업로드' 메뉴 > 업로드 파일 선택
		""")
    @ApiResponse(responseCode = "200", description = "업로드 성공")
    @PostMapping("/upload")
    public ResponseEntity<Map<String, Object>> upload(
            @Parameter(description = "업로드할 파일 이름", example = "demo.txt") @RequestParam String filename
    ) {
        return ResponseEntity.ok(Map.of("filename", filename, "message", "파일이 업로드된 것으로 처리되었습니다."));
    }

    @Operation(summary = "일간 리포트 조회", description = """
		특정 날짜의 일간 리포트를 제공합니다.
		이동 경로 예시: 홈 > 경영 리포트 > '일간 리포트' 탭 > 날짜 선택
		""")
    @GetMapping("/reports/daily")
    public ResponseEntity<Map<String, Object>> getDailyReport(
            @Parameter(description = "리포트를 조회할 날짜", example = "2025-01-01") @RequestParam(required = false) LocalDate date
    ) {
        LocalDate targetDate = date != null ? date : LocalDate.now();
        return ResponseEntity.ok(Map.of("date", targetDate, "summary", "일간 리포트 요약"));
    }

    @Operation(summary = "월간 리포트 조회", description = """
		특정 월의 리포트를 제공합니다.
		이동 경로 예시: 홈 > 경영 리포트 > 상단 드롭다운에서 '월간' 선택 > 대상 월 지정
		""")
    @GetMapping("/reports/monthly")
    public ResponseEntity<Map<String, Object>> getMonthlyReport(
            @Parameter(description = "YYYY-MM 형식의 월", example = "2025-01") @RequestParam String month
    ) {
        return ResponseEntity.ok(Map.of("month", month, "summary", "월간 리포트 요약"));
    }

    @Operation(summary = "로그인", description = """
		아이디와 비밀번호를 통해 액세스 토큰을 발급합니다.
		이동 경로 예시: 홈 > 우측 상단 '로그인' > 아이디/비밀번호 입력 > 로그인 버튼 클릭
		""")
    @PostMapping("/auth/login")
    public ResponseEntity<Map<String, Object>> login(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(description = "로그인 요청 정보", required = true,
                    content = @Content(schema = @Schema(implementation = LoginRequest.class)))
            @RequestBody LoginRequest request
    ) {
        return ResponseEntity.ok(Map.of(
                "accessToken", "dummy-token",
                "userId", request.username(),
                "message", "로그인 성공"
        ));
    }

    @Operation(summary = "로그아웃", description = """
		발급된 토큰을 만료시킵니다.
		이동 경로 예시: 홈 > 우측 상단 사용자 메뉴 > '로그아웃' 선택 > 확인
		""")
    @PostMapping("/auth/logout")
    public ResponseEntity<Map<String, Object>> logout(
            @Parameter(description = "만료시킬 액세스토큰", example = "dummy-token") @RequestParam String accessToken
    ) {
        return ResponseEntity.ok(Map.of("token", accessToken, "message", "로그아웃 처리되었습니다."));
    }

    public record CreateUserRequest(
            @Schema(description = "사용자 이름", example = "홍길동") String name,
            @Schema(description = "사용자 이메일", example = "hong@example.com") String email
    ) {}

    public record UpdateUserRequest(
            @Schema(description = "수정할 사용자 이름", example = "김철수") String name,
            @Schema(description = "수정할 사용자 이메일", example = "kim@example.com") String email
    ) {}

    public record UpdateEmailRequest(
            @Schema(description = "새로운 이메일 주소", example = "new@example.com") String email
    ) {}

    public record CreateOrderRequest(
            @Schema(description = "상품 ID 목록", example = "[101,102,103]") List<Long> productIds
    ) {}

    public record LoginRequest(
            @Schema(description = "로그인 아이디", example = "admin") String username,
            @Schema(description = "로그인 비밀번호", example = "pass1234") String password
    ) {}
}


