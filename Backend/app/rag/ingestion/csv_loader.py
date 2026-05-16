"""
app/rag/ingestion/csv_loader.py
────────────────────────────────
Medical CSV loader — converts structured tables into RAG-ready text documents.

Primary use case: drug interaction databases, lab reference ranges,
medication formularies, and clinical decision tables.

Strategy:
  - Each CSV row becomes one Document with a human-readable prose summary
  - Column names are used to build the prose ("Drug A interacts with Drug B…")
  - Metadata preserves all original column values for filtering
  - Supports both detected and explicit schema types

Supported schemas (auto-detected or specified):
  - "drug_interactions" : columns contain drug names + interaction severity
  - "lab_reference"     : columns contain test name + normal ranges
  - "medications"       : medication formulary (name, class, dosage, contraindications)
  - "generic"           : any CSV — key=value prose for every row
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog

from app.rag.ingestion.pdf_loader import Document

logger = structlog.get_logger(__name__)

# ── Schema column mappings ─────────────────────────────────────────────────────
# Maps schema type → columns expected.  Only the FIRST match per alias list is used.
_DRUG_INTERACTION_COLS = {
    "drug_a":    ["drug_a", "drug1", "drug_name", "medication_a", "interacting_drug"],
    "drug_b":    ["drug_b", "drug2", "interacting_with", "medication_b"],
    "severity":  ["severity", "level", "risk", "interaction_level"],
    "effect":    ["effect", "description", "interaction_description", "consequence"],
    "mechanism": ["mechanism", "mechanism_of_action"],
}

_LAB_REFERENCE_COLS = {
    "test":    ["test", "test_name", "analyte", "parameter"],
    "low":     ["low", "lower_limit", "min", "normal_low", "reference_low"],
    "high":    ["high", "upper_limit", "max", "normal_high", "reference_high"],
    "unit":    ["unit", "units", "measure"],
    "notes":   ["notes", "clinical_notes", "interpretation"],
}

_MEDICATION_COLS = {
    "name":              ["name", "drug_name", "generic_name", "medication"],
    "class":             ["class", "drug_class", "category", "therapeutic_class"],
    "dosage":            ["dosage", "dose", "typical_dose", "standard_dose"],
    "contraindications": ["contraindications", "contraindicated_with", "avoid_with"],
    "side_effects":      ["side_effects", "adverse_effects", "adverse_reactions"],
}


class MedicalCSVLoader:
    """
    Loads a CSV file and converts each row into a prose Document for RAG.

    Usage:
        loader = MedicalCSVLoader()
        docs = loader.load(
            "/path/to/drug_interactions.csv",
            schema="drug_interactions",
            source_name="DrugBank Interactions v5.1",
        )
    """

    def load(
        self,
        file_path: str | Path,
        schema: str = "auto",
        source_name: Optional[str] = None,
        language: str = "en",
    ) -> list[Document]:
        """
        Load a CSV and return one Document per row.

        Args:
            file_path  : Path to the CSV file.
            schema     : "drug_interactions" | "lab_reference" | "medications" | "generic" | "auto"
            source_name: Human-readable citation label.
            language   : Document language code.

        Returns:
            List of Document objects, one per data row.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")

        filename = source_name or path.name
        logger.info("csv_loader.start", filename=filename, schema=schema)

        with open(path, newline="", encoding="utf-8-sig") as f:
            content = f.read()

        return self._parse(content, schema, filename, language)

    def load_bytes(
        self,
        data: bytes,
        schema: str = "auto",
        source_name: str = "uploaded_table",
        language: str = "en",
    ) -> list[Document]:
        """Load a CSV from raw bytes (HTTP upload)."""
        content = data.decode("utf-8-sig", errors="replace")
        return self._parse(content, schema, source_name, language)

    def _parse(
        self,
        content: str,
        schema: str,
        filename: str,
        language: str,
    ) -> list[Document]:
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)

        if not rows:
            logger.warning("csv_loader.empty", filename=filename)
            return []

        # Auto-detect schema if not specified
        headers = [h.lower().strip() for h in (reader.fieldnames or [])]
        if schema == "auto":
            schema = self._detect_schema(headers)
        logger.info("csv_loader.schema_detected", schema=schema, filename=filename)

        # Select row-to-prose converter
        converters = {
            "drug_interactions": self._drug_interaction_prose,
            "lab_reference":     self._lab_reference_prose,
            "medications":       self._medication_prose,
            "generic":           self._generic_prose,
        }
        converter = converters.get(schema, self._generic_prose)

        documents: list[Document] = []
        skipped = 0

        for row_idx, row in enumerate(rows):
            # Normalise keys to lowercase
            norm_row = {k.lower().strip(): v.strip() for k, v in row.items() if k}

            prose = converter(norm_row)
            if not prose or len(prose) < 20:
                skipped += 1
                continue

            documents.append(Document(
                content=prose,
                metadata={
                    "source":   filename,
                    "row":      row_idx + 2,    # +2 = 1-indexed + header
                    "schema":   schema,
                    "language": language,
                    "doc_type": "structured_data",
                    **{f"col_{k}": v for k, v in norm_row.items()},  # preserve raw values
                },
            ))

        logger.info(
            "csv_loader.done",
            filename=filename,
            total_rows=len(rows),
            loaded=len(documents),
            skipped=skipped,
        )
        return documents

    # ── Schema detection ───────────────────────────────────────────────────────
    @staticmethod
    def _detect_schema(headers: list[str]) -> str:
        headers_set = set(headers)

        drug_signals = {"drug_a", "drug_b", "drug1", "drug2", "interacting_drug",
                        "severity", "interaction", "mechanism"}
        lab_signals  = {"test_name", "analyte", "normal_range", "reference_range",
                        "lower_limit", "upper_limit", "reference_low"}
        med_signals  = {"generic_name", "drug_class", "therapeutic_class",
                        "contraindications", "side_effects", "adverse_effects"}

        if headers_set & drug_signals:
            return "drug_interactions"
        if headers_set & lab_signals:
            return "lab_reference"
        if headers_set & med_signals:
            return "medications"
        return "generic"

    # ── Row-to-prose converters ────────────────────────────────────────────────
    @staticmethod
    def _drug_interaction_prose(row: dict) -> str:
        drug_a   = _find(row, _DRUG_INTERACTION_COLS["drug_a"])
        drug_b   = _find(row, _DRUG_INTERACTION_COLS["drug_b"])
        severity = _find(row, _DRUG_INTERACTION_COLS["severity"])
        effect   = _find(row, _DRUG_INTERACTION_COLS["effect"])
        mechanism = _find(row, _DRUG_INTERACTION_COLS["mechanism"])

        if not drug_a:
            return ""

        parts = [f"Drug interaction: {drug_a}"]
        if drug_b:
            parts[0] += f" and {drug_b}"
        if severity:
            parts.append(f"Severity: {severity}.")
        if effect:
            parts.append(f"Effect: {effect}.")
        if mechanism:
            parts.append(f"Mechanism: {mechanism}.")

        return " ".join(parts)

    @staticmethod
    def _lab_reference_prose(row: dict) -> str:
        test  = _find(row, _LAB_REFERENCE_COLS["test"])
        low   = _find(row, _LAB_REFERENCE_COLS["low"])
        high  = _find(row, _LAB_REFERENCE_COLS["high"])
        unit  = _find(row, _LAB_REFERENCE_COLS["unit"])
        notes = _find(row, _LAB_REFERENCE_COLS["notes"])

        if not test:
            return ""

        range_str = ""
        if low and high:
            range_str = f"Normal range: {low}–{high}"
            if unit:
                range_str += f" {unit}"
            range_str += "."
        elif low:
            range_str = f"Lower limit: {low} {unit or ''}."
        elif high:
            range_str = f"Upper limit: {high} {unit or ''}."

        parts = [f"Laboratory test: {test}."]
        if range_str:
            parts.append(range_str)
        if notes:
            parts.append(f"Clinical notes: {notes}.")

        return " ".join(parts)

    @staticmethod
    def _medication_prose(row: dict) -> str:
        name    = _find(row, _MEDICATION_COLS["name"])
        cls     = _find(row, _MEDICATION_COLS["class"])
        dosage  = _find(row, _MEDICATION_COLS["dosage"])
        contra  = _find(row, _MEDICATION_COLS["contraindications"])
        effects = _find(row, _MEDICATION_COLS["side_effects"])

        if not name:
            return ""

        parts = [f"Medication: {name}."]
        if cls:
            parts.append(f"Drug class: {cls}.")
        if dosage:
            parts.append(f"Typical dosage: {dosage}.")
        if contra:
            parts.append(f"Contraindicated with: {contra}.")
        if effects:
            parts.append(f"Common side effects: {effects}.")

        return " ".join(parts)

    @staticmethod
    def _generic_prose(row: dict) -> str:
        """Fallback: key=value pairs for all columns."""
        pairs = [f"{k}: {v}" for k, v in row.items() if v and v.lower() not in ("", "n/a", "null")]
        return ". ".join(pairs)


# ── Helper ─────────────────────────────────────────────────────────────────────
def _find(row: dict, aliases: list[str]) -> str:
    """Return the first non-empty value from the row matching any alias."""
    for alias in aliases:
        val = row.get(alias, "").strip()
        if val and val.lower() not in ("n/a", "null", "none", "-"):
            return val
    return ""
