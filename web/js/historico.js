(function () {
  "use strict";

  document.getElementById("btn-logout").addEventListener("click", async (e) => {
    e.preventDefault();
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
  });

  const lista = document.getElementById("lista-sprints");
  const flash = document.getElementById("flash");

  function mostrarFlash(msg) {
    flash.textContent = msg;
    flash.hidden = false;
    setTimeout(() => { flash.hidden = true; }, 3500);
  }

  function escapeHTML(s) {
    const d = document.createElement("div");
    d.textContent = String(s ?? "");
    return d.innerHTML;
  }

  function badgeStatus(status) {
    const v = (status || "").toLowerCase();
    let cls = "gp-badge-int";
    if (v.includes("conclu")) cls = "gp-badge-conclu";
    else if (v.includes("and")) cls = "gp-badge-and";
    else if (v.includes("sprint")) cls = "gp-badge-sprint";
    return `<span class="gp-badge ${cls}">${escapeHTML(status)}</span>`;
  }

  function tabelaItens(itens) {
    if (!itens.length) return '<p class="gp-caption">Nenhum item</p>';
    let html = '<table class="gp-table"><thead><tr><th>Id</th><th>Título</th><th>Status final</th></tr></thead><tbody>';
    itens.forEach((i) => {
      html += `<tr><td>${i.id ?? "—"}</td><td>${escapeHTML(i.titulo)}</td><td>${badgeStatus(i.status_final)}</td></tr>`;
    });
    return html + "</tbody></table>";
  }

  function metrica(valor, rotulo) {
    return `<div class="gp-metric"><div class="valor">${valor}</div><div class="rotulo">${rotulo}</div></div>`;
  }

  function blocoSprint(s) {
    return `
      <details class="gp-expander">
        <summary>🏁 ${escapeHTML(s.nome)} — encerrada em ${escapeHTML(s.encerrada_em || "—")}</summary>
        ${s.meta ? `<div class="gp-flash" style="background:#d0ebff;color:#1864ab;">🎯 Meta: ${escapeHTML(s.meta)}</div>` : ""}
        <div class="gp-metrics">
          ${metrica(s.total, "Total")}
          ${metrica(s.planejadas, "Planejadas")}
          ${metrica(s.paraquedas, "Paraquedas")}
          ${metrica(s.internas, "Internas")}
          ${metrica(s.concluidas, "Concluídas")}
          ${metrica(s.pct_conclusao + "%", "% Conclusão")}
        </div>
        <p class="gp-caption">
          Planejado x Executado: ${s.planejadas} planejadas, ${s.concluidas} concluídas ao todo (${s.pct_conclusao}%).
          Planejado x Paraquedas: de ${s.total} itens, ${s.paraquedas} entraram depois do início (${s.pct_paraquedas}% de impacto).
        </p>
        <h3>Lições aprendidas</h3>
        <div class="gp-form-grid-2" style="grid-template-columns:1fr 1fr 1fr;">
          <div><b>✅ O que funcionou bem</b><p class="gp-caption">${escapeHTML(s.retro_bem) || "<em>não preenchido</em>"}</p></div>
          <div><b>⚠️ O que dificultou</b><p class="gp-caption">${escapeHTML(s.retro_dificultou) || "<em>não preenchido</em>"}</p></div>
          <div><b>🎯 Ações p/ próxima sprint</b><p class="gp-caption">${escapeHTML(s.retro_acoes) || "<em>não preenchido</em>"}</p></div>
        </div>
        <h3>Demandas planejadas</h3>
        ${tabelaItens(s.planejadas_itens)}
        <h3>Demandas Paraquedas <span class="gp-caption">(adicionadas após o início da sprint)</span></h3>
        ${tabelaItens(s.paraquedas_itens)}
        ${s.internas ? `<h3>Demandas internas</h3>${tabelaItens(s.internas_itens)}` : ""}
        <hr>
        <label class="gp-checkbox-row">
          <input type="checkbox" class="conf-excluir" data-id="${s.id}">
          Sim, quero excluir esta sprint do histórico
        </label>
        <button type="button" class="btn-excluir" data-id="${s.id}" disabled>🗑️ Excluir esta sprint do histórico</button>
      </details>`;
  }

  async function carregar() {
    const resp = await fetch("/api/historico");
    if (resp.status === 401) { window.location.href = "/login"; return; }
    const sprints = await resp.json();

    if (!sprints.length) {
      lista.innerHTML = '<p class="gp-caption">Nenhuma sprint encerrada ainda.</p>';
      return;
    }
    lista.innerHTML = sprints.map(blocoSprint).join("");

    lista.querySelectorAll("table.gp-table").forEach((t) => gpMakeSortable(t));

    lista.querySelectorAll(".conf-excluir").forEach((cb) => {
      cb.addEventListener("change", (e) => {
        const btn = lista.querySelector(`.btn-excluir[data-id="${cb.dataset.id}"]`);
        btn.disabled = !e.target.checked;
      });
    });
    lista.querySelectorAll(".btn-excluir").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const resp = await fetch(`/api/historico/sprint/${btn.dataset.id}`, { method: "DELETE" });
        if (resp.ok) {
          mostrarFlash("🗑️ Sprint excluída do histórico.");
          carregar();
        } else {
          mostrarFlash("Não foi possível excluir.");
        }
      });
    });
  }

  carregar();
})();
