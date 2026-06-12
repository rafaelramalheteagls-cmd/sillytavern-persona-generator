#!/usr/bin/env python3
"""
Gerador automático de personas do SillyTavern.
Uso: python auto_persona.py <character_card.json> [output.json]
"""

import json
import sys
from pathlib import Path


def load_card(file_path: str) -> dict:
    with open(file_path, 'r', encoding='utf-8') as f:
        card = json.load(f)
    
    if 'spec' in card and card.get('spec') == 'chara_card_v2':
        return card.get('data', card)
    elif 'name' in card:
        return card
    else:
        raise ValueError("Formato não reconhecido")


def detect_tone(personality: str, description: str) -> str:
    text = (personality + ' ' + description).lower()
    
    romantic = ['amor', 'romântico', 'carinho', 'afetuoso', 'gentil', 'terno']
    dark = ['sombrio', 'misterioso', 'maldoso', 'villão', 'vilão', 'sombrio']
    friendly = ['amigável', 'amigo', 'divertido', 'alegre', 'feliz']
    
    if any(w in text for w in romantic):
        return 'romantic'
    if any(w in text for w in dark):
        return 'dark'
    if any(w in text for w in friendly):
        return 'friendly'
    return 'neutral'


def generate_persona(card_data: dict) -> dict:
    name = card_data.get('name', 'Character')
    personality = card_data.get('personality', '')
    description = card_data.get('description', '')
    scenario = card_data.get('scenario', '')
    
    tone = detect_tone(personality, description)
    
    templates = {
        'romantic': f"Você é uma pessoa carinhosa e atenciosa desenvolvendo uma conexão especial com {name}. Demonstre afeto genuíno e respeito mútuo.",
        'dark': f"Você é uma pessoa determinada e corajosa que encara {name} de igual para igual. Não se intimide facilmente.",
        'friendly': f"Você é um bom amigo(a) de {name}. Compartilhem risadas e experiências juntos.",
        'neutral': f"Você está interagindo com {name}. Responda de forma natural e envolvente.",
    }
    
    persona_desc = templates[tone]
    
    if scenario:
        persona_desc += f"\n\nContexto: {scenario}"
    
    return {
        'name': '{{user}}',
        'description': persona_desc,
        'avatar': ''
    }


def main():
    if len(sys.argv) < 2:
        print("Uso: python auto_persona.py <character_card.json> [output.json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else f"persona_{Path(input_file).stem}.json"
    
    card = load_card(input_file)
    persona = generate_persona(card)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(persona, f, indent=2, ensure_ascii=False)
    
    print(f"Persona gerada: {output_file}")
    print(f"Para {card.get('name', 'Personagem')}")
    print(f"\nPara usar no SillyTavern:")
    print(f"1. Abra o SillyTavern")
    print(f"2. Clique no ícone de persona")
    print(f"3. Clique em 'Create'")
    print(f"4. Importe o arquivo {output_file}")


if __name__ == '__main__':
    main()
