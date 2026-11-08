import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from sidescroller.env import ShooterEnv
from sidescroller.experiments.config import ExperimentConfig, load_config
from trajectory import snapshot

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
ROOT = Path(__file__).resolve().parents[1]


class ExperimentTests(unittest.TestCase):
    def test_golden_trajectory_from_unrelated_directory(self):
        fixture = json.loads((ROOT / 'tests/fixtures/baseline.json').read_text())
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                for run in fixture['runs']:
                    env = ShooterEnv(max_episode_steps=fixture['max_steps'])
                    try:
                        obs, _ = env.reset(seed=run['seed'])
                        self.assertEqual(snapshot(env, obs), run['records'][0])
                        for index, action in enumerate(run['actions'], 1):
                            obs, reward, terminal, truncated, _ = env.step(action)
                            self.assertEqual(snapshot(env, obs, reward, terminal, truncated),
                                             run['records'][index], f"seed={run['seed']} step={index}")
                    finally:
                        env.close()
            finally:
                os.chdir(previous)

    def test_baseline_config_and_validation(self):
        self.assertEqual(load_config(ROOT / 'configs/baseline.toml'), ExperimentConfig())
        default = ExperimentConfig()
        for changes in ({'batch_size': 0}, {'episodes': True}, {'gamma': 1.2},
                        {'learning_rate': float('nan')}, {'epsilon_min': 2},
                        {'batch_size': 100001}, {'seed': -1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(default, training=replace(default.training, **changes))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.toml'
            for text in ('[unknown]\na=1', '[training]\nbatch_siz=3', '[simulation]\nfps=30'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_training_metadata_and_weights_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            run = directory / 'run'
            command = [sys.executable, '-m', 'sidescroller.rl.train', '--config',
                       str(ROOT / 'configs/baseline.toml'), '--episodes', '2', '--max-steps', '20',
                       '--batch-size', '8', '--seed', '7', '--run-dir', str(run)]
            result = subprocess.run(command, cwd=folder, env=dict(os.environ), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            metrics = [json.loads(line) for line in (run / 'episodes.jsonl').read_text().splitlines()]
            self.assertEqual(len(metrics), 2)
            self.assertEqual([m['seed'] for m in metrics], [7, 8])
            self.assertTrue(all(m['updates'] > 0 and m['loss'] is not None for m in metrics))
            config = json.loads((run / 'config.json').read_text())
            self.assertEqual(config['training']['max_steps'], 20)
            self.assertEqual(config['simulation_constants']['physics']['GRAVITY'], 0.75)
            metadata = json.loads((run / 'metadata.json').read_text())
            self.assertIn('commit', metadata['git'])
            self.assertFalse(metadata['resume'])
            weights = run / metadata['checkpoint']
            self.assertTrue(weights.is_file())
            second = directory / 'loaded'
            subprocess.run(command[:-1] + [str(second), '--load', str(weights)],
                           cwd=folder, env=dict(os.environ), check=True, capture_output=True, text=True)
            self.assertEqual(json.loads((second / 'metadata.json').read_text())['weights_loaded'], str(weights.resolve()))
            playback_config = directory / 'playback.toml'
            playback_config.write_text('[training]\nmax_steps=2\nseed=7\n')
            result = subprocess.run(
                [sys.executable, '-m', 'sidescroller.rl.playback', str(weights),
                 '--config', str(playback_config)], cwd=folder, env=dict(os.environ),
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # Reusing a run directory must fail, never overwrite an experiment.
            result = subprocess.run(command, cwd=folder, env=dict(os.environ), capture_output=True)
            self.assertNotEqual(result.returncode, 0)
