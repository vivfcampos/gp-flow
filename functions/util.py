"""
Funções utilitárias usadas em várias telas do GP Flow.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

from config import COR_AGING_OK, COR_AGING_ATENCAO, COR_AGING_CRITICO

FUSO_BR = ZoneInfo("America/Sao_Paulo")


def agora_br() -> str:
    """
    Data/hora atual no fuso de Brasília, já formatada para gravar no banco
    e exibir na tela (dd/mm/aaaa hh:mm:ss).

    Existe porque o CURRENT_TIMESTAMP do SQLite grava sempre em UTC, o que
    deixava a hora de importação 3h adiantada em relação ao horário local.
    """
    return datetime.now(FUSO_BR).strftime("%d/%m/%Y %H:%M:%S")


def calcular_aging(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona a coluna 'aging_dias'. Usa o aging já calculado pelo Trace
    ('aging_trace' = Tempo da Demanda em dias) quando disponível — é o número
    oficial da ferramenta. Só recalcula pela data de criação quando o Trace
    não trouxe o valor.
    """
    df = df.copy()
    datas = pd.to_datetime(df["data_criacao"], errors="coerce")
    hoje = pd.Timestamp(datetime.now().date())
    aging_calc = (hoje - datas).dt.days

    if "aging_trace" in df.columns:
        aging_trace = pd.to_numeric(df["aging_trace"], errors="coerce")
        df["aging_dias"] = aging_trace.fillna(aging_calc)
    else:
        df["aging_dias"] = aging_calc

    # inteiro; aging desconhecido vira 0 (evita NA se propagando p/ score, grid, excel)
    df["aging_dias"] = pd.to_numeric(df["aging_dias"], errors="coerce").fillna(0).astype(int)
    return df


def classificar_aging(dias):
    """Classifica o aging em faixas simples de leitura rápida."""
    if pd.isna(dias):
        return "—"
    if dias <= 15:
        return "🟢 Em dia"
    if dias <= 30:
        return "🟡 Atenção"
    return "🔴 Crítico"


def cor_aging(dias) -> str:
    if pd.isna(dias):
        return "#95a5a6"
    if dias <= 15:
        return COR_AGING_OK
    if dias <= 30:
        return COR_AGING_ATENCAO
    return COR_AGING_CRITICO


def aplicar_filtros(df: pd.DataFrame, texto_busca: str = "", **filtros) -> pd.DataFrame:
    """
    Aplica busca textual (no título e no solicitante) e filtros exatos
    (estado, prioridade, tipo, responsavel_atendimento, ...).
    """
    resultado = df.copy()

    if texto_busca:
        termo = texto_busca.strip().lower()
        resultado = resultado[
            resultado["titulo"].str.lower().str.contains(termo, na=False)
            | resultado["solicitante"].str.lower().str.contains(termo, na=False)
            | resultado["id"].astype(str).str.contains(termo, na=False)
        ]

    for coluna, valores in filtros.items():
        if valores:
            resultado = resultado[resultado[coluna].isin(valores)]

    return resultado


def busca_universal(df: pd.DataFrame, termo: str, colunas: list = None) -> pd.DataFrame:
    """
    Pesquisa única: procura o termo em QUALQUER coluna (texto ou número),
    não só título/solicitante. Usada no Backlog conforme a especificação
    ("Pesquisar em qualquer coluna").
    """
    if not termo:
        return df
    termo = termo.strip().lower()
    colunas = colunas or df.columns.tolist()
    mascara = pd.Series(False, index=df.index)
    for coluna in colunas:
        mascara = mascara | df[coluna].astype(str).str.lower().str.contains(termo, na=False)
    return df[mascara]


def formatar_codigo(texto) -> str:
    """
    Remove o código técnico de campos como Tipo/Prioridade para exibição.
    Ex.: "3.20 - Serviço Suporte" -> "Serviço Suporte"; "1 - Baixa" -> "Baixa".
    O banco continua guardando o valor original — isso é só cosmético.
    """
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    texto = str(texto)
    partes = texto.split(" - ", 1)
    if len(partes) == 2 and any(c.isdigit() for c in partes[0]):
        return partes[1].strip()
    return texto.strip()


def limpar_texto(valor) -> str:
    """
    Normaliza um valor de texto para exibição, tratando resíduos como vazio.
    Retorna "" quando o valor é None, NaN, ou a string "nan"/"none"/"null"
    (lixo que sobrou de importações antigas). Caso contrário, devolve o texto.
    Use em campos como impedimento/observações antes de mostrar na tela.
    """
    if valor is None:
        return ""
    if isinstance(valor, float) and pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.lower() in ("nan", "none", "null"):
        return ""
    return texto


def busca_por_ids(df: pd.DataFrame, texto: str) -> pd.DataFrame:
    """
    Busca por vários Ids de uma vez. Aceita separadores ; , espaço, quebra de
    linha e traço/hífen entre eles. Ex.: "123456;123457", "123456 123457",
    "123456-123457" (traço aqui é SEPARADOR, não intervalo).
    Retorna None se o texto não parece uma lista de Ids (aí quem chama usa a
    busca universal normal).
    """
    if not texto:
        return None
    import re as _re
    # extrai todos os grupos de dígitos com 4+ algarismos (Ids do Trace)
    ids = [int(x) for x in _re.findall(r"\d{4,}", texto)]
    if len(ids) < 1:
        return None
    # só trata como "busca por Ids" se o texto for essencialmente números+separadores
    resto = _re.sub(r"[\d\s;,\-–—/]+", "", texto)
    if resto:  # sobrou letra/palavra -> não é busca por Ids, é busca textual
        return None
    return df[df["id"].isin(ids)]
