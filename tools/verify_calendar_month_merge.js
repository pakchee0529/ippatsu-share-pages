#!/usr/bin/env node
"use strict";

function monthBounds(year, month) {
  const monthStart = year + "-" + String(month).padStart(2, "0") + "-01";
  const lastDay = new Date(year, month, 0).getDate();
  const monthEnd = year + "-" + String(month).padStart(2, "0") + "-" + String(lastDay).padStart(2, "0");
  return { monthStart, monthEnd };
}

function overlaps(ev, year, month) {
  const { monthStart, monthEnd } = monthBounds(year, month);
  const start = String(ev.dateStart || "");
  const end = String(ev.dateEnd || start);
  return Boolean(start) && start <= monthEnd && end >= monthStart;
}

function merge(events, year, month, incoming) {
  const byId = new Map(incoming.map((event) => [String(event.id), event]));
  return events
    .filter((event) => !byId.has(String(event.id)) && !overlaps(event, year, month))
    .concat([...byId.values()]);
}

const cross = { id: "cross", dateStart: "2026-09-30", dateEnd: "2026-10-02" };
const septemberOnly = { id: "sep", dateStart: "2026-09-29", dateEnd: "2026-09-29" };
let events = [cross, septemberOnly];
events = merge(events, 2026, 10, [cross]);
if (events.filter((event) => event.id === "cross").length !== 1) throw new Error("cross-month event duplicated in October");
const octoberVisible = events.filter((event) => overlaps(event, 2026, 10));
if (octoberVisible.length !== 1 || octoberVisible[0].id !== "cross") {
  throw new Error("October display contains an event outside the visible month");
}
events = merge(events, 2026, 9, [cross, septemberOnly]);
if (events.filter((event) => event.id === "cross").length !== 1) throw new Error("cross-month event duplicated returning to September");
if (!events.some((event) => event.id === "sep")) throw new Error("September event missing after refresh");
console.log("OK: calendar month merge keeps cross-month events unique");
