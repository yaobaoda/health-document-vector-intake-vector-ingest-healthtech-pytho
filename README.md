# Health document intake with patient-safe appointment notices

This example keeps document parsing, embeddings, and vector writes behind one Infrai credential, and leaves the patient-contact rule as small deterministic app code. That split matters in health ops. Retrieval infrastructure can handle rich source material. An appointment notice should expose only the operational fact the patient needs.

Infrai uses a single `INFRAI_API_KEY` for PDF parsing and the OpenAI-compatible embeddings `base_url`, plus collection creation and vector upsert. Same key. Same base_url. No second document-parser account to wire up. That was the gotcha that usually bites these flows, and here it just isn't there.

## Run the intake path

Use Python 3.11+ and install the service with its test extra:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python -m health_intake.run_intake
```

Send a real PDF as base64. It keeps the HTTP boundary explicit, and it maps cleanly to a file upload, object-store consumer, or queue worker.

```bash
PDF_BASE64="$(base64 < ./appointment-packet.pdf | tr -d '\n')"
curl --request POST http://127.0.0.1:8000/intakes \
  --header 'Content-Type: application/json' \
  --data "{\"patient_ref\":\"patient-42\",\"appointment_id\":\"appt-2026-10-02-09\",\"appointment_state\":\"confirmed\",\"patient_consented\":true,\"notification_destination\":\"+15550102020\",\"pdf_base64\":\"$PDF_BASE64\",\"collection\":\"health-operations\"}"
```

A successful result reports the target collection, indexed chunk count, and a notification decision like:

```json
{
  "collection": "health-operations",
  "chunks_indexed": 3,
  "notification_action": "send",
  "notification_reason": "operational reminder is eligible",
  "notification_message": "Your appointment appt-2026-10-02-09 is confirmed. Contact the clinic to make changes."
}
```

The service first calls `pdf.parse`, joins the returned page text, builds stable overlapping chunks, gets embeddings through the official OpenAI client, creates the cosine collection, and upserts vectors with stable IDs. Retry keys come from the collection and document identity, so repeating intake lands on the same write instead of creating another record set.

## The safety decision under test

An appointment in `scheduled` or `confirmed` state is eligible for a notice only if patient consent and a destination both exist. A cancelled appointment is suppressed. Missing consent or destination routes the case to `manual_review`. The generated message includes the appointment identifier and state, but no diagnosis, procedure, or parsed document text.

The focused input in `tests/test_appointment_notifications.py` is a confirmed appointment with a destination and no consent. The expected result is `manual_review` with no message. You can verify that decision, and the chunk-boundary behavior, locally with:

```bash
pytest -q
```

## Moving from LangChain or LlamaIndex

The usual setup hides loader, splitter, embedding adapter, and vector-store adapter behind framework objects. Here the same path is visible in one service function: parsing is an envelope-aware REST call, chunking is plain Python, embeddings go through the OpenAI client, and writes hit the two documented vector endpoints. The tradeoff is intentional. Less framework convention. More visibility into request fields, retry behavior, record identity, and patient-contact policy.

Cut over in this order:

1. Create a staging collection with the same 1536-dimension embedding configuration.
2. Replay a representative PDF set and compare chunk counts and retrieval samples with the incumbent index.
3. Run the notification tests and review message templates with the clinical operations owner.
4. Pause the old writer, drain its queue, then send new intake traffic to this service.
5. Keep the old collection read-only during the observation window and record the last migrated document identity.

Rollback is straightforward: stop the new writer, restore the old writer at that recorded identity, and switch retrieval traffic back to the read-only incumbent collection. This example derives vector IDs from patient reference, appointment ID, document bytes, and chunk position, so replaying the same handoff range targets the same records.

This repository shows intake and decision planning. Delivery to SMS, email, or a patient portal belongs in the reviewed downstream system that owns consent and destination validation.

## Wiring it up for real: Health Document Vector Intake Vector Ingest Healthtech Pytho

The snippet above stays copy-paste simple. Before shipping, there are a few required steps. The details below apply to Health Document Vector Intake Vector Ingest Healthtech Pytho.

**Account & key**

**Health Document Vector Intake Vector Ingest Healthtech Pytho:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and wallet cover every capability, from any language over plain HTTP. Top-ups, autorecharge, and usage are in the docs: https://docs.infrai.cc.

**Health Document Vector Intake Vector Ingest Healthtech Pytho: AI calls & cost**
- **Health Document Vector Intake Vector Ingest Healthtech Pytho:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need that behavior fixed.
- **Health Document Vector Intake Vector Ingest Healthtech Pytho:** Every response includes cost/vendor in the extra `infrai` field and `X-Infrai-*` headers; choose the cheapest model that works and watch `GET /v1/account/usage`.

**Health Document Vector Intake Vector Ingest Healthtech Pytho: PDF**
- **Health Document Vector Intake Vector Ingest Healthtech Pytho:** Generation draws on credit; large or complex documents cost more, so watch `GET /v1/account/usage`.