"""Grava o config.toml correto (sem \r\n do Windows que pode quebrar o parsing)."""
from pathlib import Path

config_dir = Path(__file__).parent / ".streamlit"
config_dir.mkdir(exist_ok=True)
config_path = config_dir / "config.toml"

linhas = [
    "[client]",
    "showErrorDetails = false",
    "",
    "[server]",
    "enableStaticServing = true",
    "",
    "[theme]",
    'base = "light"',
    'primaryColor = "#3B82F6"',
    'backgroundColor = "#FFFFFF"',
    'secondaryBackgroundColor = "#F7F8F9"',
    'textColor = "#172B4D"',
    'font = "sans serif"',
    'headingFontSizes = ["22px", "17px", "15px", "14px", "13px", "12px"]',
    "headingFontWeights = [700, 600, 500, 500, 400, 400]",
    "",
    "[theme.sidebar]",
    'backgroundColor = "#1d2125"',
    'secondaryBackgroundColor = "#282e33"',
    'textColor = "#c9d1d9"',
    'primaryColor = "#4c9aff"',
]

# newline="\n" garante line endings Unix mesmo no Windows
config_path.write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")
print("Gravado:", config_path)

has_cr = b"\r" in config_path.read_bytes()
print("tem \\r (problema):", has_cr, "— deve ser False")
print()
print(config_path.read_text())

user_cfg = Path.home() / ".streamlit" / "config.toml"
if user_cfg.exists():
    print("CONFLITO em:", user_cfg)
    print(user_cfg.read_text())
else:
    print("Sem conflito no perfil do usuario")
