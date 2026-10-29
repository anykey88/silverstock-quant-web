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

String rocYear(int year) => '民國 ${year - 1911} 年';

String dateText(DateTime d) =>
    '${d.year}/${d.month.toString().padLeft(2, '0')}/${d.day.toString().padLeft(2, '0')}';

String nowStamp() {
  final n = DateTime.now();
  return '${dateText(n)} ${n.hour.toString().padLeft(2, '0')}:${n.minute.toString().padLeft(2, '0')}';
}
