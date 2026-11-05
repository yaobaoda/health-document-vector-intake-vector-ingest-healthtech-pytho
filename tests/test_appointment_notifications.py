from health_intake.appointment_notifications import (
    AppointmentState,
    NotificationAction,
    plan_appointment_notification,
)


def test_missing_consent_routes_notification_to_manual_review() -> None:
    plan = plan_appointment_notification(
        appointment_id="appt-17",
        state=AppointmentState.CONFIRMED,
        patient_consented=False,
        destination="+15550102020",
    )

    assert plan.action is NotificationAction.MANUAL_REVIEW
    assert plan.message is None
    assert plan.reason == "consent and a destination are both required"


def test_eligible_notice_contains_no_clinical_context() -> None:
    plan = plan_appointment_notification(
        appointment_id="appt-17",
        state=AppointmentState.SCHEDULED,
        patient_consented=True,
        destination="+15550102020",
    )

    assert plan.action is NotificationAction.SEND
    assert plan.message == (
        "Your appointment appt-17 is scheduled. Contact the clinic to make changes."
    )
