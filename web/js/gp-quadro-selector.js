/**
 * Seletor de quadro na barra superior — cada equipe pode ter vários
 * quadros (Backlog+Sprint+Kanban+Histórico independentes); troca aqui
 * define qual deles as chamadas de API da página usam.
 */
(function () {
  "use strict";

  function escapeHTML(s) {
    const d = document.createElement("div");
    d.textContent = String(s ?? "");
    return d.innerHTML;
  }

  // Esconde o link "Administração" de quem não é admin/admin de equipe —
  // a página já bloqueia no servidor, isso é só pra não mostrar um link
  // que sempre redireciona de volta.
  (async function ocultarAdministracaoSeNecessario() {
    const link = document.querySelector('a[href="/administracao"]');
    if (!link) return;
    const resp = await fetch("/api/sessao/eu");
    if (!resp.ok) return;
    const eu = await resp.json();
    if (eu.perfil !== "admin" && eu.perfil !== "admin_equipe") link.remove();
  })();

  const sel = document.getElementById("gp-quadro-select");
  if (!sel) return;

  async function carregar() {
    const resp = await fetch("/api/sessao/quadros");
    if (resp.status === 401) return;
    const dados = await resp.json();
    const atualId = dados.quadro_atual ? dados.quadro_atual.id : null;
    sel.innerHTML = dados.quadros.map((q) => {
      const rotulo = q.equipe_nome ? `${q.equipe_nome} / ${q.nome}` : q.nome;
      return `<option value="${q.id}" ${q.id === atualId ? "selected" : ""}>🗂️ ${escapeHTML(rotulo)}</option>`;
    }).join("");
  }

  sel.addEventListener("change", async () => {
    await fetch("/api/sessao/quadro", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quadro_id: Number(sel.value) }),
    });
    window.location.reload();
  });

  carregar();
})();
