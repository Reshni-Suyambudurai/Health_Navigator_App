"""FHIR-grounded AI conversation logic for the patient portal."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
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
from app.database.models.clinical_guardrail_matcher import ClinicalGuardrailMatcher, GuardrailMatchType
from app.database.models.clinical_guardrail_rule import (
    ClinicalGuardrailRule,
    GuardrailActionType,
    RuleCategory,
    UrgencyLevel,
)
from app.database.models.emergency_event import EmergencyEvent, EmergencyEventStatus, EmergencyType
from app.database.models.escalation import Escalation, EscalationPriority, EscalationStatus, EscalationType
from app.database.repositories.navigator.conversation_repository import ConversationRepository
from app.services.patientFHIR.patient_fhir_service import PatientFHIRService
from app.services.navigator.trusted_medical_knowledge_service import TrustedMedicalKnowledgeService


@dataclass(frozen=True)
class GuardrailDecision:
    rule: ClinicalGuardrailRule
    matcher: Optional[ClinicalGuardrailMatcher] = None


class ConversationService:
    """Coordinates chat history, patient context, safety rules, and LLM responses."""

    def __init__(self, db: Session, monster_db: Optional[Session] = None):
        self.repository = ConversationRepository(db)
        self.fhir_service = PatientFHIRService(monster_db) if monster_db else None
        self.trusted_medical_knowledge = TrustedMedicalKnowledgeService()

    def get_history(self, user_id: int) -> dict[str, Any]:
        patient = self._patient_for_user(user_id)
        episode = self.repository.find_active_episode(patient.patient_id)
        if not episode:
            return {"messages": [], "emergency_chat_paused": False}

        thread = self.repository.find_current_thread(patient.patient_id, episode.episode_id)
        if not thread:
            return {"messages": [], "emergency_chat_paused": False}

        return {
            "messages": [self._serialize_message(message) for message in self.repository.list_messages(thread.thread_id)],
            "emergency_chat_paused": thread.status == ConversationStatus.PAUSED_EMERGENCY,
        }

    def get_care_team_requests(self, user_id: int) -> list[dict[str, Any]]:
        patient = self._patient_for_user(user_id)
        return [self._serialize_care_team_request(escalation) for escalation in self.repository.list_patient_escalations(patient.patient_id)]

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

        if self.repository.find_paused_emergency_thread(patient.patient_id, episode.episode_id):
            raise ValidationException(
                "Chat is paused for your safety. Please call 911 now.",
                "CHAT_EMERGENCY_PAUSED",
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

        guardrail_decision = self._evaluate_guardrail(text)
        if not guardrail_decision:
            guardrail_decision = self._evaluate_semantic_guardrail(text)
        safety_category = guardrail_decision.rule.rule_category.value.lower() if guardrail_decision else None
        patient_message = self.repository.add_message(
            ConversationMessage(
                thread_id=thread.thread_id,
                sender_type=SenderType.PATIENT,
                sender_user_id=user_id,
                message_text=text,
                message_intent=safety_category or "general_question",
                message_metadata={
                    "safety_category": safety_category,
                    "guardrail_rule_id": guardrail_decision.rule.rule_id if guardrail_decision else None,
                },
                sent_at=self.repository.now(),
            )
        )

        guardrail_hit_id = self._record_guardrail_hit(
            guardrail_decision, patient.patient_id, thread, patient_message, text
        )
        escalation_id = self._create_guardrail_escalation(
            guardrail_decision, patient.patient_id, episode, thread, guardrail_hit_id, text
        )
        self._record_emergency_event(guardrail_decision, patient.patient_id, thread, guardrail_hit_id, text, escalation_id)

        if guardrail_decision:
            response_text = guardrail_decision.rule.patient_response_template or (
                "Your care team should review this message. I have sent it for follow-up."
            )
            response_model_name = "safety-guardrail"
            provider_fallback = False
        else:
            clinical_context = self._clinical_context(patient.external_fhir_patient_id)
            trusted_knowledge = self.trusted_medical_knowledge.get_context(text, clinical_context)
            recent_messages = self._recent_llm_messages(thread.thread_id, patient_message.message_id)
            response_text = self._request_llm(text, clinical_context, trusted_knowledge, recent_messages)
            response_model_name = settings.LLM_MODEL
            provider_fallback = False

        assistant_message = self.repository.add_message(
            ConversationMessage(
                thread_id=thread.thread_id,
                sender_type=SenderType.AI,
                ai_model_name=response_model_name,
                message_text=response_text,
                message_intent=safety_category or "grounded_answer",
                is_guardrail_override=bool(guardrail_decision),
                message_metadata={
                    "safety_category": safety_category,
                    "guardrail_rule_id": guardrail_decision.rule.rule_id if guardrail_decision else None,
                    "guardrail_rule_name": guardrail_decision.rule.rule_name if guardrail_decision else None,
                    "guardrail_action": guardrail_decision.rule.action_type.value if guardrail_decision else None,
                    "llm_bypassed": bool(guardrail_decision),
                    "record_context_used": guardrail_decision is None,
                    "trusted_sources": [source["name"] for source in trusted_knowledge.get("sources", [])]
                    if guardrail_decision is None
                    else [],
                    "escalation_id": escalation_id,
                    "provider_fallback": False if safety_category else provider_fallback,
                },
                sent_at=self.repository.now(),
            )
        )

        emergency_chat_paused = bool(
            guardrail_decision and guardrail_decision.rule.action_type == GuardrailActionType.EMERGENCY_PROTOCOL
        )
        if emergency_chat_paused:
            self.repository.pause_for_emergency(thread)

        try:
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

        return {
            "thread_id": thread.thread_id,
            "patient_message": self._serialize_message(patient_message),
            "assistant_message": self._serialize_message(assistant_message),
            "emergency_chat_paused": emergency_chat_paused,
        }

    def request_care_team_follow_up(self, user_id: int, message_text: Optional[str] = None) -> dict[str, Any]:
        patient = self._patient_for_user(user_id)
        episode = self.repository.find_active_episode(patient.patient_id)
        if not episode:
            raise ValidationException("An active care-navigation episode is required for a care-team request.", "CHAT_EPISODE_REQUIRED")

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

        queue = self.repository.find_active_queue(episode.enrollment_id, QueueType.CLINICAL)
        if not queue:
            queue = self.repository.find_active_queue(episode.enrollment_id, QueueType.CLINICAL_REVIEW)
        if not queue:
            raise ValidationException("Your care team queue is not available right now. Please try again later.", "CARE_TEAM_QUEUE_UNAVAILABLE")

        escalation = self.repository.create_escalation(
            Escalation(
                patient_id=patient.patient_id,
                episode_id=episode.episode_id,
                thread_id=thread.thread_id,
                queue_id=queue.queue_id,
                escalation_type=EscalationType.CLINICAL_REVIEW,
                priority=EscalationPriority.MEDIUM,
                reason=(message_text or "Patient requested care-team follow-up from the portal chat.").strip(),
                patient_summary="Patient requested a human care-team follow-up from the portal chat.",
                status=EscalationStatus.OPEN,
            )
        )
        try:
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise
        return {"escalation_id": escalation.escalation_id, "status": escalation.status.value}

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

    def _record_guardrail_hit(
        self, decision: Optional[GuardrailDecision], patient_id: int, thread, message, text: str
    ) -> Optional[int]:
        if not decision:
            return None

        guardrail_hit = self.repository.add_guardrail_hit(
            ConversationGuardrailHit(
                thread_id=thread.thread_id,
                message_id=message.message_id,
                patient_id=patient_id,
                rule_id=decision.rule.rule_id,
                hit_urgency_level=self._hit_urgency_level(decision.rule.urgency_level),
                action_taken=self._hit_action(decision.rule.action_type),
                hit_reason=text,
            )
        )
        return guardrail_hit.guardrail_hit_id

    def _create_guardrail_escalation(
        self, decision: Optional[GuardrailDecision], patient_id: int, episode, thread, guardrail_hit_id: Optional[int], text: str
    ) -> Optional[int]:
        if not decision or decision.rule.action_type not in {
            GuardrailActionType.ESCALATE,
            GuardrailActionType.EMERGENCY_PROTOCOL,
            GuardrailActionType.CREATE_ESCALATION,
        }:
            return None

        queue_type = decision.rule.target_queue_type or QueueType.CLINICAL
        queue = self.repository.find_active_queue(episode.enrollment_id, queue_type)
        if not queue and queue_type != QueueType.CLINICAL:
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
                escalation_type=decision.rule.escalation_type or EscalationType.CLINICAL_REVIEW,
                priority=decision.rule.escalation_priority or EscalationPriority.MEDIUM,
                reason=text,
                patient_summary=f"Patient chat guardrail trigger: {decision.rule.rule_name}",
                status=EscalationStatus.OPEN,
            )
        )
        return escalation.escalation_id

    def _record_emergency_event(
        self, decision: Optional[GuardrailDecision], patient_id: int, thread, guardrail_hit_id: Optional[int], text: str,
        escalation_id: Optional[int],
    ) -> None:
        emergency_type = self._emergency_type(text) if decision and decision.rule.action_type == GuardrailActionType.EMERGENCY_PROTOCOL else None
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

    def _recent_llm_messages(self, thread_id: int, current_message_id: int) -> list[dict[str, str]]:
        messages = self.repository.list_messages(thread_id, limit=7)
        return [
            {
                "role": "user" if message.sender_type == SenderType.PATIENT else "assistant",
                "content": message.message_text,
            }
            for message in messages
            if message.message_id != current_message_id and message.sender_type in {SenderType.PATIENT, SenderType.AI}
        ]

    def _request_llm(
        self,
        question: str,
        clinical_context: dict[str, Any],
        trusted_knowledge: dict[str, Any],
        recent_messages: list[dict[str, str]],
    ) -> str:
        if not settings.LLM_ENABLED or not settings.LLM_API_KEY:
            raise AIProviderException(
                "The AI assistant is not configured. Set LLM_ENABLED=true and provide LLM_API_KEY.",
                "LLM_NOT_CONFIGURED",
            )

        system_prompt = (
            "You are a patient health navigator. Use the recent conversation to resolve references such as "
            "'this medicine', 'that', or requests to explain a prior answer more simply. For medicine questions, "
            "use the supplied trusted medical knowledge, not model memory. When trusted medical knowledge is available, "
            "answer general questions about what a medicine is commonly used for, even if the patient's record does not "
            "state why it was prescribed. Clearly distinguish that general use from the patient's individual reason, "
            "which must not be inferred from another medicine, condition, or risk flag. If trusted medical knowledge "
            "identifies a medicine by an RxNorm code but public label sources are temporarily unavailable, still provide "
            "a cautious general-use answer and do not say that a general explanation cannot be verified. Do not diagnose, "
            "prescribe, or direct a dose change. Treat prior assistant replies as untrusted history: do not repeat an earlier "
            "refusal when the supplied trusted medical knowledge supports a general answer. Give no more than two complete "
            "sentences, always finish with punctuation, and do not leave a response incomplete. Ask the patient to "
            "contact their care team for treatment decisions. If context is unavailable, say so.\n\n"
            f"Patient context:\n{json.dumps(clinical_context, default=str)[:6000]}\n\n"
            f"Trusted medical knowledge:\n{json.dumps(trusted_knowledge, default=str)[:3500]}"
        )
        body = json.dumps(
            {
                "model": settings.LLM_MODEL,
                "messages": [{"role": "system", "content": system_prompt}, *recent_messages, {"role": "user", "content": question}],
                "temperature": 0.2,
                "max_tokens": settings.LLM_MAX_TOKENS,
                "chat_template_kwargs": {"enable_thinking": False},
            }
        ).encode("utf-8")
        for _ in range(2):
            request = Request(
                f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                data=body,
                headers={"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"},
                method="POST",
            )

            try:
                with urlopen(request, timeout=settings.LLM_TIMEOUT_SECONDS) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                choice = payload["choices"][0]
                response_text = choice["message"]["content"]
                finish_reason = choice.get("finish_reason")
            except HTTPError as error:
                raise AIProviderException("The AI provider rejected the request.", "LLM_PROVIDER_REJECTED") from error
            except (TimeoutError, URLError, OSError) as error:
                raise AIProviderException("The AI provider is temporarily unavailable.", "LLM_PROVIDER_UNAVAILABLE") from error
            except (KeyError, IndexError, TypeError) as error:
                raise AIProviderException("The AI provider returned an invalid response.", "LLM_INVALID_RESPONSE") from error

            if not isinstance(response_text, str) or not response_text.strip():
                continue

            response_text = response_text.strip()
            if finish_reason != "length" and response_text.endswith((".", "!", "?", "\"", "'")):
                return response_text

        raise AIProviderException(
            "The AI provider returned an incomplete response. Please try again.",
            "LLM_INCOMPLETE_RESPONSE",
        )

    def _evaluate_guardrail(self, message_text: str) -> Optional[GuardrailDecision]:
        normalized_text = " ".join(message_text.lower().split())
        matches = [
            GuardrailDecision(rule=rule, matcher=matcher)
            for rule, matcher in self.repository.list_active_guardrail_matchers()
            if self._matcher_matches(normalized_text, matcher)
        ]
        if not matches:
            return None

        return min(matches, key=self._guardrail_precedence)

    def _evaluate_semantic_guardrail(self, message_text: str) -> Optional[GuardrailDecision]:
        """Maps paraphrased safety concerns to an existing active database rule."""
        if not settings.LLM_ENABLED or not settings.LLM_API_KEY:
            return None

        rules_by_id = {
            rule.rule_id: rule
            for rule, _ in self.repository.list_active_guardrail_matchers()
            if rule.rule_category
            in {
                RuleCategory.EMERGENCY,
                RuleCategory.MEDICATION,
                RuleCategory.SYMPTOM,
                RuleCategory.SYMPTOM_SAFETY,
                RuleCategory.CLINICAL_SCOPE,
            }
        }
        if not rules_by_id:
            return None

        rule_catalog = [
            {
                "rule_id": rule.rule_id,
                "name": rule.rule_name,
                "category": rule.rule_category.value,
                "urgency": rule.urgency_level.value,
                "action": rule.action_type.value,
            }
            for rule in rules_by_id.values()
        ]
        rule_id = self._request_semantic_guardrail_rule_id(message_text, rule_catalog)
        return GuardrailDecision(rule=rules_by_id[rule_id]) if rule_id in rules_by_id else None

    def _request_semantic_guardrail_rule_id(self, message_text: str, rule_catalog: list[dict[str, Any]]) -> Optional[int]:
        prompt = (
            "You classify patient messages for safety. Choose a rule only when the message clearly matches its category "
            "or urgency. Do not diagnose. For MEDICATION rules, match only requests to start, stop, increase, "
            "decrease, or otherwise change a medicine, or reports of side effects, reactions, or interactions. "
            "For general medication-information questions, such as what a medicine is for, its common uses, or how "
            "it works, return null. Do not classify those questions as CLINICAL_SCOPE, even if the patient asks why "
            "they personally received the medicine or says their record has no directions. "
            "Reply with JSON only: {\"rule_id\": positive integer} or {\"rule_id\": null}.\n\n"
            f"Active database rules:\n{json.dumps(rule_catalog)}\n\nPatient message:\n{message_text}"
        )
        body = json.dumps(
            {
                "model": settings.LLM_MODEL,
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0,
                "max_tokens": 40,
                "chat_template_kwargs": {"enable_thinking": False},
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
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            rule_id = parsed.get("rule_id")
            return int(rule_id) if isinstance(rule_id, int) or (isinstance(rule_id, str) and re.fullmatch(r"\d+", rule_id)) else None
        except (HTTPError, URLError, OSError, TimeoutError, ValueError, KeyError, IndexError, TypeError):
            return None

    @staticmethod
    def _matcher_matches(normalized_text: str, matcher: ClinicalGuardrailMatcher) -> bool:
        normalized_pattern = " ".join(matcher.pattern.lower().split())
        if matcher.match_type == GuardrailMatchType.ALL_TERMS:
            terms = [term.strip() for term in normalized_pattern.split("|") if term.strip()]
            return bool(terms) and all(term in normalized_text for term in terms)
        return normalized_pattern in normalized_text

    @staticmethod
    def _guardrail_precedence(decision: GuardrailDecision) -> tuple[int, int, int, int]:
        urgency_rank = {
            UrgencyLevel.EMERGENCY: 0,
            UrgencyLevel.HIGH: 1,
            UrgencyLevel.SAME_DAY: 1,
            UrgencyLevel.ROUTINE: 2,
        }.get(decision.rule.urgency_level, 3)
        category_rank = {
            RuleCategory.EMERGENCY: 0,
            RuleCategory.MEDICATION: 1,
            RuleCategory.SYMPTOM: 2,
            RuleCategory.CLINICAL_SCOPE: 3,
            RuleCategory.PRIVACY: 4,
            RuleCategory.SYMPTOM_SAFETY: 2,
        }.get(decision.rule.rule_category, 5)
        matcher_priority = decision.matcher.priority if decision.matcher else 999
        return urgency_rank, category_rank, matcher_priority, decision.rule.rule_id

    @staticmethod
    def _hit_urgency_level(urgency_level: UrgencyLevel) -> GuardrailHitUrgencyLevel:
        return {
            UrgencyLevel.EMERGENCY: GuardrailHitUrgencyLevel.EMERGENCY,
            UrgencyLevel.HIGH: GuardrailHitUrgencyLevel.HIGH,
            UrgencyLevel.SAME_DAY: GuardrailHitUrgencyLevel.SAME_DAY,
            UrgencyLevel.ROUTINE: GuardrailHitUrgencyLevel.ROUTINE,
        }[urgency_level]

    @staticmethod
    def _hit_action(action_type: GuardrailActionType) -> GuardrailActionTaken:
        return {
            GuardrailActionType.SAFE_RESPOND: GuardrailActionTaken.SAFE_RESPOND,
            GuardrailActionType.BLOCK_RESPONSE: GuardrailActionTaken.BLOCK_RESPONSE,
            GuardrailActionType.ESCALATE: GuardrailActionTaken.ESCALATE,
            GuardrailActionType.EMERGENCY_PROTOCOL: GuardrailActionTaken.EMERGENCY_PROTOCOL,
            GuardrailActionType.CREATE_ESCALATION: GuardrailActionTaken.ESCALATE,
        }[action_type]

    @staticmethod
    def _emergency_type(message_text: str) -> Optional[EmergencyType]:
        normalized_text = message_text.lower()
        if "chest pain" in normalized_text:
            return EmergencyType.CHEST_PAIN
        if "trouble breathing" in normalized_text or "shortness of breath" in normalized_text:
            return EmergencyType.BREATHING_DIFFICULTY
        if "stroke" in normalized_text:
            return EmergencyType.STROKE_SYMPTOMS
        if any(term in normalized_text for term in ("suicidal", "kill myself", "want to die", "hurt myself", "self harm")):
            return EmergencyType.SUICIDAL_IDEATION
        return None

    @staticmethod
    def _serialize_message(message: ConversationMessage) -> dict[str, Any]:
        metadata = message.message_metadata or {}
        safety_category = metadata.get("safety_category")
        source_labels = []
        if metadata.get("record_context_used"):
            source_labels.append("Your care record")
        elif safety_category == "medication":
            source_labels.append("Medication safety guidance")
        elif safety_category == "emergency":
            source_labels.append("Emergency guidance")
        elif safety_category in {"symptom", "clinical_scope"}:
            source_labels.append("Care-team safety guidance")

        return {
            "message_id": message.message_id,
            "sender": {
                SenderType.PATIENT: "patient",
                SenderType.STAFF: "staff",
            }.get(message.sender_type, "assistant"),
            "text": message.message_text,
            "sent_at": message.sent_at.isoformat(),
            "safety_category": safety_category,
            "escalation_id": metadata.get("escalation_id"),
            "is_guardrail_override": message.is_guardrail_override,
            "source_labels": [*source_labels, *metadata.get("trusted_sources", [])],
        }

    def _serialize_care_team_request(self, escalation: Escalation) -> dict[str, Any]:
        messages = []
        if escalation.thread_id:
            messages = [
                {"text": message.message_text, "sent_at": message.sent_at.isoformat()}
                for message in self.repository.list_messages(escalation.thread_id)
                if message.sender_type == SenderType.STAFF
                and str((message.message_metadata or {}).get("escalation_id")) == str(escalation.escalation_id)
            ]

        return {
            "escalation_id": escalation.escalation_id,
            "reason": escalation.reason or "Care-team follow-up requested.",
            "status": escalation.status.value,
            "created_at": escalation.created_at.isoformat(),
            "resolved_at": escalation.resolved_at.isoformat() if escalation.resolved_at else None,
            "messages": messages,
        }