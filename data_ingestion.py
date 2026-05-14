import json
import re
import time
import uuid
import requests

from pathlib import Path


# =========================================================
# Paths
# =========================================================
DISEASES_DIR = Path("data/raw/diseases")
DRUGS_DIR = Path("data/raw/openfda")

DISEASES_DIR.mkdir(parents=True, exist_ok=True)
DRUGS_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# APIs
# =========================================================
WIKI_API = "https://en.wikipedia.org/w/api.php"
OPENFDA_API = "https://api.fda.gov/drug/label.json"


# =========================================================
# Diseases
# =========================================================
TARGET_DISEASES = [
    {"name": "Type 2 diabetes", "slug": "Type_2_diabetes"},
    {"name": "Hypertension", "slug": "Hypertension"},
    {"name": "Coronary artery disease", "slug": "Coronary_artery_disease"},
    {"name": "Heart failure", "slug": "Heart_failure"},
    {"name": "High cholesterol", "slug": "High_cholesterol"},
    {"name": "Asthma", "slug": "Asthma"},
    {"name": "Chronic kidney disease", "slug": "Chronic_kidney_disease"},
    {"name": "Obesity", "slug": "Obesity"},
    {"name": "Atrial fibrillation", "slug": "Atrial_fibrillation"},
    {"name": "Osteoarthritis", "slug": "Osteoarthritis"},
]


# =========================================================
# Drugs
# =========================================================
TARGET_DRUGS = [

    # Diabetes
    "metformin",
    "insulin",
    "glyburide",
    "sitagliptin",

    # Hypertension
    "amlodipine",
    "lisinopril",
    "atenolol",
    "losartan",

    # Heart
    "aspirin",
    "atorvastatin",
    "warfarin",
    "clopidogrel",

    # Painkillers
    "ibuprofen",
    "acetaminophen",
    "diclofenac",

    # Antibiotics
    "amoxicillin",
    "azithromycin",
    "ciprofloxacin",
]


FIELDS_TO_EXTRACT = [
    "indications_and_usage",
    "warnings",
    "drug_interactions",
    "adverse_reactions",
    "dosage_and_administration",
    "contraindications",
    "warnings_and_cautions",
]


# =========================================================
# Clean Text
# =========================================================
def clean_text(text: str) -> str:

    if not text:
        return ""

    text = text.replace("\xa0", " ")

    # Remove extra spaces/newlines
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# Save JSON
# =========================================================
def save_json(path: Path, data: dict):

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================================================
# Fetch Disease
# =========================================================
def fetch_disease(disease: dict) -> bool:

    params = {
        "action": "query",
        "titles": disease["slug"],
        "prop": "extracts",
        "explaintext": True,
        "format": "json",
        "redirects": 1,
    }

    headers = {
        "User-Agent": "MedicalRAGBot/1.0"
    }

    try:

        response = requests.get(
            WIKI_API,
            params=params,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        pages = data.get("query", {}).get("pages", {})

        if not pages:
            print(f"  [WARN] {disease['name']}: no pages")
            return False

        page = next(iter(pages.values()))

        extract = clean_text(
            page.get("extract", "")
        )

        if not extract:
            print(f"  [WARN] {disease['name']}: empty")
            return False

        wiki_url = (
            f"https://en.wikipedia.org/wiki/"
            f"{disease['slug']}"
        )

        doc = {
            "id": str(uuid.uuid4()),

            "source": "wikipedia",
            "source_type": "disease_wiki",

            "entity_name": disease["name"],
            "entity_type": "disease",

            "url": wiki_url,

            "text": extract,
        }

        out_path = (
            DISEASES_DIR /
            f"{disease['slug'].lower()}.json"
        )

        save_json(out_path, doc)

        print(f"  [OK] {disease['name']}")

        return True

    except requests.exceptions.RequestException as e:

        print(f"  [ERROR] {disease['name']}: {e}")

        return False

    except Exception as e:

        print(f"  [ERROR] {disease['name']}: unexpected error -> {e}")

        return False


# =========================================================
# Build Drug Text
# =========================================================
def build_drug_text(sections: dict) -> str:

    full_text = ""

    for section, contents in sections.items():

        if not contents:
            continue

        full_text += f"\n\n## {section.upper()}\n\n"

        for content in contents:

            cleaned = clean_text(content)

            if cleaned:
                full_text += cleaned + "\n"

    return full_text.strip()


# =========================================================
# Fetch Drug
# =========================================================
def fetch_drug(drug_name: str) -> bool:

    params = {
        "search": drug_name,
        "limit": 5,
    }

    headers = {
        "User-Agent": "MedicalRAGBot/1.0"
    }

    try:

        response = requests.get(
            OPENFDA_API,
            params=params,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        results = data.get("results", [])

        if not results:
            print(f"  [WARN] {drug_name}: no results")
            return False

        sections = {}

        for result in results:

            for field in FIELDS_TO_EXTRACT:

                if field not in result:
                    continue

                if field not in sections:
                    sections[field] = []

                content = result[field]

                if isinstance(content, list):
                    sections[field].extend(content)
                else:
                    sections[field].append(content)

        # =====================================================
        # Cleaning + Deduplication
        # =====================================================
        for field in sections:

            cleaned_items = []

            for item in sections[field]:

                cleaned = clean_text(item)

                if cleaned:
                    cleaned_items.append(cleaned)

            sections[field] = list(set(cleaned_items))

        # =====================================================
        # Build flat text
        # =====================================================
        full_text = build_drug_text(sections)

        if not full_text:
            print(f"  [WARN] {drug_name}: empty text")
            return False

        doc = {
            "id": str(uuid.uuid4()),

            "source": "openfda",
            "source_type": "drug_label",

            "entity_name": drug_name,
            "entity_type": "drug",

            "url": response.url,

            "text": full_text,
        }

        out_path = (
            DRUGS_DIR /
            f"{drug_name.lower()}.json"
        )

        save_json(out_path, doc)

        print(f"  [OK] {drug_name}")

        return True

    except requests.exceptions.RequestException as e:

        print(f"  [ERROR] {drug_name}: {e}")

        return False

    except Exception as e:

        print(f"  [ERROR] {drug_name}: unexpected error -> {e}")

        return False


# =========================================================
# Main
# =========================================================
def run():

    print("\n" + "=" * 60)
    print("FETCHING Diseases")
    print("=" * 60)

    disease_success = 0

    for i, disease in enumerate(TARGET_DISEASES, 1):

        print(f"[{i}/{len(TARGET_DISEASES)}] {disease['name']}")

        if fetch_disease(disease):
            disease_success += 1

        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("FETCHING Drugs")
    print("=" * 60)

    drug_success = 0

    for i, drug in enumerate(TARGET_DRUGS, 1):

        print(f"[{i}/{len(TARGET_DRUGS)}] {drug}")

        if fetch_drug(drug):
            drug_success += 1

        time.sleep(0.5)

    print("\n" + "=" * 60)

    print(f"[OK] Diseases fetched : {disease_success}")
    print(f"[OK] Drugs fetched    : {drug_success}")

    print("\n📁 Saved in:")
    print(f"   - {DISEASES_DIR}")
    print(f"   - {DRUGS_DIR}")




# =========================================================
# Entry
# =========================================================
if __name__ == "__main__":
    run()