import 'dart:io';

import 'package:path_provider/path_provider.dart';

/// Local library of past conversions: one .md file per conversion inside the
/// app documents dir. Filename doubles as the entry title.
class LibraryStore {
  static Future<Directory> _dir() async {
    final base = await getApplicationDocumentsDirectory();
    final dir = Directory('${base.path}/conversions');
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  static Future<File> save(String filename, String markdown) async {
    final dir = await _dir();
    var f = File('${dir.path}/$filename');
    var n = 1;
    while (await f.exists()) {
      final stem = filename.replaceAll(RegExp(r'\.md$'), '');
      f = File('${dir.path}/$stem-${n++}.md');
    }
    await f.writeAsString(markdown);
    return f;
  }

  static Future<List<FileSystemEntity>> list() async {
    final dir = await _dir();
    final items = dir
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.md'))
        .toList();
    items.sort((a, b) => b.statSync().modified.compareTo(a.statSync().modified));
    return items;
  }

  static Future<void> delete(FileSystemEntity f) async {
    if (await f.exists()) await f.delete();
  }
}
