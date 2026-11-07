import os
import unittest
import gymnasium as gym
from settings import DEFAULT_EPISODE_STEPS, RewardSettings
import numpy as np
import pygame
import torch
from gymnasium.utils.env_checker import check_env
from gymenv import ShooterEnv
from dqn_model import DQN, ReplayBuffer
from dqn_train import optimize

# Gymnasium 1.1.1 overwrites SDL_AUDIODRIVER with "dsp" when imported on Linux.
# Apply test backends after imports but before any Pygame subsystem initializes.
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.env = ShooterEnv(max_episode_steps=100)

    def tearDown(self):
        self.env.close()

    def test_checker(self):
        check_env(self.env, skip_render_check=True)
        self.assertFalse(pygame.mixer.get_init())

    def test_complete_episode_and_seed(self):
        def rollout():
            obs, _ = self.env.reset(seed=12)
            records = [obs]
            for i in range(100):
                obs, reward, terminated, truncated, _ = self.env.step(i % 7)
                self.assertTrue(self.env.observation_space.contains(obs))
                self.assertTrue(np.isfinite(reward))
                records.append(obs)
                if terminated or truncated:
                    break
            self.assertTrue(terminated or truncated)
            return np.array(records)
        np.testing.assert_array_equal(rollout(), rollout())

    def test_terminal_and_time_limit(self):
        self.env.reset(seed=1)
        self.env.game.player.health = 0
        _, reward, terminal, truncated, _ = self.env.step(0)
        self.assertTrue(terminal)
        self.assertFalse(truncated)
        self.assertEqual(reward, -100000)
        self.env.reset(seed=1)
        next(iter(self.env.game.groups['exit'])).rect.center = self.env.game.player.rect.center
        self.assertTrue(self.env.step(5)[2])
        self.env.max_episode_steps = 1
        self.env.reset(seed=1)
        self.assertEqual(self.env.step(0)[2:4], (False, True))

    def test_frame_cooldowns_and_grenade_fuse(self):
        from settings import CounterType, ENVIRONMENT
        self.env.reset(seed=1)
        p = self.env.game.player
        self.assertEqual(p.counter_type, CounterType.FRAME_BASED)
        for _ in range(p.shoot_delay + 1):
            p.update()
        self.assertIsNotNone(p.shoot())
        self.assertIsNone(p.shoot())
        for _ in range(p.throw_delay + 1):
            p.update()
        grenade = p.throw()
        self.assertIsNotNone(grenade)
        self.assertFalse(grenade.time_based_fuse)
        for _ in range(ENVIRONMENT.GRENADE_COOLDOWN - 1):
            grenade.update()
        self.assertFalse(grenade.do_explosion)
        grenade.update()
        self.assertTrue(grenade.do_explosion)

    def test_reward_and_inventory(self):
        self.env.reset(seed=1)
        self.env.last_action = 0
        self.assertEqual(self.env._get_reward(), 0)
        self.env.game.player.rect.x += 10
        self.assertEqual(self.env._get_reward(), 1)
        self.assertEqual(self.env._get_reward(), 0)
        self.env.last_action = 5
        self.assertEqual(self.env._get_reward(), -10000)
        from weapons import ItemBox
        p = self.env.game.player
        for kind, attr, cap in [('ammo', 'ammo', p.max_ammo), ('grenade', 'grenades', p.max_grenades)]:
            box = ItemBox(0, 0, kind)
            box.rect.center = p.rect.center
            self.env.game.groups['item'].add(box)
            setattr(p, attr, cap - 1)
            self.env.game.collect_item_boxes()
            self.assertEqual(getattr(p, attr), cap)


class RegisteredLifecycleTests(unittest.TestCase):
    def test_registered_default_and_overridden_limits(self):
        # Gym's TimeLimit alone owns registered limits, so overrides can exceed 1000.
        for limit in (DEFAULT_EPISODE_STEPS, 3, DEFAULT_EPISODE_STEPS + 1):
            with self.subTest(limit=limit):
                kwargs = {} if limit == DEFAULT_EPISODE_STEPS else {'max_episode_steps': limit}
                env = gym.make('Shooter-v0', **kwargs)
                try:
                    self.assertEqual(env.spec.max_episode_steps, limit)
                    self.assertIsNone(env.unwrapped.max_episode_steps)
                    obs, _ = env.reset(seed=7)
                    self.assertTrue(env.observation_space.contains(obs))
                    # Jump commands keep the player in place, away from enemies.
                    for step in range(1, limit + 1):
                        obs, reward, terminal, truncated, _ = env.step(2)
                        self.assertTrue(env.observation_space.contains(obs))
                        self.assertTrue(np.isfinite(reward))
                        self.assertFalse(terminal)
                        self.assertEqual(truncated, step == limit)
                finally:
                    env.close()

    def test_repeated_creation_close_and_reinitialization(self):
        for mode in (None, 'human', None, 'human', None):
            with self.subTest(mode=mode):
                self.assertEqual(os.environ['SDL_AUDIODRIVER'], 'dummy')
                env = ShooterEnv(render_mode=mode, max_episode_steps=2)
                obs, _ = env.reset(seed=3)
                self.assertTrue(env.observation_space.contains(obs))
                env.step(5)
                env.render()
                env.close()
                env.close()
                self.assertFalse(pygame.display.get_init())
                self.assertFalse(pygame.mixer.get_init())
                with self.assertRaises(RuntimeError):
                    env.step(0)
                with self.assertRaises(RuntimeError):
                    env.reset()
                # Also cover external global shutdown between instances.
                pygame.quit()


class RewardTests(unittest.TestCase):
    def setUp(self):
        self.env = ShooterEnv()
        self.env.reset(seed=1)
        self.env.last_action = 0

    def tearDown(self):
        self.env.close()

    def test_progress(self):
        self.assertEqual(self.env._get_reward(), 0)
        self.env.game.player.rect.x += 10
        self.assertEqual(self.env._get_reward(), 1)
        self.assertEqual(self.env._get_reward(), 0)
        self.env.game.player.rect.x -= 20
        self.assertEqual(self.env._get_reward(), -2)

    def test_shoot_and_throw_commands(self):
        for action in (5, 6):
            with self.subTest(action=action):
                self.env.last_action = action
                self.assertEqual(self.env._get_reward(), -10000)
                self.env.game.player.rect.x += 10
                self.assertEqual(self.env._get_reward(), -9999)

    def test_death_overrides_other_components(self):
        self.env.game.player.alive = False
        self.env.game.player.rect.x += 10
        self.env.game.level_complete = True
        self.env.last_action = 6
        self.assertEqual(self.env._get_reward(), -100000)

    def test_completion_adds_to_progress_and_command(self):
        self.env.game.level_complete = True
        self.assertEqual(self.env._get_reward(), 100000)
        self.env.game.player.rect.x += 10
        self.env.last_action = 5
        self.assertEqual(self.env._get_reward(), 90001)

    def test_configurable_coefficients(self):
        self.env.reward_settings = RewardSettings(progress=2, shoot=-3, throw=-4,
                                                   death=-5, completion=6)
        self.env.game.player.rect.x += 10
        self.assertEqual(self.env._get_reward(), 20)
        for action, expected in ((5, -3), (6, -4)):
            self.env.last_action = action
            self.assertEqual(self.env._get_reward(), expected)
        self.env.last_action = 0
        self.env.game.level_complete = True
        self.assertEqual(self.env._get_reward(), 6)
        self.env.game.player.alive = False
        self.assertEqual(self.env._get_reward(), -5)


class DQNTests(unittest.TestCase):
    def test_replay_and_update(self):
        torch.manual_seed(1)
        replay = ReplayBuffer(capacity=3)
        state = torch.ones(1, 9, requires_grad=True)
        for i in range(4):
            replay.push((state, i % 7, 2, np.zeros(9), i % 2))
        state.detach().zero_()
        states, actions, rewards, next_states, dones = replay.sample(3)
        self.assertEqual(len(replay), 3)
        self.assertEqual(states.shape, (3, 9))
        self.assertEqual(next_states.shape, (3, 9))
        self.assertEqual(actions.dtype, torch.int64)
        self.assertTrue(torch.all(states == 1))
        self.assertFalse(states.requires_grad)
        online, target = DQN(9, 7), DQN(9, 7)
        target.load_state_dict(online.state_dict())
        before = [p.detach().clone() for p in online.parameters()]
        loss = optimize(online, target, replay, 3)
        self.assertTrue(np.isfinite(loss))
        self.assertTrue(any(not torch.equal(a, b) for a, b in zip(before, online.parameters())))
        self.assertTrue(all(p.grad is None for p in target.parameters()))

    def test_terminal_mask_and_truncation_bootstrap(self):
        online, target = DQN(9, 7), DQN(9, 7)
        with torch.no_grad():
            for model in (online, target):
                for p in model.parameters():
                    p.zero_()
            target.out.bias.fill_(4)
        replay = ReplayBuffer()
        replay.push((np.zeros(9), 0, 2, np.zeros(9), True))
        replay.push((np.zeros(9), 0, 2, np.zeros(9), False))
        # Huber(0,2)=1.5; Huber(0,2+0.5*4)=3.5
        self.assertAlmostEqual(optimize(online, target, replay, 2, gamma=0.5), 2.5)


if __name__ == '__main__':
    unittest.main()
