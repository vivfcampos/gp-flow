"""
Exportações Excel do GP Flow: Backlog, Curadoria e Sprint.
Todas usam o mesmo estilo visual (cabeçalho azul, zebra, bordas finas).
"""
import io
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.path.append(str(Path(__file__).parent.parent))
from functions.util import formatar_codigo

FONTE = "Arial"
COR_CABECALHO = "1F4E78"
COR_SUBTOTAL = "DDEBF7"
COR_ZEBRA = "F2F2F2"

BORDA_FINA = Border(
    left=Side(style="thin", color="B0B0B0"),
    right=Side(style="thin", color="B0B0B0"),
    top=Side(style="thin", color="B0B0B0"),
    bottom=Side(style="thin", color="B0B0B0"),
)


def _nova_planilha(titulo_aba: str, titulo_topo: str, colunas: list, larguras: list):
    wb = Workbook()
    ws = wb.active
    ws.title = titulo_aba

    ws["A1"] = titulo_topo
    ws["A1"].font = Font(name=FONTE, size=14, bold=True)

    linha_cab = 3
    for col, nome in enumerate(colunas, start=1):
        c = ws.cell(row=linha_cab, column=col, value=nome)
        c.font = Font(name=FONTE, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", start_color=COR_CABECALHO)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDA_FINA
        ws.column_dimensions[get_column_letter(col)].width = larguras[col - 1]
    ws.freeze_panes = f"A{linha_cab + 1}"
    return wb, ws, linha_cab


def _escrever_linhas(ws, linha_inicial: int, linhas: list) -> int:
    """Escreve uma lista de listas de valores a partir da linha_inicial, com zebra. Retorna a próxima linha livre."""
    linha = linha_inicial
    for zebra, valores in enumerate(linhas):
        for col, valor in enumerate(valores, start=1):
            c = ws.cell(row=linha, column=col, value=valor)
            c.font = Font(name=FONTE, size=10)
            c.border = BORDA_FINA
            if zebra % 2 == 1:
                c.fill = PatternFill("solid", start_color=COR_ZEBRA)
            c.alignment = Alignment(vertical="center", wrap_text=True)
        linha += 1
    return linha


def exportar_backlog_excel(df: pd.DataFrame) -> bytes:
    colunas = ["Id", "Título", "Solicitante", "Tipo", "Estado", "Prioridade", "Responsável", "Aging (dias)", "Score"]
    larguras = [10, 55, 22, 18, 16, 12, 22, 12, 10]
    wb, ws, linha_cab = _nova_planilha("Backlog", "Backlog de Demandas — GP Flow", colunas, larguras)

    linhas = [
        [
            int(row["id"]), row["titulo"], row.get("solicitante", ""),
            formatar_codigo(row.get("tipo")), row.get("estado", ""),
            formatar_codigo(row.get("prioridade")), row.get("responsavel_atendimento", ""),
            row.get("aging_dias", ""), row.get("score_exibicao", row.get("score", "")),
        ]
        for _, row in df.iterrows()
    ]
    _escrever_linhas(ws, linha_cab + 1, linhas)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def exportar_curadoria_excel(df: pd.DataFrame) -> bytes:
    colunas = ["Id", "Título", "Macroprocesso", "Sistema", "Score", "Observações",
               "Solicitante", "Responsável", "Data criação", "Aging (dias)"]
    larguras = [10, 50, 18, 18, 10, 40, 22, 22, 16, 12]
    wb, ws, linha_cab = _nova_planilha("Curadoria", "Curadoria — GP Flow", colunas, larguras)

    linhas = [
        [
            int(row["id"]), row["titulo"], row.get("macroprocesso", "") or "",
            row.get("sistema", "") or "", row.get("score", ""), row.get("observacoes", "") or "",
            row.get("solicitante", ""), row.get("responsavel_atendimento", ""),
            row.get("data_criacao", ""), row.get("aging_dias", ""),
        ]
        for _, row in df.iterrows()
    ]
    _escrever_linhas(ws, linha_cab + 1, linhas)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def exportar_sprint_excel(nome_sprint: str, df_demandas: pd.DataFrame, df_atividades: pd.DataFrame = None) -> bytes:
    colunas = ["Id", "Título", "Tipo de entrada", "Status", "Responsável", "Impedimento"]
    larguras = [10, 55, 16, 16, 20, 35]
    wb, ws, linha_cab = _nova_planilha("Sprint", nome_sprint, colunas, larguras)

    linhas = [
        [
            int(row["id"]), row["titulo"], row.get("tipo_entrada", ""),
            row.get("status_kanban", ""), row.get("responsavel_sprint", "") or "",
            row.get("impedimento", "") or "",
        ]
        for _, row in df_demandas.iterrows()
    ]
    if df_atividades is not None:
        linhas += [
            [
                "", row["titulo"], row.get("tipo_entrada", ""),
                row.get("status_kanban", ""), row.get("responsavel_sprint", "") or "",
                row.get("impedimento", "") or "",
            ]
            for _, row in df_atividades.iterrows()
        ]
    _escrever_linhas(ws, linha_cab + 1, linhas)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
