"""Patient conversation HTTP routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db, get_monster_db
from app.services.navigator.conversation_service import ConversationService


router = APIRouter(prefix="/conversations", tags=["Patient Conversations"])


class ConversationMessageRequest(BaseModel):
    user_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=4000)


@router.get("/users/{user_id}/messages", response_model=SuccessResponse)
async def get_conversation_history(user_id: int, db: Session = Depends(get_db)):
    messages = ConversationService(db).get_history(user_id)
    return SuccessResponse(
        status="success",
        message="Conversation history retrieved successfully",
        data={"messages": messages},
    )


@router.post("/messages", response_model=SuccessResponse)
async def send_conversation_message(
    payload: ConversationMessageRequest,
    db: Session = Depends(get_db),
    monster_db: Session = Depends(get_monster_db),
):
    data = ConversationService(db, monster_db).send_message(payload.user_id, payload.message)
    return SuccessResponse(status="success", message="Conversation message sent successfully", data=data)