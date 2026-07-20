import 'dart:convert';
import 'dart:io';

import 'package:desktop_drop/desktop_drop.dart';
import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import 'engine/jobs.dart';
import 'engine/sidecar.dart';

Future<void> main(List<String> args) async {
  // Headless self-test: `md_converter_desktop --selftest <file>` converts one
  // file through the real sidecar, prints JSON to stdout, exits. Used for CI /
  // agent verification without driving the UI.
  final selftestIx = args.indexOf('--selftest');
  if (selftestIx != -1 && selftestIx + 1 < args.length) {
    final sidecar = Sidecar();
    try {
      final res = await sidecar.convert(args[selftestIx + 1]);
      stdout.writeln(jsonEncode({
        'selftest': true,
        'ok': res['ok'],
        'title': res['title'],
        'chars': (res['markdown'] as String?)?.length,
        'engine': sidecar.resolvedCommand,
        'error': res['error'],
      }));
      sidecar.dispose();
      exit(res['ok'] == true ? 0 : 1);
    } catch (e) {
      stdout.writeln(jsonEncode({'selftest': true, 'ok': false, 'error': '$e'}));
      exit(1);
    }
  }

  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MdConverterApp());
}

class MdConverterApp extends StatelessWidget {
  const MdConverterApp({super.key});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF4F46E5);
    return MaterialApp(
      title: 'Markdrop Studio',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: seed, brightness: Brightness.light, useMaterial3: true),
      darkTheme: ThemeData(colorSchemeSeed: seed, brightness: Brightness.dark, useMaterial3: true),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final sidecar = Sidecar();
  late final JobQueue queue = JobQueue(sidecar);
  final urlController = TextEditingController();
  String engineState = 'starting engine…';
  bool dragging = false;
  bool rawView = false;

  @override
  void initState() {
    super.initState();
    queue.addListener(() => setState(() {}));
    sidecar.start().then((_) {
      setState(() => engineState = "engine ready · from Dhiva Labs");
    }).catchError((e) {
      setState(() => engineState = 'engine error: $e');
    });
  }

  @override
  void dispose() {
    sidecar.dispose();
    super.dispose();
  }

  Future<void> _pickFiles() async {
    final files = await openFiles();
    if (files.isNotEmpty) queue.addAll(files.map((f) => f.path));
  }

  Future<void> _saveSelected() async {
    final job = queue.selected;
    if (job == null || job.markdown == null) return;
    final suggested = (job.title ?? job.name).replaceAll(RegExp(r'[^\w\d-]+'), '-');
    final location = await getSaveLocation(suggestedName: '$suggested.md');
    if (location == null) return;
    await File(location.path).writeAsString(job.markdown!);
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Saved ${location.path}')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Markdrop Studio'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(
              child: Text(engineState,
                  style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant)),
            ),
          ),
          IconButton(
            tooltip: 'Clear finished',
            onPressed: queue.clearFinished,
            icon: const Icon(Icons.clear_all),
          ),
        ],
      ),
      body: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 340,
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: DropTarget(
                    onDragEntered: (_) => setState(() => dragging = true),
                    onDragExited: (_) => setState(() => dragging = false),
                    onDragDone: (detail) {
                      setState(() => dragging = false);
                      queue.addAll(detail.files.map((f) => f.path));
                    },
                    child: InkWell(
                      onTap: _pickFiles,
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        height: 110,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                              color: dragging ? cs.primary : cs.outlineVariant,
                              width: 2),
                          color: dragging
                              ? cs.primary.withValues(alpha: .08)
                              : cs.surfaceContainerLow,
                        ),
                        child: Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.file_download_outlined, color: cs.primary),
                              const SizedBox(height: 6),
                              const Text('Drop files here, or click to pick'),
                              Text('pdf · docx · xlsx · pptx · epub · html · …',
                                  style: TextStyle(
                                      fontSize: 11, color: cs.onSurfaceVariant)),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: urlController,
                          decoration: const InputDecoration(
                            isDense: true,
                            border: OutlineInputBorder(),
                            hintText: 'URL or YouTube link…',
                          ),
                          onSubmitted: (_) => _addUrl(),
                        ),
                      ),
                      const SizedBox(width: 8),
                      FilledButton(onPressed: _addUrl, child: const Text('Add')),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: ListView.builder(
                    itemCount: queue.jobs.length,
                    itemBuilder: (context, i) {
                      final job = queue.jobs[i];
                      return ListTile(
                        dense: true,
                        selected: job == queue.selected,
                        leading: _statusIcon(job, cs),
                        title: Text(job.name,
                            maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: job.error != null
                            ? Text(job.error!,
                                maxLines: 2,
                                style: TextStyle(color: cs.error, fontSize: 11))
                            : null,
                        onTap: () => queue.select(job),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
          const VerticalDivider(width: 1),
          Expanded(child: _preview(cs)),
        ],
      ),
    );
  }

  void _addUrl() {
    final url = urlController.text.trim();
    if (url.isEmpty) return;
    queue.addAll([url]);
    urlController.clear();
  }

  Widget _statusIcon(Job job, ColorScheme cs) {
    switch (job.status) {
      case JobStatus.queued:
        return Icon(Icons.schedule, color: cs.onSurfaceVariant, size: 20);
      case JobStatus.converting:
        return const SizedBox(
            width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2));
      case JobStatus.done:
        return Icon(Icons.check_circle, color: Colors.green.shade600, size: 20);
      case JobStatus.failed:
        return Icon(Icons.error, color: cs.error, size: 20);
    }
  }

  Widget _preview(ColorScheme cs) {
    final job = queue.selected;
    if (job == null || job.markdown == null) {
      return Center(
        child: Text(
          job == null
              ? 'Convert something and select it to preview'
              : (job.error ?? 'Converting…'),
          style: TextStyle(color: cs.onSurfaceVariant),
        ),
      );
    }
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
          child: Row(
            children: [
              Expanded(
                child: Text(job.title ?? job.name,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
              ),
              SegmentedButton<bool>(
                segments: const [
                  ButtonSegment(value: false, label: Text('Rendered')),
                  ButtonSegment(value: true, label: Text('Raw')),
                ],
                selected: {rawView},
                onSelectionChanged: (s) => setState(() => rawView = s.first),
              ),
              const SizedBox(width: 8),
              IconButton(
                tooltip: 'Copy markdown',
                icon: const Icon(Icons.copy),
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: job.markdown!));
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Copied to clipboard')));
                },
              ),
              IconButton(
                tooltip: 'Save .md',
                icon: const Icon(Icons.save_alt),
                onPressed: _saveSelected,
              ),
            ],
          ),
        ),
        const Divider(),
        Expanded(
          child: rawView
              ? SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: SelectableText(job.markdown!,
                      style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
                )
              : Markdown(data: job.markdown!, selectable: true),
        ),
      ],
    );
  }
}
