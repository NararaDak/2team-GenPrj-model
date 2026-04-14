from typing import Any

import torch
from PIL import Image
from diffusers.utils.import_utils import is_accelerate_available
from diffusers.pipelines.stable_diffusion_3.pipeline_stable_diffusion_3 import StableDiffusion3Pipeline
from diffusers.pipelines.stable_diffusion_3.pipeline_stable_diffusion_3_img2img import (
    StableDiffusion3Img2ImgPipeline,
)


MODEL_ID = "stabilityai/stable-diffusion-3.5-medium"
NUM_INFERENCE_STEPS = 30
GUIDANCE_SCALE = 4.5
MAX_SEQUENCE_LENGTH = 256
OOM_RETRY_MAX_SEQUENCE_LENGTH = 128


def _get_model_torch_dtype() -> torch.dtype:
    if torch.cuda.is_available():
        # 현재 환경에서는 bfloat16 로드 시 일부 컴포넌트가 float16으로 초기화되어
        # 추론 중 dtype mismatch가 발생하므로 CUDA에서는 float16을 사용합니다.
        return torch.float16
    return torch.float32


def _clear_cuda_memory() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


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
        # dtype mismatch를 피하기 위해 디바이스 이동 없이 dtype만 통일합니다.
        # 전체 모델을 즉시 CUDA로 옮기면 startup 단계에서 OOM이 발생할 수 있습니다.
        self._pipe = self._pipe.to(dtype=model_torch_dtype)
        
        # 모델 컴포넌트를 공유하여 메모리 사용량 절반으로 절감
        self._img2img_pipe = StableDiffusion3Img2ImgPipeline(**self._pipe.components)

        if torch.cuda.is_available() and is_accelerate_available():
            try:
                # SD3는 sequential offload가 VRAM 피크 완화에 더 유리합니다.
                self._pipe.enable_sequential_cpu_offload()
            except RuntimeError:
                try:
                    self._pipe.enable_model_cpu_offload()
                except RuntimeError as e:
                    print(f"⚠️ CPU offload 설정 실패: {e}. CPU 모드로 동작합니다.")
        elif torch.cuda.is_available():
            print("⚠️ accelerate를 찾지 못해 CPU offload를 사용하지 않습니다. CPU 모드로 동작합니다.")
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

    def _run_pipe_with_oom_retry(self, run_fn):
        try:
            return run_fn(MAX_SEQUENCE_LENGTH)
        except torch.OutOfMemoryError:
            _clear_cuda_memory()
            print(
                "⚠️ CUDA 메모리 부족으로 max_sequence_length를 줄여 재시도합니다 "
                f"({MAX_SEQUENCE_LENGTH} -> {OOM_RETRY_MAX_SEQUENCE_LENGTH})."
            )
            return run_fn(OOM_RETRY_MAX_SEQUENCE_LENGTH)

    def generate(self, positive_prompt: str, negative_prompt: str | None = None):
        try:
            with torch.inference_mode():
                result: Any = self._run_pipe_with_oom_retry(
                    lambda max_seq_len: self._pipe(
                        prompt=positive_prompt,
                        negative_prompt=negative_prompt,
                        num_inference_steps=NUM_INFERENCE_STEPS,
                        guidance_scale=GUIDANCE_SCALE,
                        max_sequence_length=max_seq_len,
                    )
                )
            image = self._extract_first_image(result)
            del result
            return image
        finally:
            _clear_cuda_memory()

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

        try:
            with torch.inference_mode():
                result: Any = self._run_pipe_with_oom_retry(
                    lambda max_seq_len: self._img2img_pipe(
                        prompt=positive_prompt,
                        negative_prompt=negative_prompt,
                        image=init_image,
                        strength=strength,
                        num_inference_steps=NUM_INFERENCE_STEPS,
                        guidance_scale=GUIDANCE_SCALE,
                        max_sequence_length=max_seq_len,
                    )
                )
            image = self._extract_first_image(result)
            del result
            return image
        finally:
            _clear_cuda_memory()
diffusion_service = StableDiffusionService()
