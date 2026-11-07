import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import unittest
import numpy as np
import pygame
import torch
from gymnasium.utils.env_checker import check_env
from gymenv import ShooterEnv
from dqn_model import DQN, ReplayBuffer
from dqn_train import optimize


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
