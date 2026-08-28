"""Autenticação do servidor web (sessão via cookie assinado)."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from functions.auth import autenticar
from functions.banco import resolver_perfil_usuario, listar_quadros

WEB_DIR = Path(__file__).parent.parent / "web"

router = APIRouter()


def usuario_logado(request: Request) -> str | None:
    return request.session.get("usuario")


def perfil_atual(request: Request) -> str:
    return request.session.get("perfil") or "usuario"


def equipe_atual(request: Request):
    return request.session.get("equipe_id")


def quadro_atual(request: Request):
    return request.session.get("quadro_id")


_HIERARQUIA_PERFIS = {"usuario": 0, "admin_equipe": 1, "admin": 2}


def exigir_login(request: Request) -> JSONResponse | None:
    """Use no início de uma rota de API: retorna 401 se não houver sessão."""
    if not usuario_logado(request):
        return JSONResponse({"erro": "Não autenticado."}, status_code=401)
    return None


def exigir_perfil(request: Request, minimo: str) -> JSONResponse | None:
    """
    Use depois de exigir_login pra rotas que só um perfil mais alto pode
    acessar (ex.: exigir_perfil(request, "admin_equipe")). Hierarquia:
    admin > admin_equipe > usuario. Retorna 403 se não atender.
    """
    if erro := exigir_login(request):
        return erro
    if _HIERARQUIA_PERFIS.get(perfil_atual(request), 0) < _HIERARQUIA_PERFIS.get(minimo, 99):
        return JSONResponse({"erro": "Sem permissão para esta ação."}, status_code=403)
    return None


@router.get("/login")
def pagina_login(request: Request):
    if usuario_logado(request):
        return RedirectResponse("/kanban")
    return FileResponse(WEB_DIR / "login.html")


@router.post("/api/login")
async def api_login(request: Request):
    dados = await request.json()
    usuario = str(dados.get("usuario", "")).strip()
    senha = str(dados.get("senha", ""))
    if not autenticar(usuario, senha):
        return JSONResponse({"ok": False, "erro": "Usuário ou senha incorretos."}, status_code=401)

    usuario_norm = usuario.lower()
    registro = resolver_perfil_usuario(usuario_norm)
    request.session["usuario"] = usuario_norm
    request.session["perfil"] = registro.get("perfil") or "usuario"
    request.session["equipe_id"] = registro.get("equipe_id")

    quadros = listar_quadros(registro.get("equipe_id"))
    request.session["quadro_id"] = int(quadros.iloc[0]["id"]) if not quadros.empty else None

    return {"ok": True}


@router.post("/api/logout")
def api_logout(request: Request):
    request.session.pop("usuario", None)
    return {"ok": True}
