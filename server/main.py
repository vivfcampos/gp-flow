"""
GP Flow — servidor web próprio.

Roteamento HTTP puro via FastAPI/Starlette — toda a lógica de negócio
fica em functions/. Front-end é HTML/CSS/JS servido como arquivos
estáticos, sem framework de UI.

Rodar (a partir da raiz do projeto):
    uvicorn server.main:app --reload --port 8000
ou:
    run_server.bat
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from server.routes_auth import router as auth_router, usuario_logado, perfil_atual
from server.routes_kanban import router as kanban_router
from server.routes_usuarios import router as usuarios_router
from server.routes_historico import router as historico_router
from server.routes_sprint import router as sprint_router
from server.routes_backlog import router as backlog_router
from server.routes_config import router as config_router
from server.routes_sessao import router as sessao_router
from server.routes_equipes import router as equipes_router
from server.routes_quadros import router as quadros_router
from server.routes_demandas import router as demandas_router

WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="GP Flow")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("GPFLOW_SECRET_KEY", "dev-secret-troque-em-producao"),
    session_cookie="gpflow_session",
    # RENDER é definida automaticamente pelo Render em todo serviço — só exige
    # cookie só-por-HTTPS lá (domínio público); local (run_server.bat, HTTP
    # puro) continua funcionando sem essa exigência.
    https_only=bool(os.environ.get("RENDER")),
)

app.include_router(auth_router)
app.include_router(kanban_router)
app.include_router(usuarios_router)
app.include_router(historico_router)
app.include_router(sprint_router)
app.include_router(backlog_router)
app.include_router(config_router)
app.include_router(sessao_router)
app.include_router(equipes_router)
app.include_router(quadros_router)
app.include_router(demandas_router)

app.mount("/css", StaticFiles(directory=WEB_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=WEB_DIR / "js"), name="js")


@app.get("/")
def raiz():
    return RedirectResponse("/kanban")


def _pagina(nome_arquivo: str, request: Request):
    """Serve um HTML estático da pasta web/, exigindo sessão ativa."""
    if not usuario_logado(request):
        return RedirectResponse("/login")
    return FileResponse(WEB_DIR / nome_arquivo)


@app.get("/kanban")
def pagina_kanban(request: Request):
    return _pagina("kanban.html", request)


@app.get("/usuarios")
def pagina_usuarios():
    return RedirectResponse("/administracao")


@app.get("/historico")
def pagina_historico(request: Request):
    return _pagina("historico.html", request)


@app.get("/sprint")
def pagina_sprint(request: Request):
    return _pagina("sprint.html", request)


@app.get("/backlog")
def pagina_backlog(request: Request):
    return _pagina("backlog.html", request)


@app.get("/configuracoes")
def pagina_configuracoes():
    return RedirectResponse("/administracao")


@app.get("/administracao")
def pagina_administracao(request: Request):
    if not usuario_logado(request):
        return RedirectResponse("/login")
    if perfil_atual(request) not in ("admin", "admin_equipe"):
        return RedirectResponse("/kanban")
    return FileResponse(WEB_DIR / "administracao.html")
