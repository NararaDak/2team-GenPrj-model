from typing import Any

import torch
from PIL import Image
from diffusers.pipelines.stable_diffusion_3.pipeline_stable_diffusion_3 import StableDiffusion3Pipeline
from diffusers.pipelines.stable_diffusion_3.pipeline_stable_diffusion_3_img2img import (
    StableDiffusion3Img2ImgPipeline,
)


MODEL_ID = "stabilityai/stable-diffusion-3.5-medium"
NUM_INFERENCE_STEPS = 30
GUIDANCE_SCALE = 4.5
MAX_SEQUENCE_LENGTH = 512


def _get_model_torch_dtype() -> torch.dtype:
    if torch.cuda.is_available():
        # 현재 환경에서는 bfloat16 로드 시 일부 컴포넌트가 float16으로 초기화되어
        # 추론 중 dtype mismatch가 발생하므로 CUDA에서는 float16을 사용합니다.
        return torch.float16
    return torch.float32


class StableDiffusionService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        print("🚀 SD 3.5 Medium 모델을 불러오는 중입니다... 잠시만 기다려 주세요.")

        model_torch_dtype = _get_model_torch_dtype()

        self._pipe = StableDiffusion3Pipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=model_torch_dtype,
        )
        # 모델 컴포넌트를 공유하여 메모리 사용량 절반으로 절감
        self._img2img_pipe = StableDiffusion3Img2ImgPipeline(**self._pipe.components)

        self._pipe.enable_model_cpu_offload()
        # img2img_pipe는 pipe와 같은 컴포넌트를 공유하므로 별도 offload 설정 불필요
        # VAE 메모리 최적화 (슬라이싱·타일링으로 디코딩 시 OOM 방지)
        self._pipe.vae.enable_slicing()
        self._pipe.vae.enable_tiling()
        self._initialized = True

    def _extract_first_image(self, result: Any):
        images = getattr(result, "images", None)
        if not images:
            raise RuntimeError("이미지 생성 결과를 찾을 수 없습니다.")
        return images[0]

    def generate(self, positive_prompt: str, negative_prompt: str | None = None):
        with torch.inference_mode():
            result: Any = self._pipe(
                prompt=positive_prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                max_sequence_length=MAX_SEQUENCE_LENGTH,
            )
        return self._extract_first_image(result)

    def change_image(
        self,
        positive_prompt: str,
        init_image,
        strength: float,
        negative_prompt: str | None = None,
    ):
        # SD3.5는 64의 배수 크기를 요구 - 호환되지 않는 크기는 잠재 텐서 오류 유발
        w, h = init_image.size
        new_w = max(64, (w // 64) * 64)
        new_h = max(64, (h // 64) * 64)
        if new_w != w or new_h != h:
            init_image = init_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        with torch.inference_mode():
            result: Any = self._img2img_pipe(
                prompt=positive_prompt,
                negative_prompt=negative_prompt,
                image=init_image,
                strength=strength,
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                max_sequence_length=MAX_SEQUENCE_LENGTH,
            )
        return self._extract_first_image(result)


diffusion_service = StableDiffusionService()