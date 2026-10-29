// ============================================================================
// 語音服務：國語／台語 TTS 朗讀 + 語音輸入（Web Speech API）
// ----------------------------------------------------------------------------
// 【適老化重點】
// 1. 台語（nan-TW）語音在多數瀏覽器／iOS 需自行下載；找不到時自動改用國語
//    並在畫面提示，不讓長輩卡住。
// 2. 長句會自動切成短句逐句朗讀，避免部分瀏覽器唸到一半停住。
// 3. 語音輸入（SpeechRecognition）在 Safari 需使用者手勢觸發，且舊版可能不支援，
//    不支援時提示改用鍵盤輸入。
// ============================================================================

// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:async';
import 'dart:html' as html;
import 'dart:js' as js;
import 'dart:js_util' as jsu;

import 'package:flutter/foundation.dart';

class SpeechService extends ChangeNotifier {
  bool _speaking = false;
  bool get speaking => _speaking;

  String? _note;
  String? get note => _note;

  List<dynamic>? _voiceCache;

  bool get ttsSupported => jsu.hasProperty(html.window, 'speechSynthesis');

  dynamic _synth() => jsu.getProperty<Object>(html.window, 'speechSynthesis');

  List<dynamic> _voices() {
    if (_voiceCache != null && _voiceCache!.isNotEmpty) return _voiceCache!;
    try {
      final list = jsu.callMethod(_synth(), 'getVoices', <dynamic>[]);
      final len = jsu.getProperty<int>(list, 'length');
      final out = <dynamic>[];
      for (var i = 0; i < len; i++) {
        out.add(jsu.getProperty<Object>(list, '$i'));
      }
      _voiceCache = out;
      return out;
    } catch (_) {
      return <dynamic>[];
    }
  }

  String _voiceLang(dynamic v) {
    try {
      return ((jsu.getProperty<Object?>(v, 'lang') ?? '').toString()).toString();
    } catch (_) {
      return '';
    }
  }

  String _voiceName(dynamic v) {
    try {
      return ((jsu.getProperty<Object?>(v, 'name') ?? '').toString()).toString();
    } catch (_) {
      return '';
    }
  }

  /// 找台語語音（iOS/Chrome 可能沒有）
  dynamic _findTaiwanese() {
    for (final v in _voices()) {
      final lang = _voiceLang(v).toLowerCase();
      final name = _voiceName(v);
      if (lang.startsWith('nan') ||
          name.contains('台語') ||
          name.contains('閩南') ||
          name.contains('Taiwanese')) {
        return v;
      }
    }
    return null;
  }

  dynamic _findMandarinTW() {
    dynamic fallback;
    for (final v in _voices()) {
      final lang = _voiceLang(v).toLowerCase();
      if (lang == 'zh-tw' || lang == 'zh_tw') return v;
      if (lang.startsWith('zh') && fallback == null) fallback = v;
    }
    return fallback;
  }

  /// 朗讀。kind: 'mandarin' | 'taiwanese'
  Future<void> speak(String text, {String kind = 'mandarin'}) async {
    if (!ttsSupported || text.trim().isEmpty) {
      _note = '此瀏覽器不支援語音朗讀，請改用文字閱讀。';
      notifyListeners();
      return;
    }
    stop();

    dynamic voice;
    var langCode = 'zh-TW';
    var rate = 0.86;
    _note = null;

    if (kind == 'taiwanese') {
      voice = _findTaiwanese();
      if (voice == null) {
        voice = _findMandarinTW();
        _note = '此裝置未安裝台語語音，已改用國語語音朗讀。'
            '（iPad：設定 → 輔助使用 → 朗讀內容 → 聲音 → 中文（台灣））';
        rate = 0.78;
      } else {
        langCode = _voiceLang(voice).isEmpty ? 'nan-TW' : _voiceLang(voice);
      }
    } else {
      voice = _findMandarinTW();
    }
    if (voice != null && kind == 'mandarin') {
      langCode = _voiceLang(voice).isEmpty ? 'zh-TW' : _voiceLang(voice);
    }

    final chunks = _split(text);
    _speaking = true;
    notifyListeners();

    for (var i = 0; i < chunks.length; i++) {
      if (!_speaking) break;
      await _speakOne(chunks[i], langCode, rate, voice);
    }
    _speaking = false;
    notifyListeners();
  }

  Future<void> _speakOne(String text, String lang, double rate, dynamic voice) {
    final done = Completer<void>();
    try {
      final ctor = jsu.getProperty<Object>(html.window, 'SpeechSynthesisUtterance');
      final u = jsu.callConstructor(ctor, <dynamic>[text]);
      jsu.setProperty(u, 'lang', lang);
      jsu.setProperty(u, 'rate', rate);
      jsu.setProperty(u, 'pitch', 1.0);
      if (voice != null) jsu.setProperty(u, 'voice', voice);
      jsu.setProperty(
          u,
          'onend',
          js.allowInterop((_) {
            if (!done.isCompleted) done.complete();
          }));
      jsu.setProperty(
          u,
          'onerror',
          js.allowInterop((_) {
            if (!done.isCompleted) done.complete();
          }));
      jsu.callMethod(_synth(), 'speak', <dynamic>[u]);
      // 保險：最長 20 秒強制放行下一句
      Future<void>.delayed(const Duration(seconds: 20), () {
        if (!done.isCompleted) done.complete();
      });
    } catch (_) {
      if (!done.isCompleted) done.complete();
    }
    return done.future;
  }

  void stop() {
    try {
      jsu.callMethod(_synth(), 'cancel', <dynamic>[]);
    } catch (_) {}
    _speaking = false;
    notifyListeners();
  }

  /// 切句：以句號、問號、驚嘆號與逗號斷點切成 60 字內短句
  static List<String> _split(String text) {
    final clean = text.replaceAll(RegExp(r'\s+'), ' ').trim();
    final parts = <String>[];
    final buf = StringBuffer();
    for (var i = 0; i < clean.length; i++) {
      buf.write(clean[i]);
      final ch = clean[i];
      if ((ch == '。' || ch == '！' || ch == '？' || ch == '；' || ch == '\n') &&
          buf.length > 1) {
        parts.add(buf.toString());
        buf.clear();
      } else if (buf.length >= 60) {
        parts.add(buf.toString());
        buf.clear();
      }
    }
    if (buf.isNotEmpty) parts.add(buf.toString());
    return parts;
  }
}

/// 語音輸入（Web Speech Recognition）
class SpeechInputService {
  static bool get supported =>
      jsu.hasProperty(html.window, 'webkitSpeechRecognition') ||
      jsu.hasProperty(html.window, 'SpeechRecognition');

  static dynamic _rec;
  static bool _listening = false;
  static bool get listening => _listening;

  /// 開始聆聽，回傳辨識出的文字；不支援時回傳 null。
  static Future<String?> listen({
    required void Function(String partial) onPartial,
    void Function(String error)? onError,
  }) async {
    if (!supported) return null;
    final ctor = jsu.hasProperty(html.window, 'SpeechRecognition')
        ? jsu.getProperty<Object>(html.window, 'SpeechRecognition')
        : jsu.getProperty<Object>(html.window, 'webkitSpeechRecognition');
    final rec = jsu.callConstructor(ctor, <dynamic>[]);
    _rec = rec;
    jsu.setProperty(rec, 'lang', 'zh-TW');
    jsu.setProperty(rec, 'continuous', false);
    jsu.setProperty(rec, 'interimResults', true);
    jsu.setProperty(rec, 'maxAlternatives', 1);

    final done = Completer<String?>();
    _listening = true;

    jsu.setProperty(
        rec,
        'onresult',
        js.allowInterop((event) {
          try {
            final results = jsu.getProperty<Object>(event, 'results');
            final len = jsu.getProperty<int>(results, 'length');
            final last = jsu.getProperty<Object>(results, '${len - 1}');
            final alt = jsu.getProperty<Object>(last, '0');
            final text = (jsu.getProperty<Object?>(alt, 'transcript') ?? '').toString();
            final isFinal = jsu.getProperty<Object?>(last, 'isFinal') == true;
            onPartial(text);
            if (isFinal && !done.isCompleted) done.complete(text);
          } catch (_) {}
        }));
    jsu.setProperty(
        rec,
        'onerror',
        js.allowInterop((event) {
          _listening = false;
          final err = (jsu.getProperty<Object?>(event, 'error') ?? 'unknown').toString();
          onError?.call(err);
          if (!done.isCompleted) done.complete(null);
        }));
    jsu.setProperty(
        rec,
        'onend',
        js.allowInterop((_) {
          _listening = false;
          if (!done.isCompleted) done.complete(null);
        }));

    try {
      jsu.callMethod(rec, 'start', <dynamic>[]);
    } catch (e) {
      _listening = false;
      return null;
    }

    final result = await done.future;
    _listening = false;
    return result;
  }

  static void abort() {
    try {
      if (_rec != null) jsu.callMethod(_rec!, 'abort', <dynamic>[]);
    } catch (_) {}
    _listening = false;
  }
}
