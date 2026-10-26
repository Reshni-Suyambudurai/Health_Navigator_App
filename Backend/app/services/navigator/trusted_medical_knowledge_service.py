"""Retrieves public, authoritative medication information for patient education."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen


class TrustedMedicalKnowledgeService:
    """Builds a small, source-attributed knowledge context from public health APIs."""

    def get_context(self, question: str, clinical_context: dict[str, Any]) -> dict[str, Any]:
        medication = self._referenced_medication(question, clinical_context.get("medications", []))
        condition = self._referenced_condition(question, clinical_context.get("conditions", []))
        if not medication and self._is_medication_question(question):
            rxnorm_code = self._rxnorm_code_for_question(question)
            if rxnorm_code:
                medication = {
                    "medication_name": self._rxnorm_name(rxnorm_code) or question,
                    "rxnorm_code": rxnorm_code,
                }
        if not medication and not condition:
            return {"status": "not_applicable", "sources": []}

        sources: list[dict[str, str]] = []
        result: dict[str, Any] = {"status": "temporarily_unavailable", "sources": sources}

        if medication:
            medication_name = str(medication.get("medication_name") or "").strip()
            rxnorm_code = str(medication.get("rxnorm_code") or "").strip() or self._rxnorm_code_for_name(medication_name)
            result["medication"] = {
                "name": medication_name,
                "rxnorm_code": rxnorm_code or None,
                "recorded_reason": medication.get("reason"),
            }

            medline_plus = self._medline_plus(rxnorm_code, medication_name)
            if medline_plus:
                sources.append(medline_plus)

            fda_label = self._open_fda_label(rxnorm_code)
            if fda_label:
                sources.append(fda_label)

            if not sources:
                fda_label = self._open_fda_label_by_name(medication_name)
                if fda_label:
                    sources.append(fda_label)

        if condition:
            condition_code = str(condition.get("condition_code") or "").strip()
            condition_name = str(condition.get("condition_name") or "").strip()
            result["condition"] = {"name": condition_name, "code": condition_code or None}
            medline_plus = self._medline_plus_condition(condition_code, condition_name)
            if medline_plus:
                sources.append(medline_plus)

        result["status"] = "available" if sources else "temporarily_unavailable"
        return result

    @staticmethod
    def _referenced_medication(question: str, medications: list[dict[str, Any]]) -> dict[str, Any] | None:
        normalized_question = question.lower()
        for medication in medications:
            medication_name = str(medication.get("medication_name") or "").lower()
            if medication_name and medication_name in normalized_question:
                return medication

            medication_generic_name = re.split(r"\s+\d", medication_name, maxsplit=1)[0].strip()
            if medication_generic_name and medication_generic_name in normalized_question:
                return medication

        if any(term in normalized_question for term in ("medicine", "medication", "drug", "pill")):
            return medications[0] if medications else None
        return None

    @staticmethod
    def _referenced_condition(question: str, conditions: list[dict[str, Any]]) -> dict[str, Any] | None:
        normalized_question = question.lower()
        for condition in conditions:
            condition_name = str(condition.get("condition_name") or "").lower()
            if condition_name and condition_name in normalized_question:
                return condition

        if any(term in normalized_question for term in ("condition", "diagnosis", "health problem")):
            return conditions[0] if conditions else None
        return None

    @staticmethod
    def _is_medication_question(question: str) -> bool:
        normalized_question = question.lower()
        return any(term in normalized_question for term in ("medicine", "medication", "drug", "tablet", "pill", "capsule"))

    @staticmethod
    def _read_json(url: str) -> dict[str, Any] | None:
        try:
            with urlopen(url, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
        except (OSError, TimeoutError, ValueError):
            return None

    def _rxnorm_code_for_name(self, medication_name: str) -> str:
        if not medication_name:
            return ""

        payload = self._read_json(
            f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={quote(medication_name)}&search=2"
        )
        codes = ((payload or {}).get("idGroup") or {}).get("rxnormId") or []
        return str(codes[0]).strip() if codes else ""

    def _rxnorm_code_for_question(self, question: str) -> str:
        payload = self._read_json(
            f"https://rxnav.nlm.nih.gov/REST/approximateTerm.json?term={quote(question)}&maxEntries=1"
        )
        candidates = ((payload or {}).get("approximateGroup") or {}).get("candidate") or []
        return str(candidates[0].get("rxcui") or "").strip() if candidates else ""

    def _rxnorm_name(self, rxnorm_code: str) -> str:
        if not rxnorm_code:
            return ""

        payload = self._read_json(f"https://rxnav.nlm.nih.gov/REST/rxcui/{quote(rxnorm_code)}/properties.json")
        return str(((payload or {}).get("properties") or {}).get("name") or "")

    def _medline_plus(self, rxnorm_code: str, medication_name: str) -> dict[str, str] | None:
        if not rxnorm_code:
            return None

        url = (
            "https://connect.medlineplus.gov/service?mainSearchCriteria.v.cs=2.16.840.1.113883.6.88"
            f"&mainSearchCriteria.v.c={quote(rxnorm_code)}&mainSearchCriteria.v.dn={quote(medication_name)}"
            "&knowledgeResponseType=application/json"
        )
        payload = self._read_json(url)
        entry = ((payload or {}).get("feed") or {}).get("entry") or []
        if not entry:
            return None

        content = entry[0].get("content") or {}
        return {
            "name": "MedlinePlus Connect",
            "url": str(entry[0].get("link", [{}])[0].get("href") or "https://medlineplus.gov/"),
            "content": str(content.get("$t") or entry[0].get("title", {}).get("$t") or "")[:1800],
        }

    def _open_fda_label(self, rxnorm_code: str) -> dict[str, str] | None:
        if not rxnorm_code:
            return None

        return self._fda_label_from_payload(self._read_json(
            "https://api.fda.gov/drug/label.json?search=openfda.rxcui:%22"
            f"{quote(rxnorm_code)}%22&limit=1"
        ))

    def _open_fda_label_by_name(self, medication_name: str) -> dict[str, str] | None:
        medication_generic_name = re.split(r"\s+\d", medication_name, maxsplit=1)[0].strip()
        if not medication_generic_name:
            return None

        return self._fda_label_from_payload(self._read_json(
            "https://api.fda.gov/drug/label.json?search=openfda.generic_name:%22"
            f"{quote(medication_generic_name)}%22&limit=1"
        ))

    @staticmethod
    def _fda_label_from_payload(payload: dict[str, Any] | None) -> dict[str, str] | None:
        results = (payload or {}).get("results") or []
        if not results:
            return None

        label = results[0]
        content = {
            "indications_and_usage": (label.get("indications_and_usage") or [""])[0],
            "warnings": (label.get("warnings") or label.get("warnings_and_cautions") or [""])[0],
            "patient_counseling_information": (label.get("information_for_patients") or [""])[0],
        }
        return {
            "name": "openFDA Drug Label",
            "url": "https://open.fda.gov/apis/drug/label/",
            "content": json.dumps(content)[:1800],
        }

    def _medline_plus_condition(self, condition_code: str, condition_name: str) -> dict[str, str] | None:
        if not condition_code:
            return None

        url = (
            "https://connect.medlineplus.gov/service?mainSearchCriteria.v.cs=2.16.840.1.113883.6.90"
            f"&mainSearchCriteria.v.c={quote(condition_code)}&mainSearchCriteria.v.dn={quote(condition_name)}"
            "&knowledgeResponseType=application/json"
        )
        payload = self._read_json(url)
        entry = ((payload or {}).get("feed") or {}).get("entry") or []
        if not entry:
            return None

        content = entry[0].get("content") or {}
        return {
            "name": "MedlinePlus Connect",
            "url": str(entry[0].get("link", [{}])[0].get("href") or "https://medlineplus.gov/"),
            "content": str(content.get("$t") or entry[0].get("title", {}).get("$t") or "")[:1800],
        }