from typing import Any

import torch
from PIL import Image
from transformers.models.auto.modeling_auto import AutoModelForCausalLM
from transformers.models.auto.processing_auto import AutoProcessor


MODEL_ID = "microsoft/Florence-2-base"
MAX_NEW_TOKENS = 1024
NUM_BEAMS = 3
DEFAULT_TASK_PROMPT = "<DETAILED_CAPTION>"
FORCED_BOS_TOKEN_ID = 0


class FlorenceService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🚀 Florence 모델을 불러오는 중입니다... (device={self._device})")

        model: Any = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
            # Florence remote config + 일부 transformers 버전 조합에서
            # forced_bos_token_id 속성이 없어서 초기화가 실패하는 문제를 회피합니다.
            forced_bos_token_id=FORCED_BOS_TOKEN_ID,
        )
        self._model: Any = model.to(self._device)

        processor = AutoProcessor.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
        )
        self._processor: Any = processor
        self._initialized = True

    def _extract_text_from_pil_image(self, image: Image.Image, task_prompt: str) -> Any:
        inputs: Any = self._processor(
            text=task_prompt,
            images=image,
            return_tensors="pt",
        ).to(self._device)

        with torch.inference_mode():
            generated_ids = self._model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=MAX_NEW_TOKENS,
                num_beams=NUM_BEAMS,
                do_sample=False,
            )

        generated_text = self._processor.batch_decode(
            generated_ids,
            skip_special_tokens=False,
        )[0]
        parsed_answer = self._processor.post_process_generation(
            generated_text,
            task=task_prompt,
            image_size=(image.width, image.height),
        )
        return parsed_answer[task_prompt]

    def extract_text_from_image(
        self,
        image_path: str,
        task_prompt: str = DEFAULT_TASK_PROMPT,
    ) -> Any:
        """
        이미지에서 텍스트 특성을 추출합니다.
        task_prompt 예: '<CAPTION>', '<DETAILED_CAPTION>', '<MORE_DETAILED_CAPTION>'
        """
        image = Image.open(image_path).convert("RGB")
        return self._extract_text_from_pil_image(image=image, task_prompt=task_prompt)

    def extract_text_from_pil_image(
        self,
        image: Image.Image,
        task_prompt: str = DEFAULT_TASK_PROMPT,
    ) -> Any:
        return self._extract_text_from_pil_image(
            image=image.convert("RGB"),
            task_prompt=task_prompt,
        )


florence_service = FlorenceService()


def extract_text_from_image(image_path: str, task_prompt: str = DEFAULT_TASK_PROMPT) -> Any:
    # 기존 호출 코드와의 호환을 위해 함수 인터페이스를 유지합니다.
    return florence_service.extract_text_from_image(image_path, task_prompt)


if __name__ == "__main__":
    img_path = "/workspace/project/2team-GenPrj-model/data/images/coffee.png"
    result = extract_text_from_image(img_path)
    print(f"추출된 객체 특성:\n{result}")