"""GP Flow — navegação principal"""
import streamlit as st

from functions.auth import exigir_login, logout_button

# Bloqueia o app até o usuário autenticar (usuários ficam em st.secrets)
exigir_login()

# No Streamlit 1.44+, o config.toml controla tudo via tema nativo
# incluindo [theme.sidebar] para a sidebar escura.
# O CSS abaixo é fallback mínimo para versões anteriores e ajustes
# que o tema nativo não cobre (como o item ativo do nav).
st.markdown("""
<style>
section[data-testid="stSidebar"] a[aria-current="page"] {
    background-color: #1c3a6e !important;
}
section[data-testid="stSidebar"] a[aria-current="page"] span {
    color: #4c9aff !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] li:nth-child(4) {
    margin-top: 8px !important;
    border-top: 1px solid #30363d !important;
    padding-top: 8px !important;
}
</style>
""", unsafe_allow_html=True)

paginas = st.navigation([
    st.Page("views/backlog.py",   title="Backlog",   icon="📥", default=True),
    st.Page("views/sprint.py",    title="Sprint",    icon="▶️"),
    st.Page("views/kanban.py",    title="Kanban",    icon="📊"),
    st.Page("views/historico.py", title="Histórico", icon="🕐"),
    st.Page("inicio.py",          title="Resumo",    icon="📈"),
])

logout_button()
paginas.run()
