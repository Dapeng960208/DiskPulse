# -*- coding: utf-8 -*-
import json

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from dependencies import CurrentUserDep, get_db
from schemas.aiSchema import ConversationCreate, MessageCreate
from services import ai_chat_service
from services.ai_rate_limit import enforce_ai_rate_limit


router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/models")
def models(_current_user: CurrentUserDep, db: Session = Depends(get_db)):
    return ai_chat_service.list_available_models(db)


@router.get("/conversations")
def conversations(current_user: CurrentUserDep, db: Session = Depends(get_db)):
    return ai_chat_service.list_conversations(db, current_user.id)


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, current_user: CurrentUserDep, db: Session = Depends(get_db)):
    return ai_chat_service.create_conversation(
        db,
        current_user.id,
        payload.title,
        payload.model_id,
        project_id=payload.project_id,
        current_user=current_user,
    )


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: int, current_user: CurrentUserDep, db: Session = Depends(get_db)):
    return ai_chat_service.get_conversation(db, conversation_id, current_user.id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, current_user: CurrentUserDep, db: Session = Depends(get_db)):
    ai_chat_service.delete_conversation(db, conversation_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/conversations/{conversation_id}/messages")
def message(
    conversation_id: int,
    payload: MessageCreate,
    request: Request,
    current_user: CurrentUserDep,
    db: Session = Depends(get_db),
):
    enforce_ai_rate_limit(current_user.id)
    return ai_chat_service.send_message(
        app=request.app,
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        current_user=current_user,
        content=payload.content,
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/conversations/{conversation_id}/messages/stream")
def stream_message(
    conversation_id: int,
    payload: MessageCreate,
    request: Request,
    current_user: CurrentUserDep,
    db: Session = Depends(get_db),
):
    enforce_ai_rate_limit(current_user.id)

    def events():
        stream = ai_chat_service.stream_message(
            app=request.app,
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            current_user=current_user,
            content=payload.content,
        )
        try:
            for event, data in stream:
                yield _sse(event, data)
        finally:
            # Client disconnects close the generator so the audit can record cancellation.
            stream.close()

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
