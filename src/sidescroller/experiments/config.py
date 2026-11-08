"""Small, strict TOML configuration. Simulation constants stay fixed in Phase 1.5."""
from dataclasses import asdict, dataclass, field, fields
import math
from pathlib import Path
import tomllib
from sidescroller.settings import RewardSettings, ENVIRONMENT, TILEMAP, FPS, SCREEN_WIDTH, SCREEN_HEIGHT


@dataclass(frozen=True)
class TrainingSettings:
    episodes: int = 2
    max_steps: int = 1000
    batch_size: int = 64
    seed: int = 0
    device: str = 'cpu'
    learning_rate: float = 1e-4
    gamma: float = 0.99
    epsilon_start: float = 1.0
    epsilon_min: float = 0.05
    epsilon_decay: float = 0.995
    target_update_episodes: int = 10
    replay_capacity: int = 100000
    torch_threads: int = 1


@dataclass(frozen=True)
class SimulationSettings:
    level: int = 1
    timing: str = 'frame'
    fps: int = FPS
    screen_width: int = SCREEN_WIDTH
    screen_height: int = SCREEN_HEIGHT


def simulation_constants():
    return {name: {key: value for key, value in vars(type(obj)).items()
                   if key.isupper()} for name, obj in [('physics', ENVIRONMENT), ('tiles', TILEMAP)]}


@dataclass(frozen=True)
class ExperimentConfig:
    training: TrainingSettings = field(default_factory=TrainingSettings)
    reward: RewardSettings = field(default_factory=RewardSettings)
    simulation: SimulationSettings = field(default_factory=SimulationSettings)

    def __post_init__(self):
        for section in (self.training, self.reward, self.simulation):
            defaults = type(section)()
            for f in fields(section):
                value = getattr(section, f.name)
                expected = type(getattr(defaults, f.name))
                if expected is float:
                    valid = type(value) in (int, float) and math.isfinite(value)
                else:
                    valid = type(value) is expected
                if not valid:
                    raise ValueError(f'Invalid {type(section).__name__}.{f.name}: {value!r}')
        t = self.training
        for name in ('episodes', 'max_steps', 'batch_size', 'target_update_episodes',
                     'replay_capacity', 'torch_threads'):
            if getattr(t, name) <= 0:
                raise ValueError(f'{name} must be positive')
        if not 0 <= t.seed <= t.seed + t.episodes - 1 < 2**32:
            raise ValueError('seed must be in [0, 2**32)')
        if t.batch_size > t.replay_capacity or t.learning_rate <= 0:
            raise ValueError('batch_size exceeds replay capacity or learning_rate is not positive')
        if not (0 <= t.gamma <= 1 and 0 <= t.epsilon_min <= t.epsilon_start <= 1
                and 0 <= t.epsilon_decay <= 1):
            raise ValueError('Invalid gamma or epsilon schedule')
        if t.device != 'cpu' and t.device != 'cuda' and not (
                t.device.startswith('cuda:') and t.device[5:].isdigit()):
            raise ValueError('device must be cpu, cuda, or cuda:N')
        if self.simulation != SimulationSettings():
            raise ValueError('Phase 1.5 preserves baseline simulation settings')

    def resolved(self):
        return {**asdict(self), 'simulation_constants': simulation_constants()}


def load_config(path=None):
    if path is None:
        return ExperimentConfig()
    with Path(path).open('rb') as stream:
        data = tomllib.load(stream)
    if set(data) - {'training', 'reward', 'simulation'}:
        raise ValueError('Unknown configuration section')
    try:
        return ExperimentConfig(TrainingSettings(**data.get('training', {})),
                                RewardSettings(**data.get('reward', {})),
                                SimulationSettings(**data.get('simulation', {})))
    except TypeError as exc:
        raise ValueError(f'Invalid configuration: {exc}') from exc
