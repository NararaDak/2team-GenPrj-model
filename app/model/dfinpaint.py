from typing import Any
import os

import torch
from PIL import Image
from diffusers.pipelines.auto_pipeline import AutoPipelineForInpainting
from huggingface_hub.errors import RepositoryNotFoundError


MODEL_ID = os.getenv("HF_INPAINT_MODEL_ID", "diffusers/stable-diffusion-xl-1.0-inpainting-0.1")
HF_TOKEN = os.getenv("HF_TOKEN")
NUM_INFERENCE_STEPS = 50
GUIDANCE_SCALE = 7.0
DEFAULT_PROMPT = "high quality cinematic background, seamless texture, natural lighting"
DEFAULT_NEGATIVE_PROMPT = "deformed, ugly, bad anatomy, object remains"


def _get_model_torch_dtype() -> torch.dtype:
    if torch.cuda.is_available():
        return torch.float16
    return torch.float32


def _clear_cuda_memory() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


class StableDiffusionInpaintService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        print("🚀 SDXL Inpainting 모델을 불러오는 중입니다... 잠시만 기다려 주세요.")

        model_torch_dtype = _get_model_torch_dtype()
        is_cuda = torch.cuda.is_available()

        try:
            self._pipe = AutoPipelineForInpainting.from_pretrained(
                MODEL_ID,
                torch_dtype=model_torch_dtype,
                token=HF_TOKEN,
                variant="fp16" if is_cuda else None,
            )
        except RepositoryNotFoundError as error:
            raise RuntimeError(
                f"모델 저장소를 찾을 수 없습니다: {MODEL_ID}. "
                "repo_id가 정확한지 확인하거나, 비공개/게이트 모델이면 HF_TOKEN을 설정하세요."
            ) from error

        if is_cuda:
            self._pipe.enable_model_cpu_offload()
        else:
            self._pipe.to("cpu")

        if hasattr(self._pipe, "vae") and self._pipe.vae is not None:
            self._pipe.vae.enable_slicing()
            self._pipe.vae.enable_tiling()

        self._initialized = True

    def _extract_first_image(self, result: Any):
        images = getattr(result, "images", None)
        if not images:
            raise RuntimeError("인페인팅 결과 이미지를 찾을 수 없습니다.")
        return images[0]

    def _normalize_images(self, init_image: Image.Image, mask_image: Image.Image):
        init_rgb = init_image.convert("RGB")
        mask_l = mask_image.convert("L")

        if mask_l.size != init_rgb.size:
            mask_l = mask_l.resize(init_rgb.size, Image.Resampling.NEAREST)

        w, h = init_rgb.size
        new_w = max(8, (w // 8) * 8)
        new_h = max(8, (h // 8) * 8)
        if new_w != w or new_h != h:
            init_rgb = init_rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)
            mask_l = mask_l.resize((new_w, new_h), Image.Resampling.NEAREST)

        return init_rgb, mask_l

    def inpaint(
        self,
        positive_prompt: str,
        init_image: Image.Image,
        mask_image: Image.Image,
        strength: float = 0.8,
        negative_prompt: str | None = None,
    ):
        if strength < 0.0 or strength > 1.0:
            raise ValueError("strength는 0.0~1.0 범위여야 합니다.")

        applied_strength = 0.01 if strength == 0.0 else strength
        normalized_image, normalized_mask = self._normalize_images(init_image, mask_image)

        try:
            with torch.inference_mode():
                result: Any = self._pipe(
                    prompt=positive_prompt,
                    negative_prompt=negative_prompt,
                    image=normalized_image,
                    mask_image=normalized_mask,
                    guidance_scale=GUIDANCE_SCALE,
                    num_inference_steps=NUM_INFERENCE_STEPS,
                    strength=applied_strength,
                )
            image = self._extract_first_image(result)
            del result
            return image
        finally:
            _clear_cuda_memory()


inpaint_service = StableDiffusionInpaintService()


def inpaint_image(
    image_path: str,
    mask_path: str,
    positive_prompt: str = DEFAULT_PROMPT,
    strength: float = 0.8,
    negative_prompt: str | None = DEFAULT_NEGATIVE_PROMPT,
):
    init_image = Image.open(image_path).convert("RGB")
    mask_image = Image.open(mask_path).convert("RGB")
    return inpaint_service.inpaint(
        positive_prompt=positive_prompt,
        init_image=init_image,
        mask_image=mask_image,
        strength=strength,
        negative_prompt=negative_prompt,
    )


if __name__ == "__main__":
    image_path = "/workspace/project/2team-GenPrj-model/data/images/original_image.png"
    mask_path = "/workspace/project/2team-GenPrj-model/data/images/mask_image.png"
    output_path = "/workspace/project/2team-GenPrj-model/data/images/result_inpainted.png"

    if not os.path.exists(image_path) or not os.path.exists(mask_path):
        raise FileNotFoundError(
            "예시 실행 파일이 없습니다. "
            f"image_path={image_path}, mask_path={mask_path} 경로를 실제 파일로 바꿔 실행하세요."
        )

    result = inpaint_image(
        image_path=image_path,
        mask_path=mask_path,
    )
    result.save(output_path)
    print(f"인페인팅 결과 저장 완료: {output_path}")