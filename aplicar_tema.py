"""
Execute este script uma vez para garantir que o config.toml
está correto, independente do que estava antes.

Uso: python aplicar_tema.py
"""
import os
from pathlib import Path

config_dir = Path(__file__).parent / ".streamlit"
config_dir.mkdir(exist_ok=True)
config_path = config_dir / "config.toml"

conteudo = """[client]
showErrorDetails = false

[server]
enableStaticServing = true

[theme]
base = "light"
primaryColor = "#3B82F6"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F7F8F9"
textColor = "#172B4D"
font = "sans serif"
headingFontSizes = ["22px", "17px", "15px", "14px", "13px", "12px"]
headingFontWeights = [700, 600, 500, 500, 400, 400]

[theme.sidebar]
backgroundColor = "#1d2125"
secondaryBackgroundColor = "#282e33"
textColor = "#c9d1d9"
primaryColor = "#4c9aff"
"""

# sobrescreve — sem perguntar, sem pular
config_path.write_text(conteudo, encoding="utf-8")
print(f"✅ Config gravado em: {config_path}")
print()
print("Conteúdo:")
print(config_path.read_text(encoding="utf-8"))

# verifica se há config do usuário que pode sobrescrever
user_config = Path.home() / ".streamlit" / "config.toml"
if user_config.exists():
    print(f"\n⚠️  ATENÇÃO: Existe outro config em {user_config}")
    print("   Este arquivo pode estar sobrescrevendo o do projeto.")
    print("   Conteúdo:")
    print(user_config.read_text(encoding="utf-8"))
else:
    print(f"\n✅ Sem config em {user_config} (sem conflito)")
