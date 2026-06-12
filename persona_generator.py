#!/usr/bin/env python3
"""
SillyTavern Persona Generator
Gera personas baseadas em character cards para uso no SillyTavern.
"""

import json
import os
import sys
from pathlib import Path


def load_character_card(file_path: str) -> dict:
    """Carrega um character card de um arquivo JSON."""
    with open(file_path, 'r', encoding='utf-8') as f:
        card = json.load(f)
    
    # Suporta V1 e V2
    if 'spec' in card and card.get('spec') == 'chara_card_v2':
        return card.get('data', card)
    elif 'name' in card:
        return card
    else:
        raise ValueError("Formato de character card não reconhecido")


def analyze_character(card_data: dict) -> dict:
    """Analisa o character card e extrai informações para geração da persona."""
    name = card_data.get('name', '')
    description = card_data.get('description', '')
    personality = card_data.get('personality', '')
    scenario = card_data.get('scenario', '')
    
    # Análise básica de gênero baseada no nome e descrição
    gender_hints = {
        'feminino': ['ela', 'dela', 'menina', 'mulher', 'garota', 'sra', 'miss', 'princesa', 'rainha', 'dea'],
        'masculino': ['ele', 'dele', 'menino', 'homem', 'garoto', 'sr', 'mr', 'principe', 'rei', 'deus'],
    }
    
    desc_lower = (description + ' ' + personality).lower()
    
    gender = 'neutro'
    for g, hints in gender_hints.items():
        if any(hint in desc_lower for hint in hints):
            gender = g
            break
    
    return {
        'name': name,
        'description': description,
        'personality': personality,
        'scenario': scenario,
        'detected_gender': gender,
    }


def generate_persona_suggestions(char_info: dict) -> list:
    """Gera sugestões de persona baseadas no character card."""
    suggestions = []
    name = char_info['name']
    scenario = char_info['scenario']
    personality = char_info['personality']
    gender = char_info['detected_gender']
    
    # Persona padrão - adaptável
    base_persona = {
        'name': '{{user}}',
        'description': f"Interagindo com {name}.",
    }
    suggestions.append(('Padrão', base_persona))
    
    # Persona romântica
    if any(word in personality.lower() for word in ['amor', 'romântico', 'carinho', 'afetuoso', 'gentil']):
        romantic = {
            'name': '{{user}}',
            'description': f"Você é uma pessoa carinhosa e atenciosa que está desenvolvendo uma conexão especial com {name}. Demonstre afeto de forma genuína e respeitosa.",
        }
        suggestions.append(('Romântica', romantic))
    
    # Persona de amizade
    friendship = {
        'name': '{{user}}',
        'description': f"Você é um bom amigo(a) de {name}. São confidentes um do outro e compartilham experiências juntos.",
    }
    suggestions.append(('Amizade', friendship))
    
    # Persona baseada no cenário
    if scenario:
        scenario_persona = {
            'name': '{{user}}',
            'description': f"Você está em um cenário onde {scenario}. Responda de acordo com o contexto.",
        }
        suggestions.append(('Baseada no Cenário', scenario_persona))
    
    # Persona competitiva
    competitive = {
        'name': '{{user}}',
        'description': f"Você tem uma rivalidade saudável com {name}. Desafie-a constantemente e prove seu valor.",
    }
    suggestions.append(('Competitiva', competitive))
    
    # Persona misteriosa
    mysterious = {
        'name': '{{user}}',
        'description': f"Você é uma pessoa misteriosa e enigmática que {name} está tentando decifrar. Revele pouco sobre si mesmo(a).",
    }
    suggestions.append(('Misteriosa', mysterious))
    
    return suggestions


def create_persona(name: str, description: str) -> dict:
    """Cria uma persona no formato SillyTavern."""
    return {
        'name': name,
        'description': description,
        'avatar': '',
    }


def save_persona(persona: dict, output_path: str):
    """Salva a persona em formato JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(persona, f, indent=2, ensure_ascii=False)


def display_menu(options: list, title: str) -> int:
    """Exibe um menu e retorna a opção selecionada."""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)
    
    for i, (label, _) in enumerate(options, 1):
        print(f"  {i}. {label}")
    
    print(f"  0. Voltar")
    print('-'*50)
    
    while True:
        try:
            choice = int(input("  Selecione uma opção: "))
            if 0 <= choice <= len(options):
                return choice
            print("  Opção inválida!")
        except ValueError:
            print("  Por favor, insira um número!")


def main():
    """Função principal do programa."""
    print("\n" + "="*60)
    print("     GERADOR DE PERSONAS - SILLYTAVERN")
    print("="*60)
    print("  Gere personas baseadas em character cards")
    print("  para interação imersiva no SillyTavern")
    print("="*60 + "\n")
    
    while True:
        print("\n  Menu Principal:")
        print("  " + "-"*40)
        print("  1. Carregar Character Card")
        print("  2. Sair")
        print("  " + "-"*40)
        
        choice = input("  Selecione: ").strip()
        
        if choice == '1':
            file_path = input("\n  Caminho do character card (.json): ").strip()
            
            if not os.path.exists(file_path):
                print(f"\n  [ERRO] Arquivo não encontrado: {file_path}")
                continue
            
            try:
                card_data = load_character_card(file_path)
                char_info = analyze_character(card_data)
                
                print(f"\n  [OK] Character Card carregado:")
                print(f"  Nome: {char_info['name']}")
                print(f"  Gênero detectado: {char_info['detected_gender']}")
                print(f"  Personalidade: {char_info['personality'][:50]}...")
                
                # Gerar sugestões
                suggestions = generate_persona_suggestions(char_info)
                
                while True:
                    choice = display_menu(suggestions, "SUGESTÕES DE PERSONA")
                    
                    if choice == 0:
                        break
                    
                    if choice > 0:
                        selected_label, selected_persona = suggestions[choice - 1]
                        
                        print(f"\n  Persona selecionada: {selected_label}")
                        print(f"  Nome: {selected_persona['name']}")
                        print(f"  Descrição: {selected_persona['description'][:80]}...")
                        
                        custom = input("\n  Deseja personalizar? (s/n): ").strip().lower()
                        
                        if custom == 's':
                            new_name = input(f"  Nome da persona [{selected_persona['name']}]: ").strip()
                            if new_name:
                                selected_persona['name'] = new_name
                            
                            print(f"  Descrição atual:\n  {selected_persona['description']}")
                            new_desc = input("  Nova descrição (Enter para manter): ").strip()
                            if new_desc:
                                selected_persona['description'] = new_desc
                        
                        save = input("\n  Salvar persona? (s/n): ").strip().lower()
                        
                        if save == 's':
                            output_file = input(f"  Arquivo de saída [persona_{char_info['name']}.json]: ").strip()
                            if not output_file:
                                output_file = f"persona_{char_info['name']}.json"
                            
                            save_persona(selected_persona, output_file)
                            print(f"\n  [OK] Persona salva em: {output_file}")
                            print(f"\n  Para usar no SillyTavern:")
                            print(f"  1. Abra o SillyTavern")
                            print(f"  2. Clique no ícone de persona (👤)")
                            print(f"  3. Clique em 'Create'")
                            print(f"  4. Importe o arquivo {output_file}")
                            break
            
            except Exception as e:
                print(f"\n  [ERRO] {str(e)}")
        
        elif choice == '2':
            print("\n  Até logo!")
            break
        
        else:
            print("\n  Opção inválida!")


if __name__ == '__main__':
    main()
