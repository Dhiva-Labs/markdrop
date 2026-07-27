import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';

const channel = MethodChannel('md_engine');

const _imageExts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic'};
const _videoExts = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.3gp'};

class ConversionResult {
  ConversionResult({required this.ok, this.title, this.markdown, this.error});
  final bool ok;
  final String? title;
  final String? markdown;
  final String? error;

  factory ConversionResult.fromJson(String raw) {
    try {
      final m = jsonDecode(raw) as Map<String, dynamic>;
      return ConversionResult(
        ok: m['ok'] == true,
        title: m['title'] as String?,
        markdown: m['markdown'] as String?,
        error: m['error'] as String?,
      );
    } catch (e) {
      return ConversionResult(ok: false, error: 'Bad engine response: $e');
    }
  }
}

class Engine {
  /// Convert any local file. Images go through on-device OCR; everything else
  /// through the embedded markitdown engine.
  static Future<ConversionResult> convertFile(String path) async {
    final ext = _extOf(path);
    if (_imageExts.contains(ext)) return _convertImage(path);
    if (_videoExts.contains(ext)) {
      return ConversionResult(
        ok: false,
        error: 'Video files can\'t be converted to text on-device. '
            'For YouTube videos, paste the link instead to get the transcript.',
      );
    }
    final raw = await channel.invokeMethod<String>('convertFile', {'arg': path});
    return ConversionResult.fromJson(raw ?? '{}');
  }

  static Future<ConversionResult> convertUrl(String url) async {
    final raw = await channel.invokeMethod<String>('convertUrl', {'arg': url.trim()});
    return ConversionResult.fromJson(raw ?? '{}');
  }

  static Future<String> info() async =>
      await channel.invokeMethod<String>('engineInfo', {'arg': ''}) ?? '{}';

  static Future<String> saveToDownloads(String name, String content) async =>
      await channel.invokeMethod<String>(
          'saveToDownloads', {'name': name, 'content': content}) ??
      '';

  /// Photo -> markdown via ML Kit OCR (fully on-device).
  static Future<ConversionResult> _convertImage(String path) async {
    final recognizer = TextRecognizer(script: TextRecognitionScript.latin);
    try {
      final input = InputImage.fromFilePath(path);
      final recognized = await recognizer.processImage(input);
      final name = path.split('/').last;
      final stat = await File(path).stat();
      final lines = <String>[
        _frontMatter(title: name, source: name, kind: 'image-ocr'),
        '',
        '# $name',
        '',
        '- **Size:** ${(stat.size / 1024).toStringAsFixed(1)} KB',
        '- **Modified:** ${stat.modified.toIso8601String()}',
        '',
      ];
      if (recognized.text.trim().isEmpty) {
        lines.add('*(No text detected in this image.)*');
      } else {
        lines.add('## Recognized Text');
        lines.add('');
        for (final block in recognized.blocks) {
          lines.add(block.text.trim());
          lines.add('');
        }
      }
      return ConversionResult(ok: true, title: name, markdown: lines.join('\n'));
    } catch (e) {
      return ConversionResult(ok: false, error: 'OCR failed: $e');
    } finally {
      recognizer.close();
    }
  }

  static String _frontMatter(
      {required String title, required String source, String kind = 'file'}) {
    final date = DateTime.now().toIso8601String().substring(0, 10);
    return '---\ntitle: $title\nsource: $source\nconverted: $date\n'
        'generator: dhiva-labs/markdrop-mobile\n---';
  }

  static String _extOf(String path) {
    final name = path.split('/').last;
    final dot = name.lastIndexOf('.');
    return dot == -1 ? '' : name.substring(dot).toLowerCase();
  }
}

String filenameFor(String? title, [String fallback = 'converted']) {
  final base = (title ?? fallback)
      .replaceAll(RegExp(r'[^\w\d-]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');
  final trimmed = base.length > 80 ? base.substring(0, 80) : base;
  return '${trimmed.isEmpty ? fallback : trimmed}.md';
}
