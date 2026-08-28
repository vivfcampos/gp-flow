(function () {
  "use strict";

  const CORES = ["#0052CC", "#FF991F", "#DE350B", "#6554C0", "#00875A"];

  const state = {
    board: null,
    filtroResp: new Set(),
    filtroTipo: new Set(),
    dragId: null,
    dragType: null,
    cardId: null,
  };

  const $ = (sel) => document.querySelector(sel);
  const boardEl = $("#board-quadro");
  const dailyEl = $("#board-daily");

  // ── Topbar / logout ─────────────────────────────────────────────────────
  $("#btn-logout").addEventListener("click", async (e) => {
    e.preventDefault();
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
  });

  function flash(msg) {
    const el = $("#flash");
    el.textContent = msg;
    el.hidden = false;
    setTimeout(() => { el.hidden = true; }, 3500);
  }

  // ── Carrega o quadro ─────────────────────────────────────────────────────
  async function carregarBoard() {
    const resp = await fetch("/api/kanban/board");
    if (resp.status === 401) { window.location.href = "/login"; return; }
    state.board = await resp.json();

    if (!state.board.sprint) {
      boardEl.innerHTML = '<p class="gp-caption">Não existe nenhuma sprint em andamento.</p>';
      $("#sprint-caption").textContent = "";
      return;
    }
    $("#sprint-caption").textContent =
      "Sprint: " + state.board.sprint.nome + " — clique num cartão para ver detalhes, arraste para mudar o status";

    montarFiltros();
    preencherSelects();
    renderBoard();
  }

  function montarFiltros() {
    const menuResp = document.querySelector("#filtro-resp .kb-filtro-menu");
    if (!menuResp.dataset.montado) {
      menuResp.innerHTML = state.board.apelidos.length
        ? state.board.apelidos.map((nome) =>
            `<label><input type="checkbox" value="${nome}"> ${nome}</label>`
          ).join("")
        : '<p class="gp-caption" style="margin:0;">Nenhum responsável cadastrado — cadastre em Backlog &gt; Classificar.</p>';
      menuResp.querySelectorAll("input").forEach((cb) => {
        cb.addEventListener("change", () => {
          cb.checked ? state.filtroResp.add(cb.value) : state.filtroResp.delete(cb.value);
          renderBoard();
        });
      });
      menuResp.dataset.montado = "1";
    }

    const menuTipo = document.querySelector("#filtro-tipo .kb-filtro-menu");
    if (!menuTipo.dataset.montado) {
      menuTipo.innerHTML = state.board.tipos_entrada.map((t) =>
        `<label><input type="checkbox" value="${t}"> ${t}</label>`
      ).join("");
      menuTipo.querySelectorAll("input").forEach((cb) => {
        cb.addEventListener("change", () => {
          cb.checked ? state.filtroTipo.add(cb.value) : state.filtroTipo.delete(cb.value);
          renderBoard();
        });
      });
      menuTipo.dataset.montado = "1";
    }
  }

  document.querySelectorAll(".kb-filtro-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const wrap = btn.closest(".kb-filtro");
      const estava = wrap.classList.contains("aberto");
      document.querySelectorAll(".kb-filtro.aberto").forEach((w) => w.classList.remove("aberto"));
      if (!estava) wrap.classList.add("aberto");
    });
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".kb-filtro")) {
      document.querySelectorAll(".kb-filtro.aberto").forEach((w) => w.classList.remove("aberto"));
    }
  });

  function passaFiltro(item) {
    if (state.filtroResp.size && !state.filtroResp.has(item.responsavel)) return false;
    if (state.filtroTipo.size && !state.filtroTipo.has(item.entrada)) return false;
    return true;
  }

  function badgeHTML(t) {
    if (!t) return "";
    const cls = t === "Planejada" ? "kb-plan" : t === "Paraquedas" ? "kb-para" : "kb-int";
    return `<span class="kb-badge ${cls}">${t}</span>`;
  }

  function cardHTML(item) {
    const imp = item.impedimento ? '<span class="kb-badge kb-imp">⚠ Imp.</span>' : "";
    const horas = item.horas > 0 ? `<span>⏱ ${item.horas.toFixed(1)}h</span>` : "";
    const resp = item.responsavel ? `<span>👤 ${item.responsavel}</span>` : "";
    const score = item.score ? `<span>⭐ ${item.score}</span>` : "";
    return `<div class="kb-card" draggable="true" data-id="${item.id}" data-tipo="${item.tipo}">
      <div class="kb-id">${item.tipo}${item.id}</div>
      <div class="kb-title">${escapeHTML(item.titulo)}</div>
      <div class="kb-meta">${resp}${badgeHTML(item.entrada)}${imp}${horas}${score}</div>
    </div>`;
  }

  function escapeHTML(s) {
    const d = document.createElement("div");
    d.textContent = String(s ?? "");
    return d.innerHTML;
  }

  function renderBoard() {
    let html = '<div class="kb-board">';
    state.board.colunas.forEach((col, i) => {
      const itens = col.items.filter(passaFiltro);
      const cards = itens.map(cardHTML).join("") || '<div class="kb-empty">Sem itens</div>';
      html += `<div class="kb-col" data-estado="${col.estado}">
        <div class="kb-head" style="background:${CORES[i % CORES.length]}">
          ${col.estado.toUpperCase()} (${itens.length})
        </div>
        <div class="kb-body">${cards}</div>
      </div>`;
    });
    html += "</div>";
    boardEl.innerHTML = html;
    wireBoard();
  }

  function wireBoard() {
    boardEl.querySelectorAll(".kb-card").forEach((card) => {
      const id = card.getAttribute("data-id");
      const tipo = card.getAttribute("data-tipo");
      card.addEventListener("dragstart", () => {
        state.dragId = id; state.dragType = tipo;
        card.classList.add("kb-drag");
      });
      card.addEventListener("dragend", () => card.classList.remove("kb-drag"));
      card.addEventListener("click", () => {
        if (tipo === "D") abrirCard(Number(id));
      });
    });
    boardEl.querySelectorAll(".kb-col").forEach((col) => {
      const estado = col.getAttribute("data-estado");
      col.addEventListener("dragover", (e) => { e.preventDefault(); col.classList.add("kb-over"); });
      col.addEventListener("dragleave", () => col.classList.remove("kb-over"));
      col.addEventListener("drop", async (e) => {
        e.preventDefault();
        col.classList.remove("kb-over");
        if (state.dragId === null) return;
        await fetch("/api/kanban/mover", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tipo: state.dragType, id: Number(state.dragId), estado }),
        });
        state.dragId = null; state.dragType = null;
        flash("Status atualizado!");
        carregarBoard();
      });
    });
  }

  // ── Modal de detalhes do card ────────────────────────────────────────────
  function preencherSelects() {
    const respSel = $("#card-responsavel");
    respSel.innerHTML = ['<option value=""></option>'].concat(
      state.board.apelidos.map((a) => `<option value="${a}">${a}</option>`)
    ).join("");

    const statusSel = $("#card-status");
    statusSel.innerHTML = state.board.estados.map((e) => `<option value="${e}">${e}</option>`).join("");

    const tipoSel = $("#card-tipo");
    tipoSel.innerHTML = state.board.tipos_entrada.map((t) => `<option value="${t}">${t}</option>`).join("");

    $("#ativ-resp").innerHTML = ['<option value=""></option>'].concat(
      state.board.apelidos.map((a) => `<option value="${a}">${a}</option>`)
    ).join("");
    const tipoDefault = state.board.tipos_entrada.includes("Interna") ? "Interna" : state.board.tipos_entrada[0];
    $("#ativ-tipo").innerHTML = state.board.tipos_entrada
      .map((t) => `<option value="${t}" ${t === tipoDefault ? "selected" : ""}>${t}</option>`).join("");
  }

  async function abrirCard(id) {
    const resp = await fetch(`/api/kanban/card/${id}`);
    if (!resp.ok) { flash("Demanda não encontrada."); return; }
    const d = await resp.json();
    state.cardId = id;

    $("#card-titulo").textContent = `📋 D${id} · ${d.titulo}`;
    $("#card-meta").innerHTML = `
      <div><b>Estado (Trace)</b>${escapeHTML(d.estado || "—")}</div>
      <div><b>Prioridade</b>${escapeHTML(d.prioridade || "—")}</div>
      <div><b>Macroprocesso</b>${escapeHTML(d.macroprocesso || "—")}</div>
      <div><b>Sistema</b>${escapeHTML(d.sistema || "—")}</div>`;

    $("#card-responsavel").value = d.responsavel_sprint || "";
    $("#card-status").value = d.status_kanban || state.board.estados[0];
    $("#card-tipo").value = d.tipo_entrada || "Planejada";
    $("#card-horas").value = d.horas_trabalhadas || 0;
    $("#card-impedimento").value = (d.impedimento && d.impedimento.toLowerCase() !== "nan") ? d.impedimento : "";
    $("#card-observacoes").value = d.observacoes || "";
    $("#card-descricao").value = d.descricao_interna || "";

    const info = [];
    if (d.solicitante) info.push(`<b>Solicitante:</b> ${escapeHTML(d.solicitante)}`);
    if (d.responsavel_atendimento) info.push(`<b>Resp. atendimento:</b> ${escapeHTML(d.responsavel_atendimento)}`);
    if (d.data_criacao) info.push(`<b>Criado em:</b> ${escapeHTML(String(d.data_criacao).slice(0, 10))}`);
    if (d.score) info.push(`<b>Score:</b> ${Number(d.score).toFixed(1)}`);
    $("#card-info").innerHTML = info.join("  ·  ");

    $("#card-conf-remover").checked = false;
    $("#card-remover").disabled = true;

    $("#modal-card").showModal();
  }

  $("#card-fechar").addEventListener("click", () => $("#modal-card").close());
  $("#card-conf-remover").addEventListener("change", (e) => {
    $("#card-remover").disabled = !e.target.checked;
  });

  $("#card-salvar").addEventListener("click", async () => {
    await fetch(`/api/kanban/card/${state.cardId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        responsavel_sprint: $("#card-responsavel").value,
        status_kanban: $("#card-status").value,
        tipo_entrada: $("#card-tipo").value,
        impedimento: $("#card-impedimento").value,
        observacoes: $("#card-observacoes").value,
        horas_trabalhadas: parseFloat($("#card-horas").value || "0"),
        descricao_interna: $("#card-descricao").value,
      }),
    });
    $("#modal-card").close();
    flash(`Card D${state.cardId} atualizado.`);
    carregarBoard();
  });

  $("#card-remover").addEventListener("click", async () => {
    await fetch(`/api/kanban/card/${state.cardId}/voltar-backlog`, { method: "POST" });
    $("#modal-card").close();
    flash(`Demanda D${state.cardId} voltou para o Backlog.`);
    carregarBoard();
  });

  // ── Nova atividade interna ───────────────────────────────────────────────
  $("#btn-nova-atividade").addEventListener("click", () => {
    $("#popover-atividade").hidden = !$("#popover-atividade").hidden;
  });
  $("#ativ-titulo").addEventListener("input", (e) => {
    $("#ativ-criar").disabled = !e.target.value.trim();
  });
  $("#ativ-criar").addEventListener("click", async () => {
    const titulo = $("#ativ-titulo").value.trim();
    if (!titulo) return;
    await fetch("/api/kanban/atividades", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        titulo,
        responsavel: $("#ativ-resp").value,
        tipo: $("#ativ-tipo").value,
      }),
    });
    $("#ativ-titulo").value = "";
    $("#ativ-criar").disabled = true;
    $("#popover-atividade").hidden = true;
    flash(`Atividade '${titulo}' criada.`);
    carregarBoard();
  });

  // ── Modo Daily ────────────────────────────────────────────────────────────
  const STATUS_COR = {
    "sprint": ["#d0ebff", "#1864ab"], "em and": ["#fff3bf", "#e67700"],
    "pendente": ["#ffe3e3", "#c92a2a"], "homolog": ["#ffe8cc", "#d9480f"],
    "conclu": ["#d3f9d8", "#2b8a3e"],
  };
  function corStatus(status) {
    const v = (status || "").toLowerCase();
    for (const chave in STATUS_COR) {
      if (v.includes(chave)) return STATUS_COR[chave];
    }
    return null;
  }

  async function carregarDaily() {
    const resp = await fetch("/api/kanban/daily");
    if (resp.status === 401) { window.location.href = "/login"; return; }
    const dados = await resp.json();
    if (!dados.sprint) {
      dailyEl.innerHTML = '<p class="gp-caption">Não existe nenhuma sprint em andamento.</p>';
      return;
    }
    let html = `<table class="kb-daily-table"><thead><tr>
      <th>Id</th><th>Título</th><th>Responsável</th><th>Status</th><th>Impedimento</th>
      </tr></thead><tbody>`;
    dados.linhas.forEach((l) => {
      const cor = corStatus(l.status);
      const badge = cor
        ? `<span class="kb-status-badge" style="background:${cor[0]};color:${cor[1]}">${escapeHTML(l.status)}</span>`
        : escapeHTML(l.status);
      html += `<tr>
        <td>${l.tipo}${l.id}</td>
        <td>${escapeHTML(l.titulo)}</td>
        <td>${escapeHTML(l.responsavel)}</td>
        <td>${badge}</td>
        <td data-sort="${escapeHTML(l.impedimento)}"><input type="text" value="${escapeHTML(l.impedimento)}" data-tipo="${l.tipo}" data-id="${l.id}"></td>
      </tr>`;
    });
    html += "</tbody></table>";
    dailyEl.innerHTML = html;
    gpMakeSortable(dailyEl.querySelector("table"));
    gpSyncDataSort(dailyEl);
    dailyEl.querySelectorAll("input[type=text]").forEach((inp) => {
      inp.addEventListener("change", async () => {
        await fetch("/api/kanban/impedimento", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tipo: inp.dataset.tipo, id: Number(inp.dataset.id), impedimento: inp.value }),
        });
        flash("Impedimento atualizado.");
      });
    });
  }

  $("#toggle-daily").addEventListener("change", (e) => {
    const daily = e.target.checked;
    boardEl.hidden = daily;
    dailyEl.hidden = !daily;
    $(".kb-toolbar").querySelectorAll(".kb-filtro, #btn-nova-atividade").forEach((el) => {
      el.style.display = daily ? "none" : "";
    });
    if (daily) carregarDaily();
  });

  carregarBoard();
})();
