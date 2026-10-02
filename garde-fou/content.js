/* Copyright (C) 2026 Thomas Pourbaix
   SPDX-License-Identifier: AGPL-3.0-only */

/* Order guard: runs on CIC's order confirmation page ("2/2 Passer un ordre", ORDR_ValeurValidation2.aspx).
   Neutralises the "Confirmer" button until the order passes the checks of check.js, then asks the
   user for the maturity year they INTEND, with the summary blurred: a wrong ISIN then shows up as a
   mismatch between the intention and the bond actually selected (INV-017). */

const DATA_URL = document.documentElement.dataset.guardDataUrl
  || "https://thomas-pourbaix.github.io/oat-rendements/data/oats.json";
const DELAY_SECONDS = 5;

let state = null; // { button, summary, allowed }

// Element ids of the bank's page, read from saved copies of ORDR_ValeurValidation2.aspx (2026-10-02).
const SUMMARY = "#esdtblCaractOrd";
const FIELDS = ["#lbSens", "#lbInfo", "#lbInfoModalite"]; // side, "1,00 EUR OAT ... (ISIN)", limit
const CONFIRM = "#btnConfirmer"; // <input type="image" alt="Confirmer">
const BANK_MESSAGES = ".blocmsg";

// Fallback in case the id changes: any button-like element labelled "Confirmer".
function findConfirmButton() {
  return document.querySelector(CONFIRM)
    || [...document.querySelectorAll("button, a, input")]
      .find((el) => (el.value || el.alt || el.textContent || "").trim() === "Confirmer");
}

const findSummary = () => document.querySelector(SUMMARY);
const summaryText = () => FIELDS.map((id) => document.querySelector(id)?.textContent ?? "").join("\n");
const bankWarning = () => [...document.querySelectorAll(BANK_MESSAGES)]
  .some((el) => /[ée]cart de cours important/i.test(el.textContent));

// While the order is not allowed, any click, Enter or form submission aimed at "Confirmer" is
// swallowed, however the page listens to it (capture phase on window runs first). INV-016.
function intercept(e) {
  if (!state || state.allowed || !state.button) return;
  // A submit is blocked only when "Confirmer" is its submitter: the bank's page is one big form,
  // and its other actions must keep working while the order is blocked.
  const aimed = e.type === "submit" ? e.submitter === state.button : e.composedPath().includes(state.button);
  const key = e.type !== "keydown" || e.key === "Enter" || e.key === " ";
  if (aimed && key) {
    e.preventDefault();
    e.stopImmediatePropagation();
  }
}
["click", "mousedown", "pointerdown", "keydown", "submit"].forEach((t) => window.addEventListener(t, intercept, true));

function neutralise(button, on) {
  button.classList.toggle("gf-neutralised", on);
  button.setAttribute("aria-disabled", on ? "true" : "false");
  if ("disabled" in button) button.disabled = on;
}

function showPanel(html, kind) {
  document.getElementById("gf-panel")?.remove();
  const div = document.createElement("div");
  div.id = "gf-panel";
  div.className = kind;
  div.innerHTML = html;
  state.summary.before(div);
  div.scrollIntoView({ block: "start" });
  return div;
}

const escape = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

function showBlock(reasons) {
  state.summary.classList.remove("gf-blurred");
  showPanel(
    `<p class="gf-title">✋ ORDRE BLOQUÉ PAR LE GARDE-FOU</p>
     <ul>${reasons.map((r) => `<li>${escape(r)}</li>`).join("")}</ul>
     <p class="gf-strong">Il n'y a pas de bouton pour passer outre. Clique sur « Abandonner » ou « Modifier ».</p>`,
    "block"
  );
}

function askIntention(order, result) {
  state.summary.classList.add("gf-blurred");
  const verb = order.side === "buy" ? "acheter" : "vendre";
  const div = showPanel(
    `<p class="gf-title">Contrôle avant confirmation</p>
     <label for="gf-year">Sans relire l'ordre : en quelle année doit être remboursée l'obligation que tu veux ${verb} ?</label>
     <input id="gf-year" inputmode="numeric" maxlength="4" autocomplete="off" placeholder="AAAA">
     <p class="gf-help">Le récapitulatif est flouté exprès. Une seule tentative : une erreur bloque l'ordre.</p>`,
    "ask"
  );
  const input = div.querySelector("#gf-year");
  input.focus();
  input.addEventListener("input", () => {
    if (input.value.length < 4) return;
    const intended = +input.value;
    if (intended !== result.year) {
      showBlock([
        `Tu vises une obligation remboursée en ${intended}, mais ce titre (${order.label}, ${order.isin}) ` +
        `est remboursé en ${result.year}. Ce n'est pas le bon titre.`,
      ]);
    } else {
      allowAfterDelay(order, result);
    }
  });
}

function allowAfterDelay(order, result) {
  state.summary.classList.remove("gf-blurred");
  const years = result.year - new Date().getFullYear();
  const div = showPanel(
    `<p class="gf-title">Contrôles passés</p>
     <p>${escape(order.label)} (${escape(order.isin)}) : remboursée en <strong>${escape(result.year)}</strong>, dans ${years} an${years > 1 ? "s" : ""}.</p>
     <p>Limite <strong>${escape(order.limit.toLocaleString("fr-FR"))} %</strong>, dernier cours connu <strong>${escape(result.price.toLocaleString("fr-FR"))} %</strong>.</p>
     <p class="gf-strong" id="gf-countdown"></p>`,
    "pass"
  );
  let left = DELAY_SECONDS;
  const tick = () => {
    const out = div.querySelector("#gf-countdown");
    if (left > 0) {
      out.textContent = `« Confirmer » se débloque dans ${left} s. Relis la ligne ci-dessus.`;
      left -= 1;
      setTimeout(tick, 1000);
    } else {
      out.textContent = "« Confirmer » est débloqué.";
      state.allowed = true;
      neutralise(state.button, false);
    }
  };
  tick();
}

// oats.json is external input running into a bank session: only a row with the expected types is
// kept, so a tampered file can at worst make the guard block (unknown price), never inject markup
// into the page (INV-025). The request carries no cookie and no referrer: GitHub learns nothing
// about the bank page it is called from.
async function loadBond(isin) {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer" });
    const row = (await response.json()).bonds.find((b) => b.isin === isin);
    const valid = row
      && Number.isFinite(row.price) && row.price > 0 && row.price < 1000
      && /^\d{4}-\d{2}-\d{2}$/.test(row.maturity)
      && (row.last_trade == null || !Number.isNaN(Date.parse(row.last_trade)));
    return valid ? { price: row.price, maturity: row.maturity, last_trade: row.last_trade } : null;
  } catch {
    return null;
  }
}

async function start() {
  const button = findConfirmButton();
  if (!button || (state && state.button === button)) return;
  const summary = findSummary();
  state = { button, summary: summary || button.parentElement, allowed: false };
  neutralise(button, true);

  if (!summary) {
    showBlock(["Récapitulatif de l'ordre introuvable : le garde-fou ne peut rien vérifier. La page de la banque a peut-être changé."]);
    return;
  }
  // Only OAT orders are checked: shares have no price in oats.json.
  if (!/\bOAT\b/.test(summaryText())) {
    state.allowed = true;
    neutralise(button, false);
    return;
  }
  const order = Guard.readOrder(summaryText());
  // The bank's warning is a banner above the summary, not inside it.
  order.bankWarning = bankWarning();
  const result = Guard.evaluate(order, order.isin ? await loadBond(order.isin) : null);
  if (result.verdict === "block") showBlock(result.reasons);
  else askIntention(order, result);
}

// The page may build or rebuild itself after loading.
new MutationObserver(() => {
  if (state?.button && !state.button.isConnected) state = null;
  if (!state) start();
  else if (!state.allowed) neutralise(state.button, true);
}).observe(document.documentElement, { childList: true, subtree: true });
start();
