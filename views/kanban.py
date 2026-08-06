"""
Kanban — GP Flow (CCv2 drag-and-drop)

Quadro Kanban com cartões clicáveis:
- Arrastar coluna muda o status (HTML5 drag-and-drop nativo)
- Clicar num cartão abre o modal de detalhes/edição
- Modo Daily (toggle) mostra tabela enxuta para a reunião diária
"""

import pandas as pd
import streamlit as st

from functions.banco import (
    criar_tabelas, sprint_ativa, listar_demandas_sprint, listar_atividades_sprint,
    atualizar_status_kanban, atualizar_atividade_interna,
    atualizar_responsavel_sprint, atualizar_impedimento,
    atualizar_card_kanban, adicionar_atividade_interna,
    remover_demanda_da_sprint,
    ESTADOS_KANBAN, TIPOS_ENTRADA,
)
from functions.sprint import lista_apelidos, apelido
from functions.util import limpar_texto

# ── Componente Kanban (CCv2) — drag-and-drop real via setTriggerValue ─────────
_KANBAN_HTML = '<div id="kb-root"></div>'

_KANBAN_CSS = """
.kb-board { display:flex; gap:10px; width:100%; align-items:stretch; }
.kb-col { flex:1 1 0; min-width:0; border-radius:8px; background:#f4f5f7;
          display:flex; flex-direction:column;
          overflow:hidden; border:2px solid transparent; transition:border-color .15s; }
.kb-col.kb-over { border-color:#4a90d9; background:#eef4fb; }
.kb-head { padding:9px 12px; color:#fff; font-size:11px; font-weight:700;
           letter-spacing:.05em; text-transform:uppercase; }
.kb-body { padding:8px; min-height:400px; flex:1 1 auto; }
.kb-card { background:#fff; border-radius:6px; padding:9px 11px; margin-bottom:6px;
           cursor:grab; box-shadow:0 1px 2px rgba(0,0,0,.08), 0 0 0 1px rgba(0,0,0,.06);
           border-left:3px solid #4a90d9; font-size:12px; line-height:1.45; color:#172b4d;
           user-select:none; transition:box-shadow .12s, transform .1s; }
.kb-card:hover { box-shadow:0 4px 10px rgba(0,0,0,.14); background:#f8f9fa; }
.kb-card:active { cursor:grabbing; }
.kb-card.kb-drag { opacity:.4; }
.kb-id { font-size:10px; color:#6c757d; margin-bottom:2px; }
.kb-title { font-weight:600; font-size:12px; margin-bottom:5px; line-height:1.35; }
.kb-meta { font-size:11px; color:#495057; display:flex; flex-wrap:wrap; gap:6px; align-items:center; }
.kb-badge { display:inline-block; border-radius:3px; padding:1px 6px; font-size:10px; font-weight:600; }
.kb-plan { background:#d0ebff; color:#1864ab; }
.kb-para { background:#ffe8cc; color:#d9480f; }
.kb-int  { background:#f1f3f5; color:#495057; }
.kb-imp  { background:#ffecec; color:#c92a2a; }
.kb-empty { padding:16px 8px; text-align:center; color:#adb5bd; font-size:11px; }
"""

_KANBAN_JS = """
export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const root = parentElement.querySelector("#kb-root");
  if (!root) return;

  const colunas = (data && data.colunas) || [];
  const cores = (data && data.cores) || ["#0052CC", "#FF991F", "#DE350B", "#6554C0", "#00875A"];
  let dragId = null, dragType = null;

  function badge(t) {
    if (!t) return "";
    const cls = t === "Planejada" ? "kb-plan" : t === "Paraquedas" ? "kb-para" : "kb-int";
    return '<span class="kb-badge ' + cls + '">' + t + '</span>';
  }
  function cardHTML(item) {
    const imp = item.impedimento ? '<span class="kb-badge kb-imp">\\u26A0 Imp.</span>' : "";
    const horas = item.horas > 0 ? '<span>\\u23F1 ' + item.horas.toFixed(1) + 'h</span>' : "";
    const resp = item.responsavel ? '<span>\\u{1F464} ' + item.responsavel + '</span>' : "";
    const score = item.score ? '<span>\\u2B50 ' + item.score + '</span>' : "";
    return '<div class="kb-card" draggable="true" data-id="' + item.id + '" data-tipo="' + item.tipo + '">'
      + '<div class="kb-id">' + item.tipo + item.id + '</div>'
      + '<div class="kb-title">' + item.titulo + '</div>'
      + '<div class="kb-meta">' + resp + badge(item.entrada) + imp + horas + score + '</div>'
      + '</div>';
  }
  function render() {
    let html = '<div class="kb-board">';
    colunas.forEach(function (col, i) {
      const cards = col.items.map(cardHTML).join("") || '<div class="kb-empty">Sem itens</div>';
      html += '<div class="kb-col" data-estado="' + col.estado + '">'
        + '<div class="kb-head" style="background:' + cores[i % cores.length] + '">'
        + col.estado.toUpperCase() + ' (' + col.items.length + ')</div>'
        + '<div class="kb-body">' + cards + '</div></div>';
    });
    html += '</div>';
    root.innerHTML = html;
    wire();
  }
  function wire() {
    root.querySelectorAll(".kb-card").forEach(function (card) {
      const id = card.getAttribute("data-id");
      const tipo = card.getAttribute("data-tipo");
      card.addEventListener("dragstart", function (e) {
        dragId = id; dragType = tipo;
        card.classList.add("kb-drag");
        e.dataTransfer.effectAllowed = "move";
      });
      card.addEventListener("dragend", function () { card.classList.remove("kb-drag"); });
      card.addEventListener("click", function () {
        setTriggerValue("evt", { action: "open", tipo: tipo, id: Number(id), ts: Date.now() });
      });
    });
    root.querySelectorAll(".kb-col").forEach(function (col) {
      const estado = col.getAttribute("data-estado");
      col.addEventListener("dragover", function (e) { e.preventDefault(); col.classList.add("kb-over"); });
      col.addEventListener("dragleave", function () { col.classList.remove("kb-over"); });
      col.addEventListener("drop", function (e) {
        e.preventDefault(); col.classList.remove("kb-over");
        if (dragId === null) return;
        setTriggerValue("evt", { action: "move", tipo: dragType, id: Number(dragId), estado: estado, ts: Date.now() });
        dragId = null; dragType = null;
      });
    });
  }
  render();
}
"""

_KANBAN_COMPONENT = st.components.v2.component(
    "gpflow_kanban_board",
    html=_KANBAN_HTML,
    css=_KANBAN_CSS,
    js=_KANBAN_JS,
)

st.set_page_config(page_title="Kanban — GP Flow", page_icon="📊", layout="wide")
criar_tabelas()

st.title("Kanban")

if flash := st.session_state.pop("flash_kanban", None):
    st.success(flash)

sprint = sprint_ativa()
if not sprint:
    st.info("Não existe nenhuma sprint em andamento.")
    st.stop()

demandas = listar_demandas_sprint(sprint["id"])
atividades = listar_atividades_sprint(sprint["id"])

# ── Modo Daily ────────────────────────────────────────────────────────────────
modo_daily = st.toggle(
    "⏱️ Modo Daily",
    value=False,
    help="Tabela enxuta para a reunião diária.",
)

# ── Nova atividade interna ────────────────────────────────────────────────────
with st.popover("➕ Nova atividade interna"):
    st.caption("Cria uma atividade interna (cerimônia, feriado, reunião…) já na sprint ativa.")
    titulo_interno = st.text_input("Título", placeholder="Cerimônia Ágil, Feriado…", key="kan_titulo_interno")
    ki1, ki2 = st.columns(2)
    resp_interno = ki1.selectbox("Responsável", [""] + lista_apelidos(), key="kan_resp_interno")
    tipo_interno = ki2.selectbox("Tipo", TIPOS_ENTRADA,
                                  index=TIPOS_ENTRADA.index("Interna") if "Interna" in TIPOS_ENTRADA else 0,
                                  key="kan_tipo_interno")
    if st.button("➕ Criar", type="primary", disabled=not titulo_interno.strip(), key="kan_criar_interno"):
        adicionar_atividade_interna(sprint["id"], titulo_interno.strip(), resp_interno, 0, tipo_interno)
        st.session_state.flash_kanban = f"Atividade '{titulo_interno.strip()}' criada."
        st.rerun()

# ── Modal de detalhes do card ─────────────────────────────────────────────────
@st.dialog("📋 Detalhes da demanda", width="large")
def abrir_card_kanban(demanda_id: int):
    row = demandas[demandas["id"] == demanda_id]
    if row.empty:
        st.error("Demanda não encontrada.")
        return
    d = row.iloc[0]

    st.markdown(f"### D{demanda_id} · {d['titulo']}")
    col_meta = st.columns(4)
    col_meta[0].markdown(f"**Estado (Trace)**\n\n{d.get('estado') or '—'}")
    col_meta[1].markdown(f"**Prioridade**\n\n{d.get('prioridade') or '—'}")
    col_meta[2].markdown(f"**Macroprocesso**\n\n{d.get('macroprocesso') or '—'}")
    col_meta[3].markdown(f"**Sistema**\n\n{d.get('sistema') or '—'}")
    st.divider()

    c1, c2 = st.columns(2)
    apelidos = lista_apelidos()
    resp_atual = str(d.get("responsavel_sprint") or "")
    resp_opts = [""] + apelidos
    resp_idx = resp_opts.index(resp_atual) if resp_atual in resp_opts else 0
    novo_resp = c1.selectbox("👤 Responsável", resp_opts, index=resp_idx, key=f"kcard_resp_{demanda_id}")

    status_val = str(d.get("status_kanban") or ESTADOS_KANBAN[0])
    status_idx = ESTADOS_KANBAN.index(status_val) if status_val in ESTADOS_KANBAN else 0
    novo_status = c2.selectbox("📍 Status", ESTADOS_KANBAN, index=status_idx, key=f"kcard_status_{demanda_id}")

    c3, c4 = st.columns(2)
    tipo_val = str(d.get("tipo_entrada") or "Planejada")
    tipo_idx = TIPOS_ENTRADA.index(tipo_val) if tipo_val in TIPOS_ENTRADA else 0
    novo_tipo = c3.selectbox("📋 Tipo de entrada", TIPOS_ENTRADA, index=tipo_idx, key=f"kcard_tipo_{demanda_id}")

    horas_val = float(d.get("horas_trabalhadas") or 0)
    novas_horas = c4.number_input("⏱️ Horas trabalhadas", min_value=0.0, value=horas_val,
                                   step=0.5, format="%.1f", key=f"kcard_horas_{demanda_id}")

    imp_val = d.get("impedimento")
    imp_texto = "" if not tem_impedimento(imp_val) else str(imp_val)
    novo_impedimento = st.text_input("🚧 Impedimento", value=imp_texto,
                                      key=f"kcard_imp_{demanda_id}")
    nova_obs = st.text_area("📝 Observações", value=limpar_texto(d.get("observacoes")),
                             height=90, key=f"kcard_obs_{demanda_id}")
    nova_desc = st.text_area("📄 Descrição interna (notas da equipe)",
                              value=limpar_texto(d.get("descricao_interna")),
                              height=90, key=f"kcard_desc_{demanda_id}")

    st.divider()
    info = []
    if d.get("solicitante"):              info.append(f"**Solicitante:** {d['solicitante']}")
    if d.get("responsavel_atendimento"):  info.append(f"**Resp. atendimento:** {d['responsavel_atendimento']}")
    if d.get("data_criacao"):             info.append(f"**Criado em:** {str(d['data_criacao'])[:10]}")
    if d.get("score"):                    info.append(f"**Score:** {float(d['score']):.1f}")
    if info: st.caption("  ·  ".join(info))

    b1, b2 = st.columns(2)
    if b1.button("💾 Salvar", type="primary", key=f"kcard_salvar_{demanda_id}"):
        atualizar_card_kanban(
            demanda_id,
            responsavel_sprint=novo_resp or None,
            status_kanban=novo_status,
            tipo_entrada=novo_tipo,
            impedimento=novo_impedimento.strip(),
            observacoes=nova_obs.strip(),
            horas_trabalhadas=novas_horas,
            descricao_interna=nova_desc.strip(),
        )
        st.session_state["flash_kanban"] = f"Card D{demanda_id} atualizado."
        st.rerun()
    if b2.button("✖️ Fechar", key=f"kcard_fechar_{demanda_id}"):
        st.rerun()

    st.divider()
    st.caption("Tirar da sprint devolve a demanda ao Backlog (não exclui).")
    confirmar = st.checkbox("Confirmo devolver ao Backlog", key=f"kcard_conf_rem_{demanda_id}")
    if st.button("↩️ Voltar ao Backlog", disabled=not confirmar,
                 key=f"kcard_remover_{demanda_id}"):
        remover_demanda_da_sprint(demanda_id)
        st.session_state["flash_kanban"] = f"Demanda D{demanda_id} voltou para o Backlog."
        st.rerun()


if modo_daily:
    # ── MODO DAILY ────────────────────────────────────────────────────────────
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode
    from functions.aggrid_helper import AG_CSS, STATUS_KANBAN_STYLE, TIPO_ENTRADA_STYLE

    st.caption(f"Sprint: **{sprint['nome']}** — Daily de hoje")
    todos = []
    for _, d in demandas.iterrows():
        todos.append({"Id": int(d["id"]), "Título": d["titulo"],
                      "Responsável": apelido(d.get("responsavel_sprint") or ""),
                      "Status": d.get("status_kanban") or "Sprint",
                      "Impedimento": limpar_texto(d.get("impedimento"))})
    for _, a in atividades.iterrows():
        todos.append({"Id": int(a["id"]), "Título": a["titulo"],
                      "Responsável": apelido(a.get("responsavel_sprint") or ""),
                      "Status": a.get("status_kanban") or "Sprint",
                      "Impedimento": limpar_texto(a.get("impedimento"))})

    df_daily = pd.DataFrame(todos)
    gb = GridOptionsBuilder.from_dataframe(df_daily)
    gb.configure_default_column(resizable=True, sortable=True, editable=False)
    gb.configure_column("Id", width=70)
    gb.configure_column("Título", width=380)
    gb.configure_column("Responsável", width=100)
    gb.configure_column("Status", width=130, cellStyle=STATUS_KANBAN_STYLE)
    gb.configure_column("Impedimento", width=250, editable=True)
    gb.configure_grid_options(rowHeight=36, headerHeight=38)
    AgGrid(df_daily, gridOptions=gb.build(), height=400,
           update_mode=GridUpdateMode.NO_UPDATE,
           allow_unsafe_jscode=True, theme="streamlit", custom_css=AG_CSS, key="ag_daily")
    st.stop()


# ── MODO QUADRO ───────────────────────────────────────────────────────────────
st.caption(f"Sprint: **{sprint['nome']}** — clique num cartão para ver detalhes, arraste para mudar o status")

# filtros
TEAM = ["Cadu", "Davi", "Gi", "Vivi"]
c1, c2 = st.columns([2, 1])
filtro_resp = c1.multiselect("Filtrar por responsável", TEAM, default=[], key="kanban_filtro_resp")
filtro_tipo = c2.multiselect("Filtrar por tipo", TIPOS_ENTRADA, default=[], key="kanban_filtro_tipo")

def status_atual(valor):
    return valor if valor in ESTADOS_KANBAN else ESTADOS_KANBAN[0]

def tem_impedimento(valor):
    """True só quando há impedimento real (ignora None, vazio e resíduo 'nan')."""
    return limpar_texto(valor) != ""

def passa_filtro(responsavel, tipo_entrada):
    if filtro_resp and apelido(responsavel or "") not in filtro_resp: return False
    if filtro_tipo and (tipo_entrada or "") not in filtro_tipo: return False
    return True

# monta dados para o componente
colunas = []
for estado in ESTADOS_KANBAN:
    items = []
    for _, d in demandas.iterrows():
        if status_atual(d["status_kanban"]) != estado: continue
        if not passa_filtro(d["responsavel_sprint"], d["tipo_entrada"]): continue
        titulo = str(d["titulo"])
        titulo_curto = (titulo[:52] + "…") if len(titulo) > 53 else titulo
        items.append({
            "id":          int(d["id"]),
            "tipo":        "D",
            "titulo":      titulo_curto,
            "responsavel": apelido(d.get("responsavel_sprint") or ""),
            "entrada":     str(d.get("tipo_entrada") or ""),
            "impedimento": tem_impedimento(d.get("impedimento")),
            "horas":       float(d.get("horas_trabalhadas") or 0),
            "score":       f"{float(d['score']):.1f}" if pd.notna(d.get("score")) and d.get("score") else "",
        })
    for _, a in atividades.iterrows():
        if status_atual(a["status_kanban"]) != estado: continue
        if not passa_filtro(a["responsavel_sprint"], a["tipo_entrada"]): continue
        titulo = str(a["titulo"])
        titulo_curto = (titulo[:52] + "…") if len(titulo) > 53 else titulo
        items.append({
            "id":          int(a["id"]),
            "tipo":        "A",
            "titulo":      titulo_curto,
            "responsavel": apelido(a.get("responsavel_sprint") or ""),
            "entrada":     str(a.get("tipo_entrada") or ""),
            "impedimento": tem_impedimento(a.get("impedimento")),
            "horas":       0,
            "score":       "",
        })
    colunas.append({"estado": estado, "items": items})

# ── renderiza o quadro (CCv2: drag-and-drop real) ─────────────────────────────
CORES = ["#0052CC", "#FF991F", "#DE350B", "#6554C0", "#00875A"]
_KB_KEY = f"kb_board_{sprint['id']}"

result = _KANBAN_COMPONENT(
    key=_KB_KEY,
    data={"colunas": colunas, "cores": CORES},
    on_evt_change=lambda: None,  # garante que result.evt exista
)

evt = getattr(result, "evt", None)

if st.query_params.get("kbdebug"):
    st.info(f"DEBUG evt = {evt!r}")

_ultimo = st.session_state.get("_kb_ultimo_evt")
if evt and evt.get("ts") != _ultimo:
    st.session_state["_kb_ultimo_evt"] = evt.get("ts")
    action = evt.get("action")
    tipo = evt.get("tipo")
    item_id = evt.get("id")

    if item_id is not None and action == "move":
        novo_est = evt.get("estado")
        if novo_est in ESTADOS_KANBAN:
            if tipo == "D":
                atualizar_status_kanban(int(item_id), novo_est)
            else:
                atualizar_atividade_interna(int(item_id), status_kanban=novo_est)
            st.session_state["flash_kanban"] = "Status atualizado!"
            st.rerun()

    elif item_id is not None and action == "open" and tipo == "D":
        abrir_card_kanban(int(item_id))
