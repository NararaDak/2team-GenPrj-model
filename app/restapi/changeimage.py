import base64
from io import BytesIO

from fastapi import APIRouter, HTTPException, Response
from PIL import Image
from pydantic import BaseModel, Field

router = APIRouter()


class ChangeImageRequest(BaseModel):
    prompt: str | None = None
    positive_prompt: str | None = None
    negative_prompt: str | None = None
    image_base64: str = Field(..., description="Base64 encoded image bytes (optionally data URL)")
    strength: float = 0.55


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


@router.post("/changeimage")
async def change_image(req: ChangeImageRequest):
    if req.strength < 0.0 or req.strength > 1.0:
        raise HTTPException(status_code=400, detail="strength는 0.0~1.0 범위여야 합니다.")

    applied_strength = 0.01 if req.strength == 0.0 else req.strength
    resolved_prompt = _resolve_positive_prompt(req.prompt, req.positive_prompt)

    print(f"🛠️ 이미지 변환 요청 positive_prompt: {resolved_prompt}")

    raw_base64 = req.image_base64
    if "," in raw_base64:
        raw_base64 = raw_base64.split(",", 1)[1]

    try:
        input_bytes = base64.b64decode(raw_base64, validate=True)
        init_image = Image.open(BytesIO(input_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="유효한 base64 이미지가 아닙니다.") from exc

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



