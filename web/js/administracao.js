(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  $("btn-logout").addEventListener("click", async (e) => {
    e.preventDefault();
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
  });

  function flash(msg) {
    $("flash").textContent = msg; $("flash").hidden = false;
    setTimeout(() => { $("flash").hidden = true; }, 3500);
  }
  function flashErro(msg) {
    $("flash-erro").textContent = msg; $("flash-erro").hidden = false;
    setTimeout(() => { $("flash-erro").hidden = true; }, 4500);
  }
  function escapeHTML(s) {
    const d = document.createElement("div");
    d.textContent = String(s ?? "");
    return d.innerHTML;
  }

  const NOME_PERFIL = { admin: "Administrador", admin_equipe: "Administrador de equipe", usuario: "Usuário" };

  const state = { eu: null, equipes: [] };

  // ── Abas ─────────────────────────────────────────────────────────────────
  document.querySelectorAll(".aba-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".aba-btn").forEach((b) => b.classList.remove("ativo"));
      btn.classList.add("ativo");
      ["usuarios", "equipes", "permissoes", "configuracoes"].forEach((a) => { $("aba-" + a).hidden = a !== btn.dataset.aba; });
    });
  });

  // ── ABA USUÁRIOS ─────────────────────────────────────────────────────────
  const tabelaUsuarios = $("tabela-usuarios");
  gpMakeSortable(tabelaUsuarios.closest("table"));

  function montarSelectsNovoUsuario() {
    const selEquipe = $("novo-usuario-equipe");
    if (state.eu.perfil === "admin") {
      selEquipe.innerHTML = state.equipes.map((e) => `<option value="${e.id}">${escapeHTML(e.nome)}</option>`).join("");
      selEquipe.disabled = false;
    } else {
      selEquipe.innerHTML = `<option value="${state.eu.equipe_id}">${escapeHTML(state.eu.equipe_nome)}</option>`;
      selEquipe.disabled = true;
    }
    const selPerfil = $("novo-usuario-perfil");
    selPerfil.querySelector('option[value="admin"]').hidden = state.eu.perfil !== "admin";
  }

  const usuariosEmEdicao = new Set();

  function opcoesEquipe(equipeIdAtual) {
    if (state.eu.perfil === "admin") {
      return state.equipes.map((e) => `<option value="${e.id}" ${e.id === equipeIdAtual ? "selected" : ""}>${escapeHTML(e.nome)}</option>`).join("");
    }
    return `<option value="${state.eu.equipe_id}" selected>${escapeHTML(state.eu.equipe_nome)}</option>`;
  }

  function opcoesPerfil(perfilAtual) {
    const perfis = state.eu.perfil === "admin" ? ["usuario", "admin_equipe", "admin"] : ["usuario", "admin_equipe"];
    return perfis.map((p) => `<option value="${p}" ${p === perfilAtual ? "selected" : ""}>${escapeHTML(NOME_PERFIL[p])}</option>`).join("");
  }

  async function carregarUsuarios() {
    const resp = await fetch("/api/usuarios");
    if (resp.status === 401) { window.location.href = "/login"; return; }
    const usuarios = await resp.json();
    const nomeEquipe = (id) => (state.equipes.find((e) => e.id === id) || {}).nome || "—";

    tabelaUsuarios.innerHTML = usuarios.map((u) => {
      const editando = usuariosEmEdicao.has(u.id);
      // admin_equipe não edita um Administrador global — nem mostra o lápis.
      const podeEditar = state.eu.perfil === "admin" || u.perfil !== "admin";
      if (editando) {
        return `
      <tr data-id="${u.id}">
        <td>${escapeHTML(u.usuario)}</td>
        <td><input type="text" class="us-edit-apelido" value="${escapeHTML(u.apelido || "")}" placeholder="Ex.: Vivi"></td>
        <td><select class="us-edit-equipe">${opcoesEquipe(u.equipe_id)}</select></td>
        <td><select class="us-edit-perfil">${opcoesPerfil(u.perfil)}</select></td>
        <td><input type="password" class="us-edit-senha" placeholder="Nova senha (opcional)" autocomplete="new-password"></td>
        <td>
          <button type="button" class="us-btn-salvar" data-id="${u.id}">💾 Salvar</button>
          <button type="button" class="us-btn-cancelar" data-id="${u.id}">Cancelar</button>
        </td>
      </tr>`;
      }
      return `
      <tr>
        <td>${escapeHTML(u.usuario)}</td>
        <td data-sort="${escapeHTML(u.apelido || "")}">${escapeHTML(u.apelido || "—")}</td>
        <td data-sort="${escapeHTML(nomeEquipe(u.equipe_id))}">${escapeHTML(nomeEquipe(u.equipe_id))}</td>
        <td data-sort="${escapeHTML(u.perfil || "usuario")}">${escapeHTML(NOME_PERFIL[u.perfil] || u.perfil || "Usuário")}</td>
        <td data-sort="${escapeHTML(u.criado_em || "")}" data-sort-tipo="data-br">${escapeHTML(u.criado_em || "—")}</td>
        <td>
          ${podeEditar ? `<button type="button" class="us-btn-editar" data-id="${u.id}">✏️ Editar</button>` : ""}
          <button type="button" class="us-btn-remover" data-id="${u.id}">Remover</button>
        </td>
      </tr>`;
    }).join("") || '<tr><td colspan="6" class="gp-caption">Nenhum usuário cadastrado ainda.</td></tr>';

    tabelaUsuarios.querySelectorAll(".us-btn-editar").forEach((btn) => {
      btn.addEventListener("click", () => {
        usuariosEmEdicao.add(Number(btn.dataset.id));
        carregarUsuarios();
      });
    });
    tabelaUsuarios.querySelectorAll(".us-btn-cancelar").forEach((btn) => {
      btn.addEventListener("click", () => {
        usuariosEmEdicao.delete(Number(btn.dataset.id));
        carregarUsuarios();
      });
    });
    tabelaUsuarios.querySelectorAll(".us-btn-salvar").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const linha = tabelaUsuarios.querySelector(`tr[data-id="${btn.dataset.id}"]`);
        const equipe_id = Number(linha.querySelector(".us-edit-equipe").value);
        const perfil = linha.querySelector(".us-edit-perfil").value;
        const apelido = linha.querySelector(".us-edit-apelido").value.trim();
        const senha = linha.querySelector(".us-edit-senha").value;
        if (senha && senha.length < 6) {
          flashErro("A nova senha precisa ter pelo menos 6 caracteres.");
          return;
        }
        const corpo = { equipe_id, perfil, apelido };
        if (senha) corpo.senha = senha;
        const resp = await fetch(`/api/usuarios/${btn.dataset.id}`, {
          method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo),
        });
        const dados = await resp.json();
        if (resp.ok && dados.ok) {
          usuariosEmEdicao.delete(Number(btn.dataset.id));
          flash("Usuário atualizado.");
          carregarUsuarios();
        } else {
          flashErro(dados.erro || "Não foi possível salvar.");
        }
      });
    });
    tabelaUsuarios.querySelectorAll(".us-btn-remover").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Remover este usuário? Ele perde acesso imediatamente.")) return;
        const resp = await fetch(`/api/usuarios/${btn.dataset.id}`, { method: "DELETE" });
        const dados = await resp.json();
        if (resp.ok && dados.ok) {
          flash("Usuário removido.");
          carregarUsuarios();
        } else {
          flashErro(dados.erro || "Não foi possível remover.");
        }
      });
    });
  }

  $("form-novo-usuario").addEventListener("submit", async (e) => {
    e.preventDefault();
    const usuario = $("novo-usuario").value.trim();
    const senha = $("nova-senha").value;
    const apelido = $("novo-usuario-apelido").value.trim();
    const equipe_id = Number($("novo-usuario-equipe").value);
    const perfil = $("novo-usuario-perfil").value;

    const resp = await fetch("/api/usuarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario, senha, apelido, equipe_id, perfil }),
    });
    const dados = await resp.json();
    if (resp.ok && dados.ok) {
      $("form-novo-usuario").reset();
      montarSelectsNovoUsuario();
      flash(`Usuário '${usuario}' criado.`);
      carregarUsuarios();
    } else {
      flashErro(dados.erro || "Não foi possível criar o usuário.");
    }
  });

  // ── ABA EQUIPES E QUADROS ────────────────────────────────────────────────
  async function carregarEquipes() {
    const resp = await fetch("/api/equipes");
    if (resp.status === 401) { window.location.href = "/login"; return; }
    state.equipes = await resp.json();
    montarSelectsNovoUsuario();

    const souAdmin = state.eu.perfil === "admin";
    $("form-nova-equipe").hidden = !souAdmin;
    $("equipes-escopo-caption").textContent = souAdmin
      ? "Cada equipe tem seus próprios usuários e quadros — dados de uma equipe não aparecem pra outra."
      : `Você administra a equipe ${state.eu.equipe_nome}.`;

    const lista = $("lista-equipes");
    lista.innerHTML = state.equipes.map((eq) => `
      <details class="gp-expander" data-equipe-id="${eq.id}">
        <summary>🏢 ${escapeHTML(eq.nome)}</summary>
        ${souAdmin ? `
          <label class="gp-checkbox-row"><input type="checkbox" class="eq-conf-excluir" data-id="${eq.id}"> Sim, quero excluir esta equipe</label>
          <button type="button" class="eq-btn-excluir" data-id="${eq.id}" disabled>🗑️ Excluir equipe</button>
          <hr>
        ` : ""}
        <h4>Quadros</h4>
        <table class="gp-table eq-quadros-table">
          <thead><tr><th>Nome</th><th></th></tr></thead>
          <tbody class="eq-tabela-quadros" data-equipe-id="${eq.id}"></tbody>
        </table>
        <div class="eq-quadro-novo">
          <input type="text" class="eq-novo-quadro-nome" placeholder="Nome do novo quadro">
          <button type="button" class="primary eq-btn-criar-quadro" data-equipe-id="${eq.id}">➕ Criar quadro</button>
        </div>
      </details>
    `).join("") || '<p class="gp-caption">Nenhuma equipe cadastrada ainda.</p>';

    lista.querySelectorAll(".eq-conf-excluir").forEach((cb) => {
      cb.addEventListener("change", (e) => {
        lista.querySelector(`.eq-btn-excluir[data-id="${cb.dataset.id}"]`).disabled = !e.target.checked;
      });
    });
    lista.querySelectorAll(".eq-btn-excluir").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const resp = await fetch(`/api/equipes/${btn.dataset.id}`, { method: "DELETE" });
        const dados = await resp.json();
        if (resp.ok && dados.ok) {
          flash("Equipe excluída.");
          carregarEquipes();
        } else {
          flashErro(dados.erro || "Não foi possível excluir a equipe.");
        }
      });
    });
    lista.querySelectorAll(".eq-btn-criar-quadro").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const input = lista.querySelector(`details[data-equipe-id="${btn.dataset.equipeId}"] .eq-novo-quadro-nome`);
        const nome = input.value.trim();
        if (!nome) return;
        const resp = await fetch("/api/quadros", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ equipe_id: Number(btn.dataset.equipeId), nome }),
        });
        const dados = await resp.json();
        if (resp.ok && dados.ok) {
          input.value = "";
          flash(`Quadro '${nome}' criado.`);
          carregarQuadrosDaEquipe(Number(btn.dataset.equipeId));
        } else {
          flashErro(dados.erro || "Não foi possível criar o quadro.");
        }
      });
    });

    state.equipes.forEach((eq) => carregarQuadrosDaEquipe(eq.id));
  }

  async function carregarQuadrosDaEquipe(equipeId) {
    const resp = await fetch(`/api/quadros?equipe_id=${equipeId}`);
    const quadros = await resp.json();
    const tbody = document.querySelector(`.eq-tabela-quadros[data-equipe-id="${equipeId}"]`);
    if (!tbody) return;
    tbody.innerHTML = quadros.map((q) => `
      <tr data-id="${q.id}">
        <td><input type="text" class="eq-quadro-nome-input" value="${escapeHTML(q.nome)}"></td>
        <td>
          <button type="button" class="eq-btn-icone eq-btn-renomear-quadro" data-id="${q.id}">💾</button>
          <button type="button" class="eq-btn-icone eq-btn-excluir-quadro" data-id="${q.id}">🗑️</button>
        </td>
      </tr>
    `).join("") || '<tr><td colspan="2" class="gp-caption">Nenhum quadro ainda.</td></tr>';

    tbody.querySelectorAll(".eq-btn-renomear-quadro").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const input = tbody.querySelector(`tr[data-id="${btn.dataset.id}"] .eq-quadro-nome-input`);
        const nome = input.value.trim();
        if (!nome) return;
        const resp = await fetch(`/api/quadros/${btn.dataset.id}`, {
          method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nome }),
        });
        const dados = await resp.json();
        if (resp.ok && dados.ok) {
          flash("Quadro renomeado.");
        } else {
          flashErro(dados.erro || "Não foi possível renomear.");
        }
      });
    });
    tbody.querySelectorAll(".eq-btn-excluir-quadro").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Excluir este quadro? Só funciona se ele estiver vazio (sem demandas nem sprints).")) return;
        const resp = await fetch(`/api/quadros/${btn.dataset.id}`, { method: "DELETE" });
        const dados = await resp.json();
        if (resp.ok && dados.ok) {
          flash("Quadro excluído.");
          carregarQuadrosDaEquipe(equipeId);
        } else {
          flashErro(dados.erro || "Não foi possível excluir o quadro.");
        }
      });
    });
  }

  $("nova-equipe-nome").addEventListener("input", (e) => { $("btn-criar-equipe").disabled = !e.target.value.trim(); });
  $("form-nova-equipe").addEventListener("submit", async (e) => {
    e.preventDefault();
    const nome = $("nova-equipe-nome").value.trim();
    const resp = await fetch("/api/equipes", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nome }),
    });
    const dados = await resp.json();
    if (resp.ok && dados.ok) {
      $("form-nova-equipe").reset();
      $("btn-criar-equipe").disabled = true;
      flash(`Equipe '${nome}' criada.`);
      carregarEquipes();
    } else {
      flashErro(dados.erro || "Não foi possível criar a equipe.");
    }
  });

  // ── ABA CONFIGURAÇÕES ────────────────────────────────────────────────────
  function atualizarCamposLdap() {
    const modo = document.querySelector('input[name="modo"]:checked')?.value || "local";
    $("cf-ldap-campos").classList.toggle("desligado", modo === "local");
  }
  document.querySelectorAll('input[name="modo"]').forEach((r) => r.addEventListener("change", atualizarCamposLdap));

  async function carregarConfig() {
    const resp = await fetch("/api/config/auth");
    if (resp.status === 401) { window.location.href = "/login"; return; }
    if (resp.status === 403) {
      $("aba-configuracoes").innerHTML = '<p class="gp-caption">Só o Administrador global pode ver/alterar essa configuração — ela vale pro sistema todo, não só pra sua equipe.</p>';
      return;
    }
    if (state.eu.perfil !== "admin") {
      document.querySelectorAll("#form-config input, #form-config button").forEach((el) => { el.disabled = true; });
      $("form-config").insertAdjacentHTML("afterbegin", '<p class="gp-caption">Somente leitura — só o Administrador global pode alterar (essa configuração vale pro sistema todo).</p>');
    }
    const config = await resp.json();
    const radio = document.querySelector(`input[name="modo"][value="${config.modo}"]`);
    if (radio) radio.checked = true;
    $("ldap-server").value = config.ldap_server || "";
    $("ldap-domain").value = config.ldap_domain || "";
    atualizarCamposLdap();
  }

  $("btn-testar-ldap").addEventListener("click", async () => {
    const servidor = $("ldap-server").value.trim();
    const resultado = $("teste-resultado");
    resultado.className = "cf-teste-resultado";
    resultado.textContent = "Testando…";
    const resp = await fetch("/api/config/auth/testar-ldap", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ldap_server: servidor }),
    });
    const dados = await resp.json();
    resultado.textContent = dados.mensagem;
    resultado.classList.add(dados.ok ? "ok" : "erro");
  });

  $("form-config").addEventListener("submit", async (e) => {
    e.preventDefault();
    const modo = document.querySelector('input[name="modo"]:checked').value;
    const resp = await fetch("/api/config/auth", {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modo, ldap_server: $("ldap-server").value, ldap_domain: $("ldap-domain").value }),
    });
    const dados = await resp.json();
    if (resp.ok && dados.ok) {
      flash("Configuração salva.");
    } else {
      flashErro(dados.erro || "Não foi possível salvar.");
    }
  });

  // ── Inicialização ────────────────────────────────────────────────────────
  (async function init() {
    const resp = await fetch("/api/sessao/eu");
    if (resp.status === 401) { window.location.href = "/login"; return; }
    state.eu = await resp.json();

    const respEq = await fetch("/api/equipes");
    state.equipes = await respEq.json();
    montarSelectsNovoUsuario();

    $("usuarios-escopo-caption").textContent = state.eu.perfil === "admin"
      ? "Quem pode entrar no GP Flow com usuário/senha próprios do sistema — todas as equipes."
      : `Usuários da equipe ${state.eu.equipe_nome}.`;

    carregarUsuarios();
    carregarEquipes();
    carregarConfig();
  })();
})();
