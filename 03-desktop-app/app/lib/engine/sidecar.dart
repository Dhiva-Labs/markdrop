import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// Client for the md-engine sidecar (`md_engine.py serve` / frozen binary).
/// Line-delimited JSON over stdio; one warm Python process for all jobs.
class Sidecar {
  Process? _proc;
  final _pending = <int, Completer<Map<String, dynamic>>>{};
  int _nextId = 1;
  bool _ready = false;
  String? resolvedCommand;

  bool get isReady => _ready;

  /// Locations tried in order; first that exists wins.
  static List<List<String>> _candidates() {
    final exeDir = File(Platform.resolvedExecutable).parent.path;
    final env = Platform.environment['MD_ENGINE'];
    final home = Platform.environment['HOME'] ?? '';
    return [
      if (env != null && env.isNotEmpty) [env, 'serve'],
      // bundled next to the app binary
      ['$exeDir/md-engine/md-engine', 'serve'],
      // dev tree: repo layout
      [
        '$home/dhiva-labs/md-files-dhivalabs/03-desktop-app/engine/dist/md-engine/md-engine',
        'serve'
      ],
      [
        '$home/dhiva-labs/md-files-dhivalabs/03-desktop-app/engine/.venv/bin/python',
        '$home/dhiva-labs/md-files-dhivalabs/03-desktop-app/engine/md_engine.py',
        'serve'
      ],
    ];
  }

  Future<void> start() async {
    if (_proc != null) return;
    for (final cmd in _candidates()) {
      if (!File(cmd.first).existsSync()) continue;
      try {
        final proc = await Process.start(cmd.first, cmd.sublist(1));
        _proc = proc;
        resolvedCommand = cmd.join(' ');
        final readyCompleter = Completer<void>();
        proc.stdout
            .transform(utf8.decoder)
            .transform(const LineSplitter())
            .listen((line) {
          if (line.trim().isEmpty) return;
          Map<String, dynamic> msg;
          try {
            msg = jsonDecode(line) as Map<String, dynamic>;
          } catch (_) {
            return;
          }
          if (msg['ready'] == true) {
            _ready = true;
            if (!readyCompleter.isCompleted) readyCompleter.complete();
            return;
          }
          final id = msg['id'];
          if (id is int && _pending.containsKey(id)) {
            _pending.remove(id)!.complete(msg);
          }
        });
        proc.stderr.transform(utf8.decoder).listen((s) {
          stderr.write('[md-engine] $s');
        });
        unawaited(proc.exitCode.then((_) {
          _ready = false;
          _proc = null;
          for (final c in _pending.values) {
            c.complete({'ok': false, 'error': 'Engine process exited'});
          }
          _pending.clear();
        }));
        await readyCompleter.future.timeout(const Duration(seconds: 60));
        return;
      } catch (_) {
        _proc = null;
        continue;
      }
    }
    throw StateError(
        'md-engine not found. Build it with PyInstaller (engine/) or set MD_ENGINE.');
  }

  Future<Map<String, dynamic>> _rpc(Map<String, dynamic> req) async {
    await start();
    final id = _nextId++;
    req['id'] = id;
    final completer = Completer<Map<String, dynamic>>();
    _pending[id] = completer;
    _proc!.stdin.writeln(jsonEncode(req));
    return completer.future.timeout(const Duration(seconds: 120), onTimeout: () {
      _pending.remove(id);
      return {'ok': false, 'error': 'Conversion timed out (120s)'};
    });
  }

  Future<Map<String, dynamic>> convert(String source, {String? output}) =>
      _rpc({'cmd': 'convert', 'source': source, if (output != null) 'output': output});

  Future<Map<String, dynamic>> formats() => _rpc({'cmd': 'formats'});

  void dispose() {
    if (_proc != null) {
      _proc!.stdin.writeln(jsonEncode({'cmd': 'quit', 'id': _nextId++}));
      Future.delayed(const Duration(seconds: 2), () => _proc?.kill());
    }
  }
}
