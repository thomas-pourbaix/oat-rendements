/* Copyright (C) 2026 Thomas Pourbaix
   SPDX-License-Identifier: AGPL-3.0-only */

const KIND_LABEL = { strip: "strip", inflation_euro: "OAT€i", inflation_france: "OATi" };
const STALE_DAYS = 30;

const $ = (sel) => document.querySelector(sel);
const pct = (x, d = 2) => (x * 100).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d }) + " %";
const num = (x, d = 2) => x.toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
const dateFr = (iso) => new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });

let data = null;
let sort = { key: "ytm", dir: -1 };

function label(b) {
  const month = new Date(b.maturity).toLocaleDateString("fr-FR", { month: "short", year: "numeric" });
  return b.kind === "strip" ? `Strip ${month}` : `OAT ${num(b.coupon, b.coupon % 1 ? 2 : 0)} % ${month}`;
}

function ageDays(iso) {
  return iso ? (Date.now() - new Date(iso).getTime()) / 864e5 : Infinity;
}

function filtered() {
  const n = +$("#n").value;
  const w = $("#w").value;
  const kinds = new Set([...document.querySelectorAll("input[name=kind]:checked")].map((c) => c.value));
  const fresh = $("#fresh").checked;
  return data.bonds.filter((b) =>
    kinds.has(b.kind) &&
    (!fresh || ageDays(b.last_trade) <= STALE_DAYS) &&
    (w === "all" || Math.abs(b.years - n) <= +w)
  );
}

function sorted(rows) {
  const { key, dir } = sort;
  return [...rows].sort((a, b) => {
    const x = a[key] ?? "", y = b[key] ?? "";
    return (x < y ? -1 : x > y ? 1 : 0) * dir;
  });
}

function render() {
  $("#n-out").textContent = $("#n").value;
  const rows = sorted(filtered());
  const best = rows.length ? Math.max(...rows.map((b) => b.ytm)) : null;
  const tbody = $("#table tbody");

  tbody.innerHTML = rows.length ? rows.map((b) => {
    const stale = ageDays(b.last_trade) > 7;
    const tag = KIND_LABEL[b.kind] ? `<span class="tag">${KIND_LABEL[b.kind]}</span>` : "";
    const final = 1000 * Math.pow(1 + b.ytm, b.years);
    return `<tr class="${b.ytm === best ? "best" : ""}">
      <td><a href="${b.url}" target="_blank" rel="noopener" title="${b.name}">${label(b)}</a>${tag}<button type="button" class="isin" data-isin="${b.isin}" title="Copier l'ISIN" aria-label="Copier l'ISIN ${b.isin}">${b.isin}</button></td>
      <td>${dateFr(b.maturity)}</td>
      <td class="num">${num(b.years, 1)} ans</td>
      <td class="num">${num(b.coupon, 2)} %</td>
      <td class="num">${num(b.price, 2)} %</td>
      <td class="${stale ? "stale" : ""}" title="${stale ? "Cours ancien : peu représentatif du prix actuel" : ""}">${b.last_trade ? dateFr(b.last_trade) : "–"}</td>
      <td class="num ytm">${pct(b.ytm)}${b.kind.startsWith("inflation") ? " réel" : ""}</td>
      <td class="num">${Math.round(final).toLocaleString("fr-FR")} €</td>
    </tr>`;
  }).join("") : `<tr><td colspan="8" class="empty">Aucune OAT cotée pour cet horizon. Élargissez la fenêtre ou cochez d'autres types de titres.</td></tr>`;

  const w = $("#w").value;
  const scope = w === "all" ? "toutes échéances" : `échéance à ${$("#n").value} ans ± ${w === "0.5" ? "6 mois" : w + " an" + (w > 1 ? "s" : "")}`;
  $("#summary").innerHTML = rows.length
    ? `<strong>${rows.length}</strong> titre${rows.length > 1 ? "s" : ""} (${scope}). Meilleur rendement : <strong>${pct(best)}</strong>.`
    : `Aucun titre (${scope}).`;

  document.querySelectorAll("th").forEach((th) => th.removeAttribute("aria-sort"));
  const th = document.querySelector(`th[data-key="${sort.key}"]`);
  if (th) th.setAttribute("aria-sort", sort.dir > 0 ? "ascending" : "descending");
}

document.querySelectorAll("th[data-key]").forEach((th) =>
  th.addEventListener("click", () => {
    const key = th.dataset.key;
    sort = { key, dir: sort.key === key ? -sort.dir : key === "ytm" ? -1 : 1 };
    render();
  })
);
document.querySelectorAll("#panel-table input, #panel-table select").forEach((el) => el.addEventListener("input", render));

function showTab(name) {
  const calc = name === "calc";
  $("#tab-table").setAttribute("aria-selected", String(!calc));
  $("#tab-calc").setAttribute("aria-selected", String(calc));
  $("#panel-table").hidden = calc;
  $("#panel-calc").hidden = !calc;
}

$("#tab-table").addEventListener("click", () => { history.replaceState(null, "", location.pathname); showTab("table"); });
$("#tab-calc").addEventListener("click", () => { history.replaceState(null, "", "#calcul"); showTab("calc"); });
if (location.hash === "#calcul") showTab("calc");

const ISIN_RE = /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/;

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function parsePrice(text) {
  const clean = text.replace(/[\s%]/g, "").replace(",", ".");
  return /^\d+(\.\d+)?$/.test(clean) ? parseFloat(clean) : null;
}

function renderCalc() {
  const out = $("#calc-result");
  const isin = $("#calc-isin").value.replace(/\s/g, "").toUpperCase();
  const priceText = $("#calc-price").value.trim();
  const feeText = $("#calc-fee").value.trim();
  if (!isin) { out.innerHTML = ""; return; }
  if (!ISIN_RE.test(isin)) { out.innerHTML = `<p class="calc-msg">ISIN incomplet ou invalide : 12 caractères, par exemple FR0014016G71.</p>`; return; }
  if (!data) { out.innerHTML = `<p class="calc-msg">Chargement des données…</p>`; return; }
  const b = data.bonds.find((x) => x.isin === isin);
  if (!b) { out.innerHTML = `<p class="calc-msg">Cet ISIN ne figure pas parmi les OAT cotées sur Euronext Paris.</p>`; return; }

  const settlement = Yields.addBusinessDays(todayIso(), 2);
  const head = `<p class="calc-bond"><strong>${label(b)}</strong>${KIND_LABEL[b.kind] ? `<span class="tag">${KIND_LABEL[b.kind]}</span>` : ""} · échéance le ${dateFr(b.maturity)}</p>`;
  if (b.maturity <= settlement) { out.innerHTML = head + `<p class="calc-msg">Ce titre arrive à échéance avant le règlement d'un achat fait aujourd'hui.</p>`; return; }
  if (!priceText) { out.innerHTML = head + `<p class="calc-msg">Saisissez votre cours d'achat. Dernier cours coté : ${num(b.price, 2)} %.</p>`; return; }
  const price = parsePrice(priceText);
  if (price === null || price <= 0) { out.innerHTML = head + `<p class="calc-msg">Cours invalide : saisissez un nombre en % du nominal, par exemple 96,25.</p>`; return; }
  const feePct = feeText ? parsePrice(feeText) : 0;
  if (feePct === null || feePct >= 100) { out.innerHTML = head + `<p class="calc-msg">Frais invalides : saisissez un pourcentage, par exemple 0,2, ou laissez le champ vide.</p>`; return; }
  const fee = feePct / 100;

  const ytm = Yields.yieldToMaturity(price, b.coupon, settlement, b.maturity);
  const accrued = Yields.accruedInterest(b.coupon, settlement, b.maturity);
  const years = (Date.parse(b.maturity) - Date.parse(settlement)) / 864e5 / 365.25;
  const real = b.kind.startsWith("inflation") ? " réel" : "";
  const cost = Yields.totalCost(price, fee, b.coupon, settlement, b.maturity);
  const net = feeText ? Yields.netYieldToMaturity(price, fee, b.coupon, settlement, b.maturity) : null;
  out.innerHTML = head + `
    <p class="calc-ytm">Rendement annuel à l'échéance : <strong id="calc-ytm">${pct(ytm)}${real}</strong></p>
    ${net === null ? "" : `<p class="calc-ytm">Net de frais : <strong id="calc-net">${pct(net)}${real}</strong></p>`}
    <dl class="calc-details">
      <dt>Durée restante</dt><dd>${num(years, 1)} ans</dd>
      <dt>Coupon couru payé en plus</dt><dd>${num(accrued, 3)} %</dd>
      <dt>Prix plein (cours + coupon couru)</dt><dd>${num(price + accrued, 3)} %</dd>
      ${net === null ? "" : `<dt>Frais (${num(feePct, 2)} %)</dt><dd>${num(cost - price - accrued, 3)} %</dd>
      <dt>Coût total, frais inclus</dt><dd>${num(cost, 3)} %</dd>
      <dt>Prix de revient unitaire (par euro de nominal)</dt><dd id="calc-unit">${num(cost / 100, 4)}</dd>`}
      <dt>1 000 € ${net === null ? "" : "investis frais inclus "}deviennent</dt><dd>${Math.round(1000 * Math.pow(1 + (net ?? ytm), years)).toLocaleString("fr-FR")} €</dd>
      <dt>Pour comparaison, au dernier cours (${num(b.price, 2)} %)</dt><dd>${pct(b.ytm)}${real}</dd>
    </dl>
    <p class="calc-note">Règlement le ${dateFr(settlement)} (J+2 ouvrés). ${net === null ? "Avant frais et impôts." : "Frais calculés sur le montant payé, coupon couru inclus. Avant impôts."} <a href="comprendre.html">Comprendre ces montants</a></p>`;
}

$("#calc-isin").addEventListener("input", renderCalc);
$("#calc-price").addEventListener("input", renderCalc);
$("#calc-fee").addEventListener("input", renderCalc);

$("#table tbody").addEventListener("click", (e) => {
  const btn = e.target.closest("button.isin");
  if (!btn) return;
  const isin = btn.dataset.isin;
  const done = (text) => {
    btn.textContent = text;
    setTimeout(() => { btn.textContent = isin; }, 1500);
  };
  navigator.clipboard.writeText(isin).then(() => done("ISIN copié ✓"), () => done("Copie impossible"));
});

fetch("data/oats.json")
  .then((r) => r.json())
  .then((d) => {
    data = d;
    const when = new Date(d.generated_at).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" });
    $("#updated").textContent = `Dernière mise à jour : ${when} (règlement au ${dateFr(d.settlement)}).`;
    render();
    renderCalc();
  })
  .catch(() => {
    $("#summary").textContent = "Impossible de charger les données.";
  });
