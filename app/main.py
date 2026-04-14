from fastapi import FastAPI
import uvicorn

if __package__ == "app":
    from .restapi.changeimage import router as changeimage_router
    from .restapi.image2text import router as image2text_router
    from .restapi.generate import router as generate_router
else:
    # Fallback for direct script execution (python app/main.py)
    from restapi.changeimage import router as changeimage_router
    from restapi.image2text import router as image2text_router
    from restapi.generate import router as generate_router

app = FastAPI()

app.include_router(generate_router)
app.include_router(changeimage_router)
app.include_router(image2text_router)

if __name__ == "__main__":
    # 컨테이너 내부 8000 포트 실행
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
