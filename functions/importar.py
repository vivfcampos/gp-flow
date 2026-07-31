"""
Importação do export do Trace (Excel) para o banco do GP Flow.

O Trace exporta um .xls com uma linha de título ("Demandas") acima do
cabeçalho real, e nem todas as colunas do score existem lá. Este módulo:
  - detecta automaticamente a linha de cabeçalho (procura por 'Id'/'Título');
  - mapeia as colunas por nome normalizado (tolerante a acento/caixa);
  - exige só o essencial (Id + Título); o resto é opcional;
  - aproveita o máximo do que o Trace já traz preenchido (Responsável,
    Estado, Prioridade, aging pronto), para reduzir preenchimento manual.
"""
import re
import unicodedata
import pandas as pd


# Nome de coluna esperado (normalizado) -> nome interno usado no banco.
# Só 'id' e 'titulo' são obrigatórios; os demais entram se existirem.
MAPA_COLUNAS = {
    "id": "id",
    "titulo": "titulo",
    "solicitante": "solicitante",
    "tipo": "tipo",
    "estado": "estado",
    "destino": "destino",
    "prioridade": "prioridade",
    "prioridade de atendimento": "prioridade_atendimento",
    "responsavel atendimento": "responsavel_atendimento",
    "data hora de criacao": "data_criacao",
    "tempo da demanda dias": "aging_trace",       # aging já calculado pelo Trace
    "urgencia importancia": "urgencia_importancia",  # normalmente NÃO existe no Trace
}

OBRIGATORIAS = {"id", "titulo"}


def _normalizar(texto: str) -> str:
    """Remove acentos, baixa a caixa e troca pontuação por espaço."""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-z0-9]+", " ", texto).strip()
    return texto


def _achar_linha_cabecalho(caminho_ou_arquivo) -> int:
    """
    Descobre em qual linha está o cabeçalho real. O Trace põe 'Demandas'
    numa linha antes do cabeçalho ('Id', 'Título', ...). Procura, nas
    primeiras linhas, aquela que contém 'id' e 'titulo'.
    """
    previa = pd.read_excel(caminho_ou_arquivo, header=None, nrows=10, dtype=str)
    for i in range(len(previa)):
        valores = {_normalizar(v) for v in previa.iloc[i].tolist() if pd.notna(v)}
        if "id" in valores and "titulo" in valores:
            return i
    return 0  # se não achar, assume a primeira linha


def ler_excel_trace(caminho_ou_arquivo) -> pd.DataFrame:
    """
    Lê o export do Trace e devolve um DataFrame com as colunas padronizadas,
    prontas para o banco. Aceita caminho ou objeto de upload do Streamlit.
    """
    linha_cab = _achar_linha_cabecalho(caminho_ou_arquivo)
    df_bruto = pd.read_excel(caminho_ou_arquivo, header=linha_cab, dtype=str)

    # mapeia colunas do arquivo -> nomes internos, por nome normalizado
    colunas_encontradas = {}
    for coluna_original in df_bruto.columns:
        chave = _normalizar(coluna_original)
        if chave in MAPA_COLUNAS and MAPA_COLUNAS[chave] not in colunas_encontradas.values():
            colunas_encontradas[coluna_original] = MAPA_COLUNAS[chave]

    internos = set(colunas_encontradas.values())
    faltando_obrig = OBRIGATORIAS - internos
    if faltando_obrig:
        raise ValueError(
            "O arquivo não parece um export válido do Trace. "
            f"Faltam colunas essenciais: {', '.join(sorted(faltando_obrig))}. "
            f"Colunas recebidas: {', '.join(map(str, df_bruto.columns))}"
        )

    df = df_bruto.rename(columns=colunas_encontradas)[list(internos)].copy()

    # garante que todas as colunas internas conhecidas existam (as ausentes viram vazias)
    for interno in set(MAPA_COLUNAS.values()):
        if interno not in df.columns:
            df[interno] = pd.NA

    # linhas sem Id não são demandas (linhas em branco / totais) -> descarta
    df = df[df["id"].notna() & (df["id"].astype(str).str.strip() != "")]
    df["id"] = df["id"].astype(str).str.extract(r"(\d+)")[0]
    df = df[df["id"].notna()]
    df["id"] = df["id"].astype(int)

    # data de criação -> ISO
    df["data_criacao"] = pd.to_datetime(
        df["data_criacao"], dayfirst=True, errors="coerce"
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    # urgência/importância: opcional. Se não veio, fica nulo (o score se ajusta).
    df["urgencia_importancia"] = pd.to_numeric(
        df["urgencia_importancia"], errors="coerce"
    ).astype("Int64")

    # aging pronto do Trace (Tempo da Demanda em dias) -> inteiro, se existir
    df["aging_trace"] = pd.to_numeric(df["aging_trace"], errors="coerce").astype("Int64")

    # prioridade de atendimento: se a principal vier vazia, usa a de atendimento
    for col in ["titulo", "solicitante", "tipo", "estado", "destino", "prioridade",
                "prioridade_atendimento", "responsavel_atendimento"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    sem_prioridade = df["prioridade"] == ""
    df.loc[sem_prioridade, "prioridade"] = df.loc[sem_prioridade, "prioridade_atendimento"]

    df = df.drop_duplicates(subset="id", keep="last").reset_index(drop=True)
    return df
