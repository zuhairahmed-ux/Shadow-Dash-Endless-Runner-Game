"""Main controller for Shadow Dash: Endless Escape."""

import array
import math
import os
import random

import pygame

import settings
from entities import BackgroundLayer, Coin, Obstacle, ParticleSystem, Player


STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"


class SoundManager(object):
    """Small audio wrapper that works even when asset files are missing."""

    def __init__(self, asset_dir):
        self.asset_dir = asset_dir
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init(44100, -16, 1, 512)
            except pygame.error:
                pass
        self.enabled = pygame.mixer.get_init() is not None
        self.muted = False
        self.sounds = {}
        self.music_sound = None
        self.music_channel = None

        if not self.enabled:
            return

        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(1)
        self.music_channel = pygame.mixer.Channel(0)
        self.sounds["jump"] = self._load_or_tone(settings.ASSET_JUMP_SOUND, 620, 0.08)
        self.sounds["coin"] = self._load_or_tone(settings.ASSET_COIN_SOUND, 940, 0.07)
        self.sounds["hit"] = self._load_or_tone(settings.ASSET_HIT_SOUND, 140, 0.16)
        self.music_sound = self._load_music_or_loop()

    def _asset_path(self, filename):
        return os.path.join(self.asset_dir, filename)

    def _load_or_tone(self, filename, frequency, duration):
        path = self._asset_path(filename)
        if os.path.exists(path):
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(settings.SFX_VOLUME * settings.MASTER_VOLUME)
                return sound
            except pygame.error:
                pass
        sound = self._make_tone(frequency, duration)
        if sound:
            sound.set_volume(settings.SFX_VOLUME * settings.MASTER_VOLUME)
        return sound

    def _load_music_or_loop(self):
        path = self._asset_path(settings.ASSET_MUSIC)
        if os.path.exists(path):
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(settings.MUSIC_VOLUME * settings.MASTER_VOLUME)
                return sound
            except pygame.error:
                pass
        sound = self._make_music_loop()
        if sound:
            sound.set_volume(settings.MUSIC_VOLUME * settings.MASTER_VOLUME)
        return sound

    def _make_tone(self, frequency, duration):
        try:
            sample_rate = 44100
            sample_count = int(sample_rate * duration)
            samples = array.array("h")
            for i in range(sample_count):
                t = float(i) / sample_rate
                envelope = max(0.0, 1.0 - (t / duration))
                value = int(math.sin(2.0 * math.pi * frequency * t) * 9000 * envelope)
                samples.append(value)
            return pygame.mixer.Sound(buffer=samples.tobytes())
        except (pygame.error, AttributeError):
            return None

    def _make_music_loop(self):
        try:
            sample_rate = 44100
            duration = 2.4
            sample_count = int(sample_rate * duration)
            samples = array.array("h")
            bass_notes = [55.0, 55.0, 65.41, 73.42]
            lead_notes = [220.0, 277.18, 329.63, 415.30, 329.63, 277.18, 246.94, 329.63]
            for i in range(sample_count):
                t = float(i) / sample_rate
                beat = int(t / 0.3)
                bass = bass_notes[beat % len(bass_notes)]
                lead = lead_notes[beat % len(lead_notes)]
                beat_position = (t % 0.3) / 0.3
                pulse = 1.0 - beat_position
                wave = math.sin(2.0 * math.pi * bass * t) * 0.50
                wave += math.sin(2.0 * math.pi * lead * t) * 0.30 * pulse
                wave += math.sin(2.0 * math.pi * lead * 2.0 * t) * 0.12 * pulse
                samples.append(int(wave * 15500))
            return pygame.mixer.Sound(buffer=samples.tobytes())
        except (pygame.error, AttributeError):
            return None

    def play(self, name):
        if self.muted or not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.play()

    def start_music(self):
        if self.muted or not self.enabled or not self.music_sound:
            return
        self.music_channel.set_volume(settings.MUSIC_VOLUME * settings.MASTER_VOLUME)
        if not self.music_channel.get_busy():
            self.music_channel.play(self.music_sound, loops=-1)

    def stop_music(self):
        if self.music_channel:
            self.music_channel.stop()

    def toggle_mute(self):
        self.muted = not self.muted
        if not self.enabled:
            return self.muted
        if self.muted:
            pygame.mixer.stop()
        return self.muted


class Game(object):
    """Game states, spawning, difficulty, collisions, UI, and persistence."""

    def __init__(self, screen):
        self.screen = screen
        self.running = True
        self.state = STATE_MENU
        self.asset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        self.highscore_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")

        self.font_title = pygame.font.SysFont(settings.FONT_NAME, settings.TITLE_FONT_SIZE, bold=True)
        self.font_large = pygame.font.SysFont(settings.FONT_NAME, settings.LARGE_FONT_SIZE, bold=True)
        self.font_medium = pygame.font.SysFont(settings.FONT_NAME, settings.MEDIUM_FONT_SIZE, bold=True)
        self.font_small = pygame.font.SysFont(settings.FONT_NAME, settings.SMALL_FONT_SIZE)

        self.player = Player()
        self.obstacles = []
        self.coins = []
        self.particles = ParticleSystem()
        self.background_layers = self._create_background()
        self.sound = SoundManager(self.asset_dir)

        self.highscore = self.load_highscore()
        self.score = 0
        self.coin_score = 0
        self.distance_score = 0.0
        self.coins_collected = 0
        self.distance = 0.0
        self.speed = settings.WORLD_SCROLL_SPEED
        self.speed_multiplier = 1.0
        self.combo = 1
        self.combo_timer = 0.0

        self.obstacle_timer = 0.8
        self.coin_timer = 0.9
        self.trail_timer = 0.0
        self.shake_timer = 0.0
        self.shake_strength = 0.0
        self.transition_alpha = 255
        self.menu_pulse = 0.0
        self.buttons = {}

    def _create_background(self):
        return [
            BackgroundLayer(0.08, (42, 52, 92), 80, "stars"),
            BackgroundLayer(0.22, (18, 25, 55), 0, "buildings"),
            BackgroundLayer(0.47, settings.NEON_MAGENTA, 18, "signs"),
            BackgroundLayer(0.82, settings.NEON_CYAN, 24, "ground"),
        ]

    def reset_game(self):
        self.player.reset()
        self.obstacles = []
        self.coins = []
        self.particles.clear()
        self.score = 0
        self.coin_score = 0
        self.distance_score = 0.0
        self.coins_collected = 0
        self.distance = 0.0
        self.speed = settings.WORLD_SCROLL_SPEED
        self.speed_multiplier = 1.0
        self.combo = 1
        self.combo_timer = 0.0
        self.obstacle_timer = 0.95
        self.coin_timer = 0.55
        self.trail_timer = 0.0
        self.shake_timer = 0.0
        self.shake_strength = 0.0
        self.transition_alpha = 150

    def start_game(self):
        self.reset_game()
        self.state = STATE_PLAYING
        self.sound.start_music()

    def load_highscore(self):
        if not os.path.exists(self.highscore_path):
            self.save_highscore_value(0)
            return 0
        try:
            with open(self.highscore_path, "r") as file_obj:
                value = int(file_obj.read().strip() or "0")
                return max(0, value)
        except (IOError, ValueError):
            self.save_highscore_value(0)
            return 0

    def save_highscore_value(self, value):
        try:
            with open(self.highscore_path, "w") as file_obj:
                file_obj.write(str(int(value)))
        except IOError:
            pass

    def save_highscore(self):
        if self.score > self.highscore:
            self.highscore = self.score
            self.save_highscore_value(self.highscore)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_mouse_click(event.pos)

    def _handle_keydown(self, key):
        if key == pygame.K_ESCAPE:
            if self.state == STATE_PLAYING:
                self.state = STATE_PAUSED
                self.sound.stop_music()
            elif self.state == STATE_PAUSED:
                self.state = STATE_PLAYING
                self.sound.start_music()
            elif self.state in (STATE_MENU, STATE_GAME_OVER):
                self.running = False
            return

        if key == pygame.K_m:
            self._toggle_mute()
            return

        if self.state == STATE_MENU:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_game()
            return

        if self.state == STATE_GAME_OVER:
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                self.start_game()
            return

        if key == pygame.K_p and self.state in (STATE_PLAYING, STATE_PAUSED):
            self.state = STATE_PAUSED if self.state == STATE_PLAYING else STATE_PLAYING
            if self.state == STATE_PLAYING:
                self.sound.start_music()
            else:
                self.sound.stop_music()
            return

        if self.state != STATE_PLAYING:
            return

        if key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
            can_jump = self.player.on_ground or self.player.jump_count < 2
            self.player.queue_jump()
            if can_jump:
                self.sound.play("jump")
                self.particles.emit(
                    self.player.rect.left, self.player.rect.bottom, 8,
                    settings.NEON_CYAN, math.pi, 50, 180, 0.35
                )
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.player.start_slide()

    def _handle_mouse_click(self, position):
        if self.state == STATE_MENU and self.buttons.get("start", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.start_game()
        elif self.state == STATE_GAME_OVER and self.buttons.get("restart", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self.start_game()
        elif self.buttons.get("mute", pygame.Rect(0, 0, 0, 0)).collidepoint(position):
            self._toggle_mute()

    def _toggle_mute(self):
        self.sound.toggle_mute()
        if self.state == STATE_PLAYING:
            self.sound.start_music()

    def update(self, dt):
        self.menu_pulse += dt
        if self.transition_alpha > 0:
            self.transition_alpha = max(0, self.transition_alpha - int(360 * dt))

        if self.state == STATE_MENU:
            self._update_background(dt, settings.WORLD_SCROLL_SPEED * 0.35)
            self.particles.update(dt)
            return

        if self.state == STATE_GAME_OVER:
            self._update_background(dt, settings.WORLD_SCROLL_SPEED * 0.18)
            self.particles.update(dt)
            if self.shake_timer > 0.0:
                self.shake_timer -= dt
            return

        if self.state != STATE_PLAYING:
            return

        self._update_difficulty()
        self._update_background(dt, self.speed)

        keys = pygame.key.get_pressed()
        slide_held = keys[pygame.K_DOWN] or keys[pygame.K_s]
        self.player.update(dt, slide_held)

        if self.player.just_landed():
            self.start_shake(settings.SHAKE_LANDING_DURATION, settings.SHAKE_LANDING_STRENGTH)
            self.particles.emit(
                self.player.rect.centerx, self.player.rect.bottom, 10,
                settings.NEON_AMBER, math.pi, 40, settings.LANDING_PARTICLE_SPEED, 0.28
            )

        self._update_trail(dt)
        self._update_spawning(dt)
        self._update_obstacles(dt)
        self._update_coins(dt)
        self.particles.update(dt)

        self.distance += self.speed * dt
        self.distance_score += self.speed * dt * settings.DISTANCE_SCORE_RATE
        if self.combo_timer > 0.0:
            self.combo_timer -= dt
        else:
            self.combo = 1
        self.score = int(self.distance_score + self.coin_score)

        if self.shake_timer > 0.0:
            self.shake_timer -= dt

    def _update_difficulty(self):
        self.speed_multiplier = 1.0 + self.distance * settings.SPEED_SCALE_PER_DISTANCE
        base_speed = settings.WORLD_SCROLL_SPEED * self.speed_multiplier
        self.speed = min(settings.MAX_SCROLL_SPEED, base_speed)

    def _update_background(self, dt, speed):
        for layer in self.background_layers:
            layer.update(dt, speed)

    def _update_trail(self, dt):
        self.trail_timer -= dt
        if self.trail_timer <= 0.0:
            self.trail_timer = settings.TRAIL_PARTICLE_INTERVAL
            self.particles.emit(
                self.player.rect.left - 4,
                self.player.rect.centery + random.randint(-18, 16),
                2,
                settings.NEON_PURPLE,
                math.pi / 5.0,
                -120,
                -40,
                0.24
            )

    def _update_spawning(self, dt):
        self.obstacle_timer -= dt
        self.coin_timer -= dt

        if self.obstacle_timer <= 0.0:
            self.spawn_obstacle_group()
            self.obstacle_timer = self._next_obstacle_interval()

        if self.coin_timer <= 0.0:
            self.spawn_coin_pattern()
            self.coin_timer = self._next_coin_interval()

    def _next_obstacle_interval(self):
        pressure = min(0.65, self.distance / 4200.0)
        interval = settings.OBSTACLE_BASE_INTERVAL - pressure
        interval = max(settings.OBSTACLE_MIN_INTERVAL, interval)
        return random.uniform(interval * 0.82, interval * 1.22)

    def _next_coin_interval(self):
        pressure = min(0.38, self.distance / 6000.0)
        interval = settings.COIN_BASE_INTERVAL - pressure
        interval = max(settings.COIN_MIN_INTERVAL, interval)
        return random.uniform(interval * 0.8, interval * 1.25)

    def spawn_obstacle_group(self):
        if self.obstacles:
            rightmost = max(obstacle.rect.right for obstacle in self.obstacles)
            if settings.OBSTACLE_SPAWN_X - rightmost < settings.MIN_OBSTACLE_GAP:
                return

        kinds = ["spike", "rock"]
        if self.distance > 420:
            kinds.append("wall")
        if self.distance > 850:
            kinds.append("drone")

        first_kind = random.choice(kinds)
        self.obstacles.append(Obstacle(first_kind, settings.OBSTACLE_SPAWN_X))

        if self.distance > settings.HARD_MODE_DISTANCE and random.random() < 0.24:
            second_kind = random.choice(["spike", "rock", "drone"])
            gap = random.randint(135, 190)
            self.obstacles.append(Obstacle(second_kind, settings.OBSTACLE_SPAWN_X + gap))

        if self.distance > settings.EXPERT_MODE_DISTANCE and random.random() < 0.12:
            third_kind = random.choice(["spike", "rock"])
            self.obstacles.append(Obstacle(third_kind, settings.OBSTACLE_SPAWN_X + random.randint(300, 360)))

    def spawn_coin_pattern(self):
        pattern = random.choice(["line", "arc", "wave", "cluster"])
        base_x = settings.COIN_SPAWN_X
        base_y = random.choice([240, 285, 325, 360])

        if pattern == "line":
            for i in range(6):
                self.coins.append(Coin(base_x + i * 34, base_y))
        elif pattern == "arc":
            for i in range(8):
                y = base_y - math.sin(i / 7.0 * math.pi) * 78
                self.coins.append(Coin(base_x + i * 32, y))
        elif pattern == "wave":
            for i in range(9):
                y = base_y + math.sin(i * 0.85) * 42
                self.coins.append(Coin(base_x + i * 30, y))
        else:
            for _ in range(8):
                self.coins.append(Coin(
                    base_x + random.randint(0, 180),
                    base_y + random.randint(-55, 40)
                ))

    def _update_obstacles(self, dt):
        alive = []
        player_hitbox = self.player.rect.inflate(-8, -8)
        for obstacle in self.obstacles:
            obstacle.update(dt, self.speed)
            if not obstacle.is_offscreen():
                alive.append(obstacle)
            if player_hitbox.colliderect(obstacle.rect):
                self._trigger_game_over()
                return
        self.obstacles = alive

    def _update_coins(self, dt):
        alive = []
        for coin in self.coins:
            coin.update(dt, self.speed)
            if coin.rect.colliderect(self.player.rect):
                self._collect_coin(coin)
            elif not coin.is_offscreen():
                alive.append(coin)
        self.coins = alive

    def _collect_coin(self, coin):
        coin.collected = True
        self.coins_collected += 1
        self.combo_timer = settings.COMBO_TIMEOUT
        self.combo = min(settings.MAX_COMBO_MULTIPLIER, self.combo + 1)
        self.coin_score += settings.COIN_SCORE_VALUE * self.combo
        self.sound.play("coin")
        self.particles.emit_burst(coin.x, coin.y, 13, settings.NEON_AMBER)

    def _trigger_game_over(self):
        if self.state != STATE_PLAYING:
            return
        self.sound.play("hit")
        self.player.hurt()
        self.player.die()
        self.particles.emit_burst(self.player.rect.centerx, self.player.rect.centery, 38, settings.HOT_RED)
        self.start_shake(settings.SHAKE_COLLISION_DURATION, settings.SHAKE_COLLISION_STRENGTH)
        self.save_highscore()
        self.state = STATE_GAME_OVER
        self.sound.stop_music()
        self.transition_alpha = 120

    def start_shake(self, duration, strength):
        self.shake_timer = max(self.shake_timer, duration)
        self.shake_strength = max(self.shake_strength, strength)

    def draw(self):
        offset = self._camera_offset()
        self._draw_background()
        self._draw_world(offset)
        self._draw_hud()

        if self.state == STATE_MENU:
            self._draw_menu()
        elif self.state == STATE_PAUSED:
            self._draw_pause()
        elif self.state == STATE_GAME_OVER:
            self._draw_game_over()

        self._draw_crt_overlay()
        self._draw_transition()

    def _camera_offset(self):
        if self.shake_timer <= 0.0:
            return (0, 0)
        amount = self.shake_strength * (self.shake_timer / settings.SHAKE_COLLISION_DURATION)
        return (random.randint(-int(amount), int(amount)), random.randint(-int(amount), int(amount)))

    def _draw_background(self):
        self.screen.fill(settings.BLACK)
        for y in range(settings.SCREEN_HEIGHT):
            blend = y / float(settings.SCREEN_HEIGHT)
            r = int(settings.DEEP_SPACE[0] * (1.0 - blend) + settings.NIGHT[0] * blend)
            g = int(settings.DEEP_SPACE[1] * (1.0 - blend) + settings.NIGHT[1] * blend)
            b = int(settings.DEEP_SPACE[2] * (1.0 - blend) + settings.NIGHT[2] * blend)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (settings.SCREEN_WIDTH, y))

        for layer in self.background_layers:
            layer.draw(self.screen)

        pygame.draw.rect(
            self.screen,
            settings.GROUND_FILL,
            (0, settings.GROUND_Y, settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT - settings.GROUND_Y)
        )
        pygame.draw.line(
            self.screen,
            settings.GROUND_TOP,
            (0, settings.GROUND_Y),
            (settings.SCREEN_WIDTH, settings.GROUND_Y),
            3
        )

    def _draw_world(self, offset):
        for coin in self.coins:
            coin.draw(self.screen, offset)
        for obstacle in self.obstacles:
            obstacle.draw(self.screen, offset)
        self.player.draw(self.screen, offset)
        self.particles.draw(self.screen, offset)

    def _draw_hud(self):
        if self.state == STATE_MENU:
            return
        panel = pygame.Rect(16, 14, 928, 58)
        self._draw_panel(panel, 150)
        score_text = "Score  {0}".format(self.score)
        coin_text = "Coins  {0}".format(self.coins_collected)
        dist_text = "Distance  {0}m".format(int(self.distance / 10))
        high_text = "Best  {0}".format(self.highscore)
        speed_text = "x{0:.2f}".format(self.speed / settings.WORLD_SCROLL_SPEED)

        self._draw_text(score_text, self.font_medium, settings.SOFT_WHITE, (34, 28))
        self._draw_text(coin_text, self.font_small, settings.NEON_AMBER, (220, 31))
        self._draw_text(dist_text, self.font_small, settings.NEON_CYAN, (354, 31))
        self._draw_text(high_text, self.font_small, settings.MUTED_TEXT, (540, 31))
        self._draw_text(speed_text, self.font_medium, settings.NEON_LIME, (850, 27))

        if self.combo > 1 and self.combo_timer > 0.0:
            self._draw_text("Combo x{0}".format(self.combo), self.font_small, settings.NEON_MAGENTA, (34, 78))

        mute_text = "MUTE" if self.sound.muted else "SOUND"
        self.buttons["mute"] = pygame.Rect(742, 26, 78, 25)
        pygame.draw.rect(self.screen, settings.HUD_PANEL, self.buttons["mute"], border_radius=5)
        self._draw_text(mute_text, self.font_small, settings.NEON_CYAN, (753, 29))

    def _draw_menu(self):
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 80))
        self.screen.blit(overlay, (0, 0))

        title_y = 98 + int(math.sin(self.menu_pulse * 2.0) * 5)
        self._draw_centered_text(settings.TITLE, self.font_title, settings.NEON_CYAN, title_y)
        self._draw_centered_text("Endless Escape", self.font_large, settings.NEON_MAGENTA, title_y + 58)
        self._draw_centered_text(
            "Jump, double jump, slide, collect coins, and outrun the neon city.",
            self.font_small, settings.MUTED_TEXT, 210
        )

        self.buttons["start"] = self._draw_button("START RUN", 292, settings.NEON_CYAN)
        self._draw_centered_text("Space / Up: Jump    Down / S: Slide    P: Pause    M: Mute", self.font_small, settings.SOFT_WHITE, 366)
        self._draw_centered_text("High Score: {0}".format(self.highscore), self.font_medium, settings.NEON_AMBER, 410)

    def _draw_pause(self):
        self._draw_dim_overlay(150)
        self._draw_centered_text("PAUSED", self.font_title, settings.NEON_CYAN, 170)
        self._draw_centered_text("Press P or Esc to resume", self.font_medium, settings.SOFT_WHITE, 244)

    def _draw_game_over(self):
        self._draw_dim_overlay(165)
        self._draw_centered_text("RUN ENDED", self.font_title, settings.HOT_RED, 122)
        self._draw_centered_text("Score: {0}".format(self.score), self.font_large, settings.SOFT_WHITE, 202)
        self._draw_centered_text("Coins: {0}    Distance: {1}m".format(self.coins_collected, int(self.distance / 10)), self.font_medium, settings.NEON_CYAN, 250)
        self._draw_centered_text("Best: {0}".format(self.highscore), self.font_medium, settings.NEON_AMBER, 292)
        self.buttons["restart"] = self._draw_button("RESTART", 350, settings.NEON_MAGENTA)

    def _draw_dim_overlay(self, alpha):
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        self.screen.blit(overlay, (0, 0))

    def _draw_transition(self):
        if self.transition_alpha <= 0:
            return
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self.transition_alpha))
        self.screen.blit(overlay, (0, 0))

    def _draw_crt_overlay(self):
        scan = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(0, settings.SCREEN_HEIGHT, 4):
            pygame.draw.line(scan, (255, 255, 255, settings.CRT_SCANLINE_ALPHA), (0, y), (settings.SCREEN_WIDTH, y))
        self.screen.blit(scan, (0, 0))

    def _draw_panel(self, rect, alpha):
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        panel.fill((settings.HUD_PANEL[0], settings.HUD_PANEL[1], settings.HUD_PANEL[2], alpha))
        pygame.draw.rect(panel, (48, 232, 255, 80), panel.get_rect(), 1, border_radius=6)
        self.screen.blit(panel, rect)

    def _draw_button(self, text, y, color):
        rect = pygame.Rect(
            (settings.SCREEN_WIDTH - settings.BUTTON_WIDTH) // 2,
            y,
            settings.BUTTON_WIDTH,
            settings.BUTTON_HEIGHT
        )
        mouse_over = rect.collidepoint(pygame.mouse.get_pos())
        fill = (22, 32, 62) if not mouse_over else (34, 49, 92)
        pygame.draw.rect(self.screen, fill, rect, border_radius=7)
        pygame.draw.rect(self.screen, color, rect, 2, border_radius=7)
        text_surface = self.font_medium.render(text, True, settings.SOFT_WHITE)
        self.screen.blit(text_surface, text_surface.get_rect(center=rect.center))
        return rect

    def _draw_text(self, text, font, color, position):
        surface = font.render(text, True, color)
        self.screen.blit(surface, position)

    def _draw_centered_text(self, text, font, color, y):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(settings.SCREEN_WIDTH // 2, y))
        self.screen.blit(surface, rect)

    def shutdown(self):
        self.save_highscore()
        self.sound.stop_music()
