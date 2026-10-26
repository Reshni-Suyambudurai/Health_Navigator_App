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
    new_session: bool = False


class CareTeamRequest(BaseModel):
    user_id: int = Field(gt=0)
    message: str | None = Field(default=None, max_length=4000)


@router.get("/users/{user_id}/messages", response_model=SuccessResponse)
async def get_conversation_history(
    user_id: int,
    thread_id: int | None = None,
    db: Session = Depends(get_db),
):
    history = ConversationService(db).get_history(user_id, thread_id)
    return SuccessResponse(
        status="success",
        message="Conversation history retrieved successfully",
        data=history,
    )


@router.get("/users/{user_id}/care-team-requests", response_model=SuccessResponse)
async def get_care_team_requests(user_id: int, db: Session = Depends(get_db)):
    requests = ConversationService(db).get_care_team_requests(user_id)
    return SuccessResponse(status="success", message="Care-team requests retrieved successfully", data={"requests": requests})


@router.post("/messages", response_model=SuccessResponse)
async def send_conversation_message(
    payload: ConversationMessageRequest,
    db: Session = Depends(get_db),
    monster_db: Session = Depends(get_monster_db),
):
    data = ConversationService(db, monster_db).send_message(payload.user_id, payload.message, payload.new_session)
    return SuccessResponse(status="success", message="Conversation message sent successfully", data=data)


@router.post("/care-team-requests", response_model=SuccessResponse)
async def create_care_team_request(payload: CareTeamRequest, db: Session = Depends(get_db)):
    data = ConversationService(db).request_care_team_follow_up(payload.user_id, payload.message)
    return SuccessResponse(status="success", message="Care-team request created successfully", data=data)