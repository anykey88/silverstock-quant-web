// 數字／日期格式化工具（台灣慣用格式）
String money(num v, {int digits = 0}) {
  final s = v.toStringAsFixed(digits);
  final parts = s.split('.');
  final intPart = parts[0];
  final buf = StringBuffer();
  final neg = intPart.startsWith('-');
  final digitsOnly = neg ? intPart.substring(1) : intPart;
  for (var i = 0; i < digitsOnly.length; i++) {
    if (i > 0 && (digitsOnly.length - i) % 3 == 0) buf.write(',');
    buf.write(digitsOnly[i]);
  }
  final body = parts.length > 1 ? '${buf.toString()}.${parts[1]}' : buf.toString();
  return neg ? '-$body' : body;
}

String pct(num v, {int digits = 1}) => '${v.toStringAsFixed(digits)}%';

String signedPct(num v, {int digits = 1}) =>
    '${v >= 0 ? '+' : ''}${v.toStringAsFixed(digits)}%';

// ============================================================================
// V2.7 修訂：指標缺值「依實際原因」顯示，不再一律猜測
// ----------------------------------------------------------------------------
// 原則：
//   · 沒有明確證據時，一律顯示中性「N/A」並附「資料待補」tooltip（不妄加原因）。
//   · 「N/A（虧損）」只在近四季 EPS 明確為負時顯示。
//   · 「N/A（未配息）」只在確定沒有現金股利紀錄時顯示。
//   · ETF 等標的本來就沒有本益比 → 顯示中性「N/A」，
//     絕不可同時出現「N/A（虧損）」與「ETF 無此資料」的矛盾。
// ============================================================================

/// 指標缺值的原因。只有在呼叫端能提出明確證據時才傳入。
enum NaReason {
  /// 近四季 EPS 為負（虧損），本益比不具意義。
  loss,

  /// 確定沒有現金股利紀錄（近 12 個月未配息）。
  noDividend,

  /// 此類標的（如 ETF）本來就沒有這項指標。
  notApplicable,

  /// 資料來源未提供／抓取失敗，原因不明（預設）。
  noData,
}

/// 殖利率：有值才顯示百分比；缺值依原因標註，無原因時只顯示中性 N/A。
String fmtYield(double? v, {NaReason reason = NaReason.noData}) {
  if (v != null && v > 0) return pct(v, digits: 2);
  switch (reason) {
    case NaReason.noDividend:
      return 'N/A（未配息）';
    case NaReason.noData:
    case NaReason.loss:
    case NaReason.notApplicable:
      return 'N/A';
  }
}

/// 本益比：有正值才顯示；缺值依原因標註，無原因時只顯示中性 N/A。
String fmtPe(double? v, {NaReason reason = NaReason.noData}) {
  if (v != null && v > 0) return v.toStringAsFixed(1);
  switch (reason) {
    case NaReason.loss:
      return 'N/A（虧損）';
    case NaReason.notApplicable:
    case NaReason.noDividend:
    case NaReason.noData:
      return 'N/A';
  }
}

/// 股價淨值比：不及判斷原因，一律中性 N/A。
String fmtPb(double? v) => (v == null || v <= 0) ? 'N/A' : v.toStringAsFixed(2);

// ---- tooltip 文案（與上面原因一一對應）----
const String kYieldNaTip = '近 12 個月未配發現金股利，不適用殖利率。';
const String kPeNaTip = '近四季 EPS 合計為負（虧損），本益比不具意義。';
const String kPbNaTip = '資料來源未提供股價淨值比。';
const String kNoDataTip = '資料來源未提供此指標，暫時無法計算（資料待補）。';
const String kEtfNaTip = 'ETF 等標的本來就沒有本益比，不適用。';

/// 依原因回傳對應 tooltip，方便呼叫端統一取用。
String naTip(NaReason reason, {String metric = ''}) {
  switch (reason) {
    case NaReason.loss:
      return kPeNaTip;
    case NaReason.noDividend:
      return kYieldNaTip;
    case NaReason.notApplicable:
      return kEtfNaTip;
    case NaReason.noData:
      return kNoDataTip;
  }
}

String rocYear(int year) => '民國 ${year - 1911} 年';

String dateText(DateTime d) =>
    '${d.year}/${d.month.toString().padLeft(2, '0')}/${d.day.toString().padLeft(2, '0')}';

String nowStamp() {
  final n = DateTime.now();
  return '${dateText(n)} ${n.hour.toString().padLeft(2, '0')}:${n.minute.toString().padLeft(2, '0')}';
}
