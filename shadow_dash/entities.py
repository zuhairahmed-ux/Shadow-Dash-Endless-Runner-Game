"""Gameplay entities for Shadow Dash: Endless Escape."""

import math
import random

import pygame

import settings


class Player(object):
    """Player physics, collision box, and state-based animation."""

    def __init__(self):
        self.x = settings.PLAYER_START_X
        self.y = settings.GROUND_Y - settings.PLAYER_HEIGHT
        self.width = settings.PLAYER_WIDTH
        self.height = settings.PLAYER_HEIGHT
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        self.vel_y = 0.0
        self.on_ground = True
        self.was_on_ground = True
        self.jump_count = 0
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0
        self.slide_timer = 0.0
        self.slide_cooldown = 0.0
        self.invulnerable_timer = 0.0
        self.animation_timer = 0.0
        self.state = "run"
        self.dead = False

    def reset(self):
        self.__init__()

    def queue_jump(self):
        self.jump_buffer = settings.JUMP_BUFFER_TIME

    def start_slide(self):
        if self.on_ground and self.slide_cooldown <= 0.0 and not self.dead:
            self.slide_timer = settings.SLIDE_DURATION
            self.slide_cooldown = settings.SLIDE_DURATION + settings.SLIDE_COOLDOWN
            self._apply_slide_rect()

    def hurt(self):
        self.state = "hurt"
        self.invulnerable_timer = 0.55

    def die(self):
        self.dead = True
        self.state = "death"

    def update(self, dt, slide_held):
        self.was_on_ground = self.on_ground
        self.animation_timer += dt

        if self.jump_buffer > 0.0:
            self.jump_buffer -= dt
        if self.coyote_timer > 0.0:
            self.coyote_timer -= dt
        if self.slide_cooldown > 0.0:
            self.slide_cooldown -= dt
        if self.invulnerable_timer > 0.0:
            self.invulnerable_timer -= dt

        if self.slide_timer > 0.0:
            self.slide_timer -= dt
            if not slide_held and self.slide_timer < settings.SLIDE_DURATION * 0.45:
                self.slide_timer = 0.0

        if self.jump_buffer > 0.0:
            self._try_jump()

        self.vel_y += settings.GRAVITY * dt
        if self.vel_y > settings.MAX_FALL_SPEED:
            self.vel_y = settings.MAX_FALL_SPEED
        self.y += self.vel_y * dt

        if self.y + self.height >= settings.GROUND_Y:
            self.y = settings.GROUND_Y - self.height
            self.vel_y = 0.0
            self.on_ground = True
            self.coyote_timer = settings.COYOTE_TIME
            self.jump_count = 0
        else:
            self.on_ground = False

        if self.dead:
            self.state = "death"
        elif self.invulnerable_timer > 0.0:
            self.state = "hurt"
        elif self.slide_timer > 0.0 and self.on_ground:
            self.state = "slide"
        elif not self.on_ground and self.jump_count >= 2:
            self.state = "double_jump"
        elif not self.on_ground:
            self.state = "jump"
        else:
            self.state = "run"

        if self.state == "slide":
            self._apply_slide_rect()
        else:
            self._apply_stand_rect()

    def _try_jump(self):
        can_ground_jump = self.on_ground or self.coyote_timer > 0.0
        can_double_jump = (not can_ground_jump) and self.jump_count < 2

        if can_ground_jump:
            self.vel_y = settings.JUMP_FORCE
            self.jump_count = 1
            self.on_ground = False
            self.coyote_timer = 0.0
            self.slide_timer = 0.0
            self.jump_buffer = 0.0
        elif can_double_jump:
            self.vel_y = settings.DOUBLE_JUMP_FORCE
            self.jump_count = 2
            self.jump_buffer = 0.0

    def _apply_stand_rect(self):
        bottom = self.y + self.height
        self.width = settings.PLAYER_WIDTH
        self.height = settings.PLAYER_HEIGHT
        self.y = bottom - self.height
        self.rect = pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def _apply_slide_rect(self):
        bottom = self.y + self.height
        self.width = settings.PLAYER_SLIDE_WIDTH
        self.height = settings.PLAYER_SLIDE_HEIGHT
        self.y = bottom - self.height
        self.rect = pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def just_landed(self):
        return self.on_ground and not self.was_on_ground

    def draw(self, surface, offset):
        rect = self.rect.move(offset)
        flicker = self.invulnerable_timer > 0.0 and int(self.animation_timer * 18) % 2 == 0
        if flicker:
            return

        glow_rect = rect.inflate(24, 24)
        glow = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        glow_color = (48, 232, 255, 36)
        if self.state == "double_jump":
            glow_color = (255, 52, 176, 44)
        elif self.state == "hurt" or self.state == "death":
            glow_color = (255, 78, 92, 50)
        pygame.draw.rect(glow, glow_color, glow.get_rect(), border_radius=14)
        surface.blit(glow, glow_rect)

        if self.state == "slide":
            self._draw_slide_pose(surface, rect)
        else:
            self._draw_runner_pose(surface, rect)

    def _draw_runner_pose(self, surface, rect):
        phase = math.sin(self.animation_timer * 13.5)
        bounce = 0
        if self.on_ground and self.state == "run":
            bounce = int(abs(math.sin(self.animation_timer * 13.5)) * 3)
        if self.state == "hurt":
            bounce += int(math.sin(self.animation_timer * 40.0) * 2)
        if self.state == "death":
            bounce = 8

        body = pygame.Rect(rect.x + 9, rect.y + 25 + bounce, 30, 34)
        head = pygame.Rect(rect.x + 5, rect.y + 2 + bounce, 34, 30)

        self._draw_runner_legs(surface, rect, phase, bounce)
        self._draw_runner_arms(surface, rect, phase, bounce)

        pygame.draw.rect(surface, settings.HERO_OUTLINE, body.inflate(6, 6), border_radius=8)
        pygame.draw.rect(surface, settings.HERO_SHIRT, body, border_radius=7)
        overalls = pygame.Rect(body.x + 5, body.y + 8, body.width - 8, body.height - 4)
        pygame.draw.rect(surface, settings.HERO_OVERALLS, overalls, border_radius=5)
        pygame.draw.line(
            surface, settings.HERO_OVERALLS_DARK,
            (body.x + 10, body.y + 9),
            (body.x + 18, body.bottom - 3),
            4
        )
        pygame.draw.line(
            surface, settings.HERO_OVERALLS_DARK,
            (body.right - 8, body.y + 9),
            (body.x + 19, body.bottom - 3),
            4
        )
        pygame.draw.circle(surface, settings.NEON_AMBER, (body.x + 12, body.y + 17), 2)
        pygame.draw.circle(surface, settings.NEON_AMBER, (body.right - 10, body.y + 17), 2)

        if self.state == "double_jump":
            pygame.draw.arc(surface, settings.NEON_MAGENTA, rect.inflate(22, 18), 0.4, 5.5, 3)

        self._draw_head(surface, head, looking_hurt=self.state == "hurt")

    def _draw_runner_legs(self, surface, rect, phase, bounce):
        hip_y = rect.y + 57 + bounce
        if not self.on_ground:
            front_knee = (rect.x + 33, hip_y + 11)
            back_knee = (rect.x + 15, hip_y + 4)
            front_foot = (rect.x + 39, rect.bottom - 1)
            back_foot = (rect.x + 11, rect.bottom - 4)
        else:
            front_knee = (rect.x + 26 + int(8 * phase), hip_y + 10)
            back_knee = (rect.x + 21 - int(8 * phase), hip_y + 9)
            front_foot = (rect.x + 31 + int(15 * phase), rect.bottom + 3)
            back_foot = (rect.x + 21 - int(15 * phase), rect.bottom + 3)

        self._draw_limb(surface, (rect.x + 30, hip_y), front_knee, front_foot, settings.HERO_OVERALLS)
        self._draw_limb(surface, (rect.x + 18, hip_y), back_knee, back_foot, settings.HERO_OVERALLS_DARK)
        self._draw_boot(surface, front_foot)
        self._draw_boot(surface, back_foot)

    def _draw_runner_arms(self, surface, rect, phase, bounce):
        shoulder_y = rect.y + 36 + bounce
        if not self.on_ground:
            front_hand = (rect.x + 41, shoulder_y + 2)
            back_hand = (rect.x + 3, shoulder_y + 13)
        else:
            front_hand = (rect.x + 41 - int(8 * phase), shoulder_y + 16)
            back_hand = (rect.x + 5 + int(7 * phase), shoulder_y + 7)

        self._draw_arm(surface, (rect.x + 34, shoulder_y), front_hand)
        self._draw_arm(surface, (rect.x + 13, shoulder_y + 2), back_hand)

    def _draw_slide_pose(self, surface, rect):
        body = pygame.Rect(rect.x + 14, rect.y + 12, 43, 22)
        head = pygame.Rect(rect.x + 50, rect.y + 2, 25, 24)

        pygame.draw.ellipse(surface, (0, 0, 0, 80), (rect.x + 5, rect.bottom - 8, rect.width - 6, 10))
        pygame.draw.rect(surface, settings.HERO_OUTLINE, body.inflate(6, 6), border_radius=10)
        pygame.draw.rect(surface, settings.HERO_OVERALLS, body, border_radius=9)
        pygame.draw.rect(surface, settings.HERO_SHIRT, (body.x + 2, body.y + 2, 18, body.height - 4), border_radius=7)
        pygame.draw.line(surface, settings.NEON_CYAN, (body.x + 4, body.bottom - 3), (body.right - 3, body.bottom - 3), 2)

        pygame.draw.line(surface, settings.HERO_OUTLINE, (rect.x + 12, rect.y + 21), (rect.x + 2, rect.y + 29), 7)
        pygame.draw.circle(surface, settings.HERO_GLOVE, (rect.x + 2, rect.y + 29), 5)
        self._draw_boot(surface, (rect.x + 17, rect.bottom - 2))
        self._draw_boot(surface, (rect.x + 42, rect.bottom - 1))
        self._draw_head(surface, head, looking_hurt=False)

    def _draw_head(self, surface, head, looking_hurt):
        pygame.draw.ellipse(surface, settings.HERO_OUTLINE, head.inflate(6, 6))
        pygame.draw.ellipse(surface, settings.HERO_SKIN, head)

        cap = pygame.Rect(head.x - 2, head.y - 7, head.width + 5, 18)
        brim = pygame.Rect(head.right - 4, head.y + 4, 16, 7)
        pygame.draw.rect(surface, settings.HERO_CAP_DARK, cap.inflate(3, 3), border_radius=8)
        pygame.draw.rect(surface, settings.HERO_CAP, cap, border_radius=8)
        pygame.draw.ellipse(surface, settings.HERO_CAP, brim)
        pygame.draw.circle(surface, settings.SOFT_WHITE, (cap.centerx, cap.y + 8), 5)
        pygame.draw.circle(surface, settings.NEON_CYAN, (cap.centerx, cap.y + 8), 2)

        eye_y = head.y + 13
        pygame.draw.circle(surface, settings.HERO_OUTLINE, (head.x + 22, eye_y), 3)
        if looking_hurt:
            pygame.draw.line(surface, settings.HERO_OUTLINE, (head.x + 7, eye_y - 2), (head.x + 15, eye_y + 3), 2)
        else:
            pygame.draw.circle(surface, settings.HERO_OUTLINE, (head.x + 12, eye_y), 2)
        pygame.draw.rect(surface, settings.HERO_OUTLINE, (head.right - 2, head.y + 17, 6, 4), border_radius=2)
        pygame.draw.arc(surface, settings.HERO_OUTLINE, (head.x + 9, head.y + 17, 15, 8), 0.1, 2.6, 2)

    def _draw_limb(self, surface, hip, knee, foot, color):
        pygame.draw.line(surface, settings.HERO_OUTLINE, hip, knee, 8)
        pygame.draw.line(surface, settings.HERO_OUTLINE, knee, foot, 8)
        pygame.draw.line(surface, color, hip, knee, 5)
        pygame.draw.line(surface, color, knee, foot, 5)

    def _draw_arm(self, surface, shoulder, hand):
        pygame.draw.line(surface, settings.HERO_OUTLINE, shoulder, hand, 8)
        pygame.draw.line(surface, settings.HERO_SHIRT, shoulder, hand, 5)
        pygame.draw.circle(surface, settings.HERO_OUTLINE, hand, 7)
        pygame.draw.circle(surface, settings.HERO_GLOVE, hand, 5)

    def _draw_boot(self, surface, foot):
        boot = pygame.Rect(foot[0] - 8, foot[1] - 5, 18, 10)
        pygame.draw.rect(surface, settings.HERO_OUTLINE, boot.inflate(3, 3), border_radius=5)
        pygame.draw.rect(surface, settings.HERO_BOOT, boot, border_radius=5)


class Obstacle(object):
    """A reusable moving obstacle with a few visual/collision variants."""

    DATA = {
        "spike": {"size": (44, 44), "y": settings.GROUND_Y - 44},
        "rock": {"size": (56, 48), "y": settings.GROUND_Y - 48},
        "wall": {"size": (40, 92), "y": settings.GROUND_Y - 92},
        "drone": {"size": (58, 34), "y": settings.GROUND_Y - 92},
    }

    def __init__(self, kind, x):
        self.kind = kind
        data = self.DATA[kind]
        self.width, self.height = data["size"]
        self.x = float(x)
        self.y = float(data["y"])
        self.rect = pygame.Rect(int(self.x), int(self.y), self.width, self.height)
        self.phase = random.random() * math.pi * 2.0
        self.passed = False

    def update(self, dt, speed):
        self.x -= speed * dt
        if self.kind == "drone":
            self.phase += dt * 4.0
            self.y += math.sin(self.phase) * 18.0 * dt
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def is_offscreen(self):
        return self.x + self.width < -80

    def draw(self, surface, offset):
        rect = self.rect.move(offset)
        if self.kind == "spike":
            points = [(rect.centerx, rect.y), (rect.right, rect.bottom), (rect.x, rect.bottom)]
            pygame.draw.polygon(surface, settings.HOT_RED, points)
            pygame.draw.lines(surface, settings.NEON_AMBER, True, points, 2)
        elif self.kind == "rock":
            pygame.draw.ellipse(surface, (70, 78, 98), rect)
            pygame.draw.ellipse(surface, settings.NEON_PURPLE, rect, 2)
            pygame.draw.line(surface, (42, 47, 68), rect.midleft, rect.center, 3)
        elif self.kind == "wall":
            pygame.draw.rect(surface, (51, 59, 88), rect, border_radius=4)
            for y in range(rect.y + 12, rect.bottom, 22):
                pygame.draw.line(surface, settings.NEON_MAGENTA, (rect.x + 4, y), (rect.right - 4, y), 2)
            pygame.draw.rect(surface, settings.NEON_CYAN, rect, 2, border_radius=4)
        elif self.kind == "drone":
            pygame.draw.rect(surface, (42, 45, 70), rect, border_radius=12)
            pygame.draw.circle(surface, settings.NEON_MAGENTA, rect.center, 9)
            pygame.draw.line(surface, settings.NEON_CYAN, (rect.x - 12, rect.centery), (rect.x, rect.centery), 3)
            pygame.draw.line(surface, settings.NEON_CYAN, (rect.right, rect.centery), (rect.right + 12, rect.centery), 3)


class Coin(object):
    """Animated collectible coin."""

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.radius = 11
        self.rect = pygame.Rect(int(x - 11), int(y - 11), 22, 22)
        self.animation = random.random() * math.pi * 2.0
        self.collected = False

    def update(self, dt, speed):
        self.x -= speed * dt
        self.animation += dt * 8.0
        self.rect.x = int(self.x - self.radius)
        self.rect.y = int(self.y - self.radius)

    def is_offscreen(self):
        return self.x + self.radius < -50

    def draw(self, surface, offset):
        cx = int(self.x + offset[0])
        cy = int(self.y + offset[1])
        pulse = 0.65 + 0.35 * abs(math.sin(self.animation))
        width = max(4, int(self.radius * pulse))
        pygame.draw.ellipse(
            surface, settings.NEON_AMBER,
            pygame.Rect(cx - width, cy - self.radius, width * 2, self.radius * 2)
        )
        pygame.draw.ellipse(
            surface, settings.SOFT_WHITE,
            pygame.Rect(cx - width, cy - self.radius, width * 2, self.radius * 2), 2
        )


class PowerUp(object):
    """Collectible ability item: shield, magnet, or slow motion."""

    COLORS = {
        "shield": settings.NEON_CYAN,
        "magnet": settings.NEON_MAGENTA,
        "slowmo": settings.NEON_LIME,
    }

    LABELS = {
        "shield": "S",
        "magnet": "M",
        "slowmo": "T",
    }

    def __init__(self, kind, x, y):
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.size = 30
        self.rect = pygame.Rect(int(x), int(y), self.size, self.size)
        self.animation = random.random() * math.pi * 2.0

    def update(self, dt, speed):
        self.x -= speed * dt
        self.animation += dt * 5.5
        bob = math.sin(self.animation) * 4.0
        self.rect.x = int(self.x)
        self.rect.y = int(self.y + bob)

    def is_offscreen(self):
        return self.x + self.size < -50

    def draw(self, surface, offset):
        rect = self.rect.move(offset)
        color = self.COLORS[self.kind]
        glow_rect = rect.inflate(14, 14)
        glow = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (color[0], color[1], color[2], 46), glow.get_rect())
        surface.blit(glow, glow_rect)

        pygame.draw.rect(surface, settings.HUD_PANEL, rect, border_radius=7)
        pygame.draw.rect(surface, color, rect, 3, border_radius=7)

        cx, cy = rect.center
        if self.kind == "shield":
            points = [(cx, rect.y + 5), (rect.right - 6, cy), (cx, rect.bottom - 4), (rect.x + 6, cy)]
            pygame.draw.polygon(surface, color, points, 2)
        elif self.kind == "magnet":
            pygame.draw.arc(surface, color, rect.inflate(-8, -8), 0.2, math.pi - 0.2, 4)
            pygame.draw.line(surface, color, (rect.x + 8, cy), (rect.x + 8, rect.bottom - 7), 4)
            pygame.draw.line(surface, color, (rect.right - 8, cy), (rect.right - 8, rect.bottom - 7), 4)
        else:
            pygame.draw.circle(surface, color, (cx, cy), 9, 2)
            pygame.draw.line(surface, color, (cx, cy), (cx + 7, cy - 5), 3)
            pygame.draw.line(surface, color, (cx, cy), (cx, cy + 7), 3)


class BackgroundLayer(object):
    """Infinite parallax layer drawn from primitive neon city elements."""

    def __init__(self, speed_factor, color, density, kind):
        self.speed_factor = speed_factor
        self.color = color
        self.kind = kind
        self.elements = []
        self.offset = 0.0
        self._create_elements(density)

    def _create_elements(self, density):
        width = settings.SCREEN_WIDTH * 2
        if self.kind == "stars":
            for _ in range(density):
                self.elements.append((
                    random.randint(0, width),
                    random.randint(20, 230),
                    random.randint(1, 3),
                    random.randint(1, 3)
                ))
        elif self.kind == "buildings":
            x = 0
            while x < width + 100:
                w = random.randint(34, 88)
                h = random.randint(80, 250)
                y = settings.GROUND_Y - h
                self.elements.append((x, y, w, h))
                x += w + random.randint(8, 34)
        elif self.kind == "signs":
            for _ in range(density):
                self.elements.append((
                    random.randint(0, width),
                    random.randint(130, 350),
                    random.randint(28, 70),
                    random.randint(6, 16)
                ))
        else:
            for _ in range(density):
                self.elements.append((
                    random.randint(0, width),
                    random.randint(settings.GROUND_Y + 12, settings.SCREEN_HEIGHT - 15),
                    random.randint(80, 190),
                    2
                ))

    def update(self, dt, speed):
        self.offset -= speed * self.speed_factor * dt
        wrap_width = settings.SCREEN_WIDTH * 2
        if self.offset <= -wrap_width:
            self.offset += wrap_width

    def draw(self, surface):
        wrap_width = settings.SCREEN_WIDTH * 2
        for repeat in (0, wrap_width):
            ox = int(self.offset + repeat)
            for element in self.elements:
                x, y, w, h = element
                draw_x = x + ox
                if draw_x + w < -20 or draw_x > settings.SCREEN_WIDTH + 20:
                    continue
                if self.kind == "stars":
                    pygame.draw.rect(surface, self.color, (draw_x, y, w, h))
                elif self.kind == "buildings":
                    rect = pygame.Rect(draw_x, y, w, h)
                    pygame.draw.rect(surface, self.color, rect)
                    if w > 45:
                        for wy in range(y + 14, y + h - 10, 28):
                            pygame.draw.rect(surface, settings.NEON_AMBER, (draw_x + 9, wy, 8, 4))
                            pygame.draw.rect(surface, settings.NEON_CYAN, (draw_x + w - 18, wy + 8, 8, 4))
                elif self.kind == "signs":
                    pygame.draw.rect(surface, self.color, (draw_x, y, w, h), border_radius=4)
                else:
                    pygame.draw.line(surface, self.color, (draw_x, y), (draw_x + w, y), h)


class Particle(object):
    """Small fading particle used by several effects."""

    def __init__(self, x, y, vx, vy, color, life, radius):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.life = float(life)
        self.max_life = float(life)
        self.radius = float(radius)

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 320.0 * dt

    def is_dead(self):
        return self.life <= 0.0

    def draw(self, surface, offset):
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        radius = max(1, int(self.radius * (self.life / self.max_life)))
        particle_surface = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(
            particle_surface,
            (self.color[0], self.color[1], self.color[2], alpha),
            (radius + 1, radius + 1),
            radius
        )
        surface.blit(particle_surface, (int(self.x + offset[0]) - radius, int(self.y + offset[1]) - radius))


class ParticleSystem(object):
    """Lightweight particle manager with a fixed upper limit."""

    def __init__(self):
        self.particles = []

    def clear(self):
        self.particles = []

    def emit(self, x, y, count, color, spread, speed_min, speed_max, life):
        for _ in range(count):
            if len(self.particles) >= settings.MAX_PARTICLES:
                self.particles.pop(0)
            angle = random.uniform(-spread, spread)
            speed = random.uniform(speed_min, speed_max)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            radius = random.uniform(2.0, 5.0)
            self.particles.append(Particle(x, y, vx, vy, color, life, radius))

    def emit_burst(self, x, y, count, color):
        for _ in range(count):
            if len(self.particles) >= settings.MAX_PARTICLES:
                self.particles.pop(0)
            angle = random.uniform(0.0, math.pi * 2.0)
            speed = random.uniform(80.0, 330.0)
            self.particles.append(Particle(
                x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                color, random.uniform(0.35, 0.75), random.uniform(2.0, 6.0)
            ))

    def update(self, dt):
        alive = []
        for particle in self.particles:
            particle.update(dt)
            if not particle.is_dead():
                alive.append(particle)
        self.particles = alive

    def draw(self, surface, offset):
        for particle in self.particles:
            particle.draw(surface, offset)
