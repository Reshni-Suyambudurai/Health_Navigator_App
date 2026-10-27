from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import AuthorizationException, NotFoundException, ValidationException
from app.database.repositories.navigator.safety_evaluation_repository import SafetyEvaluationRepository


class SafetyEvaluationService:
    DECISIONS={"APPROVED","REMEDIATION_REQUIRED","ACCEPTED_RISK"}

    def __init__(self, db): self.repository=SafetyEvaluationRepository(db)

    def get_overview(self, user_id: int, organization_id: int | None=None) -> dict[str,Any]:
        identity=self._authorize(user_id); selected=organization_id or identity["organization_id"]
        if not self.repository.organization_exists(selected): raise NotFoundException("Organization not found","ORGANIZATION_NOT_FOUND")
        counts=self.repository.evidence_counts(selected); results=self._build_results(counts)
        decisions=self.repository.list_decisions(selected)
        latest_by_key={}
        for decision in decisions: latest_by_key.setdefault(decision["details"]["result_key"],decision)
        for result in results: result["latest_decision"]=latest_by_key.get(result["result_key"])
        passed=sum(1 for result in results if result["status"]=="PASS")
        return {
            "organizations":self.repository.list_organizations(),"selected_organization_id":selected,
            "run":{"run_key":datetime.now(timezone.utc).strftime("live-%Y%m%d%H%M"),"status":"COMPLETED","generated_at":datetime.now(timezone.utc).isoformat(),"source_window":"All available organization evidence","total_checks":len(results),"passed":passed,"failed":len(results)-passed},
            "results":results,"decisions":decisions,
        }

    def record_decision(self,user_id:int,organization_id:int,result_key:str,decision:str,notes:str)->None:
        self._authorize(user_id)
        if decision not in self.DECISIONS: raise ValidationException("Invalid evaluation decision","INVALID_EVALUATION_DECISION")
        if not notes.strip(): raise ValidationException("Decision notes are required","DECISION_NOTES_REQUIRED")
        overview=self.get_overview(user_id,organization_id); result=next((item for item in overview["results"] if item["result_key"]==result_key),None)
        if not result: raise NotFoundException("Evaluation result not found","EVALUATION_RESULT_NOT_FOUND")
        self.repository.record_decision(user_id,organization_id,result_key,decision,notes.strip(),{"status":result["status"],"observed":result["observed"],"expected":result["expected"],"evidence_ids":result["evidence_ids"]})

    def _build_results(self,c:dict[str,Any])->list[dict[str,Any]]:
        emergency=max(int(c["emergency_events"] or 0),1); hits=max(int(c["emergency_hits"] or 0),1); rules=max(int(c["active_rules"] or 0),1)
        checks=[
          ("emergency_instruction_delivery","Red-team","Emergency instructions delivered",int(c["instructions_sent"] or 0),int(c["emergency_events"] or 0),"Every emergency event sends approved instructions"),
          ("care_team_notification","Missed escalation","Care team notified",int(c["teams_notified"] or 0),int(c["emergency_events"] or 0),"Every emergency event notifies the care team"),
          ("emergency_event_creation","Clinical acuity","Emergency hits create events",int(c["emergency_events"] or 0),int(c["emergency_hits"] or 0),"Every emergency/high-acuity hit creates an emergency event"),
          ("escalation_linkage","Missed escalation","High-acuity hits create escalation",int(c["emergency_escalations"] or 0),int(c["emergency_hits"] or 0),"Every emergency/high-acuity hit creates an escalation"),
          ("active_matcher_coverage","Deterministic rules","Active rules have matchers",int(c["covered_rules"] or 0),int(c["active_rules"] or 0),"Every active rule has an active deterministic matcher"),
          ("emergency_resolution","Post-deployment","Emergency events resolved",int(c["events_resolved"] or 0),int(c["emergency_events"] or 0),"Emergency events are resolved or closed"),
        ]
        evidence=c["evidence"]
        results=[]
        for key,category,title,observed,expected_count,expected in checks:
            passed=expected_count==0 or observed>=expected_count
            relevant=[item for item in evidence if (key not in {"active_matcher_coverage"})][:8]
            results.append({"result_key":key,"category":category,"title":title,"status":"PASS" if passed else "FAIL","expected":expected,"observed":f"{observed} of {expected_count}","failure_count":max(0,expected_count-observed),"issue_status":"VERIFIED" if passed else "OPEN","evidence":relevant,"evidence_ids":[item["guardrail_hit_id"] for item in relevant]})
        return results

    def _authorize(self,user_id:int)->dict[str,Any]:
        identity=self.repository.find_active_role(user_id)
        if not identity or identity["role_name"] not in {"CLINICAL_GOVERNANCE","SYSTEM_ADMIN"}: raise AuthorizationException("Clinical Governance access is required","SAFETY_EVALUATION_ACCESS_DENIED")
        return identity
