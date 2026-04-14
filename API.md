# API 문서

이 문서는 현재 모델 서버의 FastAPI 엔드포인트를 정리한 문서입니다.

## 1. 서버 정보

- 기본 실행 포트: 8000
- 기본 Content-Type 응답: image/png
- 엔드포인트 prefix: 없음
- OpenAPI 문서: `/docs` (Swagger UI), `/openapi.json`

권장 Base URL 예시:

- 로컬: `http://localhost:8000`
- 스테이징/운영: 팀에서 배포한 API 도메인 사용

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
- 요청 본문은 `Content-Type: application/json` 기준입니다.
- 비동기 생성 API 사용 시, 이미지 생성 완료 전에는 결과 조회가 `409 Conflict`를 반환합니다.

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
| POST | `/generate/jobs` | 비동기 이미지 생성 작업 생성 |
| GET | `/generate/jobs/{job_id}` | 비동기 작업 상태 조회 |
| GET | `/generate/jobs/{job_id}/result` | 비동기 작업 결과 이미지 조회 |
| POST | `/changeimage` | base64 입력 이미지를 기반으로 이미지 변환 |
| POST | `/changeimage/jobs` | 비동기 이미지 변환 작업 생성 |
| GET | `/changeimage/jobs/{job_id}` | 비동기 변환 작업 상태 조회 |
| GET | `/changeimage/jobs/{job_id}/result` | 비동기 변환 작업 결과 이미지 조회 |
| POST | `/image2text` | base64 입력 이미지의 텍스트/설명 추출 |

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

## 7. changeimage 비동기 API

`/changeimage`도 긴 처리 시간이 발생할 수 있으므로 비동기 작업 방식 사용이 가능합니다.

### 7-1. POST /changeimage/jobs

이미지 변환 작업을 큐에 등록하고 즉시 `job_id`를 반환합니다.

요청 본문은 `POST /changeimage`와 동일합니다.

성공 응답:

- 상태 코드: `200 OK`
- 응답 타입: `application/json`

```json
{
  "job_id": "b4b22e65-45e5-4d53-9d03-1ea8cd73ed8e",
  "status": "queued"
}
```

### 7-2. GET /changeimage/jobs/{job_id}

작업 상태를 조회합니다.

상태 값:

- `queued`
- `running`
- `done`
- `failed`

응답 예시:

```json
{
  "job_id": "b4b22e65-45e5-4d53-9d03-1ea8cd73ed8e",
  "status": "running",
  "error": null
}
```

실패 응답:

- 상태 코드: `404 Not Found`
- 조건: 존재하지 않는 `job_id`

```json
{
  "detail": "존재하지 않는 job_id입니다."
}
```

### 7-3. GET /changeimage/jobs/{job_id}/result

작업이 완료되면 PNG 이미지를 반환합니다.

- 완료 전(`queued`/`running`): `409 Conflict`
- 실패(`failed`): `500 Internal Server Error`
- 완료(`done`): `200 OK` + `image/png`

요청 예시:

```bash
curl -X GET "http://localhost:8000/changeimage/jobs/{job_id}/result" --output changed.png
```

권장 호출 순서:

1. `POST /changeimage/jobs` 호출로 `job_id` 받기
2. `GET /changeimage/jobs/{job_id}`를 1~2초 간격으로 폴링
3. 상태가 `done`이면 `GET /changeimage/jobs/{job_id}/result` 호출

## 8. 비동기 생성 API

긴 생성 시간으로 인해 게이트웨이 타임아웃이 발생할 수 있는 환경에서는 비동기 API 사용을 권장합니다.

### 7-1. POST /generate/jobs

이미지 생성 작업을 큐에 등록하고 즉시 `job_id`를 반환합니다.

요청 본문은 `POST /generate`와 동일합니다.

성공 응답:

- 상태 코드: `200 OK`
- 응답 타입: `application/json`

응답 예시:

```json
{
  "job_id": "e2a1e3fe-744a-439d-a6d3-870908e234b2",
  "status": "queued"
}
```

### 7-2. GET /generate/jobs/{job_id}

작업 상태를 조회합니다.

상태 값:

- `queued`
- `running`
- `done`
- `failed`

응답 예시:

```json
{
  "job_id": "e2a1e3fe-744a-439d-a6d3-870908e234b2",
  "status": "running",
  "error": null
}
```

실패 응답:

- 상태 코드: `404 Not Found`
- 조건: 존재하지 않는 `job_id`

```json
{
  "detail": "존재하지 않는 job_id입니다."
}
```

### 7-3. GET /generate/jobs/{job_id}/result

작업이 완료되면 PNG 이미지를 반환합니다.

- 완료 전(`queued`/`running`): `409 Conflict`
- 실패(`failed`): `500 Internal Server Error`
- 완료(`done`): `200 OK` + `image/png`

완료 전 응답 예시:

```json
{
  "detail": "작업이 아직 완료되지 않았습니다. status=running"
}
```

요청 예시:

```bash
curl -X GET "http://localhost:8000/generate/jobs/{job_id}/result" --output generated.png
```

### 권장 호출 순서

1. `POST /generate/jobs` 호출로 `job_id` 받기
2. `GET /generate/jobs/{job_id}`를 1~2초 간격으로 폴링
3. 상태가 `done`이면 `GET /generate/jobs/{job_id}/result` 호출

통합 권장 규칙:

1. 폴링 간격은 최소 1초 이상 유지
2. 최대 대기 시간(예: 5~10분) 초과 시 사용자에게 재시도 안내
3. 상태가 `failed`면 `error` 메시지를 그대로 노출하거나 로깅

프론트엔드 구현 예시(JavaScript):

```javascript
async function generateImageAsync(baseUrl, payload) {
  const createRes = await fetch(`${baseUrl}/generate/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!createRes.ok) {
    throw new Error(`job create failed: ${createRes.status}`);
  }

  const { job_id } = await createRes.json();

  const startedAt = Date.now();
  const timeoutMs = 10 * 60 * 1000;
  while (true) {
    if (Date.now() - startedAt > timeoutMs) {
      throw new Error("job polling timeout");
    }

    const statusRes = await fetch(`${baseUrl}/generate/jobs/${job_id}`);
    if (!statusRes.ok) {
      throw new Error(`status check failed: ${statusRes.status}`);
    }

    const statusJson = await statusRes.json();
    if (statusJson.status === "done") {
      const resultRes = await fetch(`${baseUrl}/generate/jobs/${job_id}/result`);
      if (!resultRes.ok) {
        throw new Error(`result fetch failed: ${resultRes.status}`);
      }
      return await resultRes.blob();
    }

    if (statusJson.status === "failed") {
      throw new Error(statusJson.error || "image generation failed");
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}
```

## 9. POST /image2text

base64 이미지에서 텍스트/설명(Florence 결과)을 추출합니다.

### 요청 본문

```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "task_prompt": "<DETAILED_CAPTION>"
}
```

### 요청 필드

| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `image_base64` | string | 필수 | base64 인코딩 이미지 문자열, data URL 형식도 허용 |
| `task_prompt` | string | 선택 | 기본값 `<DETAILED_CAPTION>` |

### 성공 응답

- 상태 코드: `200 OK`
- 응답 타입: `application/json`

```json
{
  "text": "..."
}
```

### 실패 응답

- 상태 코드: `400 Bad Request`
- 조건: `image_base64` 누락 또는 잘못된 base64 이미지

## 10. 구현 위치

- 앱 엔트리포인트: app/main.py
- 이미지 생성 API: app/restapi/generate.py
- 이미지 변환 API: app/restapi/changeimage.py
- Diffusion 서비스: app/model/diffusion.py