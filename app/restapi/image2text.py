import base64
from io import BytesIO
from typing import Any

from fastapi import APIRouter, HTTPException
from PIL import Image
from pydantic import BaseModel, Field


router = APIRouter()


class Image2TextRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image bytes (optionally data URL)")
    task_prompt: str = "<DETAILED_CAPTION>"


def _get_florence_service():
    if __package__ == "app.restapi":
        from ..model.florence import florence_service
    else:
        from model.florence import florence_service

    return florence_service


@router.post("/image2text")
async def image2text(req: Image2TextRequest) -> dict[str, Any]:
    raw_base64 = (req.image_base64 or "").strip()
    if not raw_base64:
        raise HTTPException(status_code=400, detail="image_base64는 필수입니다.")

    if "," in raw_base64:
        raw_base64 = raw_base64.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(raw_base64, validate=True)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="유효한 base64 이미지가 아닙니다.") from exc

    text = _get_florence_service().extract_text_from_pil_image(
        image=image,
        task_prompt=(req.task_prompt or "<DETAILED_CAPTION>").strip() or "<DETAILED_CAPTION>",
    )

    return {"text": text}
