# SillyTavern Persona Generator

Gere personas automaticamente a partir de character cards para uso no SillyTavern.

![Main Window](screenshots/main_window.png)

## Features

- **Interface Gráfica** com tema escuro
- **Suporte a múltiplos provedores de IA**: OpenAI, Anthropic, Groq, OpenRouter, Together, DeepSeek, NVIDIA, Ollama
- **Carregamento de character cards**: JSON e PNG (V2/V3)
- **4 estilos de prompt**: Narrativo, Estruturado, Ficha, Diálogo
- **Opções de pessoa**: Primeira ou terceira pessoa
- **Integração com card-forge** para validação de cards

## Download

Baixe o executável standalone (não precisa de Python instalado):

[**Download Persona Generator.exe**](https://github.com/rafaelramalheteagls-cmd/sillytavern-persona-generator/releases/download/v1.0.0/Persona.Generator.exe)

## Uso

1. Execute o `Persona Generator.exe`
2. Clique em **Configurar API** e insira sua API key
3. Clique em **Carregar Arquivo** e selecione um character card (JSON ou PNG)
4. Configure as opções (sexo, idade, espécie, estilo, pessoa)
5. Clique em **Gerar Persona**
6. Salve a persona gerada

## Configuração da API

O aplicativo suporta múltiplos provedores:

| Provedor | URL Padrão |
|----------|------------|
| OpenAI | api.openai.com |
| Anthropic | api.anthropic.com |
| Groq | api.groq.com |
| OpenRouter | openrouter.ai |
| Together | api.together.xyz |
| DeepSeek | api.deepseek.com |
| NVIDIA | integrate.api.nvidia.com |
| Ollama | localhost:11434 |

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

## Para Desenvolvedores

```bash
# Instalar dependências
pip install card-forge pillow pydantic

# Executar a interface
python persona_gui.py

# Geração via linha de comando
python auto_persona.py character_card.json
```

## Requisitos

- Python 3.8+ (para executar o código fonte)
- Windows (para o executável)

## Licença

MIT License
