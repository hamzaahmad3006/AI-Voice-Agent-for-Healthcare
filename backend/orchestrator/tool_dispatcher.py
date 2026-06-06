from __future__ import annotations

import json
import logging
from datetime import date, timedelta

from models.appointment import BookingRequest, SlotSearchRequest
from models.fsm_state import ConversationSession, LLMToolCall, ToolCallType
from models.insurance import InsuranceCheckRequest
from models.patient import (
    PatientCreateRequest,
    PatientLookupRequest,
    PatientMatchStatus,
)
from models.session_log import ConsentType, ConsentValue
from orchestrator.fsm import ToolResult

logger = logging.getLogger(__name__)

_SLOT_SEARCH_WINDOW_DAYS = 14


class DomainToolDispatcher:
    """Concrete implementation of ToolDispatcherProtocol.

    Routes every LLMToolCall to the appropriate helper function,
    converts the response into a ToolResult with slot updates,
    and handles domain-specific error cases.
    """

    async def dispatch(
        self,
        tool_call: LLMToolCall,
        session: ConversationSession,
    ) -> ToolResult:
        try:
            match tool_call.name:
                case ToolCallType.LOOKUP_PATIENT:
                    return await self._lookup_patient(session)
                case ToolCallType.CREATE_PATIENT:
                    return await self._create_patient(session)
                case ToolCallType.SEARCH_SLOTS:
                    return await self._search_slots(session)
                case ToolCallType.BOOK_APPOINTMENT:
                    return await self._book_appointment(session)
                case ToolCallType.CHECK_INSURANCE:
                    return await self._check_insurance(session)
                case ToolCallType.RECORD_CONSENT:
                    return await self._record_consent(tool_call, session)
                case _:
                    logger.error("Unknown tool call: %s", tool_call.name)
                    return ToolResult(success=False, error_message=f"unknown_tool:{tool_call.name}")
        except Exception as exc:
            logger.exception("Tool %s failed: %s", tool_call.name, exc)
            return ToolResult(success=False, error_message=str(exc))

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def _lookup_patient(self, session: ConversationSession) -> ToolResult:
        from helpers import fhir_helper

        slots = session.slots
        if not all([slots.first_name, slots.last_name, slots.date_of_birth, slots.phone]):
            return ToolResult(
                success=False,
                error_message="missing_identity_slots",
            )

        request = PatientLookupRequest(
            first_name=slots.first_name or "",
            last_name=slots.last_name or "",
            date_of_birth=slots.date_of_birth or "",
            phone=slots.phone or "",
        )
        response = await fhir_helper.lookup_patient(request)

        if response.status == PatientMatchStatus.EXISTING_PATIENT and response.patient:
            return ToolResult(
                success=True,
                slots_to_update={
                    "patient_id": response.patient.patient_id,
                    "fhir_id": response.patient.fhir_id,
                    "is_new_patient": False,
                },
            )

        if response.status == PatientMatchStatus.NO_MATCH:
            return ToolResult(
                success=True,
                slots_to_update={"is_new_patient": True},
            )

        # AMBIGUOUS — let FSM route to HUMAN_HANDOFF
        return ToolResult(
            success=False,
            error_message="ambiguous_patient",
        )

    async def _create_patient(self, session: ConversationSession) -> ToolResult:
        from helpers import consent_helper, fhir_helper

        slots = session.slots
        consent_ref = slots.data_consent_ref or consent_helper.new_consent_ref()

        request = PatientCreateRequest(
            first_name=slots.first_name or "",
            last_name=slots.last_name or "",
            date_of_birth=slots.date_of_birth or "",
            phone=slots.phone or "",
            consent_ref=consent_ref,
        )
        response = await fhir_helper.create_patient(request)

        return ToolResult(
            success=True,
            slots_to_update={
                "patient_id": response.patient_id,
                "fhir_id": response.fhir_id,
                "is_new_patient": True,
                "data_consent_ref": consent_ref,
            },
        )

    async def _search_slots(self, session: ConversationSession) -> ToolResult:
        from helpers import talkehr_helper

        slots = session.slots
        today = date.today()
        request = SlotSearchRequest(
            location_id=slots.location_id or "loc-default",
            visit_type=slots.visit_type or "consult",
            from_date=today.isoformat(),
            to_date=(today + timedelta(days=_SLOT_SEARCH_WINDOW_DAYS)).isoformat(),
            provider_id=slots.provider_id,
        )
        response = await talkehr_helper.search_slots(request)

        slots_json = json.dumps([s.model_dump() for s in response.slots])
        return ToolResult(
            success=True,
            slots_to_update={"available_slots_json": slots_json},
        )

    async def _book_appointment(self, session: ConversationSession) -> ToolResult:
        from helpers import consent_helper, talkehr_helper
        from mocks.talkehr_mock import SlotTakenError

        slots = session.slots
        consent_ref = slots.booking_consent_ref or consent_helper.new_consent_ref()

        request = BookingRequest(
            patient_id=slots.patient_id or "",
            slot_id=slots.selected_slot_id or "",
            reason=slots.reason_for_visit or "",
            consent_ref=consent_ref,
            idempotency_key=session.session_id,
        )

        try:
            response = await talkehr_helper.book_appointment(request)
        except SlotTakenError:
            return ToolResult(success=False, error_message="slot_taken")

        return ToolResult(
            success=True,
            slots_to_update={
                "appointment_id": response.appointment_id,
                "confirmation_code": response.confirmation_code,
                "booking_consent_ref": consent_ref,
            },
        )

    async def _check_insurance(self, session: ConversationSession) -> ToolResult:
        from helpers import insurance_helper

        slots = session.slots
        request = InsuranceCheckRequest(
            payer_name=slots.insurer_name or "unknown",
            member_id=slots.member_id or "",
            group_number=slots.group_number,
            patient_dob=slots.date_of_birth or "",
            provider_id=slots.provider_id or "prov-001",
        )
        await insurance_helper.check_insurance(request)

        # Insurance check result does not block booking — always advance.
        return ToolResult(
            success=True,
            slots_to_update={"coverage_checked": True},
        )

    async def _record_consent(
        self, tool_call: LLMToolCall, session: ConversationSession
    ) -> ToolResult:
        from helpers import consent_helper

        slots = session.slots

        # Determine consent type from session state
        if not slots.data_consent_given:
            consent_type = ConsentType.DATA_PROCESSING
            consent_value = ConsentValue.YES if slots.data_consent_given else ConsentValue.NO
        else:
            consent_type = ConsentType.BOOKING
            consent_value = ConsentValue.YES if slots.booking_consent_given else ConsentValue.NO

        snippet = str(tool_call.arguments.get("transcript_snippet", ""))
        event = await consent_helper.record_consent(
            session_id=session.session_id,
            consent_type=consent_type,
            value=consent_value,
            transcript_snippet=snippet,
        )

        if consent_type == ConsentType.DATA_PROCESSING:
            return ToolResult(
                success=True,
                slots_to_update={"data_consent_ref": consent_helper.new_consent_ref()},
            )
        return ToolResult(
            success=True,
            slots_to_update={"booking_consent_ref": consent_helper.new_consent_ref()},
        )
