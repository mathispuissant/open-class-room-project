#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script : cycle4_svt_dual_calls_txt_inline.py

Description :
    - Charge la clé OPENAI_API_KEY et le chemin TXT depuis .env ou argument CLI.
    - Lit le fichier texte (programme SVT cycle 4) et injecte directement son contenu dans le prompt.
    - Appel 1 : GPT-4.1 en JSON mode pour récupérer un JSON valide sans texte parasite.
    - Appel 2 : GPT-4o avec Structured Outputs (schéma JSON) pour valider la structure.
    - Chaque sortie est sauvegardée dans un fichier “.json” séparé.

Pré-requis :
    pip install python-dotenv openai jsonschema
    Avoir un fichier .env contenant au minimum :
        OPENAI_API_KEY=sk-…
        TXT_PATH=/chemin/vers/mon_programme_cycle4_svt.txt
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from jsonschema import validate, ValidationError

# 1. Chargement des variables depuis .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TXT_PATH_ENV = os.getenv("TXT_PATH", "")

# 2. Debug prints pour vérifier le chemin
print(f"[DEBUG] OPENAI_API_KEY loaded: {'yes' if OPENAI_API_KEY else 'no'}")
print(f"[DEBUG] Raw TXT_PATH from .env: {TXT_PATH_ENV}")

# 3. Support override via argument
if len(sys.argv) > 1:
    TXT_PATH = Path(sys.argv[1])
    print(f"[DEBUG] TXT_PATH overridden by CLI arg: {TXT_PATH}")
else:
    TXT_PATH = Path(TXT_PATH_ENV)

print(f"[DEBUG] Resolved TXT_PATH: {TXT_PATH}")
print(f"[DEBUG] Exists? {TXT_PATH.exists()}, Is file? {TXT_PATH.is_file()}")

if OPENAI_API_KEY is None or not TXT_PATH.is_file():
    raise RuntimeError(
        "Il manque OPENAI_API_KEY dans .env ou le chemin TXT est invalide."
    )

# Initialisation du client OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Lecture du contenu du fichier texte
with TXT_PATH.open('r', encoding='utf-8') as f:
    txt_content = f.read()


def call_gpt4_1_json_mode(content: str, output_path: str):
    messages = [
        {"role": "system",
         "content": (
             "Tu es un assistant expert en SVT. Ci-dessous le contenu complet du programme SVT cycle 4 :\n" 
             f"""{content}""" "\n"
             "RENVOIE UNIQUEMENT un objet JSON valide respectant cette structure :\n"
             "{\n"
             "  \"matiere\": \"SVT\",\n"
             "  \"cycle\": \"cycle 4\",\n"
             "  \"chapitres\": [ … ]\n"
             "}\n"
             "PAS DE TEXTE SUPPLÉMENTAIRE, JUSTE LE JSON."
         )},
        {"role": "user",
         "content": "Analyse le contenu et renvoie-moi le JSON demandé."}
    ]

    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        temperature=0,
        max_tokens=8000
    )

    text = resp.choices[0].message.content
    try:
        output_json = json.loads(text)
    except json.JSONDecodeError as e:
        print("===== REPLY FROM MODEL =====")
        print(text)
        raise RuntimeError(f"Échec du parsing JSON : {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=2)

    print(f"[✓] GPT-4.1 JSON-mode → sauvegardé dans « {output_path} »")


def call_gpt4o_structured(content: str, output_path: str):
    schema = {
        # … votre schéma JSON dict …
    }

    messages = [
        {"role": "system",
         "content": (
             "Tu es un assistant expert en SVT. Ci-dessous le contenu complet du programme SVT cycle 4 :\n" 
             f"""{content}""" "\n"
             "Renvoie EXACTEMENT un JSON conforme au schéma suivant :\n"
             f"{json.dumps(schema, indent=2)}\n"
             "RIEN D’AUTRE."
         )},
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

    try:
        validate(output_json, schema)
    except ValidationError as e:
        raise RuntimeError(f"Le JSON retourné n’est pas conforme : {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=2)

    print(f"[✓] GPT-4o Structured → sauvegardé dans « {output_path} »")


if __name__ == "__main__":
    base_name = TXT_PATH.stem
    out1 = f"{base_name}_gpt4-1_jsonmode.json"
    print("[+] Appel 1 : GPT-4.1 (JSON mode)…")
    call_gpt4_1_json_mode(txt_content, out1)

    out2 = f"{base_name}_gpt4o_structured.json"
    print("[+] Appel 2 : GPT-4o (Structured Outputs)…")
    call_gpt4o_structured(txt_content, out2)

    print("\nTous les appels sont terminés.")
