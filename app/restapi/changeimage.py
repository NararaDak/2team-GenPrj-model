import base64
from io import BytesIO

from fastapi import APIRouter, HTTPException, Response
from PIL import Image
from pydantic import BaseModel, Field

from model.diffusion import diffusion_service

router = APIRouter()


class ChangeImageRequest(BaseModel):
    prompt: str
    image_base64: str = Field(..., description="Base64 encoded image bytes (optionally data URL)")
    strength: float = 0.55


@router.post("/changeimage")
async def change_image(req: ChangeImageRequest):
    if req.strength < 0.0 or req.strength > 1.0:
        raise HTTPException(status_code=400, detail="strength는 0.0~1.0 범위여야 합니다.")

    applied_strength = 0.01 if req.strength == 0.0 else req.strength

    print(f"🛠️ 이미지 변환 요청 프롬프트: {req.prompt}")

    raw_base64 = req.image_base64
    if "," in raw_base64:
        raw_base64 = raw_base64.split(",", 1)[1]

    try:
        input_bytes = base64.b64decode(raw_base64, validate=True)
        init_image = Image.open(BytesIO(input_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="유효한 base64 이미지가 아닙니다.") from exc

    image = diffusion_service.change_image(
        prompt=req.prompt,
        init_image=init_image,
        strength=applied_strength,
    )

    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")

    print("✅ 이미지 변환 완료!")
    return Response(content=img_byte_arr.getvalue(), media_type="image/png")



