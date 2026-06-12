# Gerador de Personas - SillyTavern

Gere personas automaticamente a partir de character cards para uso no SillyTavern.

## Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `persona_generator.py` | Interface interativa com menu |
| `auto_persona.py` | Geração automática via linha de comando |
| `persona_example.json` | Exemplo de character card |

## Uso Rápido

```bash
# Geração automática
python auto_persona.py character_card.json

# Com saída customizada
python auto_persona.py character_card.json minha_persona.json

# Interface interativa
python persona_generator.py
```

## Como Importar no SillyTavern

1. Abra o SillyTavern
2. Clique no ícone de persona (👤) no menu superior
3. Clique em "Create"
4. Importe o arquivo JSON gerado
5. A persona estará pronta para uso

## Formato da Persona

```json
{
  "name": "{{user}}",
  "description": "Descrição da persona",
  "avatar": ""
}
```

## Detecção Automática

O programa detecta automaticamente:
- Gênero do personagem
- Tom da personalidade (romântico, sombrio, amigável, neutro)
- Gera persona adequada ao contexto

## Requisitos

- Python 3.6+
- Nenhuma dependência externa
