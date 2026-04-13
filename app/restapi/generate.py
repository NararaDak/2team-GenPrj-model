from io import BytesIO

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

router = APIRouter()


class GenerateImageRequest(BaseModel):
    prompt: str | None = None
    positive_prompt: str | None = None
    negative_prompt: str | None = None


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
