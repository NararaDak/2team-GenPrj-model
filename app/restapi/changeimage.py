import asyncio
import base64
import uuid
from io import BytesIO
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from PIL import Image
from pydantic import BaseModel, Field

router = APIRouter()


JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_DONE = "done"
JOB_STATUS_FAILED = "failed"


_changeimage_jobs: dict[str, dict[str, Any]] = {}
_changeimage_jobs_lock = asyncio.Lock()


class ChangeImageRequest(BaseModel):
    prompt: str | None = None
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    image_base64: str = Field(..., description="Base64 encoded image bytes (optionally data URL)")
    strength: float = 0.55


class ChangeImageJobCreateResponse(BaseModel):
    job_id: str
    status: str


class ChangeImageJobStatusResponse(BaseModel):
    job_id: str
    status: str
    error: str | None = None


def _get_diffusion_service():
    if __package__ == "app.restapi":
        from ..model.diffusion import diffusion_service
    else:
        from model.diffusion import diffusion_service

    return diffusion_service


def _resolve_positive_prompt(prompt: str | None, positive_prompt: str | None) -> str:
    resolved_prompt = (positive_prompt or prompt or "").strip()
    if not resolved_prompt:
        raise HTTPException(status_code=400, detail="positive_prompt 또는 prompt는 필수입니다.")
    return resolved_prompt


def _normalize_raw_base64(image_base64: str) -> str:
    raw_base64 = (image_base64 or "").strip()
    if "," in raw_base64:
        raw_base64 = raw_base64.split(",", 1)[1]
    return raw_base64


def _decode_base64_image(image_base64: str) -> Image.Image:
    raw_base64 = _normalize_raw_base64(image_base64)
    try:
        input_bytes = base64.b64decode(raw_base64, validate=True)
        return Image.open(BytesIO(input_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="유효한 base64 이미지가 아닙니다.") from exc


async def _set_job(job_id: str, payload: dict[str, Any]) -> None:
    async with _changeimage_jobs_lock:
        existing = _changeimage_jobs.get(job_id, {})
        existing.update(payload)
        _changeimage_jobs[job_id] = existing


async def _get_job(job_id: str) -> dict[str, Any] | None:
    async with _changeimage_jobs_lock:
        return _changeimage_jobs.get(job_id)


async def _run_changeimage_job(
    job_id: str,
    resolved_prompt: str,
    negative_prompt: str | None,
    image_base64: str,
    strength: float,
) -> None:
    await _set_job(job_id, {"status": JOB_STATUS_RUNNING})
    try:
        init_image = _decode_base64_image(image_base64)
        image = await asyncio.to_thread(
            _get_diffusion_service().change_image,
            resolved_prompt,
            init_image,
            strength,
            negative_prompt,
        )

        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        await _set_job(
            job_id,
            {
                "status": JOB_STATUS_DONE,
                "result_bytes": img_byte_arr.getvalue(),
                "error": None,
            },
        )
    except Exception as exc:
        await _set_job(
            job_id,
            {
                "status": JOB_STATUS_FAILED,
                "error": str(exc),
            },
        )


@router.post("/changeimage")
async def change_image(req: ChangeImageRequest):
    if req.strength < 0.0 or req.strength > 1.0:
        raise HTTPException(status_code=400, detail="strength는 0.0~1.0 범위여야 합니다.")

    applied_strength = 0.01 if req.strength == 0.0 else req.strength
    resolved_prompt = _resolve_positive_prompt(req.prompt, req.positive_prompt)

    print(f"🛠️ 이미지 변환 요청 positive_prompt: {resolved_prompt}")

    init_image = _decode_base64_image(req.image_base64)

    image = _get_diffusion_service().change_image(
        positive_prompt=resolved_prompt,
        negative_prompt=req.negative_prompt,
        init_image=init_image,
        strength=applied_strength,
    )

    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")

    print("✅ 이미지 변환 완료!")
    return Response(content=img_byte_arr.getvalue(), media_type="image/png")


@router.post("/changeimage/jobs", response_model=ChangeImageJobCreateResponse)
async def create_changeimage_job(req: ChangeImageRequest):
    if req.strength < 0.0 or req.strength > 1.0:
        raise HTTPException(status_code=400, detail="strength는 0.0~1.0 범위여야 합니다.")

    resolved_prompt = _resolve_positive_prompt(req.prompt, req.positive_prompt)
    applied_strength = 0.01 if req.strength == 0.0 else req.strength
    _ = _decode_base64_image(req.image_base64)

    job_id = str(uuid.uuid4())
    await _set_job(
        job_id,
        {
            "status": JOB_STATUS_QUEUED,
            "error": None,
            "result_bytes": None,
        },
    )
    asyncio.create_task(
        _run_changeimage_job(
            job_id,
            resolved_prompt,
            req.negative_prompt,
            req.image_base64,
            applied_strength,
        )
    )
    return ChangeImageJobCreateResponse(job_id=job_id, status=JOB_STATUS_QUEUED)


@router.get("/changeimage/jobs/{job_id}", response_model=ChangeImageJobStatusResponse)
async def get_changeimage_job_status(job_id: str):
    job = await _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 job_id입니다.")

    return ChangeImageJobStatusResponse(
        job_id=job_id,
        status=job.get("status", JOB_STATUS_FAILED),
        error=job.get("error"),
    )


@router.get("/changeimage/jobs/{job_id}/result")
async def get_changeimage_job_result(job_id: str):
    job = await _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 job_id입니다.")

    status = job.get("status")
    if status != JOB_STATUS_DONE:
        if status == JOB_STATUS_FAILED:
            raise HTTPException(
                status_code=500,
                detail=job.get("error") or "이미지 변환 작업이 실패했습니다.",
            )
        raise HTTPException(status_code=409, detail=f"작업이 아직 완료되지 않았습니다. status={status}")

    result_bytes = job.get("result_bytes")
    if not result_bytes:
        raise HTTPException(status_code=500, detail="생성 결과를 찾을 수 없습니다.")

    return Response(content=result_bytes, media_type="image/png")



