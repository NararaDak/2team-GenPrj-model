# API 문서

이 문서는 현재 모델 서버의 FastAPI 엔드포인트를 정리한 문서입니다.

## 1. 서버 정보

- 기본 실행 포트: 8000
- 기본 Content-Type 응답: image/png
- 엔드포인트 prefix: 없음

실행 예:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 2. 공통 사항

- `positive_prompt`가 우선 사용됩니다.
- `positive_prompt`가 비어 있으면 `prompt`를 대체 입력으로 사용합니다.
- `positive_prompt`와 `prompt`가 모두 비어 있으면 `400 Bad Request`를 반환합니다.
- 이미지 응답은 바이너리 PNG 데이터로 반환됩니다.
- 에러 응답은 FastAPI 기본 형식의 JSON으로 반환됩니다.

에러 응답 예:

```json
{
  "detail": "positive_prompt 또는 prompt는 필수입니다."
}
```

## 3. 엔드포인트 목록

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/generate` | 텍스트 프롬프트로 이미지 생성 |
| POST | `/generate` | JSON 본문으로 이미지 생성 |
| POST | `/changeimage` | base64 입력 이미지를 기반으로 이미지 변환 |

## 4. GET /generate

쿼리스트링으로 이미지를 생성합니다.

### 요청 파라미터

| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `prompt` | string | 선택 | 하위 호환용 입력 프롬프트 |
| `positive_prompt` | string | 선택 | 생성에 사용할 메인 프롬프트 |
| `negative_prompt` | string | 선택 | 제외하고 싶은 요소를 지정하는 프롬프트 |

### 성공 응답

- 상태 코드: `200 OK`
- Content-Type: `image/png`
- 본문: PNG 바이너리 이미지

### 실패 응답

- 상태 코드: `400 Bad Request`
- 조건: `positive_prompt`와 `prompt`가 모두 비어 있음

### 요청 예시

```bash
curl -G "http://localhost:8000/generate" \
  --data-urlencode "positive_prompt=a futuristic cafe poster, ultra detailed" \
  --data-urlencode "negative_prompt=blurry, low quality" \
  --output generated.png
```

## 5. POST /generate

JSON 본문으로 이미지를 생성합니다. 백엔드 서버 연동 시 이 방식을 사용하는 것을 권장합니다.

### 요청 본문

```json
{
  "positive_prompt": "a futuristic cafe poster, ultra detailed",
  "negative_prompt": "blurry, low quality"
}
```

### 요청 필드

| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `prompt` | string | 선택 | 하위 호환용 입력 프롬프트 |
| `positive_prompt` | string | 선택 | 생성에 사용할 메인 프롬프트 |
| `negative_prompt` | string | 선택 | 제외하고 싶은 요소를 지정하는 프롬프트 |

### 성공 응답

- 상태 코드: `200 OK`
- Content-Type: `image/png`
- 본문: PNG 바이너리 이미지

### 실패 응답

- 상태 코드: `400 Bad Request`
- 조건: `positive_prompt`와 `prompt`가 모두 비어 있음

### 요청 예시

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "positive_prompt": "a futuristic cafe poster, ultra detailed",
    "negative_prompt": "blurry, low quality"
  }' \
  --output generated.png
```

## 6. POST /changeimage

base64로 전달된 입력 이미지를 바탕으로 프롬프트 기반 이미지 변환을 수행합니다.

### 요청 본문

```json
{
  "positive_prompt": "convert to watercolor illustration",
  "negative_prompt": "blurry, distorted, low quality",
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "strength": 0.55
}
```

### 요청 필드

| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `prompt` | string | 선택 | 하위 호환용 입력 프롬프트 |
| `positive_prompt` | string | 선택 | 변환에 사용할 메인 프롬프트 |
| `negative_prompt` | string | 선택 | 제외하고 싶은 요소를 지정하는 프롬프트 |
| `image_base64` | string | 필수 | base64 인코딩 이미지 문자열, data URL 형식도 허용 |
| `strength` | number | 선택 | 변환 강도, 범위는 0.0 이상 1.0 이하, 기본값은 0.55 |

### 성공 응답

- 상태 코드: `200 OK`
- Content-Type: `image/png`
- 본문: PNG 바이너리 이미지

### 실패 응답

- 상태 코드: `400 Bad Request`
- 조건: `strength`가 0.0 미만 또는 1.0 초과

```json
{
  "detail": "strength는 0.0~1.0 범위여야 합니다."
}
```

- 상태 코드: `400 Bad Request`
- 조건: `image_base64`가 유효한 base64 이미지가 아님

```json
{
  "detail": "유효한 base64 이미지가 아닙니다."
}
```

- 상태 코드: `400 Bad Request`
- 조건: `positive_prompt`와 `prompt`가 모두 비어 있음

### 요청 예시

```bash
curl -X POST "http://localhost:8000/changeimage" \
  -H "Content-Type: application/json" \
  -d '{
    "positive_prompt": "convert to watercolor illustration",
    "negative_prompt": "blurry, distorted, low quality",
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
    "strength": 0.55
  }' \
  --output changed.png
```

## 7. 구현 위치

- 앱 엔트리포인트: app/main.py
- 이미지 생성 API: app/restapi/generate.py
- 이미지 변환 API: app/restapi/changeimage.py
- Diffusion 서비스: app/model/diffusion.py