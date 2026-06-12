#!/usr/bin/env python3
"""
SillyTavern Persona Generator - GUI Interface
Generate personas from character cards using AI.
"""

import json
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import urllib.request
import urllib.error
import socket
import threading

from forge.models import CharacterCardV2, CharacterCardV3
from forge.helper import extract_card_data, upgrade_v2_to_v3
from PIL import Image
import base64

socket.setdefaulttimeout(120)


def extract_card_from_png(file_path):
    """
    Extract character card data from PNG file with support for multiple formats.
    Handles V2 cards with missing required fields by adding defaults.
    """
    try:
        image = Image.open(file_path)
        
        if not hasattr(image, "text") or not image.text:
            return None
        
        # Try different keys used by various tools
        possible_keys = ["ccv3", "chara", "chara_card_v2", "chara_card_v3", "card"]
        
        for key in possible_keys:
            if key in image.text:
                embedded_data = image.text[key]
                try:
                    decoded_text = base64.b64decode(embedded_data).decode("utf-8")
                    json_data = json.loads(decoded_text)
                    
                    # Check spec version
                    spec = json_data.get("spec", "")
                    
                    if spec == "chara_card_v3" or (key == "ccv3"):
                        return CharacterCardV3.model_validate(json_data)
                    else:
                        # Try V3 first (more flexible)
                        try:
                            return CharacterCardV3.model_validate(json_data)
                        except:
                            pass
                        
                        # Try V2 with defaults for missing fields
                        return _try_v2_with_defaults(json_data)
                            
                except Exception as e:
                    print(f"Error processing chunk '{key}': {e}")
                    continue
        
        # If no known key found, try to decode any text chunk
        for key, value in image.text.items():
            try:
                decoded_text = base64.b64decode(value).decode("utf-8")
                json_data = json.loads(decoded_text)
                
                if "data" in json_data or "name" in json_data:
                    # Try V3 first
                    try:
                        return CharacterCardV3.model_validate(json_data)
                    except:
                        pass
                    
                    # Try V2 with defaults
                    return _try_v2_with_defaults(json_data)
            except:
                continue
        
        return None
        
    except Exception as e:
        print(f"Error extracting card from PNG: {e}")
        return None


def _try_v2_with_defaults(json_data):
    """Try to validate as V2, adding default values for missing required fields."""
    # Add defaults for missing required V2 fields
    defaults = {
        "creator": "",
        "character_version": "",
        "system_prompt": "",
        "post_history_instructions": ""
    }
    
    for field, default_value in defaults.items():
        if field not in json_data:
            json_data[field] = default_value
    
    try:
        wrapped = {"data": json_data}
        card_v2 = CharacterCardV2.model_validate(wrapped)
        return upgrade_v2_to_v3(card_v2)
    except Exception as e:
        print(f"Error in V2 validation: {e}")
        return None

CONFIG_FILE = "api_config.json"

PROVIDERS = {
    "OpenAI": {
        "url": "https://api.openai.com/v1/chat/completions",
        "models_url": "https://api.openai.com/v1/models",
        "header_key": "Authorization",
        "header_prefix": "Bearer "
    },
    "Anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "models_url": None,
        "header_key": "x-api-key",
        "header_prefix": ""
    },
    "Groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "models_url": "https://api.groq.com/openai/v1/models",
        "header_key": "Authorization",
        "header_prefix": "Bearer "
    },
    "OpenRouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "models_url": "https://openrouter.ai/api/v1/models",
        "header_key": "Authorization",
        "header_prefix": "Bearer "
    },
    "Together": {
        "url": "https://api.together.xyz/v1/chat/completions",
        "models_url": "https://api.together.xyz/v1/models",
        "header_key": "Authorization",
        "header_prefix": "Bearer "
    },
    "DeepSeek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "models_url": "https://api.deepseek.com/v1/models",
        "header_key": "Authorization",
        "header_prefix": "Bearer "
    },
    "NVIDIA": {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "models_url": "https://integrate.api.nvidia.com/v1/models",
        "header_key": "Authorization",
        "header_prefix": "Bearer "
    },
    "Local (Ollama)": {
        "url": "http://localhost:11434/v1/chat/completions",
        "models_url": "http://localhost:11434/v1/models",
        "header_key": "Authorization",
        "header_prefix": "Bearer "
    }
}


class PersonaGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SillyTavern Persona Generator")
        self.root.geometry("850x680")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)

        self.card_data = None
        self.persona_text = ""
        self.api_config = self.load_config()

        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("Title.TLabel", background="#1a1a2e", foreground="#e94560", font=("Segoe UI", 16, "bold"))
        style.configure("Subtitle.TLabel", background="#1a1a2e", foreground="#aaa", font=("Segoe UI", 9))
        style.configure("Card.TFrame", background="#16213e", relief="flat")
        style.configure("Info.TLabel", background="#16213e", foreground="#aaa", font=("Segoe UI", 9))
        style.configure("Value.TLabel", background="#16213e", foreground="#fff", font=("Segoe UI", 10, "bold"))
        style.configure("Accent.TButton", background="#e94560", foreground="#fff", font=("Segoe UI", 11, "bold"))
        style.map("Accent.TButton", background=[("active", "#c81e45")])
        style.configure("Secondary.TButton", background="#0f3460", foreground="#fff", font=("Segoe UI", 9))
        style.map("Secondary.TButton", background=[("active", "#1a4a7a")])
        style.configure("Success.TButton", background="#27ae60", foreground="#fff", font=("Segoe UI", 11, "bold"))
        style.map("Success.TButton", background=[("active", "#219a52")])
        style.configure("Config.TFrame", background="#1a1a2e", relief="flat")
        style.configure("ConfigTitle.TLabel", background="#1a1a2e", foreground="#e94560", font=("Segoe UI", 14, "bold"))

    def create_widgets(self):
        header = ttk.Frame(self.root, padding=(20, 10, 20, 5))
        header.pack(fill=tk.X)

        ttk.Label(header, text="SILLYTAVERN PERSONA GENERATOR", style="Title.TLabel").pack(side=tk.LEFT)

        self.btn_config = ttk.Button(header, text="Configure API", style="Secondary.TButton", command=self.open_config)
        self.btn_config.pack(side=tk.RIGHT)

        self.api_status_var = tk.StringVar(value="API: Not configured")
        ttk.Label(header, textvariable=self.api_status_var, style="Info.TLabel").pack(side=tk.RIGHT, padx=10)

        ttk.Label(self.root, text="Generate personas from character cards", style="Subtitle.TLabel").pack(pady=(0, 5))

        main = ttk.Frame(self.root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        card_frame = ttk.Frame(main, style="Card.TFrame", padding=15)
        card_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(card_frame, text="CHARACTER CARD", style="Value.TLabel").pack(anchor=tk.W, pady=(0, 8))

        btn_row = ttk.Frame(card_frame, style="Card.TFrame")
        btn_row.pack(fill=tk.X)

        ttk.Button(btn_row, text="Load File (JSON/PNG)", style="Accent.TButton", command=self.load_card).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="Paste JSON", style="Secondary.TButton", command=self.paste_json).pack(side=tk.LEFT)

        self.lbl_card_name = ttk.Label(card_frame, text="No card loaded", style="Info.TLabel")
        self.lbl_card_name.pack(anchor=tk.W, pady=(8, 0))

        user_frame = ttk.Frame(main, style="Card.TFrame", padding=15)
        user_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(user_frame, text="YOUR OPTIONS", style="Value.TLabel").pack(anchor=tk.W, pady=(0, 8))

        row1 = ttk.Frame(user_frame, style="Card.TFrame")
        row1.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row1, text="Gender:", style="Info.TLabel").pack(side=tk.LEFT)
        self.var_sex = tk.StringVar(value="Male")
        ttk.Combobox(row1, textvariable=self.var_sex, values=["Male", "Female", "Other", "Not specified"], state="readonly", width=15).pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(row1, text="Age:", style="Info.TLabel").pack(side=tk.LEFT)
        self.var_age = tk.StringVar(value="25")
        ttk.Entry(row1, textvariable=self.var_age, width=8).pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(row1, text="Species/Race:", style="Info.TLabel").pack(side=tk.LEFT)
        self.var_species = tk.StringVar(value="Human")
        ttk.Entry(row1, textvariable=self.var_species, width=15).pack(side=tk.LEFT, padx=5)

        row2 = ttk.Frame(user_frame, style="Card.TFrame")
        row2.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row2, text="Prompt Style:", style="Info.TLabel").pack(side=tk.LEFT)
        self.var_style = tk.StringVar(value="Structured")
        ttk.Combobox(row2, textvariable=self.var_style, values=["Narrative", "Structured", "Profile", "Dialogue"], state="readonly", width=15).pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(row2, text="Person:", style="Info.TLabel").pack(side=tk.LEFT)
        self.var_person = tk.StringVar(value="First person")
        ttk.Combobox(row2, textvariable=self.var_person, values=["First person", "Third person"], state="readonly", width=15).pack(side=tk.LEFT, padx=(5, 5))

        ttk.Label(user_frame, text="Character description (optional):", style="Info.TLabel").pack(anchor=tk.W, pady=(5, 3))
        self.txt_user_desc = tk.Text(user_frame, height=2, bg="#0d1b2a", fg="#ccc", insertbackground="#ccc", font=("Segoe UI", 9), wrap=tk.WORD)
        self.txt_user_desc.pack(fill=tk.X)

        gen_frame = ttk.Frame(main, style="Card.TFrame", padding=15)
        gen_frame.pack(fill=tk.X, pady=(0, 10))

        btn_row2 = ttk.Frame(gen_frame, style="Card.TFrame")
        btn_row2.pack(fill=tk.X)

        self.btn_generate = ttk.Button(btn_row2, text="Generate Persona with AI", style="Success.TButton", command=self.generate_persona, state=tk.DISABLED)
        self.btn_generate.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Waiting for character card...")
        ttk.Label(btn_row2, textvariable=self.status_var, style="Info.TLabel").pack(side=tk.LEFT, padx=15)

        result_frame = ttk.Frame(main, style="Card.TFrame", padding=15)
        result_frame.pack(fill=tk.BOTH, expand=True)

        btn_row3 = ttk.Frame(result_frame, style="Card.TFrame")
        btn_row3.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(btn_row3, text="GENERATED PERSONA", style="Value.TLabel").pack(side=tk.LEFT)

        self.btn_save = ttk.Button(btn_row3, text="Save Persona", style="Accent.TButton", command=self.save_persona, state=tk.DISABLED)
        self.btn_save.pack(side=tk.RIGHT)

        self.txt_persona = scrolledtext.ScrolledText(result_frame, height=6, bg="#0d1b2a", fg="#e0e0e0", insertbackground="#e0e0e0", font=("Consolas", 10), wrap=tk.WORD)
        self.txt_persona.pack(fill=tk.BOTH, expand=True)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.api_status_var = tk.StringVar(value=f"API: {config.get('provider', 'Not configured')}")
                    return config
            except:
                pass
        return {"provider": "", "api_key": "", "model": "", "custom_url": ""}

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.api_config, f, indent=2)
        self.api_status_var.set(f"API: {self.api_config.get('provider', 'Not configured')}")

    def open_config(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("API Configuration")
        dialog.geometry("520x480")
        dialog.configure(bg="#1a1a2e")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="API CONFIGURATION", style="ConfigTitle.TLabel").pack(pady=15)

        form = ttk.Frame(dialog, style="Config.TFrame", padding=20)
        form.pack(fill=tk.BOTH, expand=True)

        ttk.Label(form, text="Provider:", style="Info.TLabel").pack(anchor=tk.W)
        provider_var = tk.StringVar(value=self.api_config.get("provider", ""))
        provider_combo = ttk.Combobox(form, textvariable=provider_var, values=list(PROVIDERS.keys()), state="readonly", width=30)
        provider_combo.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(form, text="API Key:", style="Info.TLabel").pack(anchor=tk.W)
        key_var = tk.StringVar(value=self.api_config.get("api_key", ""))
        ttk.Entry(form, textvariable=key_var, width=50, show="*").pack(fill=tk.X, pady=(0, 10))

        model_frame = ttk.Frame(form, style="Config.TFrame")
        model_frame.pack(fill=tk.X, pady=(0, 10))

        model_label_frame = ttk.Frame(model_frame, style="Config.TFrame")
        model_label_frame.pack(fill=tk.X)
        ttk.Label(model_label_frame, text="Model:", style="Info.TLabel").pack(side=tk.LEFT)

        btn_fetch = ttk.Button(model_label_frame, text="Fetch Models", style="Secondary.TButton")
        btn_fetch.pack(side=tk.RIGHT)

        model_var = tk.StringVar(value=self.api_config.get("model", ""))
        model_combo = ttk.Combobox(model_frame, textvariable=model_var, width=40)
        model_combo.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(form, text="Custom URL (optional):", style="Info.TLabel").pack(anchor=tk.W)
        url_var = tk.StringVar(value=self.api_config.get("custom_url", ""))
        url_entry = ttk.Frame(form, style="Config.TFrame")
        url_entry.pack(fill=tk.X, pady=(0, 10))
        ttk.Entry(url_entry, textvariable=url_var, width=45).pack(side=tk.LEFT)
        ttk.Label(url_entry, text="(leave empty for default)", style="Info.TLabel").pack(side=tk.LEFT, padx=5)

        def fetch_models():
            provider = provider_var.get()
            api_key = key_var.get().strip()

            if not provider:
                messagebox.showwarning("Warning", "Select a provider", parent=dialog)
                return

            if provider != "Local (Ollama)" and not api_key:
                messagebox.showwarning("Warning", "Enter the API Key", parent=dialog)
                return

            prov_config = PROVIDERS[provider]
            models_url = prov_config.get("models_url")

            if not models_url:
                messagebox.showinfo("Info", "This provider does not support model listing.", parent=dialog)
                return

            btn_fetch.config(state=tk.DISABLED, text="Fetching...")

            def run_fetch():
                try:
                    headers = {"Accept": "application/json"}
                    if api_key:
                        headers[prov_config["header_key"]] = prov_config["header_prefix"] + api_key

                    req = urllib.request.Request(models_url, headers=headers, method="GET")

                    with urllib.request.urlopen(req, timeout=60) as response:
                        result = json.loads(response.read().decode())

                        models = []
                        if "data" in result:
                            models = [m.get("id", "") for m in result["data"] if m.get("id")]
                        elif "models" in result:
                            models = [m.get("id", m.get("name", "")) for m in result["models"]]

                        models.sort()

                        self.root.after(0, lambda: self._update_models(dialog, model_combo, model_var, models))

                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed:\n{str(e)}", parent=dialog))
                finally:
                    self.root.after(0, lambda: btn_fetch.config(state=tk.NORMAL, text="Fetch Models"))

            threading.Thread(target=run_fetch, daemon=True).start()

        btn_fetch.config(command=fetch_models)

        def on_provider_change(event):
            provider = provider_var.get()
            model_combo['values'] = []
            model_var.set("")
            if provider in PROVIDERS:
                url_var.set(PROVIDERS[provider]["url"])

        provider_combo.bind("<<ComboboxSelected>>", on_provider_change)

        def test_connection():
            provider = provider_var.get()
            api_key = key_var.get().strip()
            model = model_var.get().strip()

            if not provider:
                messagebox.showwarning("Warning", "Select a provider", parent=dialog)
                return

            if provider != "Local (Ollama)" and not api_key:
                messagebox.showwarning("Warning", "Enter the API Key", parent=dialog)
                return

            if not model:
                messagebox.showwarning("Warning", "Select a model", parent=dialog)
                return

            self.status_var.set("Testing connection...")

            def run_test():
                try:
                    prov_config = PROVIDERS[provider]
                    url = url_var.get().strip() or prov_config["url"]

                    headers = {"Content-Type": "application/json"}
                    if api_key:
                        headers[prov_config["header_key"]] = prov_config["header_prefix"] + api_key

                    payload = {"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}

                    data = json.dumps(payload).encode('utf-8')
                    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

                    with urllib.request.urlopen(req, timeout=30) as response:
                        self.root.after(0, lambda: messagebox.showinfo("Success", f"Connection OK!\nModel: {model}"))
                        self.root.after(0, lambda: self.status_var.set("Connection OK"))

                except urllib.error.HTTPError as e:
                    error_code = e.code
                    error_msg = f"HTTP {error_code}"
                    try:
                        body = e.read().decode()
                        j = json.loads(body)
                        if "error" in j:
                            error_msg += f"\n{j['error'].get('message', '')}"
                    except:
                        pass
                    self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
                    self.root.after(0, lambda: self.status_var.set(f"Error {error_code}"))
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda: messagebox.showerror("Error", error_msg))

            threading.Thread(target=run_test, daemon=True).start()

        def save():
            self.api_config = {
                "provider": provider_var.get(),
                "api_key": key_var.get().strip(),
                "model": model_var.get().strip(),
                "custom_url": url_var.get().strip()
            }
            self.save_config()
            messagebox.showinfo("Success", "Configuration saved!", parent=dialog)
            dialog.destroy()

        btn_frame = ttk.Frame(form, style="Config.TFrame")
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(btn_frame, text="Test Connection", style="Secondary.TButton", command=test_connection).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Save", style="Accent.TButton", command=save).pack(side=tk.RIGHT)

    def _update_models(self, dialog, combo, var, models):
        if not models:
            messagebox.showinfo("Info", "No models found", parent=dialog)
            return
        combo['values'] = models
        if models:
            var.set(models[0])
        self.status_var.set(f"{len(models)} models found")

    def load_card(self):
        file_path = filedialog.askopenfilename(
            title="Select Character Card",
            filetypes=[("Character Cards", "*.json *.png"), ("JSON", "*.json"), ("PNG", "*.png"), ("All", "*.*")]
        )

        if file_path:
            try:
                ext = Path(file_path).suffix.lower()

                if ext == '.png':
                    card = extract_card_from_png(file_path)
                    if card:
                        self.card_data = card.data.model_dump()
                    else:
                        messagebox.showerror("Error", "Could not extract data from PNG.\n\nPlease verify the file is a valid character card.")
                        return
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.card_data = json.load(f)

                    if 'spec' in self.card_data:
                        if self.card_data.get('spec') == 'chara_card_v3':
                            validated = CharacterCardV3.model_validate(self.card_data)
                            self.card_data = validated.data.model_dump()
                        elif self.card_data.get('spec') == 'chara_card_v2':
                            validated = CharacterCardV2.model_validate(self.card_data)
                            self.card_data = validated.data.model_dump()
                        elif 'data' in self.card_data:
                            self.card_data = self.card_data['data']

                self.lbl_card_name.config(text=f"Loaded: {self.card_data.get('name', '?')}")
                self.status_var.set("Card loaded - Ready to generate")

                if self.api_config.get("api_key") or self.api_config.get("provider") == "Local (Ollama)":
                    self.btn_generate.config(state=tk.NORMAL)

            except Exception as e:
                messagebox.showerror("Error", f"Error loading:\n{str(e)}")

    def paste_json(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Paste JSON")
        dialog.geometry("500x400")
        dialog.configure(bg="#1a1a2e")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Paste the character card JSON:", style="Subtitle.TLabel").pack(pady=10)

        txt = scrolledtext.ScrolledText(dialog, height=15, bg="#16213e", fg="#ccc", insertbackground="#ccc", font=("Consolas", 9))
        txt.pack(fill=tk.BOTH, expand=True, padx=10)

        def apply():
            try:
                self.card_data = json.loads(txt.get("1.0", tk.END))

                if 'spec' in self.card_data:
                    if self.card_data.get('spec') == 'chara_card_v2':
                        validated = CharacterCardV2.model_validate(self.card_data)
                        self.card_data = validated.data.model_dump()
                    elif 'data' in self.card_data:
                        self.card_data = self.card_data['data']

                self.lbl_card_name.config(text=f"Loaded: {self.card_data.get('name', '?')}")
                self.status_var.set("JSON loaded - Ready to generate")

                if self.api_config.get("api_key") or self.api_config.get("provider") == "Local (Ollama)":
                    self.btn_generate.config(state=tk.NORMAL)

                dialog.destroy()
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON:\n{str(e)}", parent=dialog)

        ttk.Button(dialog, text="Apply", style="Accent.TButton", command=apply).pack(pady=10)

    def build_prompt(self):
        name = self.card_data.get('name', 'Unknown')
        desc = self.card_data.get('description', '')
        personality = self.card_data.get('personality', '')
        scenario = self.card_data.get('scenario', '')
        first_mes = self.card_data.get('first_mes', '')

        sex = self.var_sex.get()
        age = self.var_age.get()
        species = self.var_species.get()
        user_desc = self.txt_user_desc.get("1.0", tk.END).strip()
        style = self.var_style.get()
        person = self.var_person.get()

        user_prefs = f"Gender: {sex}\nAge: {age}\nSpecies/Race: {species}\nNarrative Perspective: {person}"
        if user_desc:
            user_prefs += f"\nAdditional details from user: {user_desc}"

        card_context = f"Name: {name}\nPersonality: {personality}\nScenario: {scenario}\nDescription: {desc}\nFirst Message: {first_mes}"

        if style == "Narrative":
            return self._prompt_narrative(name, user_prefs, card_context, person)
        elif style == "Structured":
            return self._prompt_structured(name, user_prefs, card_context, person)
        elif style == "Profile":
            return self._prompt_profile(name, user_prefs, card_context, person)
        elif style == "Dialogue":
            return self._prompt_dialogue(name, user_prefs, card_context, person)
        else:
            return self._prompt_structured(name, user_prefs, card_context, person)

    def _prompt_narrative(self, name, user_prefs, card_context, person):
        if person == "First person":
            pov_rules = 'Write a first-person narrative introduction. The persona must feel like a real person introducing themselves naturally - casual, honest, with personality showing through word choice.\n\nInclude: name, age, appearance, personality, skills, history with {name}, and current motivation.\n\nRULES:\n- First person only ("I", "my", "me")'
        else:
            pov_rules = 'Write a third-person narrative description. Describe the character as if telling their story to someone else - casual, vivid, with personality showing through details.\n\nInclude: name, age, appearance, personality, skills, history with {name}, and current motivation.\n\nRULES:\n- Third person only ("he/she", "his/her", "the character")'

        return f"""You are an expert persona designer for roleplay scenarios. Design a persona profile for a user who will interact with {name}.

USER PREFERENCES:
{user_prefs}

{pov_rules}
- 200-350 words
- No bullet points or lists
- Natural and immersive
- Do NOT mention {{user}} or {{char}}
- Do NOT include meta-commentary

CHARACTER CONTEXT:
{card_context}

Write the persona as a cohesive narrative."""

    def _prompt_structured(self, name, user_prefs, card_context, person):
        if person == "First person":
            pov_label = "first person"
            pronouns = '("I", "my", "me")'
            overview_example = '"A concise 2-3 sentence overview that captures the persona\'s essence, current role, and what makes them unique"'
            name_example = '"My name"'
            species_example = '"What I am (human, elf, whatever)"'
            gender_example = '"My gender"'
            age_example = '"My age"'
        else:
            pov_label = "third person"
            pronouns = '("he/she", "his/her", "the character")'
            overview_example = '"A concise 2-3 sentence overview that captures the character\'s essence, current role, and what makes them unique"'
            name_example = '"Character\'s name"'
            species_example = '"What they are (human, elf, whatever)"'
            gender_example = '"Their gender"'
            age_example = '"Their age"'

        return f"""You are an expert persona designer for roleplay scenarios. Create a persona profile for someone who will interact with {name}.

Write in {pov_label} {pronouns}. Keep it casual and direct - no fancy academic language, no overwrought descriptions. Think "friend helping you brainstorm" not "literature professor."

USER PREFERENCES:
{user_prefs}

CHARACTER CONTEXT:
{card_context}

FORMAT:

<overview>
-{overview_example}
</overview>

<general_info>
-Name: {name_example}
-Species: {species_example}
-Gender: {gender_example}
-Age: {age_example}
-Occupation: "What they do"
</general_info>

<backstory>
-Origins: "Where they started - be specific about formative experiences"
-Major events: "The big shit that changed them - trauma, victories, failures that still affect them"
-Current situation: "What's happening in their life right now and how they got here"
-Key relationships: "People who matter - family, friends, enemies, lovers - and how these connections still influence them"
</backstory>

<personality_core>
-How they actually behave: "Skip generic traits. Instead: What do THEY specifically do when scared? How do THEY handle being pissed off? What are THEIR weird habits?"
-What drives them: "What gets them up in the morning? What do they love/hate/need? Connect this directly to their past."
-Internal conflicts: "What wars are happening in their head? Where do they contradict themselves?"
-Stress responses: "Their specific ways of dealing with pressure - healthy and unhealthy"
</personality_core>

<quick_reference>
-Likes: "What they enjoy, appreciate, or find pleasant"
-Loves: "What they feel passionate about or hold most dear"
-Dislikes: "What they find annoying or mildly objectionable"
-Hates: "What they despise or feel strong aversion toward"
-Wants: "Short and long-term desires and goals"
-Fears: "What they dread, including phobias and deep concerns"
</quick_reference>

<physical_presence>
-Body: "Height, build, distinctive features - stuff that matters to who they are"
-How they carry themselves: "Posture, movement, presence - what does their body language say?"
-Memorable details: "Scars, marks, quirks that tell their story"
</physical_presence>

<expression_patterns>
-Movement style: "How do THEY specifically move? Not generic gestures - their unique physical habits"
-Speech patterns: "Their vocabulary, rhythm, verbal tics - shaped by background and personality"
-Emotional displays: "How do THEY show feelings? What are their specific tells? Avoid cliches."
-Social masks: "How do they act differently with different people?"
</expression_patterns>

<worldview>
-Core beliefs: "What they think about life, right/wrong, relationships - and why they think it"
-How they make decisions: "Their process for choices - what matters most to them?"
-Blind spots: "What they can't see about themselves or situations"
</worldview>

<capabilities>
-Special abilities: "Powers, magic, supernatural stuff (if any) and how it connects to their story"
-Practical skills: "What they're good at and how they learned it"
-Their style: "How do they use their abilities? What's their approach?"
</capabilities>

<style_choices>
-Fashion sense: "What they wear and why - how clothes reflect personality"
-Favorite apparel: "Typical outfits based on personality"
</style_choices>

<context>
-Cultural influences: "Background elements that shape their worldview"
-Special knowledge: "Unique concepts, specialized info needed to understand them"
-Relationship patterns: "How they typically connect with others - what patterns emerge"
</context>

EACH section must be informative while avoiding redundancy at all costs. Keep it direct, have fun with it, and make every behavior SPECIFIC to this character's background. No generic reactions/actions - make sure it's UNIQUE to the character.

Do NOT mention {{user}} or {{char}}. Do NOT include meta-commentary or system instructions."""

    def _prompt_profile(self, name, user_prefs, card_context, person):
        if person == "First person":
            pov_rules = "Each field value must be written in first person"
            field_template = "NAME: [My name]\nAGE: [My age]\nGENDER: [My gender]\nSPECIES: [My species/race]\nOCCUPATION: [What I do]"
        else:
            pov_rules = "Each field value must be written in third person"
            field_template = "NAME: [Character name]\nAGE: [Character age]\nGENDER: [Character gender]\nSPECIES: [Character species/race]\nOCCUPATION: [What they do]"

        return f"""You are an expert persona designer for roleplay scenarios. Create a character profile sheet for a user who will interact with {name}.

USER PREFERENCES:
{user_prefs}

Generate a PERSONA PROFILE CARD with these fields:

{field_template}

APPEARANCE: [2-3 sentences about physical appearance]

PERSONALITY: [2-3 sentences about how they behave and speak]

BACKGROUND: [2-3 sentences about history and connection to {name}]

SKILLS: [1-2 sentences about abilities]

FLAWS: [1-2 sentences about weaknesses]

GOALS: [1-2 sentences about what they want]

RELATIONSHIP TO {name.upper()}: [How they know them and their dynamic]

RULES:
- {pov_rules}
- Keep each field concise but descriptive
- Total: 200-350 words
- Do NOT mention {{user}} or {{char}}
- Do NOT include meta-commentary

CHARACTER CONTEXT:
{card_context}

Generate the persona profile card."""

    def _prompt_dialogue(self, name, user_prefs, card_context, person):
        if person == "First person":
            pov_rules = 'Write as spoken dialogue in first person with natural speech patterns\n- Include brief action/narration in asterisks (*adjusts cloak*, *smiles*)\n- Make it feel like meeting a real person'
        else:
            pov_rules = 'Write as a narrative description of the character introducing themselves in third person\n- Include action/narration in asterisks (*adjusts cloak*, *smiles*)\n- Make it feel like observing a real person'

        return f"""You are an expert persona designer for roleplay scenarios. Create a self-introduction for a user who will meet {name}.

USER PREFERENCES:
{user_prefs}

Include naturally:
- Name and how they prefer to be called
- What they look like (mentioned casually)
- Their personality showing through how they speak
- Why they are here and their connection to {name}
- A hint at their skills or background
- What they want or are looking for

RULES:
- {pov_rules}
- 150-300 words
- Do NOT mention {{user}} or {{char}}
- Do NOT include system instructions or meta-commentary

CHARACTER CONTEXT:
{card_context}

Write the self-introduction."""

    def generate_persona(self):
        if not self.card_data:
            messagebox.showwarning("Warning", "Load a character card first")
            return

        provider = self.api_config.get("provider", "")
        api_key = self.api_config.get("api_key", "")
        model = self.api_config.get("model", "")

        if not provider:
            messagebox.showwarning("Warning", "Configure the API first")
            return

        if provider != "Local (Ollama)" and not api_key:
            messagebox.showwarning("Warning", "Configure the API Key")
            return

        if not model:
            messagebox.showwarning("Warning", "Select a model in the configuration")
            return

        self.btn_generate.config(state=tk.DISABLED, text="Generating...")
        self.status_var.set("Generating persona...")
        self.txt_persona.delete("1.0", tk.END)
        self.txt_persona.insert("1.0", "Generating persona with AI, please wait...")
        self.btn_save.config(state=tk.DISABLED)

        def run():
            try:
                prov_config = PROVIDERS[provider]
                url = self.api_config.get("custom_url") or prov_config["url"]
                prompt = self.build_prompt()

                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers[prov_config["header_key"]] = prov_config["header_prefix"] + api_key

                if provider == "Anthropic":
                    payload = {"model": model, "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]}
                else:
                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.8,
                        "max_tokens": 2048
                    }

                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers)

                with urllib.request.urlopen(req, timeout=120) as response:
                    result = json.loads(response.read().decode())

                    if provider == "Anthropic":
                        content = result["content"][0]["text"]
                    else:
                        content = result["choices"][0]["message"]["content"]

                    self.persona_text = content.strip()

                    self.root.after(0, lambda: self._show_result())

            except urllib.error.HTTPError as e:
                error_code = e.code
                error_msg = f"HTTP {error_code}"
                try:
                    body = e.read().decode()
                    j = json.loads(body)
                    if "error" in j:
                        error_msg += f"\n{j['error'].get('message', '')}"
                except:
                    pass
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
                self.root.after(0, lambda: self.status_var.set("Error generating"))
                self.root.after(0, lambda: self.txt_persona.delete("1.0", tk.END))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
                self.root.after(0, lambda: self.status_var.set("Error generating"))
                self.root.after(0, lambda: self.txt_persona.delete("1.0", tk.END))
            finally:
                self.root.after(0, lambda: self.btn_generate.config(state=tk.NORMAL, text="Generate Persona with AI"))

        threading.Thread(target=run, daemon=True).start()

    def _show_result(self):
        self.txt_persona.delete("1.0", tk.END)
        self.txt_persona.insert("1.0", self.persona_text)
        self.btn_save.config(state=tk.NORMAL)
        self.status_var.set("Persona generated successfully")

    def save_persona(self):
        if not self.persona_text:
            return

        persona = {
            "name": "{{user}}",
            "description": self.persona_text,
            "avatar": ""
        }

        file_path = filedialog.asksaveasfilename(
            title="Save Persona",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=f"persona_{self.card_data.get('name', 'character')}.json"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(persona, f, indent=2, ensure_ascii=False)

                self.status_var.set(f"Saved: {Path(file_path).name}")
                messagebox.showinfo("Success", f"Persona saved to:\n{file_path}\n\nTo use in SillyTavern:\n1. Open SillyTavern\n2. Click the persona icon\n3. Click 'Create'\n4. Import the file")

            except Exception as e:
                messagebox.showerror("Error", f"Error saving:\n{str(e)}")


def main():
    root = tk.Tk()
    PersonaGeneratorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
