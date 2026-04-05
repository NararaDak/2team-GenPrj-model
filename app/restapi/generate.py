from io import BytesIO

from fastapi import APIRouter, Response

from model.diffusion import diffusion_service

router = APIRouter()


@router.get("/generate")
async def generate(prompt: str = "A stylish cafe advertising poster, high quality, 8k"):
    print(f"🎨 요청받은 프롬프트: {prompt}")

    image = diffusion_service.generate(prompt)

    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")

    print("✅ 이미지 생성 완료!")
    return Response(content=img_byte_arr.getvalue(), media_type="image/png")
