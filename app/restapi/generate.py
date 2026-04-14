import asyncio
import uuid
from io import BytesIO
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

router = APIRouter()


JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_DONE = "done"
JOB_STATUS_FAILED = "failed"


_generate_jobs: dict[str, dict[str, Any]] = {}
_generate_jobs_lock = asyncio.Lock()


class GenerateImageRequest(BaseModel):
    prompt: str | None = None
    positive_prompt: str | None = None
    negative_prompt: str | None = None


class GenerateJobCreateResponse(BaseModel):
    job_id: str
    status: str


class GenerateJobStatusResponse(BaseModel):
    job_id: str
    status: str
    error: str | None = None


async def _set_job(job_id: str, payload: dict[str, Any]) -> None:
    async with _generate_jobs_lock:
        existing = _generate_jobs.get(job_id, {})
        existing.update(payload)
        _generate_jobs[job_id] = existing


async def _get_job(job_id: str) -> dict[str, Any] | None:
    async with _generate_jobs_lock:
        return _generate_jobs.get(job_id)


async def _run_generate_job(
    job_id: str,
    resolved_prompt: str,
    negative_prompt: str | None,
) -> None:
    await _set_job(job_id, {"status": JOB_STATUS_RUNNING})
    try:
        image = await asyncio.to_thread(
            _get_diffusion_service().generate,
            resolved_prompt,
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


@router.get("/generate")
async def generate(
    prompt: str | None = None,
    positive_prompt: str | None = None,
    negative_prompt: str | None = None,
):
    resolved_prompt = _resolve_positive_prompt(prompt, positive_prompt)
    print(f"🎨 요청받은 positive_prompt: {resolved_prompt}")

    image = _get_diffusion_service().generate(
        positive_prompt=resolved_prompt,
        negative_prompt=negative_prompt,
    )

    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")

    print("✅ 이미지 생성 완료!")
    return Response(content=img_byte_arr.getvalue(), media_type="image/png")


@router.post("/generate")
async def generate_with_body(req: GenerateImageRequest):
    resolved_prompt = _resolve_positive_prompt(req.prompt, req.positive_prompt)
    print(f"🎨 요청받은 positive_prompt: {resolved_prompt}")

    image = _get_diffusion_service().generate(
        positive_prompt=resolved_prompt,
        negative_prompt=req.negative_prompt,
    )

    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")

    print("✅ 이미지 생성 완료!")
    return Response(content=img_byte_arr.getvalue(), media_type="image/png")


@router.post("/generate/jobs", response_model=GenerateJobCreateResponse)
async def create_generate_job(req: GenerateImageRequest):
    resolved_prompt = _resolve_positive_prompt(req.prompt, req.positive_prompt)
    job_id = str(uuid.uuid4())

    await _set_job(
        job_id,
        {
            "status": JOB_STATUS_QUEUED,
            "error": None,
            "result_bytes": None,
        },
    )
    asyncio.create_task(_run_generate_job(job_id, resolved_prompt, req.negative_prompt))

    return GenerateJobCreateResponse(job_id=job_id, status=JOB_STATUS_QUEUED)


@router.get("/generate/jobs/{job_id}", response_model=GenerateJobStatusResponse)
async def get_generate_job_status(job_id: str):
    job = await _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 job_id입니다.")

    return GenerateJobStatusResponse(
        job_id=job_id,
        status=job.get("status", JOB_STATUS_FAILED),
        error=job.get("error"),
    )


@router.get("/generate/jobs/{job_id}/result")
async def get_generate_job_result(job_id: str):
    job = await _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 job_id입니다.")

    status = job.get("status")
    if status != JOB_STATUS_DONE:
        if status == JOB_STATUS_FAILED:
            raise HTTPException(
                status_code=500,
                detail=job.get("error") or "이미지 생성 작업이 실패했습니다.",
            )
        raise HTTPException(status_code=409, detail=f"작업이 아직 완료되지 않았습니다. status={status}")

    result_bytes = job.get("result_bytes")
    if not result_bytes:
        raise HTTPException(status_code=500, detail="생성 결과를 찾을 수 없습니다.")

    return Response(content=result_bytes, media_type="image/png")
