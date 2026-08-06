"""
Backlog — GP Flow v0.7.1

Tela inicial e central do GP Flow, organizada em abas para reduzir rolagem
e troca de página:

  📥 Importar     — sobe o export do Trace e limpa o backlog
  🏷️ Classificar  — lista e cura as demandas (macroprocesso, sistema, score…)
  🏃 Planejar     — envia demandas à sprint ativa ou cria uma sprint nova

Os dados são carregados uma vez no topo; cada aba usa o que precisa.
"""
from datetime import date

import pandas as pd
import streamlit as st



from functions.banco import (
    criar_tabelas, upsert_demandas, listar_backlog, registrar_importacao,
    ultima_importacao, contar_backlog, limpar_backlog, excluir_demandas,
    atualizar_curadoria, concluir_demanda, criar_sprint,
    sprint_ativa, sprint_em_andamento, adicionar_demanda_a_sprint,
    adicionar_atividade_interna, TIPOS_ENTRADA,
)
from functions.importar import ler_excel_trace
from functions.util import calcular_aging, formatar_codigo, busca_por_ids, limpar_texto
from functions.curadoria import (
    calcular_scores_dataframe, carregar_macroprocessos, adicionar_macroprocesso,
    carregar_sistemas, adicionar_sistema, legenda_urgencia_importancia,
)
from functions.sprint import apelido, lista_apelidos
from functions.exportar import exportar_backlog_excel

st.set_page_config(page_title="Backlog — GP Flow", page_icon="📥", layout="wide")
criar_tabelas()

st.title("Backlog")

if flash := st.session_state.pop("flash_backlog", None):
    st.success(flash)

# ===========================================================================
# DADOS (carregados uma vez, usados nas abas Classificar e Planejar)
# ===========================================================================
df = listar_backlog()
tem_demandas = not df.empty
if tem_demandas:
    df = calcular_aging(df)
    df["score_sugerido_calc"] = calcular_scores_dataframe(df)
    df["score_exibicao"] = df["score"].fillna(df["score_sugerido_calc"]).round(1)
    df["prioridade_exibicao"] = df["prioridade"].apply(formatar_codigo)
    df["macroprocesso"] = df["macroprocesso"].fillna("")
    df["sistema"] = df["sistema"].fillna("")
    df = df.sort_values(
        ["score_sugerido_calc", "id"], ascending=[False, True]
    ).reset_index(drop=True)

qtd_backlog = contar_backlog()
sprint = sprint_ativa()

@st.dialog("🔍 Detalhes da demanda", width="large")
def abrir_detalhes(linha, opcoes_macro, opcoes_sist):
    demanda_id = int(linha["id"])
    st.markdown(f"**{demanda_id} — {linha['titulo']}**")

    d1, d2 = st.columns(2)
    d1.markdown(f"**Solicitante (quem abriu):** {linha.get('solicitante') or '—'}")
    d2.markdown(f"**Responsável pelo atendimento:** {linha.get('responsavel_atendimento') or '—'}")
    d3, d4 = st.columns(2)
    aging_txt = f"{int(linha['aging_dias'])} dias" if pd.notna(linha.get("aging_dias")) else "—"
    data_criacao = str(linha.get("data_criacao"))[:10] if linha.get("data_criacao") else "—"
    d3.markdown(f"**Data de criação:** {data_criacao}")
    d4.markdown(f"**Aging:** {aging_txt}")

    extras = []
    for campo, rotulo in [("prioridade", "Prioridade"), ("tipo", "Tipo"),
                          ("estado", "Estado (Trace)"), ("urgencia_importancia", "Urg./Imp.")]:
        valor = linha.get(campo)
        if valor is not None and str(valor).strip() and str(valor).lower() != "nan":
            mostrar = formatar_codigo(valor) if campo in ("prioridade", "tipo") else valor
            extras.append(f"**{rotulo}:** {mostrar}")
    if extras:
        st.caption("  ·  ".join(extras))

    st.divider()
    st.markdown("**Classificação** (altere e salve):")

    # valores atuais
    macro_atual = str(linha.get("macroprocesso") or "")
    sist_atual = str(linha.get("sistema") or "")
    try:
        score_atual = float(linha.get("score")) if pd.notna(linha.get("score")) else float(linha.get("score_sugerido_calc", 0))
    except (TypeError, ValueError):
        score_atual = 0.0

    # listas com o valor atual garantido dentro das opções
    lista_macro = [""] + sorted(set(opcoes_macro) | ({macro_atual} if macro_atual else set()) - {""})
    lista_sist = [""] + sorted(set(opcoes_sist) | ({sist_atual} if sist_atual else set()) | {"TOTVS"} - {""})
    sist_default = sist_atual if sist_atual else ("TOTVS" if "TOTVS" in lista_sist else "")

    cc1, cc2 = st.columns(2)
    novo_macro = cc1.selectbox("Macroprocesso", lista_macro,
                               index=lista_macro.index(macro_atual) if macro_atual in lista_macro else 0,
                               key=f"det_macro_{demanda_id}")
    novo_sist = cc2.selectbox("Sistema", lista_sist,
                              index=lista_sist.index(sist_default) if sist_default in lista_sist else 0,
                              key=f"det_sist_{demanda_id}")
    novo_score = st.slider("Score", min_value=0.0, max_value=10.0, value=round(score_atual, 1),
                           step=0.5, key=f"det_score_{demanda_id}")
    nova_obs = st.text_area("Observações", value=limpar_texto(linha.get("observacoes")),
                            key=f"det_obs_{demanda_id}")

    b1, b2 = st.columns(2)
    if b1.button("💾 Salvar classificação", type="primary", key=f"det_salvar_{demanda_id}"):
        macro_cell = (novo_macro or "").strip()
        sist_cell = (novo_sist or "").strip()
        try:
            if macro_cell and macro_cell not in carregar_macroprocessos():
                adicionar_macroprocesso(macro_cell)
            if sist_cell and sist_cell not in carregar_sistemas():
                adicionar_sistema(sist_cell)
            atualizar_curadoria(
                demanda_id=demanda_id,
                macroprocesso=macro_cell or None,
                sistema=sist_cell or None,
                score_final=float(novo_score),
                score_sugerido=float(linha.get("score_sugerido_calc", novo_score)),
                observacoes=(nova_obs or "").strip() or None,
            )
            st.session_state["flash_backlog"] = f"Demanda {demanda_id} classificada e salva."
        except Exception:
            st.session_state["flash_backlog"] = f"Não foi possível salvar a demanda {demanda_id}."
        st.rerun()

    if b2.button("✖️ Fechar", key=f"det_fechar_{demanda_id}"):
        st.rerun()

    # ── Atalho: enviar para sprint ──────────────────────────────────────────
    sprint_det = sprint_ativa()
    if sprint_det:
        st.divider()
        em_and = sprint_em_andamento(sprint_det)
        tipo_ent = "Paraquedas" if em_and else "Planejada"
        st.markdown(f"**Sprint ativa:** {sprint_det['nome']} — envio como **{tipo_ent}**")
        resp_atalho = st.selectbox(
            "Responsável", [""] + lista_apelidos(), key=f"det_resp_{demanda_id}"
        )
        if st.button(
            f"🚀 Enviar para {sprint_det['nome']}",
            type="primary", key=f"det_enviar_{demanda_id}"
        ):
            try:
                adicionar_demanda_a_sprint(
                    demanda_id=demanda_id,
                    sprint_id=sprint_det["id"],
                    tipo_entrada=tipo_ent,
                    responsavel_sprint=resp_atalho or None,
                )
                st.session_state["flash_backlog"] = (
                    f"✅ Demanda {demanda_id} enviada para {sprint_det['nome']}."
                )
            except Exception as e:
                st.session_state["flash_backlog"] = f"Erro ao enviar: {e}"
            st.rerun()
    else:
        st.divider()
        st.caption("Não há sprint ativa. Crie uma na aba **🏃 Planejar sprint**.")



ABAS = ["📥 Importar", "🏷️ Classificar", "🏃 Planejar sprint"]

aba_ativa = st.segmented_control(
    "Seção", ABAS,
    key="aba_backlog",
    default=ABAS[1],  # abre em Classificar; Streamlit 1.60 usa default, não session_state
    label_visibility="collapsed",
)
# se desmarcar, volta para Classificar (lê do session_state do widget diretamente)
if aba_ativa is None:
    aba_ativa = ABAS[1]

# ===========================================================================
# ABA 1 — IMPORTAR
# ===========================================================================
if aba_ativa == ABAS[0]:
    if "versao_uploader_trace" not in st.session_state:
        st.session_state.versao_uploader_trace = 0

    st.markdown("#### Importar export do Trace GP")
    arquivo = st.file_uploader(
        "Selecione o arquivo exportado do Trace (.xlsx ou .xls)",
        type=["xlsx", "xls"],
        key=f"trace_uploader_{st.session_state.versao_uploader_trace}",
    )

    if arquivo is not None:
        try:
            df_importado = ler_excel_trace(arquivo)
            st.success(f"Arquivo lido: {len(df_importado)} demandas encontradas.")

            # preview das primeiras 5 linhas com AgGrid
            from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
            from functions.aggrid_helper import AG_CSS
            df_prev = df_importado.head(5)[["id","titulo","prioridade","estado","responsavel_atendimento"]].copy()
            df_prev.columns = ["Id","Título","Prioridade","Estado","Responsável"]
            gb_prev = GridOptionsBuilder.from_dataframe(df_prev)
            gb_prev.configure_default_column(resizable=True, sortable=False, editable=False)
            gb_prev.configure_column("Id",     width=80)
            gb_prev.configure_column("Título", width=320)
            gb_prev.configure_grid_options(rowHeight=36, headerHeight=38)
            AgGrid(df_prev, gridOptions=gb_prev.build(), height=260,
                   update_mode=GridUpdateMode.NO_UPDATE,
                   data_return_mode=DataReturnMode.AS_INPUT,
                   theme="streamlit", custom_css=AG_CSS, key="ag_import_preview")

            c1, c2 = st.columns([1, 1])
            confirmar = c1.button("✅ Confirmar importação", type="primary")
            if c2.button("🧹 Limpar arquivo selecionado"):
                st.session_state.versao_uploader_trace += 1
                st.rerun()

            if confirmar:
                try:
                    novas, atualizadas, ignoradas = upsert_demandas(df_importado)
                    registrar_importacao(arquivo.name, len(df_importado), novas, atualizadas, ignoradas)
                    st.session_state.versao_uploader_trace += 1
                    st.session_state.resumo_importacao = {
                        "total": len(df_importado), "novas": novas,
                        "atualizadas": atualizadas, "ignoradas": ignoradas,
                    }
                    st.rerun()
                except Exception:
                    st.error("Não foi possível concluir a importação. Verifique o arquivo e tente novamente.")

        except ValueError as erro:
            st.error(str(erro))
        except Exception:
            st.error("Não foi possível ler esse arquivo. Confira se é o export correto do Trace GP.")

    if resumo := st.session_state.pop("resumo_importacao", None):
        st.success(
            f"**Importação concluída**\n\n"
            f"Total no arquivo: {resumo['total']}  \n"
            f"Demandas novas: {resumo['novas']}  \n"
            f"Demandas atualizadas: {resumo['atualizadas']}  \n"
            f"Demandas ignoradas (sem mudança): {resumo['ignoradas']}\n\n"
            f"Nenhum dado de curadoria ou sprint foi alterado — a importação só sincroniza "
            f"os campos que vêm do Trace."
        )

    if ultima := ultima_importacao():
        st.caption(
            f"📥 Última importação: **{ultima['arquivo']}** em {ultima['data_hora']} — "
            f"{ultima['novas']} novas, {ultima['atualizadas']} atualizadas, "
            f"{ultima.get('ignoradas', 0)} ignoradas."
        )

    st.divider()

    # exportar + limpar backlog
    c_exp, _ = st.columns([1, 2])
    with c_exp:
        if tem_demandas:
            st.download_button(
                "⬇️ Exportar Backlog (Excel)",
                data=exportar_backlog_excel(df),
                file_name="backlog_gpflow.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    if msg_limpeza := st.session_state.pop("flash_limpeza_backlog", None):
        st.success(msg_limpeza)

    with st.expander("⚠️ Limpar demandas do Backlog"):
        st.warning(
            f"Isso apaga apenas as **{qtd_backlog} demanda(s) do Backlog** "
            "(as que ainda não entraram em nenhuma sprint). Demandas em sprint, "
            "congeladas em sprints encerradas ou concluídas **não são afetadas**. "
            "Ação irreversível."
        )
        _confirma = st.checkbox("Entendo que isso apaga todas as demandas do Backlog", key="confirma_limpar_backlog")
        if st.button("🗑️ Limpar Backlog", type="primary",
                     disabled=(not _confirma) or qtd_backlog == 0):
            removidas = limpar_backlog()
            st.session_state["flash_limpeza_backlog"] = (
                f"Backlog limpo: {removidas} demanda(s) removida(s). Você pode importar do zero."
            )
            st.session_state.pop("confirma_limpar_backlog", None)
            st.rerun()

# ===========================================================================
# ABA 2 — CLASSIFICAR (curadoria embutida)
# ===========================================================================
if aba_ativa == ABAS[1]:
    if not tem_demandas:
        st.info("O Backlog está vazio. Importe o export do Trace na aba **📥 Importar**.")
    else:
        with st.expander("ℹ️ Como o score é calculado"):
            legenda = legenda_urgencia_importancia()
            st.markdown(
                "Score sugerido = média ponderada de 4 fatores (pesos em `config/score.json`):\n\n"
                "- **Prioridade do Trace** (35%)\n"
                "- **Urgência/Importância** (25%) — escala de Eisenhower:\n"
                f"  - 1 = {legenda.get('1', '')}\n"
                f"  - 2 = {legenda.get('2', '')}\n"
                f"  - 3 = {legenda.get('3', '')}\n"
                f"  - 4 = {legenda.get('4', '')}\n"
                "- **Aging** (20%) — quanto mais dias parado, maior a nota\n"
                "- **Tipo** (20%) — Incidente > Melhoria > Serviço Suporte\n\n"
                "O **Score** final pode ser diferente do sugerido — é só digitar outro valor."
            )

        with st.expander("⚙️ Macroprocessos e sistemas cadastrados"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Macroprocessos**")
                st.write(", ".join(carregar_macroprocessos()) or "_nenhum cadastrado_")
                novo_macro = st.text_input("Adicionar novo macroprocesso", key="novo_macro")
                if st.button("➕ Adicionar macroprocesso", disabled=not novo_macro.strip()):
                    adicionar_macroprocesso(novo_macro.strip())
                    st.session_state.flash_backlog = f"Macroprocesso '{novo_macro.strip()}' cadastrado!"
                    st.rerun()
            with c2:
                st.markdown("**Sistemas**")
                st.write(", ".join(carregar_sistemas()) or "_nenhum cadastrado_")
                novo_sistema = st.text_input("Adicionar novo sistema", key="novo_sistema")
                if st.button("➕ Adicionar sistema", disabled=not novo_sistema.strip()):
                    adicionar_sistema(novo_sistema.strip())
                    st.session_state.flash_backlog = f"Sistema '{novo_sistema.strip()}' cadastrado!"
                    st.rerun()

        texto_busca = st.text_input(
            "🔍 Pesquisar por título ou Id(s)",
            help="Vários Ids de uma vez: separe por ; , espaço ou traço. Ex.: 123456;123457",
            key="busca_classificar",
        )
        df_filtrado = df
        if texto_busca:
            por_ids = busca_por_ids(df, texto_busca)
            if por_ids is not None:
                df_filtrado = por_ids
            else:
                df_filtrado = df[df["titulo"].str.lower().str.contains(texto_busca.lower(), na=False) |
                                 df["id"].astype(str).str.contains(texto_busca)]
        df_filtrado = df_filtrado.reset_index(drop=True)

        st.caption(
            f"{len(df_filtrado)} de {len(df)} demandas no Backlog — edite direto na tabela (salva sozinho). "
            "Para incluir um Macroprocesso/Sistema novo, cadastre no expander acima."
        )

        from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode

        opcoes_macro_grid = sorted(set(carregar_macroprocessos()) - {""})
        opcoes_sist_grid  = sorted(set(carregar_sistemas()) - {""})
        orfaos_macro = sorted(set(df_filtrado["macroprocesso"].dropna()) - set(opcoes_macro_grid) - {""})
        orfaos_sist  = sorted(set(df_filtrado["sistema"].dropna())  - set(opcoes_sist_grid)  - {""})
        opcoes_macro_grid = opcoes_macro_grid + orfaos_macro
        opcoes_sist_grid  = opcoes_sist_grid  + orfaos_sist

        st.caption(
            f"{len(df_filtrado)} de {len(df)} demandas — clique numa célula editável para alterar. "
            "Selecione linhas e use '💾 Salvar selecionadas' para persistir."
        )

        df_ag = pd.DataFrame({
            "Id":            df_filtrado["id"].astype(int),
            "Título":        df_filtrado["titulo"],
            "Estado":        df_filtrado["estado"].fillna(""),
            "Prioridade":    df_filtrado["prioridade_exibicao"],
            "Score sug.":    df_filtrado["score_sugerido_calc"].round(1),
            "Score":         df_filtrado["score_exibicao"].round(1),
            "Aging":         df_filtrado["aging_dias"].fillna(0).astype(int),
            "Macroprocesso": df_filtrado["macroprocesso"].fillna(""),
            "Sistema":       df_filtrado["sistema"].replace("", "TOTVS").fillna("TOTVS"),
            "Observações":   df_filtrado["observacoes"].fillna(""),
        })

        estado_style = JsCode("""
        function(params) {
            var v = (params.value || '').toLowerCase();
            var s = {borderRadius:'4px', padding:'2px 8px', fontWeight:'500', fontSize:'12px', display:'inline-block'};
            if (v.includes('em aten'))  return Object.assign({}, s, {background:'#d3f9d8', color:'#2b8a3e'});
            if (v.includes('planejado') && !v.includes('não') && !v.includes('nao')) return Object.assign({}, s, {background:'#d0ebff', color:'#1864ab'});
            if (v.includes('não plan') || v.includes('nao plan')) return Object.assign({}, s, {background:'#f1f3f5', color:'#495057'});
            if (v.includes('pendente f')) return Object.assign({}, s, {background:'#fff3bf', color:'#e67700'});
            if (v.includes('pendente s')) return Object.assign({}, s, {background:'#ffe8cc', color:'#d9480f'});
            if (v.includes('conclu'))    return Object.assign({}, s, {background:'#ebfbee', color:'#1b4332'});
            return {};
        }""")

        prio_style = JsCode("""
        function(params) {
            var v = (params.value || '').toLowerCase();
            var s = {borderRadius:'4px', padding:'2px 8px', fontWeight:'500', fontSize:'12px', display:'inline-block'};
            if (v.includes('crít') || v.includes('crit')) return Object.assign({}, s, {background:'#ffecec', color:'#c92a2a'});
            if (v.includes('alta'))  return Object.assign({}, s, {background:'#ffe8cc', color:'#d9480f'});
            if (v.includes('médi') || v.includes('medi')) return Object.assign({}, s, {background:'#fff3bf', color:'#e67700'});
            if (v.includes('bai'))   return Object.assign({}, s, {background:'#f1f3f5', color:'#495057'});
            return {};
        }""")

        gb = GridOptionsBuilder.from_dataframe(df_ag)
        gb.configure_default_column(resizable=True, sortable=True, filterable=True, editable=False)
        gb.configure_column("Id",           width=80,  editable=False, pinned="left")
        gb.configure_column("Título",       width=300, editable=False, tooltipField="Título")
        gb.configure_column("Estado",       width=130, editable=False, cellStyle=estado_style)
        gb.configure_column("Prioridade",   width=100, editable=False, cellStyle=prio_style)
        gb.configure_column("Score sug.",   width=90,  editable=False, headerName="Score sug.")
        gb.configure_column("Score",        width=80,  editable=True,  type=["numericColumn"])
        gb.configure_column("Aging",        width=70,  editable=False)
        gb.configure_column("Macroprocesso", width=150, editable=True,
                            cellEditor="agSelectCellEditor",
                            cellEditorParams={"values": [""] + opcoes_macro_grid})
        gb.configure_column("Sistema",      width=120, editable=True,
                            cellEditor="agSelectCellEditor",
                            cellEditorParams={"values": [""] + opcoes_sist_grid})
        gb.configure_column("Observações",  width=200, editable=True)
        gb.configure_selection(selection_mode="multiple", use_checkbox=True, header_checkbox=True)
        gb.configure_grid_options(
            rowHeight=36, headerHeight=38,
            stopEditingWhenCellsLoseFocus=True,
        )

        custom_css = {
            ".ag-theme-streamlit": {
                "--ag-font-size": "13px",
                "--ag-row-hover-color": "#f8f9fa",
                "--ag-selected-row-background-color": "#e7f3ff",
                "--ag-header-background-color": "#f8f9fa",
                "--ag-header-foreground-color": "#6c757d",
                "--ag-border-color": "#e9ecef",
            },
            ".ag-header-cell-label": {
                "font-size": "11px", "font-weight": "600",
                "text-transform": "uppercase", "letter-spacing": "0.04em",
            },
        }

        resultado = AgGrid(
            df_ag,
            gridOptions=gb.build(),
            height=480,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            allow_unsafe_jscode=True,
            theme="streamlit",
            custom_css=custom_css,
            key="aggrid_classificar",
        )

        # ── Salvar ──────────────────────────────────────────────────────────
        if resultado is not None and resultado.data is not None and not resultado.data.empty:
            if st.button("💾 Salvar alterações", type="primary"):
                salvos = 0
                for _, row in resultado.data.iterrows():
                    did = int(row["Id"])
                    orig = df_filtrado[df_filtrado["id"] == did]
                    if orig.empty:
                        continue
                    orig = orig.iloc[0]
                    macro = str(row.get("Macroprocesso") or "").strip()
                    sist  = str(row.get("Sistema") or "").strip()
                    try:
                        score_val = float(row.get("Score", orig.get("score_exibicao", 5.0)))
                    except (TypeError, ValueError):
                        score_val = float(orig.get("score_sugerido_calc", 5.0))
                    obs = str(row.get("Observações") or "").strip()
                    try:
                        if macro and macro not in carregar_macroprocessos():
                            adicionar_macroprocesso(macro)
                        if sist and sist not in carregar_sistemas():
                            adicionar_sistema(sist)
                        atualizar_curadoria(
                            demanda_id=did,
                            macroprocesso=macro or None,
                            sistema=sist or None,
                            score_final=score_val,
                            score_sugerido=float(orig.get("score_sugerido_calc", score_val)),
                            observacoes=obs or None,
                        )
                        salvos += 1
                    except Exception as e:
                        st.error(f"Erro ao salvar {did}: {e}")
                if salvos:
                    st.session_state.flash_backlog = f"✅ {salvos} demanda(s) salva(s)."
                    st.rerun()

        # ── Ver detalhes (seleção de 1 linha) ───────────────────────────────
        selecionadas = getattr(resultado, "selected_rows", None) if resultado is not None else None
        if selecionadas is not None:
            try:
                n_sel = len(selecionadas)
            except Exception:
                n_sel = 0
            if n_sel == 1:
                try:
                    if hasattr(selecionadas, "iloc"):
                        sel = selecionadas.iloc[0].to_dict()
                    else:
                        sel = selecionadas[0] if isinstance(selecionadas[0], dict) else dict(selecionadas[0])
                    sel_id = int(sel["Id"])
                    achou = df[df["id"].astype(int) == sel_id]
                    if not achou.empty:
                        abrir_detalhes(achou.iloc[0], opcoes_macro_grid, opcoes_sist_grid)
                except Exception:
                    pass

# ===========================================================================
# ABA 3 — PLANEJAR SPRINT
# ===========================================================================
if aba_ativa == ABAS[2]:
    if not tem_demandas:
        st.info("O Backlog está vazio. Importe o export do Trace na aba **📥 Importar**.")
    else:
        em_andamento = sprint_em_andamento(sprint) if sprint else False
        tipo_padrao = "Paraquedas" if em_andamento else "Planejada"

        if sprint:
            estado_txt = "🏃 em andamento" if em_andamento else "🗓️ em planejamento"
            st.caption(
                f"Sprint ativa: **{sprint['nome']}** ({estado_txt}). Marque as demandas e envie — "
                f"entram como **{tipo_padrao}** (dá para trocar o tipo, inclusive Interna)."
            )
            # ➕ criar atividade interna direto aqui (vai para a sprint ativa)
            with st.popover("➕ Nova atividade interna"):
                st.caption("Cria uma atividade interna (cerimônia, feriado, reunião…) já na sprint ativa.")
                titulo_ai = st.text_input("Atividade", placeholder="Cerimônia Ágil, Feriado…", key="plan_nova_ativ")
                pa1, pa2 = st.columns(2)
                resp_ai = pa1.selectbox("Responsável", [""] + lista_apelidos(), key="plan_ativ_resp")
                tipo_ai = pa2.selectbox("Tipo", TIPOS_ENTRADA, index=TIPOS_ENTRADA.index("Interna") if "Interna" in TIPOS_ENTRADA else 0, key="plan_ativ_tipo")
                if st.button("➕ Criar atividade", type="primary", disabled=not titulo_ai.strip(), key="plan_criar_ativ"):
                    adicionar_atividade_interna(sprint["id"], titulo_ai.strip(), resp_ai, 0, tipo_ai)
                    st.session_state.flash_backlog = f"Atividade '{titulo_ai.strip()}' criada na sprint {sprint['nome']}."
                    st.rerun()
        else:
            st.caption(
                "Não há sprint ativa. Marque as demandas e clique em **➕ Criar sprint e enviar** "
                "para abrir uma sprint nova já com elas dentro. (Atividades internas podem ser "
                "criadas depois que a sprint existir.)"
            )

        from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode
        from functions.aggrid_helper import AG_CSS, TIPO_ENTRADA_STYLE

        df_envio = pd.DataFrame({
            "Id":           df["id"].astype(int),
            "Título":       df["titulo"],
            "Score":        df["score_exibicao"].round(1),
            "Tipo entrada": tipo_padrao,
            "Responsável":  df["responsavel_atendimento"].apply(apelido),
        })

        gb_env = GridOptionsBuilder.from_dataframe(df_envio)
        gb_env.configure_default_column(resizable=True, sortable=True, editable=False)
        gb_env.configure_column("Id",           width=80,  editable=False)
        gb_env.configure_column("Título",       width=360, editable=False, tooltipField="Título")
        gb_env.configure_column("Score",        width=75,  editable=False)
        gb_env.configure_column("Tipo entrada", width=120, editable=True,
                                cellStyle=TIPO_ENTRADA_STYLE,
                                cellEditor="agSelectCellEditor",
                                cellEditorParams={"values": TIPOS_ENTRADA})
        gb_env.configure_column("Responsável",  width=110, editable=True,
                                cellEditor="agSelectCellEditor",
                                cellEditorParams={"values": [""] + lista_apelidos()})
        gb_env.configure_selection(selection_mode="multiple", use_checkbox=True, header_checkbox=True)
        gb_env.configure_grid_options(rowHeight=36, headerHeight=38,
                                      stopEditingWhenCellsLoseFocus=True)

        res_env = AgGrid(df_envio, gridOptions=gb_env.build(), height=340,
                         update_mode=GridUpdateMode.MODEL_CHANGED,
                         data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                         allow_unsafe_jscode=True, theme="streamlit",
                         custom_css=AG_CSS, key=f"ag_envio_sprint")

        # linhas marcadas = selecionadas no checkbox
        selecionadas_env = res_env.selected_rows if res_env else None
        marcadas_env = []
        if selecionadas_env is not None and len(selecionadas_env) > 0:
            rows = selecionadas_env if isinstance(selecionadas_env, list) else selecionadas_env.to_dict("records")
            # usa dados editados (res_env.data) para pegar tipo/responsável corretos
            dados_editados = res_env.data if res_env.data is not None else df_envio
            ids_sel = {int(r["Id"]) for r in rows}
            marcadas_env = dados_editados[dados_editados["Id"].astype(int).isin(ids_sel)]

        # validações de higiene
        if not (marcadas_env if isinstance(marcadas_env, list) else len(marcadas_env) > 0 if hasattr(marcadas_env,'__len__') else False):
            pass
        else:
            m = marcadas_env if hasattr(marcadas_env, 'iterrows') else pd.DataFrame(marcadas_env)
            sem_resp = m[m["Responsável"].fillna("").str.strip() == ""]
            ids_m = set(m["Id"].astype(int))
            base = df[df["id"].astype(int).isin(ids_m)]
            sem_cur = base[(base["macroprocesso"].fillna("").str.strip()=="")|(base["sistema"].fillna("").str.strip()=="")]
            avisos = []
            if not sem_resp.empty: avisos.append(f"**{len(sem_resp)}** sem responsável")
            if not sem_cur.empty:  avisos.append(f"**{len(sem_cur)}** sem curadoria")
            if avisos:
                st.warning("⚠️ Higiene: " + " e ".join(avisos) + ". Você ainda pode enviar.")

        def _mover_para_sprint(sprint_id, linhas):
            n = 0
            df_linhas = linhas if hasattr(linhas, 'iterrows') else pd.DataFrame(linhas)
            for _, row in df_linhas.iterrows():
                adicionar_demanda_a_sprint(
                    demanda_id=int(row["Id"]),
                    sprint_id=sprint_id,
                    tipo_entrada=row["Tipo entrada"],
                    responsavel_sprint=row["Responsável"],
                )
                n += 1
            return n

        @st.dialog("🚀 Criar sprint e enviar demandas")
        def criar_sprint_e_enviar(linhas):
            st.markdown(f"**{len(linhas)} demanda(s)** marcada(s) serão movidas para a nova sprint.")
            nome = st.text_input("Nome da sprint", placeholder="Sprint 12 — 06/07 a 17/07")
            meta = st.text_input("🎯 Meta da sprint (objetivo)", placeholder="Ex.: Estabilizar as integrações do módulo financeiro")
            c1, c2 = st.columns(2)
            inicio = c1.date_input("Início", value=date.today(), format="DD/MM/YYYY")
            fim = c2.date_input("Fim", value=date.today(), format="DD/MM/YYYY")
            st.caption(
                "A sprint nasce em **planejamento** e as demandas entram como **Planejada**. "
                "Depois é só abrir a página Sprint e clicar em ▶️ Iniciar."
            )
            if st.button("🚀 Criar e enviar", type="primary", disabled=not nome.strip()):
                try:
                    novo_id = criar_sprint(nome.strip(), str(inicio), str(fim), meta=meta.strip() or None)
                    n = _mover_para_sprint(novo_id, linhas)
                    st.session_state.flash_backlog = f"Sprint '{nome.strip()}' criada com {n} demanda(s)."
                    st.rerun()
                except ValueError as erro:
                    st.error(str(erro))
                except Exception:
                    st.error("Não foi possível criar a sprint. Tente novamente.")

        n_marcadas = len(marcadas_env) if hasattr(marcadas_env, '__len__') and not isinstance(marcadas_env, list) else len(marcadas_env) if isinstance(marcadas_env, list) else 0
        _marcadas_df = marcadas_env if hasattr(marcadas_env, 'iterrows') else pd.DataFrame(marcadas_env) if marcadas_env else pd.DataFrame()

        if sprint:
            if st.button(f"➕ Enviar {n_marcadas} demanda(s) para **{sprint['nome']}**",
                         type="primary", disabled=n_marcadas == 0):
                try:
                    n = _mover_para_sprint(sprint["id"], _marcadas_df)
                    st.session_state.flash_backlog = f"{n} demanda(s) enviada(s) para a sprint {sprint['nome']}."
                    st.rerun()
                except Exception:
                    st.error("Não foi possível enviar as demandas. Tente novamente.")
        else:
            if st.button(f"➕ Criar sprint e enviar {n_marcadas} demanda(s)",
                         type="primary", disabled=n_marcadas == 0):
                criar_sprint_e_enviar(_marcadas_df)
