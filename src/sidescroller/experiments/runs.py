"""Write explicit run provenance and append-only episode metrics."""
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import uuid


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def git_state():
    # Inspect the installed source checkout, never an unrelated invocation directory.
    source = Path(__file__).resolve().parent
    try:
        root = subprocess.check_output(['git', '-C', str(source), 'rev-parse', '--show-toplevel'],
                                       stderr=subprocess.DEVNULL, text=True).strip()
        commit = subprocess.check_output(['git', '-C', root, 'rev-parse', 'HEAD'], text=True).strip()
        dirty = bool(subprocess.check_output(['git', '-C', root, 'status', '--porcelain'], text=True))
        return {'commit': commit, 'dirty': dirty}
    except (OSError, subprocess.CalledProcessError):
        return {'commit': None, 'dirty': None}


def create_run(config, run_dir=None, config_path=None, weights=None):
    directory = Path(run_dir) if run_dir else Path('runs') / (
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'checkpoints').mkdir()
    write_json(directory / 'config.json', config.resolved())
    write_json(directory / 'metadata.json', {
        'started_utc': datetime.now(timezone.utc).isoformat(), 'git': git_state(),
        'seed': config.training.seed, 'config_path': str(Path(config_path).resolve()) if config_path else None,
        'weights_loaded': str(Path(weights).resolve()) if weights else None,
        'resume': False, 'python': platform.python_version(),
        'dependencies': {name: importlib.metadata.version(name)
                         for name in ('numpy', 'pygame', 'gymnasium', 'torch')},
        'checkpoint': 'checkpoints/final.pt'})
    return directory


def append_metrics(directory, metrics):
    with (directory / 'episodes.jsonl').open('a') as stream:
        stream.write(json.dumps(metrics, allow_nan=False) + '\n')
