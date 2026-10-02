/* Copyright (C) 2026 Thomas Pourbaix
   SPDX-License-Identifier: AGPL-3.0-only */

/* Order guard: pure logic (reading the order summary and deciding). No DOM access.

   Design rule: the guard is tuned for the user's worst state (tired, rushed). A warning that one
   click dismisses protects nothing, so any anomaly BLOCKS the order, with no override. The only
   way out is the bank's own "Modifier" or "Abandonner". See INV-016 to INV-018. */

const Guard = (() => {
  const MAX_GAP_POINTS = 1.5; // tolerated gap between the limit and the last traded price, in % points
  const STALE_DAYS = 10; // beyond that, the last traded price says nothing about the market

  const parseFrNumber = (s) => parseFloat(s.replace(/\s/g, "").replace(",", "."));
  const fmt = (x, d = 2) => x.toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });

  // "OAT 4%05-25042055" -> 2055 ; "OAT 0,75%17-250528" -> 2028.
  function yearFromLabel(label) {
    const m = label && label.match(/-(\d{6}|\d{8})\b/);
    if (!m) return null;
    return m[1].length === 8 ? +m[1].slice(4) : 2000 + +m[1].slice(4);
  }

  // Reads the text of CIC's order summary ("Caractéristiques de l'opération").
  function readOrder(text) {
    const isin = (text.match(/\(([A-Z]{2}[0-9A-Z]{9}[0-9])\)/) || [])[1] || null;
    const label = (text.match(/(OAT[^\n(]*?)\s*\(/) || [])[1]?.trim() || null;
    const limit = text.match(/limite\s*:\s*([\d\s.,]+?)\s*%/i);
    const side = /\bAcheter\b/.test(text) ? "buy" : /\bVendre\b/.test(text) ? "sell" : null;
    return {
      isin,
      label,
      side,
      limit: limit ? parseFrNumber(limit[1]) : null,
      bankWarning: /[ée]cart de cours important/i.test(text),
      labelYear: yearFromLabel(label),
    };
  }

  // `bond`: the oats.json row for the order's ISIN, or null.
  // Returns { verdict: "block" | "ask", reasons: [...] (French, shown to the user), year, price }.
  function evaluate(order, bond, now = new Date()) {
    const reasons = [];
    const year = bond ? +bond.maturity.slice(0, 4) : order.labelYear;
    const age = bond?.last_trade ? (now - new Date(bond.last_trade)) / 864e5 : Infinity;
    const price = bond && age <= STALE_DAYS ? bond.price : null;

    if (!order.isin) reasons.push("ISIN introuvable dans le récapitulatif.");
    if (!order.side) reasons.push("Sens de l'ordre (achat ou vente) introuvable.");
    if (order.limit == null) reasons.push("Ordre sans limite de prix : interdit sur une obligation. Passe un ordre à cours limité.");
    if (order.bankWarning) reasons.push("La banque signale un « écart de cours important » : la limite est loin du marché.");
    if (year == null) reasons.push("Date d'échéance introuvable.");

    if (price == null) {
      reasons.push("Dernier cours de ce titre inconnu ou trop ancien : impossible de vérifier la limite.");
    } else if (order.limit != null && order.side) {
      const buy = order.side === "buy";
      const gap = buy ? order.limit - price : price - order.limit;
      if (gap > MAX_GAP_POINTS) {
        reasons.push(
          `Limite ${fmt(order.limit)} % contre un dernier cours de ${fmt(price)} % : ` +
          `tu ${buy ? "paierais" : "vendrais"} ${fmt(gap)} points ${buy ? "trop cher" : "trop bas"}, ` +
          `soit environ ${fmt(gap * 10, 0)} € par tranche de 1 000 €.`
        );
      }
    }
    return { verdict: reasons.length ? "block" : "ask", reasons, year, price };
  }

  return { readOrder, yearFromLabel, evaluate, MAX_GAP_POINTS, STALE_DAYS };
})();
