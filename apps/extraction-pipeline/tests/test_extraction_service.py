"""Unit tests for the ExtractionService (mocked LLM + database)."""
import asyncio
import json
from unittest.mock import MagicMock, patch

from python_llm import GenerateResponse

from src.extraction_service import ExtractionService, coerce_value, normalize_key


class FakeLLM:
    def __init__(self, answer: str):
        self._answer = answer
        self.last_request = None

    async def generate(self, request):
        self.last_request = request
        return GenerateResponse(answer=self._answer)


def _service(llm=None, **kwargs):
    return ExtractionService(
        llm or FakeLLM("[]"),
        db_url="postgresql://u:p@localhost/db",
        **kwargs,
    )


def _ready_service(llm=None):
    svc = _service(llm=llm)
    svc.ready = True
    svc.connection = MagicMock()
    return svc


def test_normalize_key():
    assert normalize_key("Invoice Number") == "invoice_number"
    assert normalize_key("RechnungsNr.") == "rechnungsnr"
    assert normalize_key("  TAX-NR  ") == "tax_nr"
    assert normalize_key("") == ""
    assert normalize_key("!@#") == ""


def test_coerce_value():
    assert coerce_value("19,99", "currency") == 19.99
    assert coerce_value("42", "number") == 42.0
    assert coerce_value(42, "number") == 42
    assert coerce_value("true", "boolean") is True
    assert coerce_value("text", "string") == "text"


def test_parse_envelope_with_code_fence():
    svc = _service()
    answer = (
        '```json\n[{"key": "Invoice Number", "value": "4711", "type": "string", '
        '"confidence": 0.9, "source": "Rechnung 4711"}]\n```'
    )
    facts = svc.parse_envelope(answer)
    assert facts["invoice_number"]["value"] == "4711"
    assert facts["invoice_number"]["type"] == "string"
    assert facts["invoice_number"]["confidence"] == 0.9


def test_parse_envelope_invalid_json():
    assert _service().parse_envelope("nicht json") == {}


def test_parse_envelope_skips_invalid_items():
    svc = _service()
    facts = svc.parse_envelope(
        json.dumps(
            [
                {"key": "a_b", "value": 1, "type": "number"},
                {"key": "", "value": 2},
            ]
        )
    )
    assert set(facts) == {"a_b"}


def test_parse_envelope_clamps_confidence():
    svc = _service()
    facts = svc.parse_envelope(
        json.dumps([{"key": "k", "value": "v", "confidence": 7}])
    )
    assert facts["k"]["confidence"] == 1.0


@patch("src.extraction_service.psycopg2.connect")
def test_initialize_creates_fact_keys(mock_connect):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    mock_connect.return_value = conn

    svc = _service()
    assert svc.initialize() is True
    sql = cursor.execute.call_args.args[0]
    assert "CREATE TABLE IF NOT EXISTS fact_keys" in sql


def test_initialize_requires_url():
    svc = ExtractionService(FakeLLM("[]"), db_url=None)
    assert svc.initialize() is False


def test_find_pending():
    svc = _ready_service()
    cursor = MagicMock()
    svc.connection.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchall.return_value = [("1", "t", "c", "Rechnung", {"k": "v"})]

    pending = svc.find_pending()
    assert pending[0]["id"] == "1"
    assert pending[0]["document_type"] == "Rechnung"
    sql = cursor.execute.call_args.args[0]
    assert "extracted = '{}'::jsonb" in sql


def test_register_keys():
    svc = _ready_service()
    cursor = MagicMock()
    svc.connection.cursor.return_value.__enter__.return_value = cursor
    svc.register_keys("Rechnung", ["invoice_number", "amount"])
    assert cursor.execute.call_count == 2


def test_run_extracts_and_saves():
    facts = [{"key": "invoice_number", "value": "4711", "type": "string", "confidence": 0.9}]
    svc = _ready_service(llm=FakeLLM(json.dumps(facts)))
    cursor = MagicMock()
    svc.connection.cursor.return_value.__enter__.return_value = cursor
    # find_pending returns one doc; known_keys returns [].
    cursor.fetchall.side_effect = [
        [("1", "t", "c", "Rechnung", {})],
        [],
    ]

    result = asyncio.run(svc.run(limit=5))
    assert result == {"processed": 1, "failed": 0, "pending_total": 1}
    updates = [
        c.args[0]
        for c in cursor.execute.call_args_list
        if "UPDATE" in str(c.args[0])
    ]
    assert len(updates) == 1
