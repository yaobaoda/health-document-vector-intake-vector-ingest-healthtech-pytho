import argparse
import base64
import json
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the health document intake API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run("health_intake.health_document_service:service", host=args.host, port=args.port)


def encode_pdf(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def example_payload(path: Path) -> str:
    return json.dumps(
        {
            "patient_ref": "patient-42",
            "appointment_id": "appt-2026-10-02-09",
            "appointment_state": "confirmed",
            "patient_consented": True,
            "notification_destination": "+15550102020",
            "pdf_base64": encode_pdf(path),
            "collection": "health-operations",
        }
    )


if __name__ == "__main__":
    main()
