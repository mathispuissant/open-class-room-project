#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script : cycle4_svt_dual_calls.py

Description :
    - Charge la clé OPENAI_API_KEY et le chemin PDF depuis .env.
    - Upload d’un PDF (programme SVT cycle 4).
    - Appel 1 : GPT-4.1 en JSON mode pour récupérer un JSON valide sans texte parasite.
    - Appel 2 : GPT-4o avec Structured Outputs (schéma JSON) pour valider la structure.
    - Chaque sortie est sauvegardée dans un fichier “.json” séparé.
    
Pré-requis :
    pip install python-dotenv openai
    Avoir un fichier .env contenant au minimum :
        OPENAI_API_KEY=sk-…
        PDF_PATH=/chemin/vers/mon_programme_cycle4_svt.pdf
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# 1. Chargement des variables depuis .env
load_dotenv()  # cherche automatiquement un fichier nommé ".env"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PDF_PATH       = os.getenv("PDF_PATH")

if OPENAI_API_KEY is None or PDF_PATH is None:
    raise RuntimeError("Il manque OPENAI_API_KEY ou PDF_PATH dans le fichier .env.")

# Initialisation du client OpenAI (on l’utilise dans toutes les fonctions)
client = OpenAI(api_key=OPENAI_API_KEY)


def upload_pdf(pdf_path):
    """
    Upload le PDF donné sur l’API OpenAI et renvoie l’ID du fichier.
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"Le fichier PDF '{pdf_path}' n'existe pas.")
    with open(pdf_path, "rb") as f:
        resp = client.files.create(
            file = f,
            purpose = "user_data"
        )
    return resp.id


import json
# pip install jsonschema si vous voulez valider plus tard

def call_gpt4_1_json_mode(file_id, output_path):
    messages = [
        { "role": "system",
          "content": (
              "Tu es un assistant expert en SVT. À partir du PDF fourni (file_id="
              f"{file_id}"
              "), RENVOIE UNIQUEMENT un objet JSON valide respectant cette structure :\n"
              "{\n"
              '  "matiere": "SVT",\n'
              '  "cycle": "cycle 4",\n'
              '  "chapitres": [ … ]\n'
              "}\n"
              "PAS DE TEXTE SUPPLÉMENTAIRE, JUSTE LE JSON."
          )
        },
        { "role": "user",
          "content": "Analyse le PDF et renvoie-moi le JSON demandé." }
    ]

    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        temperature=0,
        max_tokens=8000
    )

    # Ici on reçoit du texte, il faut le parser soi-même
    text = resp.choices[0].message.content
    output_json = json.loads(text)

    # (Optionnel) validation avec jsonschema.validate(...)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=2)

    print(f"[✓] GPT-4.1 JSON-mode → sauvegardé dans « {output_path} »")



from jsonschema import validate, ValidationError

def call_gpt4o_structured(file_id, output_path):
    schema = {
        # … votre schéma JSON dict …
    }

    messages = [
        {"role": "system",
         "content": (
             "Tu es un assistant expert en SVT. À partir du PDF fourni (file_id="
             f"{file_id}"
             "), renvoie EXACTEMENT un JSON conforme au schéma suivant :\n"
             f"{json.dumps(schema, indent=2)}\n"
             "RIEN D’AUTRE."
         )
        },
        {"role": "user",
         "content": "Génère le JSON conforme au schéma."}
    ]

    resp = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=messages,
        temperature=0,
        max_tokens=8000
    )

    text = resp.choices[0].message.content
    output_json = json.loads(text)

    # Validation locale
    try:
        validate(output_json, schema)
    except ValidationError as e:
        raise RuntimeError(f"Le JSON retourné n’est pas conforme : {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=2)

    print(f"[✓] GPT-4o Structured → sauvegardé dans « {output_path} »")



if __name__ == "__main__":
    # 1) Upload du PDF depuis PDF_PATH
    print("[+] Upload du PDF sur l’API…")
    file_id = upload_pdf(PDF_PATH)

    # 2) Premier appel : GPT-4.1 JSON mode
    base_name = os.path.splitext(os.path.basename(PDF_PATH))[0]
    out1 = f"{base_name}_gpt4-1_jsonmode.json"
    print("[+] Appel 1 : GPT-4.1 (JSON mode)…")
    call_gpt4_1_json_mode(file_id, out1)

    # 3) Deuxième appel : GPT-4o Structured Outputs
    out2 = f"{base_name}_gpt4o_structured.json"
    print("[+] Appel 2 : GPT-4o (Structured Outputs)…")
    call_gpt4o_structured(file_id, out2)

    print("\nTous les appels sont terminés.")
