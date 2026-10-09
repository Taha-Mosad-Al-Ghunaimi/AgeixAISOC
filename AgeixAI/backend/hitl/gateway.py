import logging
from datetime import datetime, timezone
from typing import Any, Literal

from models.schemas import SoarAction, HitlDecision, AuditLogEntry
from hitl.audit import log_decision, IMMUTABLE_ACTIONS
from fastapi import HTTPException

logger = logging.getLogger("AgeixAI.hitl.gateway")

_PENDING_ACTIONS: dict[str, SoarAction] = {}
_DECISIONS: dict[str, HitlDecision] = {}


class HitlGateway:
    def submit_action(self, action: SoarAction) -> SoarAction:
        if action.action_type not in IMMUTABLE_ACTIONS:
            raise HTTPException(status_code=400, detail=f"Unknown SOAR action type: {action.action_type}")

        if action.action_id in _PENDING_ACTIONS:
            raise HTTPException(status_code=409, detail=f"Action {action.action_id} already submitted")

        _PENDING_ACTIONS[action.action_id] = action
        _DECISIONS[action.action_id] = HitlDecision(
            action_id=action.action_id,
            status="pending",
        )

        log_decision(
            action_id=action.action_id,
            action_type=action.action_type,
            target=action.target,
            source_agent=action.source_agent,
            decision="pending",
        )

        logger.info(
            "HITL: action %s (%s) submitted — awaiting human decision",
            action.action_id, action.action_type,
        )
        return action

    def get_pending_actions(self) -> list[SoarAction]:
        return [
            a for aid, a in _PENDING_ACTIONS.items()
            if _DECISIONS.get(aid, HitlDecision(action_id=aid, status="pending")).status == "pending"
        ]

    def get_action(self, action_id: str) -> SoarAction | None:
        return _PENDING_ACTIONS.get(action_id)

    def review_action(
        self,
        action_id: str,
        status: Literal["approved", "rejected", "modified"],
        approved_by: str = "human-analyst",
        modification: str | None = None,
    ) -> HitlDecision:
        action = _PENDING_ACTIONS.get(action_id)
        if not action:
            raise HTTPException(status_code=404, detail=f"Action {action_id} not found")

        decision = _DECISIONS.get(action_id)
        if decision and decision.status != "pending":
            raise HTTPException(status_code=409, detail=f"Action {action_id} already {decision.status}")

        decision = HitlDecision(
            action_id=action_id,
            status=status,
            approved_by=approved_by,
            modification=modification,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )
        _DECISIONS[action_id] = decision

        log_decision(
            action_id=action_id,
            action_type=action.action_type,
            target=action.target,
            source_agent=action.source_agent,
            decision=status,
            approved_by=approved_by,
            modification=modification,
        )

        logger.info(
            "HITL: action %s %s by %s", action_id, status, approved_by,
        )

        if status == "modified" and modification:
            action.params["modification"] = modification
            _PENDING_ACTIONS[action_id] = action

        return decision

    def is_action_approved(self, action_id: str) -> bool:
        decision = _DECISIONS.get(action_id)
        return decision is not None and decision.status == "approved"

    def get_decision(self, action_id: str) -> HitlDecision | None:
        return _DECISIONS.get(action_id)


gateway = HitlGateway()
