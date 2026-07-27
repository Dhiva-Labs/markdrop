import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import 'engine.dart';
import 'library.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MarkdropApp());
}

class MarkdropApp extends StatelessWidget {
  const MarkdropApp({super.key});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF4F46E5);
    return MaterialApp(
      title: 'Markdrop',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: seed, brightness: Brightness.light, useMaterial3: true),
      darkTheme: ThemeData(colorSchemeSeed: seed, brightness: Brightness.dark, useMaterial3: true),
      home: const HomeShell(),
    );
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int tab = 0;
  bool busy = false;
  String status = '';
  final urlController = TextEditingController();
  final GlobalKey<_LibraryTabState> libraryKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    channel.setMethodCallHandler(_onNativeCall);
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await _drainPendingShares();
      _runSelftestIfRequested();
    });
  }

  Future<dynamic> _onNativeCall(MethodCall call) async {
    if (call.method == 'onShared') {
      final shares = (call.arguments as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      await _handleShares(shares);
    }
    return null;
  }

  Future<void> _drainPendingShares() async {
    final raw = await channel.invokeMethod<List<dynamic>>('getPendingShares');
    if (raw == null || raw.isEmpty) return;
    await _handleShares(
        raw.map((e) => Map<String, dynamic>.from(e as Map)).toList());
  }

  Future<void> _handleShares(List<Map<String, dynamic>> shares) async {
    for (final share in shares) {
      final value = share['value'] as String? ?? '';
      if (share['type'] == 'file') {
        await _convert(() => Engine.convertFile(value), value.split('/').last);
      } else {
        final m = RegExp(r'https?://\S+').firstMatch(value);
        if (m != null) {
          await _convert(() => Engine.convertUrl(m.group(0)!), m.group(0)!);
        }
      }
    }
  }

  Future<void> _convert(
      Future<ConversionResult> Function() run, String sourceName) async {
    setState(() {
      busy = true;
      status = 'Converting $sourceName…';
    });
    try {
      final res = await run();
      if (!mounted) return;
      if (res.ok && res.markdown != null) {
        final saved =
            await LibraryStore.save(filenameFor(res.title, 'converted'), res.markdown!);
        libraryKey.currentState?.refresh();
        setState(() => status = '');
        await Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => ResultScreen(
            title: res.title ?? sourceName,
            markdown: res.markdown!,
            libraryFile: saved,
          ),
        ));
      } else {
        setState(() => status = res.error ?? 'Conversion failed');
      }
    } catch (e) {
      setState(() => status = 'Error: $e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _pickAndConvert() async {
    final picked = await FilePicker.platform.pickFiles(allowMultiple: true);
    if (picked == null) return;
    for (final f in picked.files) {
      final path = f.path;
      if (path != null) {
        await _convert(() => Engine.convertFile(path), f.name);
      }
    }
  }

  Future<void> _convertUrlField() async {
    final url = urlController.text.trim();
    if (url.isEmpty) {
      setState(() => status = 'Paste a link first');
      return;
    }
    await _convert(() => Engine.convertUrl(url), url);
    urlController.clear();
  }

  /// Headless E2E hook: if `app-external-files/selftest/` contains files,
  /// convert each one, write .md next to it plus _results.json. Driven by adb.
  Future<void> _runSelftestIfRequested() async {
    try {
      final ext = await getExternalStorageDirectory();
      if (ext == null) return;
      final dir = Directory('${ext.path}/selftest');
      if (!dir.existsSync()) return;
      final results = <Map<String, dynamic>>[];
      for (final f in dir.listSync().whereType<File>()) {
        if (f.path.endsWith('.md') || f.path.endsWith('.json')) continue;
        final res = await Engine.convertFile(f.path);
        if (res.ok && res.markdown != null) {
          await File('${f.path}.md').writeAsString(res.markdown!);
        }
        results.add({
          'file': f.path.split('/').last,
          'ok': res.ok,
          'chars': res.markdown?.length,
          'error': res.error,
        });
      }
      // URL leg (needs network)
      final urlRes =
          await Engine.convertUrl('https://en.wikipedia.org/wiki/Markdown');
      results.add({
        'file': 'URL:wikipedia',
        'ok': urlRes.ok,
        'chars': urlRes.markdown?.length,
        'error': urlRes.error,
      });
      try {
        final probe = await channel.invokeMethod<String>('probeImports', {'arg': ''});
        await File('${dir.path}/_imports.json').writeAsString(probe ?? '{}');
      } catch (_) {}
      await File('${dir.path}/_results.json')
          .writeAsString(const JsonEncoder.withIndent('  ').convert(results));
    } catch (_) {
      // selftest is best-effort; never crash the app for it
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Markdrop'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 14),
            child: Center(
              child: Text('from Dhiva Labs',
                  style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant)),
            ),
          ),
        ],
      ),
      body: IndexedStack(
        index: tab,
        children: [
          _convertTab(cs),
          LibraryTab(key: libraryKey),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tab,
        onDestinationSelected: (i) => setState(() => tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.swap_horiz), label: 'Convert'),
          NavigationDestination(icon: Icon(Icons.folder_outlined), label: 'Library'),
        ],
      ),
    );
  }

  Widget _convertTab(ColorScheme cs) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: InkWell(
            onTap: busy ? null : _pickAndConvert,
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 28),
              child: Column(
                children: [
                  Icon(Icons.upload_file, size: 40, color: cs.primary),
                  const SizedBox(height: 8),
                  const Text('Pick files to convert',
                      style: TextStyle(fontWeight: FontWeight.w600)),
                  Text('pdf · docx · xlsx · pptx · epub · html · csv · photos · …',
                      style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant)),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Link or YouTube video',
                    style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: urlController,
                        keyboardType: TextInputType.url,
                        decoration: const InputDecoration(
                          isDense: true,
                          border: OutlineInputBorder(),
                          hintText: 'https://…',
                        ),
                        onSubmitted: (_) => _convertUrlField(),
                      ),
                    ),
                    const SizedBox(width: 8),
                    FilledButton(
                      onPressed: busy ? null : _convertUrlField,
                      child: const Text('Convert'),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text('YouTube links become title + description + transcript.',
                    style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Text(
          'Tip: you can also share any file, photo, or link to Markdrop from '
          'other apps via the Android share sheet.',
          style: TextStyle(fontSize: 12.5, color: cs.onSurfaceVariant),
        ),
        const SizedBox(height: 16),
        if (busy) const Center(child: CircularProgressIndicator()),
        if (status.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(status,
                textAlign: TextAlign.center,
                style: TextStyle(color: cs.error)),
          ),
      ],
    );
  }
}

class ResultScreen extends StatefulWidget {
  const ResultScreen(
      {super.key, required this.title, required this.markdown, this.libraryFile});
  final String title;
  final String markdown;
  final File? libraryFile;

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  bool raw = false;

  Future<void> _shareFile() async {
    final tmp = await getTemporaryDirectory();
    final f = File('${tmp.path}/${filenameFor(widget.title)}');
    await f.writeAsString(widget.markdown);
    await SharePlus.instance.share(
        ShareParams(files: [XFile(f.path, mimeType: 'text/markdown')]));
  }

  Future<void> _saveDownloads() async {
    try {
      final where = await Engine.saveToDownloads(
          filenameFor(widget.title), widget.markdown);
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Saved to $where')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Save failed: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            tooltip: raw ? 'Rendered view' : 'Raw markdown',
            icon: Icon(raw ? Icons.article_outlined : Icons.code),
            onPressed: () => setState(() => raw = !raw),
          ),
        ],
      ),
      body: raw
          ? SingleChildScrollView(
              padding: const EdgeInsets.all(14),
              child: SelectableText(widget.markdown,
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12.5)),
            )
          : Markdown(data: widget.markdown, selectable: true),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 6, 12, 10),
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.copy, size: 18),
                  label: const Text('Copy text'),
                  onPressed: () async {
                    await Clipboard.setData(ClipboardData(text: widget.markdown));
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Markdown copied')));
                    }
                  },
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.share, size: 18),
                  label: const Text('Share .md'),
                  onPressed: _shareFile,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton.icon(
                  icon: const Icon(Icons.download, size: 18),
                  label: const Text('Save file'),
                  onPressed: _saveDownloads,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class LibraryTab extends StatefulWidget {
  const LibraryTab({super.key});

  @override
  State<LibraryTab> createState() => _LibraryTabState();
}

class _LibraryTabState extends State<LibraryTab> {
  List<FileSystemEntity> items = [];

  @override
  void initState() {
    super.initState();
    refresh();
  }

  Future<void> refresh() async {
    final list = await LibraryStore.list();
    if (mounted) setState(() => items = list);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    if (items.isEmpty) {
      return Center(
        child: Text('Converted documents appear here',
            style: TextStyle(color: cs.onSurfaceVariant)),
      );
    }
    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (context, i) {
        final f = items[i] as File;
        final name = f.path.split('/').last;
        final modified = f.statSync().modified;
        return ListTile(
          leading: Icon(Icons.description_outlined, color: cs.primary),
          title: Text(name, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text(
              '${modified.toIso8601String().substring(0, 16).replaceAll("T", " ")} · '
              '${(f.statSync().size / 1024).toStringAsFixed(1)} KB'),
          trailing: IconButton(
            icon: const Icon(Icons.delete_outline),
            onPressed: () async {
              await LibraryStore.delete(f);
              refresh();
            },
          ),
          onTap: () async {
            final markdown = await f.readAsString();
            if (!context.mounted) return;
            await Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => ResultScreen(
                  title: name.replaceAll(RegExp(r'\.md$'), ''),
                  markdown: markdown,
                  libraryFile: f),
            ));
          },
        );
      },
    );
  }
}
