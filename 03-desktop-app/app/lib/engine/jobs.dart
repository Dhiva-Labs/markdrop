import 'dart:async';

import 'package:flutter/foundation.dart';

import 'sidecar.dart';

enum JobStatus { queued, converting, done, failed }

class Job {
  Job(this.source);
  final String source;
  JobStatus status = JobStatus.queued;
  String? title;
  String? markdown;
  String? error;

  String get name {
    final s = source;
    if (s.startsWith('http')) return s;
    return s.split('/').last;
  }
}

/// Serial queue over one warm sidecar; notifies listeners on every change.
class JobQueue extends ChangeNotifier {
  JobQueue(this.sidecar);
  final Sidecar sidecar;
  final jobs = <Job>[];
  Job? selected;
  bool _running = false;

  void addAll(Iterable<String> sources) {
    for (final s in sources) {
      jobs.add(Job(s));
    }
    notifyListeners();
    _pump();
  }

  void select(Job job) {
    selected = job;
    notifyListeners();
  }

  void clearFinished() {
    jobs.removeWhere((j) => j.status == JobStatus.done || j.status == JobStatus.failed);
    if (selected != null && !jobs.contains(selected)) selected = null;
    notifyListeners();
  }

  Future<void> _pump() async {
    if (_running) return;
    _running = true;
    try {
      while (true) {
        Job? next;
        for (final j in jobs) {
          if (j.status == JobStatus.queued) {
            next = j;
            break;
          }
        }
        if (next == null) break;
        next.status = JobStatus.converting;
        notifyListeners();
        try {
          final res = await sidecar.convert(next.source);
          if (res['ok'] == true) {
            next.status = JobStatus.done;
            next.title = res['title'] as String?;
            next.markdown = res['markdown'] as String?;
            selected ??= next;
            if (selected != null && selected!.status != JobStatus.done) {
              selected = next;
            }
          } else {
            next.status = JobStatus.failed;
            next.error = res['error']?.toString() ?? 'Unknown error';
          }
        } catch (e) {
          next.status = JobStatus.failed;
          next.error = e.toString();
        }
        notifyListeners();
      }
    } finally {
      _running = false;
    }
  }
}
