"""
Sprint — GP Flow v0.6.0

Painel da sprint ativa. Absorve o antigo Planning: quando não há sprint,
esta mesma tela cria uma. O envio de demandas do Backlog é feito na página
**Backlog** (seção "Enviar para a sprint"); aqui você gerencia o que já
está na sprint, adiciona atividades internas, acompanha métricas e encerra.

O tipo de entrada (Planejada/Paraquedas) é definido automaticamente pelo
botão ▶️ Iniciar sprint: antes de iniciar, tudo entra como Planejada;
depois, como Paraquedas.
"""
from datetime import date

import pandas as pd
import streamlit as st

from functions.banco import (
    criar_tabelas, sprint_ativa, sprint_em_andamento, criar_sprint, iniciar_sprint,
    encerrar_sprint, excluir_sprint, atualizar_meta_sprint, velocidade_media,
    listar_demandas_sprint, remover_demanda_da_sprint,
    atualizar_status_kanban, atualizar_tipo_entrada, atualizar_responsavel_sprint,
    atualizar_impedimento,
    adicionar_atividade_interna, listar_atividades_sprint,
    atualizar_atividade_interna, remover_atividade_interna,
    ESTADOS_KANBAN, TIPOS_ENTRADA,
)
from functions.util import formatar_codigo, limpar_texto
from functions.sprint import lista_apelidos
from functions.metricas import lead_time_medio_dias, taxa_conclusao, resumo_recorrencia
from functions.exportar import exportar_sprint_excel

st.set_page_config(page_title="Sprint — GP Flow", page_icon="▶️", layout="wide")
criar_tabelas()

st.title("Sprint")

if flash := st.session_state.pop("flash_sprint", None):
    st.success(flash)

sprint = sprint_ativa()

# ---------------------------------------------------------------------------
# SEM SPRINT: criar uma aqui mesmo (antes isso ficava no Planning)
# ---------------------------------------------------------------------------
if not sprint:
    st.info("Não existe nenhuma sprint ativa. Crie uma para começar.")
    with st.form("nova_sprint"):
        nome = st.text_input("Nome da sprint", placeholder="Sprint 12 — 06/07 a 17/07")
        meta = st.text_input("🎯 Meta da sprint (objetivo)", placeholder="Ex.: Estabilizar as integrações do módulo financeiro")
        c1, c2 = st.columns(2)
        inicio = c1.date_input("Início", format="DD/MM/YYYY")
        fim = c2.date_input("Fim", format="DD/MM/YYYY")
        vel = velocidade_media()
        if vel:
            st.caption(f"📈 Velocidade média das últimas sprints: ~**{vel}** demanda(s) concluída(s) por sprint. Use como referência de quantas puxar.")
        if st.form_submit_button("🚀 Criar sprint", type="primary"):
            if nome.strip():
                try:
                    criar_sprint(nome.strip(), str(inicio), str(fim), meta=meta.strip() or None)
                    st.session_state.flash_sprint = (
                        "Sprint criada em planejamento! Envie demandas pela página "
                        "**Backlog** e clique em ▶️ Iniciar quando estiver pronta."
                    )
                    st.rerun()
                except ValueError as erro:
                    st.error(str(erro))
            else:
                st.warning("Dê um nome para a sprint.")
    st.stop()

# ---------------------------------------------------------------------------
# CABEÇALHO PERMANENTE
# ---------------------------------------------------------------------------
demandas_sprint = listar_demandas_sprint(sprint["id"])
atividades = listar_atividades_sprint(sprint["id"])

dias_restantes = "—"
if sprint.get("data_fim"):
    try:
        fim = pd.to_datetime(sprint["data_fim"]).date()
        dias_restantes = (fim - date.today()).days
    except Exception:
        dias_restantes = "—"

qtd_total = len(demandas_sprint) + len(atividades)
qtd_planejadas = int((demandas_sprint["tipo_entrada"] == "Planejada").sum()) if not demandas_sprint.empty else 0
qtd_paraquedas = int((demandas_sprint["tipo_entrada"] == "Paraquedas").sum()) if not demandas_sprint.empty else 0
qtd_internas = int((demandas_sprint["tipo_entrada"] == "Interna").sum()) if not demandas_sprint.empty else 0

em_andamento = sprint_em_andamento(sprint)
estado_badge = "🏃 Em andamento" if em_andamento else "🗓️ Em planejamento"
c_titulo, c_iniciar = st.columns([3, 1])
c_titulo.markdown(f"## {sprint['nome']}  \n{estado_badge}")
with c_iniciar:
    if not em_andamento:
        if st.button("▶️ Iniciar sprint", type="primary"):
            iniciar_sprint(sprint["id"])
            st.session_state.flash_sprint = "Sprint iniciada! Demandas adicionadas a partir de agora entram como Paraquedas."
            st.rerun()

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Período", f"{sprint['data_inicio']} → {sprint['data_fim']}")
c2.metric("Dias restantes", dias_restantes)
c3.metric("Demandas", qtd_total)
c4.metric("Planejadas", qtd_planejadas)
c5.metric("Paraquedas", qtd_paraquedas)
c6.metric("Internas", qtd_internas)

# --- Meta da sprint (objetivo) ---
meta_atual = sprint.get("meta") or ""
with st.expander("🎯 Meta da sprint" + (f" — {meta_atual}" if meta_atual else " (não definida)"), expanded=not meta_atual):
    nova_meta = st.text_area(
        "Objetivo desta sprint",
        value=meta_atual,
        placeholder="Ex.: Estabilizar as integrações do módulo financeiro e zerar incidentes críticos.",
        help="Uma frase curta que resume o que o time quer alcançar — ajuda a focar e priorizar.",
    )
    if st.button("💾 Salvar meta"):
        atualizar_meta_sprint(sprint["id"], nova_meta.strip() or None)
        st.session_state.flash_sprint = "Meta da sprint atualizada."
        st.rerun()

# --- Alerta de capacidade (velocidade histórica vs. carga atual) ---
_vel = velocidade_media()
if _vel:
    qtd_demandas = len(demandas_sprint)
    if qtd_demandas > _vel * 1.2:
        st.warning(
            f"📈 Capacidade: esta sprint tem **{qtd_demandas}** demanda(s), acima da sua "
            f"velocidade média (~**{_vel}** concluída(s) por sprint). Risco de sobrecarga — "
            f"considere reduzir o escopo ou priorizar."
        )
    else:
        st.caption(f"📈 Velocidade média: ~{_vel} concluída(s)/sprint · esta sprint: {qtd_demandas} demanda(s).")

st.caption("➕ Para adicionar demandas do Backlog, use a seção **Enviar para a sprint** na página Backlog.")

st.divider()

# ---------------------------------------------------------------------------
# ATIVIDADES INTERNAS (adicionar)
# ---------------------------------------------------------------------------
with st.expander("🗓️ Adicionar atividade interna (cerimônia, feriado, reunião...)"):
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    titulo_interno = c1.text_input("Atividade", placeholder="Cerimônia Ágil — Sprint")
    resp_interno = c2.selectbox("Responsável", lista_apelidos() or [""])
    tipo_interno = c3.selectbox("Tipo", TIPOS_ENTRADA)
    if c4.button("➕ Adicionar", type="primary", disabled=not titulo_interno.strip()):
        adicionar_atividade_interna(sprint["id"], titulo_interno.strip(), resp_interno, 0, tipo_interno)
        st.session_state.flash_sprint = (
            f"✅ Atividade '{titulo_interno.strip()}' adicionada! Ela aparece na seção "
            "'Atividades internas' abaixo e no **Kanban** (coluna Sprint)."
        )
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# TABELA DA SPRINT
# ---------------------------------------------------------------------------
st.markdown("### 📋 Itens da sprint")

if demandas_sprint.empty and atividades.empty:
    st.info("Nenhum item na sprint ainda. Envie demandas pela página **Backlog** ou adicione uma atividade interna acima.")
else:
    if not demandas_sprint.empty:
        st.markdown("**Demandas**")
        df_dem = demandas_sprint.copy()
        df_dem["tipo_exibicao"] = df_dem["tipo"].apply(formatar_codigo)

        from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode
        from functions.aggrid_helper import AG_CSS, STATUS_KANBAN_STYLE, TIPO_ENTRADA_STYLE

        df_ag_dem = pd.DataFrame({
            "Id":           df_dem["id"].astype(int),
            "Título":       df_dem["titulo"],
            "Tipo":         df_dem["tipo_exibicao"],
            "Tipo entrada": df_dem["tipo_entrada"].fillna("Planejada"),
            "Responsável":  df_dem["responsavel_sprint"].fillna(""),
            "Status":       df_dem["status_kanban"].fillna("Sprint"),
            "Impedimento":  df_dem["impedimento"].apply(limpar_texto),
        })

        gb = GridOptionsBuilder.from_dataframe(df_ag_dem)
        gb.configure_default_column(resizable=True, sortable=True, editable=False)
        gb.configure_column("Id",          width=80,  editable=False)
        gb.configure_column("Título",      width=340, editable=False, tooltipField="Título")
        gb.configure_column("Tipo",        width=130, editable=False)
        gb.configure_column("Tipo entrada", width=110, editable=True,
                            cellStyle=TIPO_ENTRADA_STYLE,
                            cellEditor="agSelectCellEditor",
                            cellEditorParams={"values": TIPOS_ENTRADA})
        gb.configure_column("Responsável", width=110, editable=True,
                            cellEditor="agSelectCellEditor",
                            cellEditorParams={"values": lista_apelidos()})
        gb.configure_column("Status",      width=120, editable=True,
                            cellStyle=STATUS_KANBAN_STYLE,
                            cellEditor="agSelectCellEditor",
                            cellEditorParams={"values": ESTADOS_KANBAN})
        gb.configure_column("Impedimento", width=220, editable=True)
        gb.configure_selection(selection_mode="multiple", use_checkbox=True, header_checkbox=True)
        gb.configure_grid_options(rowHeight=36, headerHeight=38,
                                  stopEditingWhenCellsLoseFocus=True)

        res_dem = AgGrid(df_ag_dem, gridOptions=gb.build(), height=360,
                         update_mode=GridUpdateMode.MODEL_CHANGED,
                         data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                         allow_unsafe_jscode=True, theme="streamlit",
                         custom_css=AG_CSS, key="ag_sprint_demandas")

        col_salvar, col_excluir = st.columns(2)
        with col_salvar:
            if st.button("💾 Salvar alterações", type="primary", key="btn_salvar_dem"):
                if res_dem is not None and res_dem.data is not None:
                    try:
                        for _, row in res_dem.data.iterrows():
                            original = df_dem[df_dem["id"] == row["Id"]]
                            if original.empty: continue
                            orig = original.iloc[0]
                            if row["Tipo entrada"] != (orig["tipo_entrada"] or ""):
                                atualizar_tipo_entrada(int(row["Id"]), row["Tipo entrada"])
                            if row["Responsável"] != (orig["responsavel_sprint"] or ""):
                                atualizar_responsavel_sprint(int(row["Id"]), row["Responsável"])
                            if row["Status"] != (orig["status_kanban"] or ""):
                                atualizar_status_kanban(int(row["Id"]), row["Status"])
                            if row["Impedimento"] != limpar_texto(orig["impedimento"]):
                                atualizar_impedimento(int(row["Id"]), row["Impedimento"] or None)
                        st.session_state.flash_sprint = "Sprint salva!"
                        st.rerun()
                    except Exception:
                        st.error("Não foi possível salvar as alterações. Tente novamente.")
        with col_excluir:
            selecionadas = res_dem.selected_rows if res_dem else None
            ids_sel = []
            if selecionadas is not None and len(selecionadas) > 0:
                ids_sel = [int(r["Id"]) if isinstance(r, dict) else int(r["Id"]) for r in (selecionadas if isinstance(selecionadas, list) else selecionadas.to_dict("records"))]
            if st.button(f"🗑️ Remover marcadas da sprint ({len(ids_sel)})", disabled=not ids_sel, key="btn_excluir_dem"):
                for did in ids_sel:
                    remover_demanda_da_sprint(did)
                st.session_state.flash_sprint = f"{len(ids_sel)} demanda(s) removida(s) — voltaram para o Backlog."
                st.rerun()

    if not atividades.empty:
        st.markdown(f"**🗓️ Atividades internas ({len(atividades)})**")
        st.caption("Cerimônias, feriados, reuniões — sem Id do Trace. Marque e clique em Salvar para excluir.")
        df_ativ = atividades.copy()

        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
        from functions.aggrid_helper import AG_CSS, STATUS_KANBAN_STYLE, TIPO_ENTRADA_STYLE

        df_ag_ativ = pd.DataFrame({
            "Id":           df_ativ["id"].astype(int),
            "Atividade":    df_ativ["titulo"],
            "Tipo entrada": df_ativ["tipo_entrada"].fillna("Interna"),
            "Responsável":  df_ativ["responsavel_sprint"].fillna(""),
            "Status":       df_ativ["status_kanban"].fillna("Sprint"),
        })

        gb2 = GridOptionsBuilder.from_dataframe(df_ag_ativ)
        gb2.configure_default_column(resizable=True, sortable=True, editable=False)
        gb2.configure_column("Id",          width=70,  editable=False)
        gb2.configure_column("Atividade",   width=320, editable=True)
        gb2.configure_column("Tipo entrada", width=110, editable=True,
                             cellStyle=TIPO_ENTRADA_STYLE,
                             cellEditor="agSelectCellEditor",
                             cellEditorParams={"values": TIPOS_ENTRADA})
        gb2.configure_column("Responsável", width=110, editable=True,
                             cellEditor="agSelectCellEditor",
                             cellEditorParams={"values": lista_apelidos()})
        gb2.configure_column("Status",      width=120, editable=True,
                             cellStyle=STATUS_KANBAN_STYLE,
                             cellEditor="agSelectCellEditor",
                             cellEditorParams={"values": ESTADOS_KANBAN})
        gb2.configure_selection(selection_mode="multiple", use_checkbox=True, header_checkbox=True)
        gb2.configure_grid_options(rowHeight=36, headerHeight=38,
                                   stopEditingWhenCellsLoseFocus=True)

        res_ativ = AgGrid(df_ag_ativ, gridOptions=gb2.build(),
                          height=max(120, min(len(df_ativ)*44+60, 300)),
                          update_mode=GridUpdateMode.MODEL_CHANGED,
                          data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                          allow_unsafe_jscode=True, theme="streamlit",
                          custom_css=AG_CSS, key="ag_sprint_atividades")

        if st.button("💾 Salvar atividades", key="btn_salvar_ativ"):
            if res_ativ is not None and res_ativ.data is not None:
                for _, row in res_ativ.data.iterrows():
                    atualizar_atividade_interna(
                        int(row["Id"]), titulo=row["Atividade"],
                        tipo_entrada=row["Tipo entrada"],
                        responsavel_sprint=row["Responsável"],
                        status_kanban=row["Status"],
                    )
            selecionadas_a = res_ativ.selected_rows if res_ativ else None
            ids_rem = []
            if selecionadas_a is not None and len(selecionadas_a) > 0:
                ids_rem = [int(r["Id"]) if isinstance(r, dict) else int(r["Id"]) for r in (selecionadas_a if isinstance(selecionadas_a, list) else selecionadas_a.to_dict("records"))]
            for aid in ids_rem:
                remover_atividade_interna(aid)
            msg = "✅ Atividades salvas!"
            if ids_rem: msg += f" ({len(ids_rem)} removida(s))"
            st.session_state.flash_sprint = msg
            st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# MÉTRICAS
# ---------------------------------------------------------------------------
st.markdown("### 📊 Métricas da sprint")
recorrencia = resumo_recorrencia(sprint["id"])
conclusao = taxa_conclusao(sprint["id"])
lead_time = lead_time_medio_dias(sprint["id"])

m1, m2, m3 = st.columns(3)
m1.metric("🔁 Demandas recorrentes", f"{recorrencia['recorrentes']} de {recorrencia['total']}")
m2.metric("✅ Taxa de conclusão", f"{conclusao['percentual']:.0f}%", f"{conclusao['concluidos']} de {conclusao['total']}")
m3.metric("⏱️ Lead time médio", f"{lead_time} dias" if lead_time is not None else "—")

st.divider()

# ---------------------------------------------------------------------------
# EXPORTAR + ENCERRAR
# ---------------------------------------------------------------------------
col_exp, col_enc = st.columns(2)
with col_exp:
    st.download_button(
        "⬇️ Exportar sprint (Excel)",
        data=exportar_sprint_excel(
            sprint["nome"], demandas_sprint, atividades,
            data_inicio=sprint.get("data_inicio"),
            data_fim=sprint.get("data_fim"),
            responsaveis=lista_apelidos(),
        ),
        file_name=f"{sprint['nome'].replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

with col_enc:
    with st.popover("🏁 Encerrar sprint"):
        st.markdown("**Retrospectiva** — respostas rápidas antes de encerrar:")
        bem = st.text_area("O que funcionou bem?")
        dificultou = st.text_area("O que dificultou?")
        acoes = st.text_area("Quais ações serão levadas para a próxima sprint?")
        if st.button("Confirmar encerramento", type="primary"):
            try:
                resumo = encerrar_sprint(sprint["id"], bem, dificultou, acoes)
                st.session_state.flash_sprint = (
                    f"🏁 Sprint encerrada! Planejadas: {resumo['planejadas']} · "
                    f"Paraquedas: {resumo['paraquedas']} · Internas: {resumo.get('internas', 0)} · "
                    f"Concluídas: {resumo['concluidas']} · "
                    f"Pendentes: {resumo['pendentes']} (voltaram para o Backlog)."
                )
                st.rerun()
            except Exception:
                st.error("Não foi possível encerrar a sprint. Tente novamente.")

st.divider()
with st.expander("⚠️ Excluir esta sprint"):
    st.warning(
        "Isso apaga o **bloco da sprint** (nome, período, retrospectiva). "
        "As demandas **não são excluídas** — todas voltam para o Backlog com a "
        "curadoria intacta. Atividades internas desta sprint são removidas "
        "(elas não têm Id do Trace, não têm para onde voltar)."
    )
    confirmar_exclusao = st.checkbox("Sim, quero excluir esta sprint e devolver as demandas ao Backlog")
    if st.button("🗑️ Excluir sprint definitivamente", type="secondary", disabled=not confirmar_exclusao):
        try:
            excluir_sprint(sprint["id"])
            st.session_state.flash_sprint = "🗑️ Sprint excluída. As demandas voltaram para o Backlog."
            st.rerun()
        except Exception:
            st.error("Não foi possível excluir a sprint. Tente novamente.")
