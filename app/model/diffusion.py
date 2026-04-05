from diffusers import StableDiffusion3Pipeline, StableDiffusion3Img2ImgPipeline
import torch
from PIL import Image


MODEL_ID = "stabilityai/stable-diffusion-3.5-medium"
NUM_INFERENCE_STEPS = 30
GUIDANCE_SCALE = 4.5
MAX_SEQUENCE_LENGTH = 512


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

        self._pipe = StableDiffusion3Pipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
        )
        # 모델 컴포넌트를 공유하여 메모리 사용량 절반으로 절감
        self._img2img_pipe = StableDiffusion3Img2ImgPipeline(**self._pipe.components)

        self._pipe.enable_model_cpu_offload()
        # img2img_pipe는 pipe와 같은 컴포넌트를 공유하므로 별도 offload 설정 불필요
        # VAE 메모리 최적화 (슬라이싱·타일링으로 디코딩 시 OOM 방지)
        self._pipe.vae.enable_slicing()
        self._pipe.vae.enable_tiling()
        self._initialized = True

    def generate(self, prompt: str):
        with torch.inference_mode():
            return self._pipe(
                prompt=prompt,
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                max_sequence_length=MAX_SEQUENCE_LENGTH,
            ).images[0]

    def change_image(self, prompt: str, init_image, strength: float):
        # SD3.5는 64의 배수 크기를 요구 - 호환되지 않는 크기는 잠재 텐서 오류 유발
        w, h = init_image.size
        new_w = max(64, (w // 64) * 64)
        new_h = max(64, (h // 64) * 64)
        if new_w != w or new_h != h:
            init_image = init_image.resize((new_w, new_h), Image.LANCZOS)

        with torch.inference_mode():
            return self._img2img_pipe(
                prompt=prompt,
                image=init_image,
                strength=strength,
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                max_sequence_length=MAX_SEQUENCE_LENGTH,
            ).images[0]


diffusion_service = StableDiffusionService()