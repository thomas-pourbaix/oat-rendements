const KIND_LABEL = { strip: "strip", indexee_euro: "OAT€i", indexee_france: "OATi" };
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
      <td><a href="${b.url}" target="_blank" rel="noopener" title="${b.name}">${label(b)}</a>${tag}<span class="isin">${b.isin}</span></td>
      <td>${dateFr(b.maturity)}</td>
      <td class="num">${num(b.years, 1)} ans</td>
      <td class="num">${num(b.coupon, 2)} %</td>
      <td class="num">${num(b.price, 2)} %</td>
      <td class="${stale ? "stale" : ""}" title="${stale ? "Cours ancien : peu représentatif du prix actuel" : ""}">${b.last_trade ? dateFr(b.last_trade) : "–"}</td>
      <td class="num ytm">${pct(b.ytm)}${b.kind.startsWith("indexee") ? " réel" : ""}</td>
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
document.querySelectorAll("input, select").forEach((el) => el.addEventListener("input", render));

fetch("data/oats.json")
  .then((r) => r.json())
  .then((d) => {
    data = d;
    const when = new Date(d.generated_at).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" });
    $("#updated").textContent = `Dernière mise à jour : ${when} (règlement au ${dateFr(d.settlement)}).`;
    render();
  })
  .catch(() => {
    $("#summary").textContent = "Impossible de charger les données.";
  });
