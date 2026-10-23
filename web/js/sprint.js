(function () {
  "use strict";

  const el = (id) => document.getElementById(id);
  el("btn-logout").addEventListener("click", async (e) => {
    e.preventDefault();
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
  });

  function escapeHTML(s) {
    const d = document.createElement("div");
    d.textContent = String(s ?? "");
    return d.innerHTML;
  }
  function flash(msg) {
    el("flash").textContent = msg;
    el("flash").hidden = false;
    setTimeout(() => { el("flash").hidden = true; }, 3500);
  }
  function flashErro(msg) {
    el("flash-erro").textContent = msg;
    el("flash-erro").hidden = false;
    setTimeout(() => { el("flash-erro").hidden = true; }, 4500);
  }
  function opcoes(lista, atual) {
    return lista.map((v) => `<option value="${v}" ${v === atual ? "selected" : ""}>${v}</option>`).join("");
  }

  let estadoItens = { apelidos: [], estados: [], tipos_entrada: [] };
  let pendentesAnteriores = [];
  let atividadesAtuais = [];
  gpMakeSortable(document.getElementById("tabela-demandas"));
  gpMakeSortable(document.getElementById("tabela-atividades"));

  // ── Cabeçalho / criação ──────────────────────────────────────────────────
  async function carregarSprint() {
    const resp = await fetch("/api/sprint");
    if (resp.status === 401) { window.location.href = "/login"; return; }
    const dados = await resp.json();

    if (!dados.sprint) {
      el("sem-sprint").hidden = false;
      el("com-sprint").hidden = true;
      el("ns-velocidade").textContent = dados.velocidade_media
        ? `📈 Velocidade média das últimas sprints: ~${dados.velocidade_media} demanda(s) concluída(s) por sprint. Use como referência de quantas puxar.`
        : "";

      const sugestao = el("sugestao-pendentes");
      sugestao.hidden = pendentesAnteriores.length === 0;
      if (pendentesAnteriores.length) {
        el("sp-qtd-pendentes").textContent = pendentesAnteriores.length;
        el("sp-lista-pendentes").innerHTML = pendentesAnteriores
          .map((p) => `<li>#${p.id} — ${escapeHTML(p.titulo)}</li>`).join("");
      }

      const transp = dados.atividades_transportar || [];
      el("sugestao-atividades").hidden = transp.length === 0;
      if (transp.length) {
        el("sp-qtd-ativ-transp").textContent = transp.length;
        el("sp-lista-ativ-transp").innerHTML = transp
          .map((a) => `<li>${escapeHTML(a.titulo)}${a.responsavel ? ` · ${escapeHTML(a.responsavel)}` : ""}</li>`).join("");
      }
      return;
    }

    el("sem-sprint").hidden = true;
    el("com-sprint").hidden = false;

    const s = dados.sprint;
    el("sp-nome").textContent = s.nome;
    el("sp-badge").textContent = s.em_andamento ? "🏃 Em andamento" : "🗓️ Em planejamento";
    el("btn-iniciar").hidden = s.em_andamento;

    el("sp-metrics-header").innerHTML = [
      [`${s.data_inicio || "—"} → ${s.data_fim || "—"}`, "Período"],
      [dados.dias_restantes ?? "—", "Dias restantes"],
      [dados.qtd_total, "Demandas"],
      [dados.qtd_planejadas, "Planejadas"],
      [dados.qtd_paraquedas, "Paraquedas"],
      [dados.qtd_internas, "Internas"],
    ].map(([v, r]) => `<div class="gp-metric"><div class="valor">${v}</div><div class="rotulo">${r}</div></div>`).join("");

    el("exp-meta").querySelector("summary").textContent = "🎯 Meta da sprint" + (s.meta ? ` — ${s.meta}` : " (não definida)");
    el("sp-meta-texto").value = s.meta || "";
    if (!s.meta) el("exp-meta").open = true;

    if (dados.velocidade_media) {
      const acima = dados.qtd_total > dados.velocidade_media * 1.2;
      if (acima) {
        el("sp-capacidade").hidden = false;
        el("sp-capacidade").textContent =
          `📈 Capacidade: esta sprint tem ${dados.qtd_total} demanda(s), acima da sua velocidade média (~${dados.velocidade_media} concluída(s) por sprint). Risco de sobrecarga.`;
      } else {
        el("sp-capacidade").hidden = true;
      }
    }

    await carregarItens();
    await carregarMetricas();
  }

  document.getElementById("form-nova-sprint").addEventListener("submit", async (e) => {
    e.preventDefault();
    const incluirPendentes = pendentesAnteriores.length > 0 && el("ns-incluir-pendentes").checked;
    const corpoBase = {
      nome: el("ns-nome").value, meta: el("ns-meta").value,
      data_inicio: el("ns-inicio").value || null, data_fim: el("ns-fim").value || null,
    };

    let resp, dados;
    if (incluirPendentes) {
      const linhas = pendentesAnteriores.map((p) => ({ id: p.id, tipo_entrada: p.tipo_entrada, responsavel: p.responsavel, status: p.status }));
      resp = await fetch("/api/backlog/criar-sprint-enviar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...corpoBase, linhas }),
      });
      dados = await resp.json();
    } else {
      resp = await fetch("/api/sprint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpoBase),
      });
      dados = await resp.json();
    }

    if (resp.ok && dados.ok) {
      pendentesAnteriores = [];
      const msg = incluirPendentes
        ? `Sprint criada com ${dados.enviadas} demanda(s) da sprint anterior! Clique em ▶️ Iniciar quando estiver pronta.`
        : "Sprint criada em planejamento! Envie demandas pela página Backlog e clique em ▶️ Iniciar quando estiver pronta.";
      flash(msg);
      carregarSprint();
    } else {
      flashErro(dados.erro || "Não foi possível criar a sprint.");
    }
  });

  el("btn-iniciar").addEventListener("click", async () => {
    const resp = await fetch("/api/sprint/iniciar", { method: "POST" });
    if (resp.ok) {
      flash("Sprint iniciada! Demandas adicionadas a partir de agora entram como Paraquedas.");
      carregarSprint();
    }
  });

  el("btn-salvar-meta").addEventListener("click", async () => {
    const resp = await fetch("/api/sprint/meta", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ meta: el("sp-meta-texto").value }),
    });
    if (resp.ok) { flash("Meta da sprint atualizada."); carregarSprint(); }
  });

  // ── Itens (demandas + atividades) ────────────────────────────────────────
  async function carregarItens() {
    const resp = await fetch("/api/sprint/itens");
    const dados = await resp.json();
    estadoItens = dados;

    el("ativ-resp").innerHTML = ['<option value=""></option>'].concat(opcoes(dados.apelidos, "")).join("");
    el("ativ-tipo").innerHTML = opcoes(dados.tipos_entrada, dados.tipos_entrada.includes("Interna") ? "Interna" : dados.tipos_entrada[0]);

    const semNada = dados.demandas.length === 0 && dados.atividades.length === 0;
    el("sem-itens").hidden = !semNada;
    el("bloco-demandas").hidden = dados.demandas.length === 0;
    el("bloco-atividades").hidden = dados.atividades.length === 0;

    const tbodyDem = document.querySelector("#tabela-demandas tbody");
    tbodyDem.innerHTML = dados.demandas.map((d) => `
      <tr data-id="${d.id}">
        <td><input type="checkbox" class="sel-demanda"></td>
        <td>${d.id}</td>
        <td>${escapeHTML(d.titulo)}</td>
        <td>${escapeHTML(d.tipo_exibicao)}</td>
        <td data-sort="${escapeHTML(d.tipo_entrada)}"><select class="f-tipo-entrada">${opcoes(dados.tipos_entrada, d.tipo_entrada)}</select></td>
        <td data-sort="${escapeHTML(d.responsavel)}"><select class="f-responsavel">${['<option value=""></option>'].concat(opcoes(dados.apelidos, d.responsavel)).join("")}</select></td>
        <td data-sort="${escapeHTML(d.status)}"><select class="f-status">${opcoes(dados.estados, d.status)}</select></td>
        <td data-sort="${escapeHTML(d.impedimento)}"><input type="text" class="f-impedimento" value="${escapeHTML(d.impedimento)}"></td>
        <td data-sort="${escapeHTML(d.data_importacao || "")}" data-sort-tipo="data-br">${escapeHTML(d.data_importacao || "—")}</td>
        <td>
          <button type="button" class="sp-btn-encerrar" title="Marcar como Concluído">✅</button>
          <button type="button" class="sp-btn-excluir" title="Excluir (só se nunca passou por sprint)">🗑️</button>
        </td>
      </tr>`).join("");

    tbodyDem.querySelectorAll(".sel-demanda").forEach((cb) => cb.addEventListener("change", atualizarContadorRemover));
    tbodyDem.querySelectorAll("tr").forEach((tr) => {
      const id = Number(tr.dataset.id);
      tr.querySelector(".sp-btn-encerrar").addEventListener("click", () => encerrarDemandaSprint(id));
      tr.querySelector(".sp-btn-excluir").addEventListener("click", () => excluirDemandaSprint(id));
    });
    gpSyncDataSort(tbodyDem);

    atividadesAtuais = dados.atividades;
    renderAtividadesEncerramento();

    const tbodyAtiv = document.querySelector("#tabela-atividades tbody");
    tbodyAtiv.innerHTML = dados.atividades.map((a) => `
      <tr data-id="${a.id}">
        <td><input type="checkbox" class="sel-atividade"></td>
        <td>${a.id}</td>
        <td data-sort="${escapeHTML(a.titulo)}"><input type="text" class="f-titulo" value="${escapeHTML(a.titulo)}"></td>
        <td data-sort="${escapeHTML(a.tipo_entrada)}"><select class="f-tipo-entrada">${opcoes(dados.tipos_entrada, a.tipo_entrada)}</select></td>
        <td data-sort="${escapeHTML(a.responsavel)}"><select class="f-responsavel">${['<option value=""></option>'].concat(opcoes(dados.apelidos, a.responsavel)).join("")}</select></td>
        <td data-sort="${escapeHTML(a.status)}"><select class="f-status">${opcoes(dados.estados, a.status)}</select></td>
      </tr>`).join("");
    gpSyncDataSort(tbodyAtiv);
  }

  async function encerrarDemandaSprint(id) {
    const resp = await fetch(`/api/demandas/${id}/concluir`, { method: "POST" });
    if (resp.ok) {
      flash(`✅ Demanda ${id} marcada como Concluído.`);
      carregarItens();
    } else {
      flashErro(`Não foi possível encerrar a demanda ${id}.`);
    }
  }

  async function excluirDemandaSprint(id) {
    if (!confirm(`Excluir a demanda ${id} de vez? Essa ação não tem volta.`)) return;
    const resp = await fetch(`/api/demandas/${id}`, { method: "DELETE" });
    const dados = await resp.json();
    if (resp.ok && dados.ok) {
      flash(`🗑️ Demanda ${id} excluída.`);
      carregarItens();
    } else {
      flashErro(dados.erro || `Não foi possível excluir a demanda ${id}.`);
    }
  }

  function atualizarContadorRemover() {
    const n = document.querySelectorAll("#tabela-demandas .sel-demanda:checked").length;
    const btn = el("btn-remover-demandas");
    btn.textContent = `🗑️ Remover marcadas da sprint (${n})`;
    btn.disabled = n === 0;
  }

  el("btn-salvar-demandas").addEventListener("click", async () => {
    const linhas = document.querySelectorAll("#tabela-demandas tbody tr");
    for (const tr of linhas) {
      await fetch(`/api/sprint/demanda/${tr.dataset.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tipo_entrada: tr.querySelector(".f-tipo-entrada").value,
          responsavel: tr.querySelector(".f-responsavel").value,
          status: tr.querySelector(".f-status").value,
          impedimento: tr.querySelector(".f-impedimento").value,
        }),
      });
    }
    flash("Sprint salva!");
    carregarSprint();
  });

  el("btn-remover-demandas").addEventListener("click", async () => {
    const ids = Array.from(document.querySelectorAll("#tabela-demandas .sel-demanda:checked"))
      .map((cb) => Number(cb.closest("tr").dataset.id));
    if (!ids.length) return;
    await fetch("/api/sprint/demandas/remover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
    flash(`${ids.length} demanda(s) removida(s) — voltaram para o Backlog.`);
    carregarSprint();
  });

  el("ativ-titulo").addEventListener("input", (e) => { el("ativ-criar").disabled = !e.target.value.trim(); });
  el("ativ-criar").addEventListener("click", async () => {
    const titulo = el("ativ-titulo").value.trim();
    const resp = await fetch("/api/sprint/atividade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ titulo, responsavel: el("ativ-resp").value, tipo_entrada: el("ativ-tipo").value }),
    });
    if (resp.ok) {
      el("ativ-titulo").value = "";
      el("ativ-criar").disabled = true;
      flash(`✅ Atividade '${titulo}' adicionada! Ela aparece na seção 'Atividades internas' abaixo e no Kanban (coluna Sprint).`);
      carregarSprint();
    }
  });

  el("btn-salvar-atividades").addEventListener("click", async () => {
    const linhas = Array.from(document.querySelectorAll("#tabela-atividades tbody tr"));
    for (const tr of linhas) {
      await fetch(`/api/sprint/atividade/${tr.dataset.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          titulo: tr.querySelector(".f-titulo").value,
          tipo_entrada: tr.querySelector(".f-tipo-entrada").value,
          responsavel: tr.querySelector(".f-responsavel").value,
          status: tr.querySelector(".f-status").value,
        }),
      });
    }
    const marcadas = linhas.filter((tr) => tr.querySelector(".sel-atividade").checked);
    for (const tr of marcadas) {
      await fetch(`/api/sprint/atividade/${tr.dataset.id}`, { method: "DELETE" });
    }
    let msg = "✅ Atividades salvas!";
    if (marcadas.length) msg += ` (${marcadas.length} removida(s))`;
    flash(msg);
    carregarSprint();
  });

  // ── Métricas ─────────────────────────────────────────────────────────────
  async function carregarMetricas() {
    const resp = await fetch("/api/sprint/metricas");
    if (!resp.ok) return;
    const m = await resp.json();
    el("sp-metricas").innerHTML = [
      [`${m.recorrencia.recorrentes} de ${m.recorrencia.total}`, "🔁 Demandas recorrentes"],
      [`${m.conclusao.percentual.toFixed(0)}%`, `✅ Taxa de conclusão (${m.conclusao.concluidos} de ${m.conclusao.total})`],
      [m.lead_time !== null ? `${m.lead_time} dias` : "—", "⏱️ Lead time médio"],
    ].map(([v, r]) => `<div class="gp-metric"><div class="valor">${v}</div><div class="rotulo">${r}</div></div>`).join("");
  }

  // ── Encerrar / excluir ───────────────────────────────────────────────────
  function renderAtividadesEncerramento() {
    el("enc-bloco-atividades").hidden = atividadesAtuais.length === 0;
    el("enc-ativ-todas").checked = false;
    el("enc-lista-atividades").innerHTML = atividadesAtuais.map((a) => `
      <label class="gp-checkbox-row"><input type="checkbox" class="enc-ativ" value="${a.id}">
        ${escapeHTML(a.titulo)} <span class="gp-caption">· ${escapeHTML(a.status)}${a.responsavel ? ` · ${escapeHTML(a.responsavel)}` : ""}</span></label>`).join("");
  }
  el("enc-ativ-todas").addEventListener("change", (e) => {
    document.querySelectorAll("#enc-lista-atividades .enc-ativ").forEach((c) => { c.checked = e.target.checked; });
  });

  el("btn-abrir-encerrar").addEventListener("click", () => {
    el("popover-encerrar").hidden = !el("popover-encerrar").hidden;
  });
  el("btn-confirmar-encerramento").addEventListener("click", async () => {
    const resp = await fetch("/api/sprint/encerrar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        retro_bem: el("retro-bem").value, retro_dificultou: el("retro-dificultou").value, retro_acoes: el("retro-acoes").value,
        atividades_transportar: Array.from(document.querySelectorAll("#enc-lista-atividades .enc-ativ:checked")).map((c) => Number(c.value)),
      }),
    });
    const dados = await resp.json();
    if (resp.ok && dados.ok) {
      const r = dados.resumo;
      pendentesAnteriores = r.itens_pendentes || [];
      flash(`🏁 Sprint encerrada! Planejadas: ${r.planejadas} · Paraquedas: ${r.paraquedas} · Internas: ${r.internas} · Concluídas: ${r.concluidas} · Pendentes: ${r.pendentes} (voltaram para o Backlog)` +
        (r.internas_transportadas ? ` · Atividades internas para a próxima sprint: ${r.internas_transportadas}.` : "."));
      el("popover-encerrar").hidden = true;
      carregarSprint();
    } else {
      flashErro(dados.erro || "Não foi possível encerrar a sprint.");
    }
  });

  el("conf-excluir-sprint").addEventListener("change", (e) => {
    el("btn-excluir-sprint").disabled = !e.target.checked;
  });
  el("btn-excluir-sprint").addEventListener("click", async () => {
    const resp = await fetch("/api/sprint", { method: "DELETE" });
    if (resp.ok) {
      flash("🗑️ Sprint excluída. As demandas voltaram para o Backlog.");
      carregarSprint();
    } else {
      flashErro("Não foi possível excluir a sprint.");
    }
  });

  carregarSprint();
})();
