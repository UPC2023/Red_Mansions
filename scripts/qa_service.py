from __future__ import annotations

# 屏蔽用户目录的 Python39 站点包，避免 pydantic 冲突
import os, sys
os.environ.setdefault("PYTHONNOUSERSITE", "1")
_BLOCK = [
    "AppData\\Roaming\\Python\\Python39\\site-packages",
    "Python39\\site-packages",
]
sys.path = [p for p in sys.path if not any(b in p for b in _BLOCK)]

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from scripts.qa_intent import detect_intent
from scripts.qa_cypher import build_query, run_query
from scripts.qa_answer import format_answer


app = FastAPI(title="RedDream-KG-QA", version="0.1.0")
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="ui")
app.mount("/photos", StaticFiles(directory="photos"), name="photos")


class QARequest(BaseModel):
    question: str
@app.get("/")
def root():
    return RedirectResponse(url="/ui/")



@app.post("/qa")
def qa(req: QARequest):
    payload = detect_intent(req.question)
    cypher, params = build_query(payload)
    rows = run_query(cypher, params)
    answer = format_answer(payload["intent"], payload, rows)
    return {
        "intent": payload["intent"],
        "payload": payload,
        "cypher": cypher,
        "params": params,
        "rows": rows[:10],
        "answer": answer,
    }


def main():
    # 为 Windows PowerShell 环境提供一键运行入口
    # 延迟导入，避免在未安装时模块导入即失败
    import uvicorn
    uvicorn.run("scripts.qa_service:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
