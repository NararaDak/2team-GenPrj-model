from fastapi import FastAPI
import uvicorn
from restapi.changeimage import router as changeimage_router
from restapi.generate import router as generate_router

app = FastAPI()

app.include_router(generate_router)
app.include_router(changeimage_router)

if __name__ == "__main__":
    # 컨테이너 내부 8000 포트 실행
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
