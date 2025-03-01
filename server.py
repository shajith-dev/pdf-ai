from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
import uvicorn
from chat import PDFChatSession
from jwt import get_current_user

app = FastAPI()


class ChatRequest(BaseModel):
    object_url: str
    query: str


class ChatResponse(BaseModel):
    answer: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    try:
        session = PDFChatSession(request.object_url)
    except Exception as e:
        # Return a 500 error with the exception message.
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}")

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        answer = session.chat(request.query)
    except Exception as e:
        # Return a 500 error if the chat processing fails.
        raise HTTPException(
            status_code=500, detail=f"Chat processing failed: {str(e)}")

    return ChatResponse(answer=answer)


if __name__ == '__main__':
    # Run the FastAPI app using Uvicorn.
    uvicorn.run(app, host="0.0.0.0", port=8000)
