from dataclasses import dataclass
from enum import StrEnum


class AppointmentState(StrEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class NotificationAction(StrEnum):
    SEND = "send"
    MANUAL_REVIEW = "manual_review"
    SUPPRESS = "suppress"


@dataclass(frozen=True)
class NotificationPlan:
    action: NotificationAction
    reason: str
    message: str | None


def plan_appointment_notification(
    *,
    appointment_id: str,
    state: AppointmentState,
    patient_consented: bool,
    destination: str | None,
) -> NotificationPlan:
    """Choose a safe operational notice without placing clinical details in it."""
    if state is AppointmentState.CANCELLED:
        return NotificationPlan(
            action=NotificationAction.SUPPRESS,
            reason="cancelled appointments do not receive reminders",
            message=None,
        )
    if not patient_consented or not destination:
        return NotificationPlan(
            action=NotificationAction.MANUAL_REVIEW,
            reason="consent and a destination are both required",
            message=None,
        )
    verb = "confirmed" if state is AppointmentState.CONFIRMED else "scheduled"
    return NotificationPlan(
        action=NotificationAction.SEND,
        reason="operational reminder is eligible",
        message=f"Your appointment {appointment_id} is {verb}. Contact the clinic to make changes.",
    )
