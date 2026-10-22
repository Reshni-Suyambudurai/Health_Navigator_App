"""FHIR-grounded AI conversation logic for the patient portal."""

from __future__ import annotations

import json
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AIProviderException, NotFoundException, ValidationException
from app.database.models.conversation_guardrail_hit import (
    ConversationGuardrailHit,
    GuardrailActionTaken,
    GuardrailHitUrgencyLevel,
)
from app.database.models.conversation_message import ConversationMessage, SenderType
from app.database.models.conversation_thread import ConversationChannel, ConversationStatus, ConversationThread
from app.database.models.care_team_queue import QueueType
from app.database.models.emergency_event import EmergencyEvent, EmergencyEventStatus, EmergencyType
from app.database.models.escalation import Escalation, EscalationPriority, EscalationStatus, EscalationType
from app.database.repositories.navigator.conversation_repository import ConversationRepository
from app.services.patientFHIR.patient_fhir_service import PatientFHIRService


EMERGENCY_TERMS = (
    "chest pain",
    "trouble breathing",
    "shortness of breath",
    "stroke",
    "fainting",
    "unconscious",
    "suicidal",
    "kill myself",
)
MEDICATION_REVIEW_TERMS = (
    "stop taking",
    "start taking",
    "can i take",
    "can i use",
    "can i have",
    "is it safe to take",
    "how much can i take",
    "increase dose",
    "reduce dose",
    "change dose",
    "change my dose",
    "skip dose",
    "double dose",
    "side effect",
    "dizzy",
    "dizziness",
)


class ConversationService:
    """Coordinates chat history, patient context, safety rules, and LLM responses."""

    def __init__(self, db: Session, monster_db: Optional[Session] = None):
        self.repository = ConversationRepository(db)
        self.fhir_service = PatientFHIRService(monster_db) if monster_db else None

    def get_history(self, user_id: int) -> list[dict[str, Any]]:
        patient = self._patient_for_user(user_id)
        episode = self.repository.find_active_episode(patient.patient_id)
        if not episode:
            return []

        thread = self.repository.find_active_thread(patient.patient_id, episode.episode_id)
        if not thread:
            return []

        return [self._serialize_message(message) for message in self.repository.list_messages(thread.thread_id)]

    def send_message(self, user_id: int, message_text: str) -> dict[str, Any]:
        text = message_text.strip()
        if not text:
            raise ValidationException("A chat message is required.", "CHAT_MESSAGE_REQUIRED")

        patient = self._patient_for_user(user_id)
        episode = self.repository.find_active_episode(patient.patient_id)
        if not episode:
            raise ValidationException(
                "An active care-navigation episode is required before starting a conversation.",
                "CHAT_EPISODE_REQUIRED",
            )

        thread = self.repository.find_active_thread(patient.patient_id, episode.episode_id)
        if not thread:
            thread = self.repository.create_thread(
                ConversationThread(
                    patient_id=patient.patient_id,
                    episode_id=episode.episode_id,
                    channel=ConversationChannel.PORTAL,
                    language=patient.preferred_language or "en",
                    started_at=self.repository.now(),
                    status=ConversationStatus.ACTIVE,
                )
            )

        safety_category = self._safety_category(text)
        patient_message = self.repository.add_message(
            ConversationMessage(
                thread_id=thread.thread_id,
                sender_type=SenderType.PATIENT,
                sender_user_id=user_id,
                message_text=text,
                message_intent=safety_category or "general_question",
                message_metadata={"safety_category": safety_category},
                sent_at=self.repository.now(),
            )
        )

        guardrail_hit_id = self._record_guardrail_hit(safety_category, patient.patient_id, thread, patient_message, text)
        escalation_id = self._create_safety_escalation(
            safety_category, patient.patient_id, episode, thread, guardrail_hit_id, text
        )
        self._record_emergency_event(safety_category, patient.patient_id, thread, guardrail_hit_id, text, escalation_id)

        if safety_category == "emergency":
            response_text = (
                "This could be an emergency. Call 911 now. Do not wait for a reply here or drive yourself. "
                "If you can, ask someone nearby to stay with you."
            )
            if escalation_id:
                response_text += " Your care team has also been alerted."
        elif safety_category == "medication_review":
            response_text = (
                "I cannot tell you to start, stop, or change a medicine. Please contact your nurse or prescriber "
                "today before changing it."
            )
            if escalation_id:
                response_text += " I have sent your message to your care team for review."
        else:
            clinical_context = self._clinical_context(patient.external_fhir_patient_id)
            record_response = self._medication_record_response(text, clinical_context)
            if record_response:
                response_text = record_response
                response_model_name = "record-lookup"
                provider_fallback = False
            else:
                try:
                    response_text = self._request_llm(text, clinical_context)
                    response_model_name = settings.LLM_MODEL
                    provider_fallback = False
                except AIProviderException:
                    response_text = self._record_based_fallback(text, clinical_context)
                    response_model_name = "record-fallback"
                    provider_fallback = True

        assistant_message = self.repository.add_message(
            ConversationMessage(
                thread_id=thread.thread_id,
                sender_type=SenderType.AI,
                ai_model_name="safety-guardrail" if safety_category else response_model_name,
                message_text=response_text,
                message_intent=safety_category or "grounded_answer",
                is_guardrail_override=bool(safety_category),
                message_metadata={
                    "safety_category": safety_category,
                    "record_context_used": safety_category is None,
                    "escalation_id": escalation_id,
                    "provider_fallback": False if safety_category else provider_fallback,
                },
                sent_at=self.repository.now(),
            )
        )

        try:
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

        return {
            "thread_id": thread.thread_id,
            "patient_message": self._serialize_message(patient_message),
            "assistant_message": self._serialize_message(assistant_message),
        }

    def _patient_for_user(self, user_id: int):
        patient = self.repository.find_patient_by_user_id(user_id)
        if not patient:
            raise NotFoundException("Patient profile not found for this user.", "CHAT_PATIENT_NOT_FOUND")
        return patient

    def _clinical_context(self, external_fhir_patient_id: Optional[str]) -> dict[str, Any]:
        if not external_fhir_patient_id or not self.fhir_service:
            return {"record_status": "No linked clinical record is available."}

        try:
            fhir_patient = self.fhir_service.get_patient_by_fhir_id(external_fhir_patient_id)
            fhir_patient_id = str(fhir_patient.get("id", ""))
            if not fhir_patient_id:
                return {"record_status": "No linked clinical record is available."}

            context = self.fhir_service.get_patient_context(fhir_patient_id)
            return {
                "record_status": "available",
                "conditions": context.get("conditions", [])[:5],
                "medications": context.get("medications", [])[:5],
                "care_plans": context.get("care_plans", [])[:3],
                "upcoming_appointments": context.get("upcoming_appointments", [])[:3],
                "risk_flags": context.get("risk_flags", []),
            }
        except Exception:
            return {"record_status": "temporarily unavailable"}

    def _record_guardrail_hit(self, safety_category: Optional[str], patient_id: int, thread, message, text: str) -> Optional[int]:
        if safety_category != "emergency":
            return None

        rule = self.repository.find_active_guardrail_rule()
        if not rule:
            return None

        guardrail_hit = self.repository.add_guardrail_hit(
            ConversationGuardrailHit(
                thread_id=thread.thread_id,
                message_id=message.message_id,
                patient_id=patient_id,
                rule_id=rule.rule_id,
                hit_urgency_level=GuardrailHitUrgencyLevel.EMERGENCY,
                action_taken=GuardrailActionTaken.EMERGENCY_PROTOCOL,
                hit_reason=text,
            )
        )
        return guardrail_hit.guardrail_hit_id

    def _create_safety_escalation(
        self, safety_category: Optional[str], patient_id: int, episode, thread, guardrail_hit_id: Optional[int], text: str
    ) -> Optional[int]:
        if safety_category == "emergency":
            queue_type = QueueType.EMERGENCY
            escalation_type = EscalationType.EMERGENCY
            priority = EscalationPriority.CRITICAL
        elif safety_category == "medication_review":
            queue_type = QueueType.MEDICATION
            escalation_type = EscalationType.MEDICATION
            priority = EscalationPriority.HIGH
        else:
            return None

        queue = self.repository.find_active_queue(episode.enrollment_id, queue_type)
        if not queue:
            queue = self.repository.find_active_queue(episode.enrollment_id, QueueType.CLINICAL)
        if not queue:
            return None

        escalation = self.repository.create_escalation(
            Escalation(
                patient_id=patient_id,
                episode_id=episode.episode_id,
                thread_id=thread.thread_id,
                guardrail_hit_id=guardrail_hit_id,
                queue_id=queue.queue_id,
                escalation_type=escalation_type,
                priority=priority,
                reason=text,
                patient_summary=f"Patient chat safety trigger: {safety_category}",
                status=EscalationStatus.OPEN,
            )
        )
        return escalation.escalation_id

    def _record_emergency_event(
        self, safety_category: Optional[str], patient_id: int, thread, guardrail_hit_id: Optional[int], text: str,
        escalation_id: Optional[int],
    ) -> None:
        emergency_type = self._emergency_type(text) if safety_category == "emergency" else None
        if not emergency_type or not guardrail_hit_id:
            return

        self.repository.add_emergency_event(
            EmergencyEvent(
                patient_id=patient_id,
                thread_id=thread.thread_id,
                guardrail_hit_id=guardrail_hit_id,
                emergency_type=emergency_type,
                emergency_instruction_sent=True,
                notified_care_team=bool(escalation_id),
                event_status=EmergencyEventStatus.OPEN,
                detected_at=self.repository.now(),
            )
        )

    def _request_llm(self, question: str, clinical_context: dict[str, Any]) -> str:
        if not settings.LLM_ENABLED or not settings.LLM_API_KEY:
            raise AIProviderException(
                "The AI assistant is not configured. Set LLM_ENABLED=true and provide LLM_API_KEY.",
                "LLM_NOT_CONFIGURED",
            )

        system_prompt = (
            "You are a patient health navigator. Answer only from the supplied clinical context when discussing "
            "the patient record. Do not diagnose, prescribe, or change a dose. Use plain language, be concise, "
            "and ask the patient to contact their care team for decisions. If context is unavailable, say so.\n\n"
            f"Clinical context:\n{json.dumps(clinical_context, default=str)[:8000]}"
        )
        body = json.dumps(
            {
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.2,
                "max_tokens": settings.LLM_MAX_TOKENS,
            }
        ).encode("utf-8")
        request = Request(
            f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=settings.LLM_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
            response_text = payload["choices"][0]["message"]["content"]
        except HTTPError as error:
            raise AIProviderException("The AI provider rejected the request.", "LLM_PROVIDER_REJECTED") from error
        except (TimeoutError, URLError, OSError) as error:
            raise AIProviderException("The AI provider is temporarily unavailable.", "LLM_PROVIDER_UNAVAILABLE") from error
        except (KeyError, IndexError, TypeError) as error:
            raise AIProviderException("The AI provider returned an invalid response.", "LLM_INVALID_RESPONSE") from error

        if not isinstance(response_text, str) or not response_text.strip():
            raise AIProviderException("The AI provider returned an empty response.", "LLM_EMPTY_RESPONSE")
        return response_text.strip()

    @staticmethod
    def _record_based_fallback(question: str, clinical_context: dict[str, Any]) -> str:
        if clinical_context.get("record_status") != "available":
            return (
                "I saved your question, but the AI service is temporarily unavailable and I cannot access a complete "
                "record-based answer right now. Please contact your care team for guidance."
            )

        question_lower = question.lower()
        medications = clinical_context.get("medications", [])
        if isinstance(medications, list):
            for medication in medications:
                if not isinstance(medication, dict):
                    continue
                name = str(medication.get("medication_name") or medication.get("name") or "").strip()
                dosage = str(medication.get("dosage_text") or medication.get("dosage") or "").strip()
                if name and name.lower() in question_lower:
                    details = f" The directions in your record are: {dosage}." if dosage else ""
                    return (
                        f"The AI service is temporarily unavailable. Your record lists {name} as an active medicine."
                        f"{details} Please contact your care team before changing how you take it."
                    )

        return (
            "The AI service is temporarily unavailable. I saved your question in this conversation. "
            "Please contact your care team for guidance based on your record."
        )

    @staticmethod
    def _medication_record_response(question: str, clinical_context: dict[str, Any]) -> Optional[str]:
        if clinical_context.get("record_status") != "available":
            return None

        question_lower = question.lower()
        if any(phrase in question_lower for phrase in ("why", "what is this for", "what is it for", "what does", "purpose")):
            return None

        medications = clinical_context.get("medications", [])
        if not isinstance(medications, list):
            return None

        ingredient_matches: list[dict[str, Any]] = []
        for medication in medications:
            if not isinstance(medication, dict):
                continue
            name = str(medication.get("medication_name") or medication.get("name") or "").strip()
            dosage = str(medication.get("dosage_text") or medication.get("dosage") or "").strip()
            if name and name.lower() in question_lower:
                directions = f" The directions in your record are: {dosage}." if dosage else ""
                return (
                    f"Your record lists {name} as an active medicine.{directions} "
                    "Please contact your care team before changing how you take it."
                )

            ingredient = name.lower().split(maxsplit=1)[0] if name else ""
            if len(ingredient) >= 4 and ingredient in question_lower:
                ingredient_matches.append(medication)

        if len(ingredient_matches) == 1:
            medication = ingredient_matches[0]
            name = str(medication.get("medication_name") or medication.get("name") or "").strip()
            dosage = str(medication.get("dosage_text") or medication.get("dosage") or "").strip()
            directions = f" The directions in your record are: {dosage}." if dosage else ""
            return (
                f"Your record lists {name} as an active medicine.{directions} "
                "Please contact your care team before changing how you take it."
            )

        return None

    @staticmethod
    def _safety_category(message_text: str) -> Optional[str]:
        normalized_text = message_text.lower()
        if any(term in normalized_text for term in EMERGENCY_TERMS):
            return "emergency"
        if any(term in normalized_text for term in MEDICATION_REVIEW_TERMS):
            return "medication_review"
        return None

    @staticmethod
    def _emergency_type(message_text: str) -> Optional[EmergencyType]:
        normalized_text = message_text.lower()
        if "chest pain" in normalized_text:
            return EmergencyType.CHEST_PAIN
        if "trouble breathing" in normalized_text or "shortness of breath" in normalized_text:
            return EmergencyType.BREATHING_DIFFICULTY
        if "stroke" in normalized_text:
            return EmergencyType.STROKE_SYMPTOMS
        if "suicidal" in normalized_text or "kill myself" in normalized_text:
            return EmergencyType.SUICIDAL_IDEATION
        return None

    @staticmethod
    def _serialize_message(message: ConversationMessage) -> dict[str, Any]:
        metadata = message.message_metadata or {}
        safety_category = metadata.get("safety_category")
        source_labels = []
        if metadata.get("record_context_used"):
            source_labels.append("Your care record")
        elif safety_category == "medication_review":
            source_labels.append("Medication safety guidance")
        elif safety_category == "emergency":
            source_labels.append("Emergency guidance")

        return {
            "message_id": message.message_id,
            "sender": "patient" if message.sender_type == SenderType.PATIENT else "assistant",
            "text": message.message_text,
            "sent_at": message.sent_at.isoformat(),
            "safety_category": safety_category,
            "escalation_id": metadata.get("escalation_id"),
            "is_guardrail_override": message.is_guardrail_override,
            "source_labels": source_labels,
        }