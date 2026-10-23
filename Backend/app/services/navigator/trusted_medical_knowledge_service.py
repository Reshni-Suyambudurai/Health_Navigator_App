"""Retrieves public, authoritative medication information for patient education."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen


class TrustedMedicalKnowledgeService:
    """Builds a small, source-attributed knowledge context from public health APIs."""

    def get_context(self, question: str, clinical_context: dict[str, Any]) -> dict[str, Any]:
        medication = self._referenced_medication(question, clinical_context.get("medications", []))
        condition = self._referenced_condition(question, clinical_context.get("conditions", []))
        if not medication and not condition:
            return {"status": "not_applicable", "sources": []}

        sources: list[dict[str, str]] = []
        result: dict[str, Any] = {"status": "temporarily_unavailable", "sources": sources}

        if medication:
            rxnorm_code = str(medication.get("rxnorm_code") or "").strip()
            medication_name = str(medication.get("medication_name") or "").strip()
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
    def _read_json(url: str) -> dict[str, Any] | None:
        try:
            with urlopen(url, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
        except (OSError, TimeoutError, ValueError):
            return None

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

        payload = self._read_json(
            "https://api.fda.gov/drug/label.json?search=openfda.rxcui:%22"
            f"{quote(rxnorm_code)}%22&limit=1"
        )
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