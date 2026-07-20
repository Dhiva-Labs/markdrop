// Spike UI: proves the Chaquopy-embedded markitdown engine works on-device.
// Shows engine diagnostics and converts a generated sample HTML file.
// Real app screens (share-sheet intake, library, batch) come after go/no-go.

import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

const _channel = MethodChannel('md_engine');

void main() => runApp(const SpikeApp());

class SpikeApp extends StatelessWidget {
  const SpikeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Markdrop',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: const Color(0xFF4F46E5), useMaterial3: true),
      home: const SpikeScreen(),
    );
  }
}

class SpikeScreen extends StatefulWidget {
  const SpikeScreen({super.key});

  @override
  State<SpikeScreen> createState() => _SpikeScreenState();
}

class _SpikeScreenState extends State<SpikeScreen> {
  String engineInfo = 'loading engine…';
  String output = '';
  bool busy = false;

  @override
  void initState() {
    super.initState();
    _loadInfo();
  }

  Future<void> _loadInfo() async {
    final sw = Stopwatch()..start();
    try {
      final raw = await _channel.invokeMethod<String>('engineInfo');
      sw.stop();
      final info = jsonDecode(raw!);
      setState(() => engineInfo =
          'Python ${info['python']} · cold start ${sw.elapsedMilliseconds} ms\n'
          'modules: ${(info['modules'] as Map).entries.map((e) => "${e.key}=${e.value ? "✓" : "✗"}").join(" ")}');
    } catch (e) {
      setState(() => engineInfo = 'engine error: $e');
    }
  }

  Future<void> _convertSample() async {
    setState(() {
      busy = true;
      output = '';
    });
    try {
      final dir = await getTemporaryDirectory();
      final sample = File('${dir.path}/sample.html');
      await sample.writeAsString('''
<html><head><title>Spike Sample</title></head><body>
<h1>Hello from Android</h1>
<p>This file was written by Dart and converted by <b>markitdown</b> running in Chaquopy.</p>
<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>
</body></html>''');
      final sw = Stopwatch()..start();
      final raw = await _channel
          .invokeMethod<String>('convertFile', {'path': sample.path});
      sw.stop();
      final res = jsonDecode(raw!);
      setState(() => output = res['ok'] == true
          ? '--- converted in ${sw.elapsedMilliseconds} ms ---\n${res['markdown']}'
          : 'FAILED: ${res['error']}');
    } catch (e) {
      setState(() => output = 'bridge error: $e');
    } finally {
      setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Markdrop — from Dhiva Labs')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Text(engineInfo, style: const TextStyle(fontSize: 12)),
              ),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: busy ? null : _convertSample,
              child: Text(busy ? 'Converting…' : 'Convert sample HTML → Markdown'),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: SingleChildScrollView(
                child: SelectableText(
                  output.isEmpty ? 'Output appears here' : output,
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
