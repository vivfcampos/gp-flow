"""
Configuração central do GP Flow.
Todos os caminhos do projeto ficam aqui para evitar problemas
quando o app rodar em outro computador ou outra pasta.
"""
from pathlib import Path

BASE_DIR = Path(__file__).parent

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE = DATA_DIR / "gpflow.db"

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

BACKUP_DIR = BASE_DIR / "backup"
BACKUP_DIR.mkdir(exist_ok=True)

# Cores usadas nos indicadores de aging (dias sem movimento)
COR_AGING_OK = "#2ecc71"      # até 15 dias
COR_AGING_ATENCAO = "#f39c12"  # 16 a 30 dias
COR_AGING_CRITICO = "#e74c3c"  # acima de 30 dias
