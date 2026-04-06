# 코드 가독성, 유지보수성, 간결성, 일관성, 확장성, 이식성을 고려하고 코드의 중복을 피하며 모듈화/클래스화/함수화하여 작성한다.

## 1. 문서 역할

이 문서는 getPrj 프로젝트의 Python/FastAPI 코딩 규칙(Convention) 문서입니다.

포함 범위:

- Python 코드 작성 규칙
- FastAPI API 작성 규칙
- 네이밍 규칙
- 함수/클래스/멤버 설계 기준

포함하지 않는 범위:

- 프로젝트 목적 및 배경 (README.md에서 관리)
- 전체 시스템 구조 및 기술 세부 사항 (별도 기술 문서에서 관리)

## 2. 개발 원칙

1) 상태를 변경하는 REST API는 POST/PUT/PATCH/DELETE를 사용한다.
2) 조회성 API는 GET을 사용한다.
3) backend와 frontend를 분리하여 개발한다.
4) 한 프로젝트 안에서는 네이밍 스타일을 섞지 않는다.
5) 의미가 같은 값은 범위가 달라도 핵심 단어를 유지한다.
6) 함수/변수/클래스, 주요 로직에는 간결한 주석을 남긴다.

## 3. 네이밍 규칙 (Python 표준)

- 모듈/파일명: snake_case
- 패키지명: 소문자
- 클래스명: PascalCase
- 함수명/메서드명: snake_case
- 변수명(파라미터/지역/멤버): snake_case
- 상수명: UPPER_SNAKE_CASE
- 내부 전용 멤버/메서드: _leading_underscore

예:

```python
MODEL_PATH = "..."

class StableDiffusionService:
    def __init__(self):
        self._model_name = "sd35"

    def change_image(self, input_image, strength):
        return input_image
```

## 4. 함수 작성 규칙

1) 함수 이름은 동사 중심의 snake_case를 사용한다.
2) 함수는 한 가지 책임만 갖도록 작성한다.
3) 파라미터 이름은 역할이 드러나도록 작성한다.
4) 불리언 파라미터는 의미가 분명한 이름을 사용한다.

좋은 예:

- `load_model`
- `build_response_data`
- `change_image`
- `input_image`
- `model_path`

피해야 할 예:

- `DoJob`
- `x`
- `img`
- `file_Path`

## 5. 클래스/멤버 규칙

1) 클래스명은 PascalCase를 사용한다.
2) 멤버 변수는 기본적으로 외부에 직접 노출하지 않는다.
3) 내부 구현 전용 멤버와 헬퍼 메서드는 `_` 접두어를 사용한다.
4) Python에서는 getter/setter를 강제하지 않으며, 필요 시 `@property`를 사용한다.

예:

```python
class ImageService:
    def __init__(self):
        self._pipe = None

    def generate(self, prompt):
        return self._pipe(prompt)
```

## 6. FastAPI 규칙

1) 라우터 핸들러 함수명은 snake_case를 사용한다.
2) API 경로는 기존 클라이언트 호환성을 우선한다.
3) 요청/응답 스키마는 Pydantic 모델로 정의한다.
4) 입력 검증 실패는 4xx 에러로 반환한다.
5) 서버 내부 예외는 로그로 남기고, 외부에는 필요한 정보만 노출한다.

## 7. 변수 범위별 이름 규칙

- 전역 상수: `MODEL_PATH`, `APP_VERSION`
- 함수/메서드 파라미터: `input_image`, `model_path`, `strength`
- 지역 변수: `raw_base64`, `input_bytes`, `applied_strength`
- 클래스 내부 변수: `self._pipe`, `self._initialized`

## 8. 주석 규칙

1) 코드 자체로 드러나는 내용은 주석으로 반복하지 않는다.
2) 복잡한 처리, 성능/메모리 최적화, 외부 제약사항은 간결하게 주석으로 남긴다.
3) 주석은 최신 코드와 항상 동기화한다.

## 9. 예외 규칙

외부 시스템과 주고받는 문자열 키/필드명은 계약(Contract)을 우선한다.

예:

- JSON 필드명: `image_base64`
- 응답 키: `prediction_result`
- 기존 API 경로: `/changeimage`
