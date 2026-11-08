"""Shared state projection used by the pre-refactor golden fixture."""
def snapshot(env, observation, reward=None, terminated=False, truncated=False):
    p = env.game.player
    def soldier(s):
        return [list(s.rect), s.vel_x, s.vel_y, s.health, s.ammo, s.grenades,
                s.alive, s.in_air, int(s.direction), int(s.action), s.frame_idx,
                s.shoot_time, s.throw_time]
    return dict(observation=observation.tolist(), reward=reward,
                terminated=terminated, truncated=truncated, player=soldier(p),
                enemies=[soldier(e) for e in env.game.groups['enemy']],
                bullets=[list(b.rect) for b in env.game.groups['bullet']],
                grenades=[[list(g.rect), g.throw_time, g.do_explosion]
                          for g in env.game.groups['grenade']],
                camera=[env.game.camera_scroll, env.game.bg_scroll])
