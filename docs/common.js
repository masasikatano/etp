// 東証上場 ETF 一覧サイトの共通ユーティリティ。

const fmt = (v, d = 2) => (v === null || v === undefined || Number.isNaN(v)) ? "—" : Number(v).toLocaleString("ja-JP", { minimumFractionDigits: d, maximumFractionDigits: d });

const signed = (v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return { t: "—", c: "" };
  const n = Number(v);
  const t = (n > 0 ? "+" : "") + n.toFixed(2);
  const c = n > 0 ? "up" : n < 0 ? "down" : "";
  return { t, c };
};

const pctFmt = (v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const n = Number(v);
  return (n * 100).toFixed(2) + "%";
};
