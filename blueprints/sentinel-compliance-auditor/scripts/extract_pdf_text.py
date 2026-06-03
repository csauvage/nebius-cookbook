#!/usr/bin/env python3
"""Extract text from regulation PDFs into .txt files for ingestion."""

import os
import pymupdf

REGULATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "regulations")

PDFS = [
    "soc2_trust_services_criteria_2017_revised_2022.pdf",
    "soc2_description_criteria_2018_revised_2022.pdf",
    "nist_ai_rmf_100_1.pdf",
    "nist_ai_600_1_genai_profile.pdf",
    "nist_ai_rmf_100_1_draft1_2022.pdf",
    "nist_ai_rmf_100_1_draft2_2022.pdf",
    "sr_11_7_occ_model_risk_management.pdf",
    "sr_26_2_model_risk_management_2026.pdf",
    "eu_ai_act_2021_commission_proposal.pdf",
]


def extract_pdf(pdf_path: str, txt_path: str) -> None:
    doc = pymupdf.open(pdf_path)
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text)
    doc.close()

    full_text = "\n\n".join(pages)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"  {os.path.basename(pdf_path)}: {len(pages)} pages -> {os.path.basename(txt_path)} ({len(full_text):,} chars)")


def main():
    for pdf_name in PDFS:
        pdf_path = os.path.join(REGULATIONS_DIR, pdf_name)
        if not os.path.exists(pdf_path):
            print(f"  SKIP: {pdf_name} not found")
            continue
        txt_name = pdf_name.replace(".pdf", ".txt")
        txt_path = os.path.join(REGULATIONS_DIR, txt_name)
        extract_pdf(pdf_path, txt_path)
    print("Done.")


if __name__ == "__main__":
    main()
