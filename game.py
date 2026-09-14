"""
   HeliOps - Helicopter Extraction & Scavenge Game
   ===============================================
   Gameplay:
   - Scavenge supplies on a large map, fly near them and press J to search (1.5s)
   - Enemies patrol and chase when you enter their alert range (optional to engage)
   - Extraction zone always exists at a fixed location, hold 3s to extract, then moves
   - Un-extracted supplies are lost if you crash or die!
"""

import pygame
import random
import math
import sys
import pickle
import os
import shutil

# ==============================
# Initialization
# ==============================
pygame.init()

WIDTH, HEIGHT = 1200,800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("HeliOps - 直升机撤离行动")

clock = pygame.time.Clock()

# ==============================
# World map size (3x3 screen size)
# ==============================
WORLD_W = WIDTH  * 3  # 2400
WORLD_H = HEIGHT * 3  # 1800

# ==============================
# Colors
# ==============================
BG_DARK      = (45, 140, 50)  # Grass green
GREEN_SUPPLY = (100, 220, 80)
GOLD_SUPPLY  = (255, 200, 30)
RED_AMMO     = (240, 80, 60)
BLUE_HEAL    = (60, 160, 255)
PLAYER_COLOR = (50, 160, 255)
BULLET_COLOR = (255, 240, 100)
ENEMY_COLOR  = (220, 60, 60)
ENEMY_ALERT  = (255, 130, 30)
EXTRACT_COLOR= (255, 220, 50)
DROP_COLOR   = (180, 80, 220)
WHITE        = (255, 255, 255)
GRAY         = (160, 160, 160)
DARK_GRAY    = (60, 60, 60)
SUPER_CHASER_COLOR = (30, 220, 80)   # Super Chaser exclusive green (invincible)

# ==============================
# Gun system
# ==============================
GUN_TYPES = {
    "pistol":  {"name": "手枪",   "icon": "", "cooldown": 12, "speed": 9,  "damage": 1, "bullets": 1, "spread": 0,    "cost": 0,    "color": (160, 160, 160)},
    "rifle":   {"name": "步枪",   "icon": "", "cooldown": 8,  "speed": 14, "damage": 1, "bullets": 1, "spread": 0,    "cost": 800,  "color": (100, 150, 220)},
    "shotgun": {"name": "霰弹枪", "icon": "", "cooldown": 30, "speed": 7,  "damage": 1, "bullets": 5, "spread": 0.25, "cost": 1500, "color": (220, 160, 60)},
    "sniper":  {"name": "狙击枪", "icon": "", "cooldown": 50, "speed": 22, "damage": 4, "bullets": 1, "spread": 0,    "cost": 2500, "color": (60, 200, 80)},
}
GUN_SHOP_PRICES = {k: v["cost"] for k, v in GUN_TYPES.items() if v["cost"] > 0}


# ==============================
# Font (CJK support, priority: filename -> font name -> default)
# ==============================
def _get_font(size):
    """Get a CJK-compatible font, compatible with Thonny sandbox environment"""
    file_candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in file_candidates:
        try:
            f = pygame.font.Font(path, size)
            return f
        except:
            pass
    name_candidates = [
        "PingFang SC", "Heiti SC", "STHeiti", "Hiragino Sans GB",
        "Microsoft YaHei", "SimHei",
        "Noto Sans CJK SC", "WenQuanYi Micro Hei",
    ]
    for name in name_candidates:
        f = pygame.font.SysFont(name, size)
        test = f.render("Test", True, (255, 255, 255))
        if test.get_width() > 20:
            return f
    return pygame.font.SysFont(None, size)

font_small  = _get_font(24)
font_normal = _get_font(32)
font_big    = _get_font(56)
font_huge   = _get_font(80)

# ==============================
# Sound system (procedural generation, no external files)
# ==============================
import struct
import wave
import io
import random as _rnd

# Volume settings (persistent)
sfx_volume = 0.6    # SFX volume 0.0~1.0
bgm_volume = 0.3    # BGM volume 0.0-1.0
sfx_enabled = True  # Whether SFX is enabled

# Initialize mixer
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    _mixer_ok = True
except Exception:
    _mixer_ok = False

_sounds = {}   # Cache all sound objects

def _gen_wav_bytes(samples, sample_rate=22050):
    """Convert sample list to WAV byte data (16-bit mono)"""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Normalize and convert to 16-bit PCM
        max_val = max(abs(s) for s in samples) or 1
        for s in samples:
            val = int((s / max_val) * 32000)
            val = max(-32768, min(32767, val))
            wf.writeframesraw(struct.pack('<h', val))
    buf.seek(0)
    return buf.read()

def _make_shoot():
    """Shooting sound: short white noise burst"""
    dur = 0.08
    n = int(22050 * dur)
    samples = []
    for i in range(n):
        t = i / 22050
        env = max(0, 1 - t / dur)        # Linear decay
        noise = (_rnd.random() * 2 - 1) * env
        samples.append(noise)
    return _gen_wav_bytes(samples)

def _make_hit():
    """Hit sound: short low-frequency tone"""
    dur = 0.06
    n = int(22050 * dur)
    samples = []
    for i in range(n):
        t = i / 22050
        env = max(0, 1 - t / dur)
        s = math.sin(2 * math.pi * 200 * t) * env * 0.7
        samples.append(s)
    return _gen_wav_bytes(samples)

def _make_pickup():
    """Pickup sound: rising double tone"""
    dur = 0.12
    n = int(22050 * dur)
    samples = []
    for i in range(n):
        t = i / 22050
        env = max(0, 1 - t / dur)
        freq = 600 + (t / dur) * 800   # 600->1400Hz rising
        s = math.sin(2 * math.pi * freq * t) * env * 0.5
        samples.append(s)
    return _gen_wav_bytes(samples)

def _make_extract():
    """Extraction sound: three-tone sequence"""
    dur = 0.6
    n = int(22050 * dur)
    samples = []
    notes = [(523, 0.0, 0.15), (659, 0.15, 0.15), (784, 0.3, 0.25)]  # C5 E5 G5
    for i in range(n):
        t = i / 22050
        s = 0
        for freq, start, ndur in notes:
            if start <= t < start + ndur:
                lt = (t - start) / ndur
                env = 1 - lt
                s += math.sin(2 * math.pi * freq * t) * env * 0.4
        samples.append(s)
    return _gen_wav_bytes(samples)

def _make_hurt():
    """Hurt sound: descending tone"""
    dur = 0.2
    n = int(22050 * dur)
    samples = []
    for i in range(n):
        t = i / 22050
        env = max(0, 1 - t / dur)
        freq = 500 - (t / dur) * 300  # 500->200Hz descending
        s = math.sin(2 * math.pi * freq * t) * env * 0.5
        samples.append(s)
    return _gen_wav_bytes(samples)

def _make_death():
    """Death sound: deep sustained tone"""
    dur = 0.5
    n = int(22050 * dur)
    samples = []
    for i in range(n):
        t = i / 22050
        env = max(0, 1 - t / dur) ** 2
        s = math.sin(2 * math.pi * 100 * t) * env * 0.6
        s += math.sin(2 * math.pi * 60 * t) * env * 0.3
        samples.append(s)
    return _gen_wav_bytes(samples)

def _make_boss_die():
    """Boss death: heavy bass"""
    dur = 0.7
    n = int(22050 * dur)
    samples = []
    for i in range(n):
        t = i / 22050
        env = max(0, 1 - t / dur) ** 1.5
        s = math.sin(2 * math.pi * 80 * t) * env * 0.7
        if t < 0.15:
            s += (_rnd.random() * 2 - 1) * env * 0.3  # Initial noise
        samples.append(s)
    return _gen_wav_bytes(samples)

def _make_click():
    """Menu click: short high tone"""
    dur = 0.04
    n = int(22050 * dur)
    samples = []
    for i in range(n):
        t = i / 22050
        env = max(0, 1 - t / dur)
        s = math.sin(2 * math.pi * 1200 * t) * env * 0.3
        samples.append(s)
    return _gen_wav_bytes(samples)

def _make_ammo_empty():
    """Empty magazine: click sound"""
    dur = 0.05
    n = int(22050 * dur)
    samples = []
    for i in range(n):
        t = i / 22050
        env = max(0, 1 - t / dur)
        s = math.sin(2 * math.pi * 800 * t) * env * 0.2
        s += (_rnd.random() * 2 - 1) * env * 0.15
        samples.append(s)
    return _gen_wav_bytes(samples)

def _make_bgm_loop():
    """Simple looping BGM: low sustained ambient tone"""
    dur = 4.0   # 4-second loop
    n = int(22050 * dur)
    samples = []
    for i in range(n):
        t = i / 22050
        # Deep sustained tone + subtle rhythm
        s = math.sin(2 * math.pi * 55 * t) * 0.15          # Bass A
        s += math.sin(2 * math.pi * 110 * t) * 0.08        # Harmonic
        # One subtle pulse per second
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * 1.0 * t)
        s += pulse * 0.05
        samples.append(s)
    return _gen_wav_bytes(samples)

def _make_footstep():
    """Footstep sound: rustling on grass"""
    dur = 0.12
    n = int(22050 * dur)
    samples = []
    prev = 0.0  # For simple low-pass filter, simulating grass damping
    for i in range(n):
        t = i / 22050
        # Fast attack + decay envelope
        if t < 0.005:
            env = t / 0.005
        else:
            env = math.exp(-(t - 0.005) * 22)
        # White noise -> low-pass filter (simulating grass rustle)
        noise = _rnd.random() * 2 - 1
        prev = prev * 0.6 + noise * 0.4  # First-order low-pass
        s = prev * env * 0.5
        # Add slight very-low-frequency impact
        s += math.sin(2 * math.pi * 45 * t) * env * 0.08
        samples.append(s)
    return _gen_wav_bytes(samples)

def init_sounds():
    """Initialize all sound effects (call after pygame.init())"""
    global _sounds
    if not _mixer_ok:
        return
    generators = {
        'shoot': _make_shoot, 'hit': _make_hit, 'pickup': _make_pickup,
        'extract': _make_extract, 'hurt': _make_hurt, 'death': _make_death,
        'boss_die': _make_boss_die, 'click': _make_click, 'ammo_empty': _make_ammo_empty,
        'footstep': _make_footstep,
    }
    for name, gen in generators.items():
        try:
            data = gen()
            _sounds[name] = pygame.mixer.Sound(buffer=data)
        except Exception:
            _sounds[name] = None

def play_sfx(name):
    """Play a sound effect (auto applies volume)"""
    global sfx_enabled, sfx_volume
    if not _mixer_ok or not sfx_enabled:
        return
    snd = _sounds.get(name)
    if snd is not None:
        snd.set_volume(sfx_volume)
        snd.play()

def play_bgm():
    """Start looping background music"""
    global bgm_volume
    if not _mixer_ok:
        return
    snd = _sounds.get('bgm')
    if snd is not None:
        snd.set_volume(bgm_volume)
        snd.play(loops=-1)

def stop_bgm():
    """Stop background music"""
    if _mixer_ok:
        snd = _sounds.get('bgm')
        if snd is not None:
            snd.stop()

def set_sfx_volume(v):
    global sfx_volume
    sfx_volume = max(0, min(1, v))

def set_bgm_volume(v):
    global bgm_volume
    bgm_volume = max(0, min(1, v))
    if _mixer_ok:
        snd = _sounds.get('bgm')
        if snd is not None:
            snd.set_volume(bgm_volume)

# Called at end of initialization
init_sounds()

# ==============================
# Player (world coordinates)
# ==============================
player_size  = 36
player_x     = float(WORLD_W // 2)
player_y     = float(WORLD_H // 2)
player_speed = 5

# Camera (world top-left mapped to screen top-left)
cam_x = player_x - WIDTH  // 2
cam_y = player_y - HEIGHT // 2

# Player facing direction tracking
face_angle = 0  # Player facing angle (degrees)
move_dx, move_dy = 0, 0  # Movement direction

# ==============================
# Supply system
# ==============================
supplies = []           # [wx, wy, type, lifetime]
SUPPLY_TYPES = {
    "common":     {"color": GREEN_SUPPLY, "points": 100, "label": "物资"},
    "rare":       {"color": GOLD_SUPPLY,  "points": 300, "label": "稀有"},
    "ammo":       {"color": RED_AMMO,     "points": 0,   "label": "弹药"},
    "heal":       {"color": BLUE_HEAL,    "points": 0,   "label": "医疗"},
    "bonus":      {"color": (255, 50, 60), "points": 0,   "label": "红包"},
    "enemy_drop": {"color": DROP_COLOR,   "points": 0,   "label": "掉落"},
    "boss_drop":  {"color": (200, 100, 255), "points": 0, "label": "Boss掉落", "glow": True},
}
SUPPLY_SIZE = 22
supply_spawn_timer    = 0
supply_spawn_interval = 90
max_supplies_on_map   = 20   # Extra supplies on large map

# Player backpack
backpack     = []
backpack_max = 8

# Supply search system
SEARCH_DURATION = 90        # Search takes 1.5 seconds (90 frames)
searching_supply = None     # Index of supply being searched (position in supplies list)
search_timer     = 0        # Remaining search frames
search_message   = ""
search_message_timer = 0

# ==============================
# Extraction zone system
# ==============================
extract_zone        = None   # [wx, wy] - always present, no timer
extract_size        = 80
extract_multiplier  = 1.0
extraction_message  = ""
extraction_message_timer = 0

# Super Chaser fullscreen broadcast
super_chaser_broadcast = ""
super_chaser_broadcast_timer = 0

# Hold extraction: player must stay in zone for EXTRACT_HOLD_FRAMES to complete
EXTRACT_HOLD_FRAMES = 180    # 3 seconds (60fps * 3)
extract_hold_timer  = 0      # Current hold frames (0 = not in zone)

# ==============================
# Enemy / Patrol system
# ==============================
enemies = []  # [wx, wy, patrol_start, patrol_end, state, alert_timer, chase_timer, hp, shoot_cd]
enemy_size          = 28
enemy_patrol_speed  = 1.5
enemy_chase_speed   = 1.8    # Slow chase
enemy_vision_range  = 150
enemy_spawn_timer   = 0
enemy_spawn_interval= 180
max_enemies         = 10    # More enemies on large map
CHASE_DURATION      = 180

# ==============================
# Bullets
# ==============================
bullets           = []   # [wx, wy, dx, dy]
bullet_speed      = 9
bullet_cooldown   = 0
bullet_cooldown_max = 12
ammo_bonus        = 0
bullet_count        = 600   # Bullet count
max_bullets         = 600   # Max bullets
ammo_empty_timer    = 0     # Ammo depleted hint timer
current_gun         = "pistol"   # Currently equipped gun
owned_guns          = {"pistol"}  # Set of owned guns

# Enemy bullets
enemy_bullets       = []    # [wx, wy, dx, dy]
enemy_bullet_speed  = 3.5
enemy_shoot_cd      = 90   # Enemy shoot cooldown (frames)
ENEMY_HP            = 3    # Enemy HP

# Boss
boss                = None             # [wx, wy, hp, shoot_cd] or None
boss_respawn_timer  = 0
BOSS_MAX_HP         = 35               # Boss HP
BOSS_SIZE           = 48               # Boss size
BOSS_SPEED          = 2.0              # Boss chase speed
BOSS_SHOOT_CD       = 20               # Shoot cooldown (60fps = 3 shots/sec)
BOSS_SPREAD         = 0.15             # Shot spread (~+/-8.6deg)
BOSS_COLOR          = (180, 30, 30)    # Boss color (dark red)
BOSS_RESPAWN_DELAY  = 300              # Respawn delay after death (5 seconds)
BOSS_VISION_RANGE   = 350              # Boss vision range (pixels)

# Chaser Boss (hunter)
chaser               = None             # [wx, wy, hp, detected] or None
chaser_respawn_timer = 0
CHASER_HP            = 10               # Chaser HP
CHASER_SIZE          = 36               # Chaser size
CHASER_SPEED         = 5.0              # Same speed as player
CHASER_COLOR         = (255, 100, 20)   # Orange-red
CHASER_VISION_RANGE  = 320              # Vision range
CHASER_RESPAWN_DELAY = 480              # Respawn delay after death/scare (8 seconds)

# Super Chaser (invincible variant - small chance to replace Chaser)
super_chaser               = None
super_chaser_respawn_timer = 0
SUPER_CHASER_SIZE          = 40               # Super Chaser size
SUPER_CHASER_SPEED         = 5.5              # Slightly faster than Chaser
SUPER_CHASER_VISION_RANGE  = 340              # Vision range
SUPER_CHASER_RESPAWN_DELAY = 480              # Respawn delay after leaving
super_chaser_spawn_chance = 0.25             # Super Chaser starts at 25%, +10% on failure, reset on spawn

# Walls
walls           = []                 # [[x, y, w, h], ...]
WALL_COUNT      = 20                 # Wall count
WALL_COLOR      = (45, 40, 55)       # Wall main color (dark slate gray)
WALL_EDGE_COLOR = (70, 65, 85)       # Wall edge highlight color

# ==============================
# Pre-allocated resources
# ==============================
_vision_surf_alert = pygame.Surface((enemy_vision_range * 2, enemy_vision_range * 2), pygame.SRCALPHA)
pygame.draw.circle(_vision_surf_alert, (*ENEMY_ALERT, 15), (enemy_vision_range, enemy_vision_range), enemy_vision_range)
_vision_surf_chase = pygame.Surface((enemy_vision_range * 2, enemy_vision_range * 2), pygame.SRCALPHA)
pygame.draw.circle(_vision_surf_chase, (*ENEMY_ALERT, 30), (enemy_vision_range, enemy_vision_range), enemy_vision_range)

# ==============================
# Score & Lives & Mission time
# ==============================
score        = 0
lives        = 10
max_lives    = 10
armor        = 0          # Armor count (each absorbs one hit)
danger_level = 0.0
mission_timer = 500 * 60
MISSION_TIME  = 500 * 60

# ==============================
# Supply station prices
# ==============================
SHOP_RESTORE_COST = 200
SHOP_ARMOR_COST   = 300
SHOP_AMMO_COST    = 150

# ==============================
# Save system (uses user directory, compatible with packaged env)
# ==============================
GAME_SAVE_DIR   = os.path.join(os.path.expanduser("~"), "Documents", "HeliOps")
os.makedirs(GAME_SAVE_DIR, exist_ok=True)
SAVE_FILE       = os.path.join(GAME_SAVE_DIR, "save.dat")
AUTO_SAVE_FILE  = os.path.join(GAME_SAVE_DIR, "auto_save.dat")
# Compat: migrate old saves from working dir to user dir (dev only).
# Never run this in a packaged build (sys.frozen) — otherwise a save file
# accidentally bundled inside the zip would be copied into every new player's
# Documents folder, making all players share one save.
if not getattr(sys, "frozen", False):
    _old_auto = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_save.dat")
    _old_save = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save.dat")
    for _old, _new in [(_old_auto, AUTO_SAVE_FILE), (_old_save, SAVE_FILE)]:
        if os.path.exists(_old) and not os.path.exists(_new):
            try:
                shutil.copy2(_old, _new)
            except Exception:
                pass
save_message = ""
save_message_timer = 0

# ==============================
# Game state
# ==============================
game_over        = False
game_over_reason = ""
paused           = False
in_shop          = False    # Post-extraction supply station UI
estimated_value  = 0        # Estimated value of current operation
in_transfer      = False    # Transfer station state (entered after being shot down)
in_main_menu     = True     # Main menu state (shown on startup/after ending)
in_death_screen  = False    # Extraction failure death screen
awaiting_departure = False    # Returning from shop to main menu, ready to redeploy
in_settings      = False    # Settings screen
tutorial_shown    = False    # Whether tutorial has been shown (persistent)
showing_tutorial  = False    # Whether tutorial is currently showing
footstep_timer    = 0        # Footstep sound timer

# Previous round result (for main menu display)
last_result      = None     # None or {"reason": str, "score": int}
# reason values:
#   "extract_success" - extraction successful (normal clear)
#   "time_up" - time expired (game_over)
#   "destroyed" - helicopter destroyed (in_transfer)

# Boss tokens and advanced modes
boss_token_count   = 0       # Boss token count (persistent)
hard_mode_unlocked = False   # Hard mode permanently unlocked (persistent)
hard_mode_active   = False   # Hard mode currently active (session only)
TOKEN_DROP_CHANCE  = 0.20    # Token drop rate from Boss (20%)

# Hard mode difficulty multipliers
HM_HP_MULT      = 1.5   # Enemy/Boss HP
HM_CHASER_MULT  = 1.3   # Chaser/Super Chaser HP
HM_SPAWN_MULT   = 1.5   # Spawn count
HM_REWARD_MULT  = 1.3   # Score reward
HM_EXTRACT_MULT = 1.5   # Extraction multiplier boost (0.45 instead of 0.3)

# Extreme mode (unlocked by killing Boss in hard mode, session only)
extreme_mode_unlocked = False   # Extreme mode unlocked (session only)
extreme_mode_active   = False   # Extreme mode currently active

# Extreme mode extra multipliers (stacked on hard mode)
EM_HP_MULT      = 1.4   # Enemy/Boss HP extra x1.4
EM_CHASER_MULT  = 1.3   # Chaser HP extra x1.3
EM_SPAWN_MULT   = 1.3   # Spawn count extra x1.3
EM_REWARD_MULT  = 1.4   # Score reward extra x1.4
EM_EXTRACT_MULT = 1.6   # Extraction mult on top of Hard 0.45, extra x1.6

# Extreme mode permanent unlock task progress (persistent)
# Task 1: Cumulative 5 Boss kills in hard mode
# Task 2: Scare away 2 Super Chasers in hard mode
# Task 3: Kill 2 Bosses in a single hard mode run
hm_boss_kills             = 0    # Task 1: Cumulative Boss kills in hard mode (persistent)
hm_super_chaser_scared    = 0    # Task 2: Super Chaser scares in hard mode (persistent)
mission_boss_kills        = 0    # Task 3: Boss kills in current run (session only)
extreme_mode_permanent    = False  # Extreme mode permanently unlocked (persistent)
extreme_plays_remaining  = 0     # Extreme mode remaining plays (persistent)

# Advanced task targets (activated after extreme mode unlock)
ADV_TASK_BOSS_KILLS     = 8    # Cumulative 8 Boss kills in extreme mode
ADV_TASK_SCARED         = 2    # Scare 2 Super Chasers in extreme mode
ADV_TASK_HIGH_EXTRACT   = 3    # 3 extractions with est>400 in extreme mode
adv_boss_kills           = 0    # Advanced task: Boss kills in extreme mode (persistent)
adv_chaser_scared        = 0    # Advanced task: Super Chaser scares in extreme mode (persistent)
adv_high_extract         = 0    # Advanced task: high-est extraction count in extreme mode (persistent)

# Task panel display control
show_task_panel           = False # Show task panel (P to open, 6 to close)

# Task target values
TASK1_BOSS_KILLS        = 5    # Cumulative 5 Boss kills in hard mode
TASK2_SCARED            = 2    # Scare 2 Super Chasers in hard mode
TASK3_MISSION_BOSS      = 2    # Kill 2 Bosses in a single hard mode run

# Helper: get combined difficulty multiplier
def _dm(hm_mult, em_mult):
    """diff_mult: Extreme=hm*em, Hard=hm, Normal=1.0"""
    if extreme_mode_active:
        return hm_mult * em_mult
    if hard_mode_active:
        return hm_mult
    return 1.0

def check_tasks():
    """Check if all extreme mode permanent unlock tasks are completed"""
    global extreme_mode_permanent, extreme_mode_unlocked, extreme_mode_active
    global extreme_plays_remaining
    global search_message, search_message_timer
    if extreme_mode_permanent:
        return  # Already permanently unlocked, skip check
    t1 = hm_boss_kills >= TASK1_BOSS_KILLS
    t2 = hm_super_chaser_scared >= TASK2_SCARED
    t3 = mission_boss_kills >= TASK3_MISSION_BOSS
    if t1 and t2 and t3:
        extreme_mode_permanent = True
        extreme_mode_unlocked = True
        extreme_mode_active = True
        extreme_plays_remaining = 25  # Grant 25 extreme mode plays
        search_message = "★★ 极难模式永久解锁！获得25次！"
        search_message_timer = 300
        auto_save()  # Persist immediately

def check_adv_tasks():
    """Check if all advanced tasks are completed (called in extreme mode)"""
    global extreme_plays_remaining
    global adv_boss_kills, adv_chaser_scared, adv_high_extract
    global search_message, search_message_timer
    if not extreme_mode_permanent:
        return  # Extreme mode not unlocked, skip advanced task check
    t1 = adv_boss_kills >= ADV_TASK_BOSS_KILLS
    t2 = adv_chaser_scared >= ADV_TASK_SCARED
    t3 = adv_high_extract >= ADV_TASK_HIGH_EXTRACT
    if t1 and t2 and t3:
        extreme_plays_remaining += 15  # Advanced tasks complete, +15 plays
        # Reset advanced task counters (repeatable)
        adv_boss_kills = 0
        adv_chaser_scared = 0
        adv_high_extract = 0
        search_message = "★ 进阶任务完成！极难模式次数+15！"
        search_message_timer = 300
        auto_save()  # Persist immediately

# Kill record (for death screen display)
killer           = ""       # "Enemy" / "Boss" / "猎手" / "超级猎手" / "Boss炮弹" / "敌方子弹" / "时间耗尽"


# ==============================
# Coordinate conversion
# ==============================
def w2s(wx, wy):
    """World coordinates -> Screen coordinates"""
    return wx - cam_x, wy - cam_y

def on_screen(wx, wy, margin=100):
    """Check if world coordinates are within the visible screen area (with margin)"""
    sx, sy = w2s(wx, wy)
    return (-margin < sx < WIDTH + margin) and (-margin < sy < HEIGHT + margin)


# ==============================
# Helper functions
# ==============================
def draw_player(wx, wy):
    """Draw player character (geometric style + rotation)"""
    sx, sy = w2s(wx, wy)
    cx, cy = player_size // 2, player_size // 2
    
    # Create temporary surface (with alpha channel)
    surf = pygame.Surface((player_size, player_size), pygame.SRCALPHA)
    
    # ---- Draw character (base direction: facing right) ----
    # 1. Head (skin-colored circle)
    head_cx, head_cy = cx, cy - 10
    pygame.draw.circle(surf, (255, 220, 180), (head_cx, head_cy), 6)
    # Eyes
    pygame.draw.circle(surf, (50, 50, 50), (head_cx + 2, head_cy - 1), 1)
    
    # 2. Body (blue rectangle)
    body_rect = pygame.Rect(cx - 6, cy - 4, 12, 16)
    pygame.draw.rect(surf, (50, 160, 255), body_rect, border_radius=3)
    # Clothing texture (vertical line)
    pygame.draw.line(surf, (30, 120, 220), (cx, cy - 4), (cx, cy + 12), 1)
    
    # 3. Right arm (holding gun)
    arm_r_x, arm_r_y = cx + 6, cy
    pygame.draw.line(surf, (255, 220, 180), (cx + 4, cy + 2), (arm_r_x, arm_r_y), 3)
    # Gun barrel (changes appearance based on weapon type)
    gun = GUN_TYPES[current_gun]
    gun_color = gun["color"]
    if current_gun == "pistol":
        gun_x = arm_r_x + 8
        pygame.draw.line(surf, gun_color, (arm_r_x, arm_r_y), (gun_x, arm_r_y + 1), 3)
        pygame.draw.rect(surf, (100, 100, 120), (gun_x - 2, arm_r_y - 2, 6, 4))
    elif current_gun == "rifle":
        gun_x = arm_r_x + 12
        pygame.draw.line(surf, gun_color, (arm_r_x, arm_r_y), (gun_x, arm_r_y), 2)
        pygame.draw.rect(surf, gun_color, (arm_r_x + 4, arm_r_y - 2, 6, 4))
        pygame.draw.rect(surf, (80, 60, 30), (arm_r_x + 3, arm_r_y - 3, 9, 6), border_radius=1)
    elif current_gun == "shotgun":
        gun_x = arm_r_x + 10
        pygame.draw.line(surf, gun_color, (arm_r_x, arm_r_y), (gun_x, arm_r_y + 1), 4)
        pygame.draw.rect(surf, gun_color, (gun_x - 3, arm_r_y - 2, 7, 5), border_radius=1)
    elif current_gun == "sniper":
        gun_x = arm_r_x + 14
        pygame.draw.line(surf, gun_color, (arm_r_x, arm_r_y), (gun_x, arm_r_y), 2)
        pygame.draw.rect(surf, gun_color, (arm_r_x + 2, arm_r_y - 2, 10, 4))
        pygame.draw.circle(surf, (200, 200, 255), (arm_r_x + 8, arm_r_y), 3)
    
    # 4. Left arm (relaxed)
    pygame.draw.line(surf, (255, 220, 180), (cx - 4, cy + 2), (cx - 8, cy + 8), 3)
    
    # 5. Legs (walking animation)
    walk_phase = pygame.time.get_ticks() * 0.01
    leg_swing = math.sin(walk_phase) * 8
    
    # Right leg
    leg_r_x = cx + 4 + leg_swing
    pygame.draw.line(surf, (40, 60, 120), (cx + 3, cy + 12), (leg_r_x, cy + 22), 3)
    # Shoes
    pygame.draw.circle(surf, (30, 30, 30), (int(leg_r_x), int(cy + 22)), 2)
    
    # Left leg
    leg_l_x = cx - 4 - leg_swing
    pygame.draw.line(surf, (40, 60, 120), (cx - 3, cy + 12), (leg_l_x, cy + 22), 3)
    # Shoes
    pygame.draw.circle(surf, (30, 30, 30), (int(leg_l_x), int(cy + 22)), 2)
    
    # ---- Rotate surface ----
    if face_angle != 0:
        rotated = pygame.transform.rotate(surf, -face_angle)
        rx, ry = rotated.get_rect().center
        screen.blit(rotated, (sx + cx - rx, sy + cy - ry))
    else:
        screen.blit(surf, (sx, sy))

def draw_enemy(ewx, ewy, state):
    sx, sy = w2s(ewx, ewy)
    cx, cy = sx + enemy_size // 2, sy + enemy_size // 2
    
    # Select color based on state
    if state == "chase":
        body_color = ENEMY_ALERT
    elif state == "alert":
        body_color = (255, 180, 100)
    elif state == "tired":
        body_color = (120, 120, 130)
    else:
        body_color = ENEMY_COLOR
    
    # 1. Head (dark red circle)
    head_radius = 5
    pygame.draw.circle(screen, (200, 50, 50), (cx, cy - 9), head_radius)
    # Eyes
    pygame.draw.circle(screen, (50, 50, 50), (cx + 2, cy - 10), 1)
    
    # 2. Body (red rectangle)
    body_h = 14
    body_top = cy - 4
    pygame.draw.rect(screen, body_color, (cx - 5, body_top, 10, body_h), border_radius=2)
    
    # 3. Arms (two line segments)
    # Right arm (holding gun)
    pygame.draw.line(screen, (200, 50, 50), (cx + 5, cy), (cx + 9, cy + 4), 2)
    # Gun barrel
    pygame.draw.line(screen, (100, 100, 120), (cx + 9, cy + 4), (cx + 16, cy + 4), 2)
    pygame.draw.rect(screen, (80, 80, 100), (cx + 14, cy + 2, 5, 5), border_radius=1)
    # Left arm
    pygame.draw.line(screen, (200, 50, 50), (cx - 5, cy), (cx - 9, cy + 4), 2)
    
    # 4. Legs (two line segments)
    # Right leg
    pygame.draw.line(screen, (80, 30, 30), (cx + 3, cy + body_h), (cx + 5, cy + body_h + 8), 2)
    # Left leg
    pygame.draw.line(screen, (80, 30, 30), (cx - 3, cy + body_h), (cx - 5, cy + body_h + 8), 2)
    
    # State indicator (preserve existing logic)
    if state == "chase":
        warn_text = font_small.render("!", True, (255, 50, 50))
        screen.blit(warn_text, (sx + enemy_size // 2 - 3, sy - 22))
    elif state == "tired":
        zzz_text = font_small.render("Z", True, GRAY)
        screen.blit(zzz_text, (sx + enemy_size // 2 - 3, sy - 22))

def draw_supply(swx, swy, stype, searching=False):
    sx, sy = w2s(swx, swy)
    info  = SUPPLY_TYPES[stype]
    color = info["color"]

    pulse = abs(math.sin(pygame.time.get_ticks() * 0.003 + swx * 0.01)) * 0.3 + 0.7
    glow_color = tuple(min(255, int(c * pulse * 0.5)) for c in color)
    cx_s = sx + SUPPLY_SIZE // 2
    cy_s = sy + SUPPLY_SIZE // 2

    pygame.draw.circle(screen, glow_color, (cx_s, cy_s), SUPPLY_SIZE // 2 + 6, 2)

    if stype == "bonus":
        # Red diamond body
        r = SUPPLY_SIZE // 2
        diamond = [(cx_s, cy_s - r), (cx_s + r, cy_s), (cx_s, cy_s + r), (cx_s - r, cy_s)]
        pygame.draw.polygon(screen, color, diamond)
        inner_r = r - 4
        inner = [(cx_s, cy_s - inner_r), (cx_s + inner_r, cy_s),
                 (cx_s, cy_s + inner_r), (cx_s - inner_r, cy_s)]
        pygame.draw.polygon(screen, WHITE, inner, 2)
        flicker = abs(math.sin(pygame.time.get_ticks() * 0.006 + sx * 0.01)) * 0.5 + 0.5
        dot_color = (255, 255, int(100 + 155 * flicker))
        pygame.draw.circle(screen, dot_color, (cx_s, cy_s), 3)
    elif stype == "common":
        # Drawer cabinet (green supply pile)
        cabinet_color = (139, 90, 43)
        pygame.draw.rect(screen, cabinet_color, (sx, sy, SUPPLY_SIZE, SUPPLY_SIZE), border_radius=2)
        drawer_h = SUPPLY_SIZE // 3
        for i in range(1, 3):
            line_y = sy + i * drawer_h
            pygame.draw.line(screen, (80, 50, 20), (sx + 2, line_y), (sx + SUPPLY_SIZE - 2, line_y), 2)
        for i in range(3):
            handle_x = sx + SUPPLY_SIZE // 2
            handle_y = sy + i * drawer_h + drawer_h // 2
            pygame.draw.circle(screen, (200, 180, 100), (handle_x, handle_y), 2)
    elif stype == "rare":
        # Silver safe (gold supply pile)
        safe_color = (180, 180, 200)
        pygame.draw.rect(screen, safe_color, (sx, sy, SUPPLY_SIZE, SUPPLY_SIZE), border_radius=3)
        door_rect = pygame.Rect(sx + 2, sy + 2, SUPPLY_SIZE - 4, SUPPLY_SIZE - 4)
        pygame.draw.rect(screen, (120, 120, 140), door_rect, 2, border_radius=2)
        handle_x = sx + SUPPLY_SIZE // 2
        handle_y = sy + SUPPLY_SIZE // 2
        pygame.draw.rect(screen, (200, 180, 50), (handle_x - 3, handle_y - 1, 6, 2), border_radius=1)
    elif stype == "ammo":
        # Dark green rectangular ammo crate
        ammo_color = (0, 80, 0)
        pygame.draw.rect(screen, ammo_color, (sx, sy, SUPPLY_SIZE, SUPPLY_SIZE), border_radius=2)
        stripe_color = (200, 200, 50)
        pygame.draw.line(screen, stripe_color, (sx + 2, sy + SUPPLY_SIZE // 2), (sx + SUPPLY_SIZE - 2, sy + SUPPLY_SIZE // 2), 2)
        for j in range(3):
            bx2 = sx + 5 + j * 4
            pygame.draw.rect(screen, (200, 200, 100), (bx2, sy + 7, 3, 6), border_radius=1)
    elif stype == "heal":
        # White square + red cross (no search needed, direct pickup)
        pygame.draw.rect(screen, (240, 240, 240), (sx, sy, SUPPLY_SIZE, SUPPLY_SIZE), border_radius=2)
        # Red cross
        cx_h = sx + SUPPLY_SIZE // 2
        cy_h = sy + SUPPLY_SIZE // 2
        pygame.draw.line(screen, (220, 30, 30), (cx_h, sy + 4), (cx_h, sy + SUPPLY_SIZE - 4), 3)
        pygame.draw.line(screen, (220, 30, 30), (sx + 4, cy_h), (sx + SUPPLY_SIZE - 4, cy_h), 3)
    elif stype == "enemy_drop":
        # Rectangular wooden crate (enemy drop)
        box_color = (160, 120, 60)
        pygame.draw.rect(screen, box_color, (sx, sy, SUPPLY_SIZE, SUPPLY_SIZE), border_radius=2)
        for i in range(1, 4):
            line_x = sx + i * (SUPPLY_SIZE // 4)
            pygame.draw.line(screen, (120, 80, 40), (line_x, sy + 2), (line_x, sy + SUPPLY_SIZE - 2), 1)
        for i in range(2):
            nail_x = sx + 3 + i * (SUPPLY_SIZE - 6)
            nail_y = sy + 3
            pygame.draw.circle(screen, (200, 200, 200), (nail_x, nail_y), 1)
    elif stype == "boss_drop":
        # Normal wooden crate (Boss drop, with glowing edge)
        box_color = (180, 140, 70)
        pygame.draw.rect(screen, box_color, (sx, sy, SUPPLY_SIZE, SUPPLY_SIZE), border_radius=3)
        # Wood grain texture (vertical lines)
        for i in range(1, 5):
            lx = sx + i * (SUPPLY_SIZE // 5)
            pygame.draw.line(screen, (140, 100, 45), (lx, sy + 2), (lx, sy + SUPPLY_SIZE - 2), 1)
        # Horizontal line reinforcement
        pygame.draw.line(screen, (140, 100, 45), (sx + 2, sy + SUPPLY_SIZE // 2),
                         (sx + SUPPLY_SIZE - 2, sy + SUPPLY_SIZE // 2), 1)
        # Iron nails (four corners)
        for dx, dy in [(3, 3), (SUPPLY_SIZE - 3, 3),
                       (3, SUPPLY_SIZE - 3), (SUPPLY_SIZE - 3, SUPPLY_SIZE - 3)]:
            pygame.draw.circle(screen, (200, 200, 200), (sx + dx, sy + dy), 1)
        # Subtle gold border (indicates Boss drop)
        pygame.draw.rect(screen, (255, 200, 60), (sx, sy, SUPPLY_SIZE, SUPPLY_SIZE), 2, border_radius=3)

    # Search progress bar
    if searching and search_timer > 0:
        bar_w = SUPPLY_SIZE + 10
        bar_h = 6
        bar_x = sx - 5
        bar_y = sy - 12
        progress = 1.0 - (search_timer / SEARCH_DURATION)
        pygame.draw.rect(screen, DARK_GRAY, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        pygame.draw.rect(screen, (100, 200, 255),
                         (bar_x, bar_y, int(bar_w * progress), bar_h), border_radius=3)

def resolve_wall_collision(ent_x, ent_y, ent_w, ent_h, walls_list):
    """Axis-aligned pushback: resolve entity-wall collisions and push out. Returns (new_x, new_y)."""
    entity_rect = pygame.Rect(ent_x, ent_y, ent_w, ent_h)

    for w in walls_list:
        wall_rect = pygame.Rect(w[0], w[1], w[2], w[3])
        if not entity_rect.colliderect(wall_rect):
            continue

        # Y-axis pushback
        if entity_rect.centery < wall_rect.centery:
            ent_y = wall_rect.top - ent_h
        else:
            ent_y = wall_rect.bottom
        entity_rect.y = ent_y

        # X-axis pushback (after Y correction)
        if entity_rect.colliderect(wall_rect):
            if entity_rect.centerx < wall_rect.centerx:
                ent_x = wall_rect.left - ent_w
            else:
                ent_x = wall_rect.right
        entity_rect.x = ent_x

    return ent_x, ent_y


def draw_boss(b):
    """Draw Boss character: large dark figure + gold frame + HP bar + BOSS label"""
    bx, by, bhp = b[0], b[1], b[2]
    if not on_screen(bx, by, BOSS_SIZE):
        return
    sx, sy = w2s(bx, by)
    sx, sy = int(sx), int(sy)
    bs = BOSS_SIZE
    cx = sx + bs // 2
    cy = sy + bs // 2
    t_ms = pygame.time.get_ticks()

    # Walking animation phase
    walk = math.sin(t_ms * 0.006) * 0.4

    # -- Legs --
    leg_color = (60, 30, 100)
    leg_w = bs // 7
    body_bottom = sy + bs * 2 // 3
    # Left leg
    lleg_off = int(walk * bs * 0.15)
    pygame.draw.rect(screen, leg_color,
                     (cx - leg_w * 2, body_bottom, leg_w + 2, bs // 3 + lleg_off), border_radius=3)
    # Right leg
    rleg_off = int(-walk * bs * 0.15)
    pygame.draw.rect(screen, leg_color,
                     (cx + leg_w, body_bottom, leg_w + 2, bs // 3 + rleg_off), border_radius=3)

    # -- Body --
    body_color = (30, 20, 60)
    body_rect = pygame.Rect(cx - bs // 3, sy + bs // 4, bs * 2 // 3, bs * 5 // 12)
    pygame.draw.rect(screen, body_color, body_rect, border_radius=4)
    # Gold emblem (chest X)
    c1x = body_rect.left + 4
    c1y = body_rect.top + 4
    c2x = body_rect.right - 4
    c2y = body_rect.bottom - 4
    pygame.draw.line(screen, (255, 200, 40), (c1x, c1y), (c2x, c2y), 2)
    pygame.draw.line(screen, (255, 200, 40), (c2x, c1y), (c1x, c2y), 2)

    # -- Arms --
    arm_color = (30, 20, 60)
    arm_offset = int(walk * bs * 0.12)
    # Left arm
    pygame.draw.rect(screen, arm_color,
                     (cx - bs // 3 - bs // 8, sy + bs // 4, bs // 8, bs * 5 // 16 - arm_offset),
                     border_radius=3)
    # Right arm (holding weapon)
    pygame.draw.rect(screen, arm_color,
                     (cx + bs // 3, sy + bs // 4, bs // 8, bs * 5 // 16 + arm_offset),
                     border_radius=3)
    # Gun (right arm tip)
    gun_x = cx + bs // 3 + bs // 8 - 2
    gun_y = sy + bs // 4 + bs * 5 // 16 + arm_offset
    pygame.draw.rect(screen, (60, 60, 60), (gun_x - 1, gun_y, 3, 10), border_radius=1)

    # -- Head --
    head_r = bs // 5
    head_cx = cx
    head_cy = sy + bs // 4 - head_r + 2
    # Hat base
    pygame.draw.rect(screen, (20, 10, 40),
                     (head_cx - head_r - 3, head_cy - 4, head_r * 2 + 6, 5))
    # Hat cylinder
    pygame.draw.rect(screen, (20, 10, 40),
                     (head_cx - head_r + 2, head_cy - 4 - head_r, head_r * 2 - 4, head_r + 2))
    # Face
    pygame.draw.circle(screen, (200, 160, 120), (head_cx, head_cy), head_r)
    # Glowing eyes (orange-red)
    eye_glow = abs(math.sin(t_ms * 0.005)) * 0.5 + 0.5
    eye_col = (int(255 * eye_glow), int(80 * eye_glow), 0)
    pygame.draw.circle(screen, eye_col, (head_cx - head_r // 3, head_cy), 3)
    pygame.draw.circle(screen, eye_col, (head_cx + head_r // 3, head_cy), 3)

    # -- Gold border aura --
    pygame.draw.rect(screen, (255, 200, 40),
                     (sx, sy, bs, bs + bs // 3), 3, border_radius=6)

    # HP bar
    bar_w = bs
    bar_h = 6
    bar_x = sx
    bar_y = sy - 14
    boss_max_hp = b[5] if len(b) > 5 else BOSS_MAX_HP
    hp_ratio = max(0, bhp / boss_max_hp)
    pygame.draw.rect(screen, (40, 10, 10), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
    if hp_ratio > 0.5:
        hp_color = (60, 220, 60)
    elif hp_ratio > 0.25:
        hp_color = (220, 220, 40)
    else:
        hp_color = (255, 40, 40)
    pygame.draw.rect(screen, hp_color,
                     (bar_x, bar_y, int(bar_w * hp_ratio), bar_h), border_radius=2)
    pygame.draw.rect(screen, (255, 200, 40), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=2)

    # BOSS label
    boss_label = font_small.render("BOSS", True, (255, 50, 50))
    screen.blit(boss_label, (sx + bs // 2 - boss_label.get_width() // 2, sy - 30))

def draw_chaser(c):
    """Draw Chaser character: orange-red hunter + tracking line + lock-on indicator"""
    global player_x, player_y, cam_x, player_size
    cx_w, cy_w, chp, detected = c[0], c[1], c[2], c[3]
    if not on_screen(cx_w, cy_w, CHASER_SIZE):
        return
    sx, sy = w2s(cx_w, cy_w)
    sx, sy = int(sx), int(sy)
    cs = CHASER_SIZE
    cx = sx + cs // 2
    cy = sy + cs // 2
    t_ms = pygame.time.get_ticks()

    # Player actual screen position
    psx = player_x + player_size // 2 - cam_x
    psy = player_y + player_size // 2 - cam_y

    # Walking animation
    walk = math.sin(t_ms * 0.008 + cx_w * 0.1) * 0.4

    # Angle toward player (for body leaning)
    to_px = psx - cx
    to_py = psy - cy
    face_dir = 1 if to_px >= 0 else -1

    # -- Legs --
    leg_color = (150, 60, 20)
    leg_w = cs // 7
    body_bottom = sy + cs * 2 // 3
    lleg_off = int(walk * cs * 0.18)
    rleg_off = int(-walk * cs * 0.18)
    pygame.draw.rect(screen, leg_color,
                     (cx - leg_w * 2, body_bottom, leg_w + 1, cs // 3 + lleg_off), border_radius=2)
    pygame.draw.rect(screen, leg_color,
                     (cx + leg_w, body_bottom, leg_w + 1, cs // 3 + rleg_off), border_radius=2)

    # -- Body --
    body_color = CHASER_COLOR
    body_rect = pygame.Rect(cx - cs // 3, sy + cs // 4, cs * 2 // 3, cs * 5 // 12)
    pygame.draw.rect(screen, body_color, body_rect, border_radius=4)
    # Body pulse border when locked on
    if detected:
        pulse = abs(math.sin(t_ms * 0.008)) * 0.6 + 0.4
        border_col = (255, int(200 * pulse), int(60 * pulse))
        pygame.draw.rect(screen, border_col, body_rect, 2, border_radius=4)

    # -- Arms --
    arm_color = (180, 80, 30)
    arm_off = int(walk * cs * 0.12)
    pygame.draw.rect(screen, arm_color,
                     (cx - cs // 3 - cs // 8, sy + cs // 4, cs // 8, cs * 5 // 16 - arm_off),
                     border_radius=2)
    pygame.draw.rect(screen, arm_color,
                     (cx + cs // 3, sy + cs // 4, cs // 8, cs * 5 // 16 + arm_off),
                     border_radius=2)
    # Dagger (right arm tip)
    knife_x = cx + cs // 3 + cs // 8 - 1
    knife_y = sy + cs // 4 + cs * 5 // 16 + arm_off
    pygame.draw.rect(screen, (200, 200, 220), (knife_x - 1, knife_y, 2, 8), border_radius=1)
    pygame.draw.polygon(screen, (180, 180, 200),
                        [(knife_x - 2, knife_y + 8), (knife_x + 2, knife_y + 8), (knife_x, knife_y + 14)])

    # -- Head --
    head_r = cs // 5
    head_cx = cx
    head_cy = sy + cs // 4 - head_r + 2
    pygame.draw.circle(screen, (220, 170, 120), (head_cx, head_cy), head_r)
    # Headband
    pygame.draw.arc(screen, (180, 60, 20),
                    pygame.Rect(head_cx - head_r, head_cy - head_r, head_r * 2, head_r * 2),
                    0, math.pi, 4)
    # Eyes (glow when locked)
    if detected:
        eye_glow = abs(math.sin(t_ms * 0.01)) * 0.5 + 0.5
        eye_col = (int(255 * eye_glow), int(120 * eye_glow), 0)
    else:
        eye_col = (60, 40, 20)
    pygame.draw.circle(screen, eye_col, (head_cx - head_r // 3, head_cy), 2)
    pygame.draw.circle(screen, eye_col, (head_cx + head_r // 3, head_cy), 2)

    # HP bar
    bar_w = cs
    bar_h = 4
    bar_x = sx
    bar_y = sy - 10
    hp_ratio = max(0, chp / (CHASER_HP * _dm(HM_CHASER_MULT, EM_CHASER_MULT)))
    pygame.draw.rect(screen, (30, 10, 5), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
    hp_color = (255, 80, 40) if hp_ratio > 0.3 else (255, 20, 20)
    pygame.draw.rect(screen, hp_color,
                     (bar_x, bar_y, int(bar_w * hp_ratio), bar_h), border_radius=2)

    # Label
    label = font_small.render("猎手" if detected else "?", True,
                              (255, 200, 100) if detected else GRAY)
    screen.blit(label, (sx + cs // 2 - label.get_width() // 2, sy - 24))

    # Tracking line when target acquired
    if detected:
        pcx_s = psx
        pcy_s = psy
        dash_len = 8
        gap_len = 6
        total = math.hypot(pcx_s - cx, pcy_s - cy)
        if total > 0:
            left  = int(min(cx, pcx_s)) - 2
            top   = int(min(cy, pcy_s)) - 2
            right = int(max(cx, pcx_s)) + 2
            bottom= int(max(cy, pcy_s)) + 2
            surf_w = right - left
            surf_h = bottom - top
            ndx = (pcx_s - cx) / total
            ndy = (pcy_s - cy) / total
            dist = 0
            dash_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
            while dist < total:
                d1x = cx + ndx * dist
                d1y = cy + ndy * dist
                d2x = cx + ndx * min(dist + dash_len, total)
                d2y = cy + ndy * min(dist + dash_len, total)
                alpha = int(60 + 40 * abs(math.sin(dist * 0.05 + t_ms * 0.003)))
                pygame.draw.line(dash_surf, (255, 60, 20, alpha),
                                 (d1x - left, d1y - top),
                                 (d2x - left, d2y - top), 2)
                dist += dash_len + gap_len
            screen.blit(dash_surf, (left, top))

def draw_super_chaser(sc):
    """Draw Super Chaser character: green elite + invincible aura + lock-on indicator"""
    global player_x, player_y, cam_x, player_size
    scx_w, scy_w, detected = sc[0], sc[1], sc[2]
    if not on_screen(scx_w, scy_w, SUPER_CHASER_SIZE):
        return
    sx, sy = w2s(scx_w, scy_w)
    sx, sy = int(sx), int(sy)
    ss = SUPER_CHASER_SIZE
    cx = sx + ss // 2
    cy = sy + ss // 2
    t_ms = pygame.time.get_ticks()

    psx = player_x + player_size // 2 - cam_x
    psy = player_y + player_size // 2 - cam_y

    # Walking animation
    walk = math.sin(t_ms * 0.007 + scx_w * 0.1) * 0.4

    # Invincible aura (pulsing rings)
    pulse = abs(math.sin(t_ms * 0.005)) * 0.5 + 0.5
    for i in range(3, 0, -1):
        radius = ss // 2 + i * 7 + int(math.sin(t_ms * 0.004 + i) * 5)
        alpha = int((4 - i) * 25 * pulse)
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow,
                           (SUPER_CHASER_COLOR[0], SUPER_CHASER_COLOR[1],
                            SUPER_CHASER_COLOR[2], alpha),
                           (radius, radius), radius, 2)
        screen.blit(glow, (cx - radius, cy - radius))

    # -- Legs --
    leg_color = (30, 120, 50)
    leg_w = ss // 7
    body_bottom = sy + ss * 2 // 3
    lleg_off = int(walk * ss * 0.18)
    rleg_off = int(-walk * ss * 0.18)
    pygame.draw.rect(screen, leg_color,
                     (cx - leg_w * 2, body_bottom, leg_w + 1, ss // 3 + lleg_off), border_radius=2)
    pygame.draw.rect(screen, leg_color,
                     (cx + leg_w, body_bottom, leg_w + 1, ss // 3 + rleg_off), border_radius=2)

    # -- Body (green armor) --
    body_color = SUPER_CHASER_COLOR
    body_rect = pygame.Rect(cx - ss // 3, sy + ss // 4, ss * 2 // 3, ss * 5 // 12)
    pygame.draw.rect(screen, body_color, body_rect, border_radius=4)
    # Armor texture
    if detected:
        pulse2 = abs(math.sin(t_ms * 0.01)) * 0.6 + 0.4
        border_col = (int(80 * pulse2 + 100), int(255 * pulse2), int(100 * pulse2 + 60))
    else:
        border_col = (80, 200, 100)
    pygame.draw.rect(screen, border_col, body_rect, 2, border_radius=4)
    # Chest cross emblem
    mx = body_rect.centerx
    my = body_rect.centery
    pygame.draw.line(screen, (150, 255, 160), (mx, my - 6), (mx, my + 6), 2)
    pygame.draw.line(screen, (150, 255, 160), (mx - 6, my), (mx + 6, my), 2)

    # -- Arms --
    arm_color = (40, 140, 60)
    arm_off = int(walk * ss * 0.12)
    pygame.draw.rect(screen, arm_color,
                     (cx - ss // 3 - ss // 8, sy + ss // 4, ss // 8, ss * 5 // 16 - arm_off),
                     border_radius=2)
    pygame.draw.rect(screen, arm_color,
                     (cx + ss // 3, sy + ss // 4, ss // 8, ss * 5 // 16 + arm_off),
                     border_radius=2)
    # Long blade (right arm tip)
    blade_x = cx + ss // 3 + ss // 8 - 1
    blade_y = sy + ss // 4 + ss * 5 // 16 + arm_off
    pygame.draw.rect(screen, (180, 220, 190), (blade_x - 1, blade_y, 2, 12), border_radius=1)
    # Blade tip
    pygame.draw.polygon(screen, (220, 255, 230),
                        [(blade_x - 2, blade_y + 12),
                         (blade_x + 2, blade_y + 12),
                         (blade_x, blade_y + 18)])

    # -- Head (military helmet) --
    head_r = ss // 5
    head_cx = cx
    head_cy = sy + ss // 4 - head_r + 2
    pygame.draw.circle(screen, (200, 160, 110), (head_cx, head_cy), head_r)
    # Helmet
    helmet_color = (30, 120, 50)
    pygame.draw.arc(screen, helmet_color,
                    pygame.Rect(head_cx - head_r - 1, head_cy - head_r - 1,
                                (head_r + 1) * 2, (head_r + 1) * 2),
                    0.1, math.pi - 0.1, head_r + 1)
    pygame.draw.rect(screen, helmet_color,
                     (head_cx - head_r - 1, head_cy - 3, (head_r + 1) * 2, 5), border_radius=1)
    # Glowing eyes (green)
    eye_glow = abs(math.sin(t_ms * 0.012)) * 0.5 + 0.5
    eye_col = (0, int(200 + 55 * eye_glow), int(60 * eye_glow))
    pygame.draw.circle(screen, eye_col, (head_cx - head_r // 3, head_cy + 1), 2)
    pygame.draw.circle(screen, eye_col, (head_cx + head_r // 3, head_cy + 1), 2)

    # Invincible + Super Chaser labels
    inv_label = font_small.render("无敌", True, (200, 255, 100))
    screen.blit(inv_label, (sx + ss // 2 - inv_label.get_width() // 2, sy - 28))
    label = font_small.render("超级猎手" if detected else "???", True,
                              (100, 255, 150) if detected else GRAY)
    screen.blit(label, (sx + ss // 2 - label.get_width() // 2, sy - 44))

    # Tracking line when target acquired (bright green)
    if detected:
        pcx_s = psx
        pcy_s = psy
        dash_len = 8
        gap_len = 6
        total = math.hypot(pcx_s - cx, pcy_s - cy)
        if total > 0:
            left  = int(min(cx, pcx_s)) - 2
            top   = int(min(cy, pcy_s)) - 2
            right = int(max(cx, pcx_s)) + 2
            bottom= int(max(cy, pcy_s)) + 2
            surf_w = right - left
            surf_h = bottom - top
            ndx = (pcx_s - cx) / total
            ndy = (pcy_s - cy) / total
            dist = 0
            dash_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
            while dist < total:
                d1x = cx + ndx * dist
                d1y = cy + ndy * dist
                d2x = cx + ndx * min(dist + dash_len, total)
                d2y = cy + ndy * min(dist + dash_len, total)
                alpha = int(60 + 40 * abs(math.sin(dist * 0.05 + t_ms * 0.004)))
                pygame.draw.line(dash_surf, (30, 255, 80, alpha),
                                 (d1x - left, d1y - top),
                                 (d2x - left, d2y - top), 2)
                dist += dash_len + gap_len
            screen.blit(dash_surf, (left, top))

def draw_grass_texture():
    """Draw grass texture (blades) - using deterministic algorithm, no random module"""
    grass_color = (35, 120, 40)
    grass_color2 = (30, 100, 35)
    
    world_left = cam_x - 50
    world_top = cam_y - 50
    world_right = cam_x + WIDTH + 50
    world_bottom = cam_y + HEIGHT + 50
    
    grid_size = 30
    
    start_x = int(world_left // grid_size) * grid_size
    start_y = int(world_top // grid_size) * grid_size
    
    for gx in range(int(start_x), int(world_right), grid_size):
        for gy in range(int(start_y), int(world_bottom), grid_size):
            # Deterministic hash (no random module)
            h = int(gx // grid_size) * 31 + int(gy // grid_size) * 37
            h = int(h) & 0xFFFF
            
            # Use hash value for grass blade params
            num_blades = 1 + (h & 1)
            length = 4 + ((h >> 1) & 7)
            angle = ((h >> 4) & 7) / 7.0 - 0.5
            
            # Grass blade position (offset within grid cell)
            ox = 2 + ((h >> 8) & 15)
            oy = 2 + ((h >> 12) & 15)
            
            sx, sy = w2s(gx + ox, gy + oy)
            
            # Draw grass blade
            for i in range(num_blades):
                ex = sx + math.sin(angle + i * 0.3) * length
                ey = sy - length
                color = grass_color if i == 0 else grass_color2
                pygame.draw.line(screen, color, (sx, sy), (ex, ey), 1)

def draw_walls():
    """Draw all walls (with 3D highlight effect)"""
    for w in walls:
        wx, wy, ww, wh = w
        if not on_screen(wx, wy):
            continue
        sx, sy = w2s(wx, wy)
        sx, sy = int(sx), int(sy)

        # Main fill
        wall_rect = pygame.Rect(sx, sy, int(ww), int(wh))
        pygame.draw.rect(screen, WALL_COLOR, wall_rect, border_radius=3)

        # Top highlight
        hl_top = pygame.Rect(sx + 2, sy, int(ww) - 4, 3)
        pygame.draw.rect(screen, WALL_EDGE_COLOR, hl_top, border_radius=1)

        # Left highlight
        hl_left = pygame.Rect(sx, sy + 3, 3, int(wh) - 6)
        pygame.draw.rect(screen, WALL_EDGE_COLOR, hl_left, border_radius=1)

        # Bottom shadow
        shadow = pygame.Rect(sx + 2, sy + int(wh) - 3, int(ww) - 4, 3)
        pygame.draw.rect(screen, (30, 25, 40), shadow, border_radius=1)

        # Surface brick texture
        for tx in range(sx + 10, sx + int(ww) - 10, 15):
            pygame.draw.line(screen, (50, 45, 60),
                             (tx, sy + 5), (tx, sy + int(wh) - 5), 1)


def draw_extract_zone(ez):
    ewx, ewy = ez[0], ez[1]
    esx, esy = w2s(ewx, ewy)
    cx, cy = esx + extract_size // 2, esy + extract_size // 2
    t_ms  = pygame.time.get_ticks()
    pulse = abs(math.sin(t_ms * 0.004)) * 0.6 + 0.4

    for i in range(5, 0, -1):
        radius = extract_size // 2 + i * 8 + int(math.sin(t_ms * 0.003 + i) * 10)
        alpha  = int((6 - i) * 15 * pulse)
        beacon = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(beacon, (*EXTRACT_COLOR, alpha), (radius, radius), radius, 2)
        screen.blit(beacon, (cx - radius, cy - radius))

    overlay = pygame.Surface((extract_size, extract_size), pygame.SRCALPHA)
    overlay.fill((*EXTRACT_COLOR, int(50 + 40 * pulse)))
    screen.blit(overlay, (esx, esy))

    for offset in [0, 2, 4]:
        rect = pygame.Rect(esx - offset, esy - offset,
                           extract_size + offset * 2, extract_size + offset * 2)
        c = tuple(min(255, int(v * pulse * (1 + offset * 0.2))) for v in EXTRACT_COLOR)
        pygame.draw.rect(screen, c, rect, max(1, 3 - offset), border_radius=8)

    icon_text = font_big.render("▼", True, EXTRACT_COLOR)
    screen.blit(icon_text, (cx - icon_text.get_width() // 2, cy - 18))

    zone_text = font_small.render("撤离点", True, WHITE)
    screen.blit(zone_text, (cx - zone_text.get_width() // 2, esy + extract_size - 18))

    # Hold progress bar (shown when player is in zone)
    if extract_hold_timer > 0:
        bar_w = extract_size
        bar_h = 8
        bar_x = esx
        bar_y = esy - 16
        progress = min(1.0, extract_hold_timer / EXTRACT_HOLD_FRAMES)
        pygame.draw.rect(screen, DARK_GRAY, (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        bar_color = (100, 255, 150) if progress < 0.9 else (255, 255, 100)
        pygame.draw.rect(screen, bar_color,
                         (bar_x, bar_y, int(bar_w * progress), bar_h), border_radius=4)
        sec_left = int((EXTRACT_HOLD_FRAMES - extract_hold_timer) / 60) + 1
        hold_text = font_small.render(f"撤离停留中... {sec_left}秒", True, (255, 255, 150))
        screen.blit(hold_text, (cx - hold_text.get_width() // 2, bar_y - 20))

    # Screen edge arrow (computed in screen coords)
    pcx = WIDTH  // 2
    pcy = HEIGHT // 2
    dx  = cx - pcx
    dy  = cy - pcy
    dist = math.hypot(dx, dy)
    if dist > 120 and dist > 0:
        ndx, ndy    = dx / dist, dy / dist
        edge_margin = 40
        t_values = []
        if ndx > 0: t_values.append((WIDTH  - edge_margin - pcx) / ndx)
        if ndx < 0: t_values.append((edge_margin - pcx) / ndx)
        if ndy > 0: t_values.append((HEIGHT - edge_margin - pcy) / ndy)
        if ndy < 0: t_values.append((edge_margin - pcy) / ndy)
        t = min(tv for tv in t_values if tv > 0)
        ax = pcx + ndx * t
        ay = pcy + ndy * t
        angle = math.atan2(dy, dx)
        for a_off in [-0.6, 0.6]:
            pygame.draw.line(screen, EXTRACT_COLOR,
                             (ax, ay),
                             (ax + math.cos(angle + a_off) * 12,
                              ay + math.sin(angle + a_off) * 12), 2)
        pygame.draw.line(screen, EXTRACT_COLOR,
                         (ax + math.cos(angle + 0.6) * 6, ay + math.sin(angle + 0.6) * 6),
                         (ax + math.cos(angle - 0.6) * 6, ay + math.sin(angle - 0.6) * 6), 2)


def draw_heart(surface, cx, cy, size, color=(255, 60, 60)):
    """Draw a heart shape centered at (cx,cy) on surface, size as radius unit."""
    s = size
    # Heart shape: two arc tops + triangle bottom
    # Left circle
    pygame.draw.circle(surface, color, (int(cx - s * 0.5), int(cy - s * 0.2)), int(s * 0.55))
    # Right circle
    pygame.draw.circle(surface, color, (int(cx + s * 0.5), int(cy - s * 0.2)), int(s * 0.55))
    # Fill center triangle (covers gap + forms bottom point)
    pts = [
        (int(cx - s * 1.0), int(cy - s * 0.2)),
        (int(cx + s * 1.0), int(cy - s * 0.2)),
        (int(cx),           int(cy + s * 1.0)),
    ]
    pygame.draw.polygon(surface, color, pts)


def draw_shield(surface, cx, cy, w, h, color=(210, 220, 235), shine=(255, 255, 255)):
    """Draw a silver shield centered at (cx,cy) on surface, w/h as dimensions."""
    hw, hh = w // 2, h // 2
    # Shield body: rounded rect top + pentagon bottom tip
    top_rect = pygame.Rect(cx - hw, cy - hh, w, h * 2 // 3)
    pygame.draw.rect(surface, color, top_rect, border_radius=4)
    # Bottom pointed polygon
    bottom_pts = [
        (cx - hw, cy - hh + h * 2 // 3),
        (cx + hw, cy - hh + h * 2 // 3),
        (cx,      cy + hh),
    ]
    pygame.draw.polygon(surface, color, bottom_pts)
    # Highlight stripe (top-left vertical line)
    hl_x = cx - hw + 4
    pygame.draw.line(surface, shine,
                     (hl_x, cy - hh + 3),
                     (hl_x, cy - hh + h * 2 // 5), 3)
    # Outer outline
    pygame.draw.rect(surface, (100, 110, 120), top_rect, 1, border_radius=4)
    pygame.draw.polygon(surface, (100, 110, 120), bottom_pts, 1)


def draw_clock_icon(surface, cx, cy, size, color=WHITE):
    """Draw a clock icon using pygame primitives centered at (cx,cy)."""
    s = size
    # Outer circle
    pygame.draw.circle(surface, color, (int(cx), int(cy)), int(s), 2)
    # Tick marks (12, 3, 6, 9 o'clock)
    for angle_deg in [0, 90, 180, 270]:
        rad = math.radians(angle_deg - 90)
        inner_r = s * 0.65
        outer_r = s * 0.9
        ix = cx + inner_r * math.cos(rad)
        iy = cy + inner_r * math.sin(rad)
        ox = cx + outer_r * math.cos(rad)
        oy = cy + outer_r * math.sin(rad)
        pygame.draw.line(surface, color, (int(ix), int(iy)), (int(ox), int(oy)), 2)
    # Hour hand (~10 o'clock)
    hr_deg = -60
    hr_rad = math.radians(hr_deg - 90)
    hr_len = s * 0.45
    hx = cx + hr_len * math.cos(hr_rad)
    hy = cy + hr_len * math.sin(hr_rad)
    pygame.draw.line(surface, color, (int(cx), int(cy)), (int(hx), int(hy)), 3)
    # Minute hand (~2 o'clock)
    min_deg = 60
    min_rad = math.radians(min_deg - 90)
    min_len = s * 0.65
    mx = cx + min_len * math.cos(min_rad)
    my = cy + min_len * math.sin(min_rad)
    pygame.draw.line(surface, color, (int(cx), int(cy)), (int(mx), int(my)), 2)
    # Center dot
    pygame.draw.circle(surface, color, (int(cx), int(cy)), int(s * 0.25))


def draw_hud():
    bar_bg = pygame.Surface((WIDTH, 56), pygame.SRCALPHA)
    bar_bg.fill((0, 0, 0, 130))
    screen.blit(bar_bg, (0, 0))

    screen.blit(font_normal.render(f"分数: {score}", True, WHITE), (12, 6))

    # HP: draw one heart icon + count (e.g., ♥ x 5)
    hx = 250
    hy = 16
    heart_size = 10
    draw_heart(screen, hx, hy, heart_size)
    screen.blit(font_small.render(f"x {lives}", True, (255, 80, 80)),
                (hx + heart_size + 10, hy - 8))

    # Armor: draw one shield icon + count, same format as HP
    if armor > 0:
        ax = hx + 70
        ay = hy
        shield_w, shield_h = 18, 22
        draw_shield(screen, ax, ay, shield_w, shield_h)
        screen.blit(font_small.render(f"x {armor}", True, (180, 210, 240)),
                    (ax + shield_w + 6, ay - 8))

    screen.blit(font_normal.render(f"倍率: x{extract_multiplier:.1f}", True, EXTRACT_COLOR),
                (WIDTH - 550, 6))

    # Backpack on second row to avoid overlap with multiplier
    bp_x = 10
    bp_y = 30
    screen.blit(font_small.render("背包:", True, WHITE), (bp_x, bp_y + 2))
    if len(backpack) == 0:
        screen.blit(font_small.render("（空）", True, GRAY), (bp_x + 55, bp_y + 2))
    else:
        for i, item in enumerate(backpack):
            pygame.draw.circle(screen, SUPPLY_TYPES[item]["color"],
                               (bp_x + 68 + i * 20, bp_y + 8), 7)
    screen.blit(font_small.render(f"{len(backpack)}/{backpack_max}", True, GRAY),
                (bp_x + 55, bp_y + 8))

    # Estimated value (right of backpack row)
    ev_text = font_small.render(f"预估: {estimated_value}", True, EXTRACT_COLOR)
    screen.blit(ev_text, (WIDTH - ev_text.get_width() - 12, bp_y + 2))

    remaining_sec = mission_timer // 60
    timer_color = WHITE if remaining_sec > 30 else ((255, 220, 80) if remaining_sec > 10 else (255, 60, 60))
    # Draw clock icon via code (no emoji dependency)
    clock_cx = WIDTH - 175
    clock_cy = 18
    draw_clock_icon(screen, clock_cx, clock_cy, 10, timer_color)
    screen.blit(font_normal.render(f"{remaining_sec}s", True, timer_color),
                (WIDTH - 160, 6))

    # Extraction message
    if extraction_message_timer > 0:
        msg_surf = font_big.render(extraction_message, True, EXTRACT_COLOR)
        bg_rect  = pygame.Rect(WIDTH // 2 - msg_surf.get_width() // 2 - 20,
                               HEIGHT // 2 - 100 - 10,
                               msg_surf.get_width() + 40, msg_surf.get_height() + 20)
        bg_surf  = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 160))
        screen.blit(bg_surf, (bg_rect.x, bg_rect.y))
        msg_surf.set_alpha(min(255, extraction_message_timer * 5))
        screen.blit(msg_surf, (WIDTH // 2 - msg_surf.get_width() // 2, HEIGHT // 2 - 100))

    # Super Chaser broadcast
    if super_chaser_broadcast_timer > 0:
        scb_surf = font_big.render(super_chaser_broadcast, True, SUPER_CHASER_COLOR)
        bg_rect  = pygame.Rect(WIDTH // 2 - scb_surf.get_width() // 2 - 20,
                               HEIGHT // 2 - 100 - 10,
                               scb_surf.get_width() + 40, scb_surf.get_height() + 20)
        bg_surf  = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 180))
        screen.blit(bg_surf, (bg_rect.x, bg_rect.y))
        scb_surf.set_alpha(min(255, super_chaser_broadcast_timer * 3))
        screen.blit(scb_surf, (WIDTH // 2 - scb_surf.get_width() // 2, HEIGHT // 2 - 100))

    # Save message
    if save_message_timer > 0:
        sv_color = (100, 255, 150) if "saved" in save_message.lower() else (255, 150, 100)
        sv_surf = font_normal.render(save_message, True, sv_color)
        sv_rect = pygame.Rect(WIDTH // 2 - sv_surf.get_width() // 2 - 12,
                              HEIGHT // 2 + 40 - 6,
                              sv_surf.get_width() + 24, sv_surf.get_height() + 12)
        sv_bg   = pygame.Surface((sv_rect.width, sv_rect.height), pygame.SRCALPHA)
        sv_bg.fill((0, 0, 0, 170))
        screen.blit(sv_bg, (sv_rect.x, sv_rect.y))
        sv_surf.set_alpha(min(255, save_message_timer * 4))
        screen.blit(sv_surf, (WIDTH // 2 - sv_surf.get_width() // 2, HEIGHT // 2 + 40))

    # Search complete message
    if search_message_timer > 0:
        msg_color = (100, 220, 255) if "cancelled" not in search_message.lower() else (255, 200, 100)
        sm_surf = font_big.render(search_message, True, msg_color)
        sm_rect = pygame.Rect(WIDTH // 2 - sm_surf.get_width() // 2 - 16,
                              HEIGHT // 2 - 30 - 8,
                              sm_surf.get_width() + 32, sm_surf.get_height() + 16)
        sm_bg   = pygame.Surface((sm_rect.width, sm_rect.height), pygame.SRCALPHA)
        sm_bg.fill((0, 0, 0, 160))
        screen.blit(sm_bg, (sm_rect.x, sm_rect.y))
        sm_surf.set_alpha(min(255, search_message_timer * 4))
        screen.blit(sm_surf, (WIDTH // 2 - sm_surf.get_width() // 2, HEIGHT // 2 - 30))

    # Bottom status bar
    if game_over:
        if game_over_reason == "time_up":
            status_text = font_small.render("任务时间耗尽", True, (255, 180, 80))
        else:
            status_text = font_small.render("! 直升机被击毁", True, (255, 80, 80))
    elif extract_hold_timer > 0:
        pct = int(extract_hold_timer / EXTRACT_HOLD_FRAMES * 100)
        status_text = font_small.render(f"● 撤离中... {pct}%  稳住！",
                                        True, EXTRACT_COLOR)
    elif searching_supply is not None:
        pct = int((1 - search_timer / SEARCH_DURATION) * 100)
        status_text = font_small.render(f"◎ 搜索中... {pct}%  别走远！",
                                        True, (100, 220, 255))
    else:
        status_text = font_small.render("● J搜索  |  停留3秒撤离  |  5存档 9读档",
                                        True, (100, 220, 100))
    screen.blit(status_text, (WIDTH // 2 - status_text.get_width() // 2, HEIGHT - 22))

    # Mission timer progress bar
    time_ratio  = mission_timer / MISSION_TIME
    time_bar_w  = int(WIDTH * 0.5)
    time_bar_x  = WIDTH // 2 - time_bar_w // 2
    time_bar_y  = HEIGHT - 34

    pygame.draw.rect(screen, DARK_GRAY, (time_bar_x, time_bar_y, time_bar_w, 8), border_radius=4)
    bar_color = (60, 200, 120) if time_ratio > 0.5 else ((255, 200, 60) if time_ratio > 0.17 else (255, 60, 60))
    pygame.draw.rect(screen, bar_color,
                     (time_bar_x, time_bar_y, int(time_bar_w * time_ratio), 8), border_radius=4)

    # Danger level bar
    danger_w = 100
    pygame.draw.rect(screen, DARK_GRAY, (WIDTH - danger_w - 12, HEIGHT - 20, danger_w, 6))
    danger_color = (int(255 * danger_level), int(200 * (1 - danger_level)), 50)
    pygame.draw.rect(screen, danger_color,
                     (WIDTH - danger_w - 12, HEIGHT - 20, int(danger_w * danger_level), 6))
    screen.blit(font_small.render("警戒", True, GRAY), (WIDTH - danger_w - 50, HEIGHT - 22))

    # Bullet count (right of timer bar) - red warning when <=30
    ammo_color = (255, 60, 60) if bullet_count <= 30 else (255, 240, 100)
    ammo_text = font_small.render(f"弹药: {bullet_count}", True, ammo_color)
    screen.blit(ammo_text, (time_bar_x + time_bar_w + 12, time_bar_y - 4))

    # Weapon bar (show all owned guns, highlight current) - never hide on ammo empty
    gun_list = ["pistol", "rifle", "shotgun", "sniper"]
    gun_x = WIDTH - 220
    for i, gn in enumerate(gun_list):
        if gn in owned_guns:
            g = GUN_TYPES[gn]
            is_current = (gn == current_gun)
            g_color = g['color'] if is_current else (100, 100, 100)
            g_label = font_small.render(f"{'▶' if is_current else ' '} {g['name']}", True, g_color)
            screen.blit(g_label, (gun_x, 50 + i * 22))
    # Scroll wheel hint
    wheel_hint = font_small.render("Tab/滚轮/1-4 切枪", True, (120, 120, 120))
    screen.blit(wheel_hint, (gun_x, 50 + len([g for g in gun_list if g in owned_guns]) * 22 + 2))

    # Ammo depleted hint (centered red text)
    if ammo_empty_timer > 0:
        et = font_normal.render("! 弹药耗尽！搜索弹药箱补给", True, (255, 80, 80))
        screen.blit(et, (WIDTH // 2 - et.get_width() // 2, HEIGHT // 2 - 60))

    # World coords position hint (bottom-left small text)
    pos_text = font_small.render(
        f"坐标 ({int(player_x)}, {int(player_y)})  地图 {WORLD_W}x{WORLD_H}",
        True, (80, 80, 100))
    screen.blit(pos_text, (8, HEIGHT - 22))


def draw_shop():
    """Post-extraction supply station screen"""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    # Panel background
    panel_w, panel_h = 500, 520
    panel_x = WIDTH // 2 - panel_w // 2
    panel_y = HEIGHT // 2 - panel_h // 2
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((20, 25, 50, 230))
    pygame.draw.rect(panel, (60, 80, 140), (0, 0, panel_w, panel_h), 3, border_radius=12)
    screen.blit(panel, (panel_x, panel_y))

    cy = panel_y + 20

    # Title
    title = font_big.render("撤离成功！补给站", True, EXTRACT_COLOR)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, cy))
    cy += title.get_height() + 5

    # Score summary
    summary = font_small.render(f"分数: {score}   |   生命: {lives}/{max_lives}   |   护甲: {armor}", True, WHITE)
    screen.blit(summary, (WIDTH // 2 - summary.get_width() // 2, cy))
    cy += 40

    # Option list
    options = [
        ("1", f"恢复生命  +1 ♥", SHOP_RESTORE_COST, lives < max_lives and score >= SHOP_RESTORE_COST),
        ("2", f"购买护甲  +1 ◆", SHOP_ARMOR_COST, score >= SHOP_ARMOR_COST),
        ("3", f"购买弹药  +50 ●", SHOP_AMMO_COST, score >= SHOP_AMMO_COST),
    ]

    for key, label, cost, available in options:
        color = WHITE if available else GRAY
        cost_color = (100, 255, 100) if available else (120, 120, 120)
        line = font_normal.render(f"[{key}] {label}   {cost} 分", True, color)
        screen.blit(line, (panel_x + 50, cy))
        cy += 50

    cy += 5
    # Armory divider
    gun_label = font_normal.render("── 武器库 ──", True, (200, 200, 100))
    screen.blit(gun_label, (panel_x + 50, cy))
    cy += 30

    gun_options = [
        ("4", "步枪", 800, score >= 800 and "rifle" not in owned_guns,
         "已拥有" if "rifle" in owned_guns else ("800 分" if score >= 800 else "分数不足")),
        ("5", "霰弹枪", 1500, score >= 1500 and "shotgun" not in owned_guns,
         "已拥有" if "shotgun" in owned_guns else ("1500 分" if score >= 1500 else "分数不足")),
        ("6", "狙击枪", 2500, score >= 2500 and "sniper" not in owned_guns,
         "已拥有" if "sniper" in owned_guns else ("2500 分" if score >= 2500 else "分数不足")),
    ]
    for key, label, cost, available, status in gun_options:
        color = WHITE if available else GRAY
        line = font_normal.render(f"[{key}] {label}   {status}", True, color)
        screen.blit(line, (panel_x + 50, cy))
        cy += 32

    cy += 10

    # Redeploy button
    action_text = font_normal.render("[Enter] 再次出发", True, (100, 255, 150))
    screen.blit(action_text, (WIDTH // 2 - action_text.get_width() // 2, cy))

    cy += 50
    help_text = font_small.render("撤离点已重置 - 准备下一轮任务", True, GRAY)
    screen.blit(help_text, (WIDTH // 2 - help_text.get_width() // 2, cy))

    cy += 30
    back_text = font_small.render("[0] 返回主菜单", True, (200, 200, 200))
    screen.blit(back_text, (WIDTH // 2 - back_text.get_width() // 2, cy))


def draw_transfer_station():
    """Post-destruction transfer station screen"""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    # Panel background
    panel_w, panel_h = 500, 520
    panel_x = WIDTH // 2 - panel_w // 2
    panel_y = HEIGHT // 2 - panel_h // 2
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((20, 25, 50, 230))
    pygame.draw.rect(panel, (180, 60, 60), (0, 0, panel_w, panel_h), 3, border_radius=12)
    screen.blit(panel, (panel_x, panel_y))

    cy = panel_y + 20

    # Title
    title = font_big.render("! 直升机被击毁！", True, (255, 80, 80))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, cy))
    cy += title.get_height() + 5

    # Transfer station subtitle
    sub = font_small.render("中转站 - 预估价值和背包已清空", True, GRAY)
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, cy))
    cy += 40

    # Status summary
    summary = font_small.render(f"分数: {score}   |   生命: {lives}/{max_lives}   |   护甲: {armor}", True, WHITE)
    screen.blit(summary, (WIDTH // 2 - summary.get_width() // 2, cy))
    cy += 40

    # Options
    options = [
        ("1", f"恢复生命  +1 ♥", SHOP_RESTORE_COST, lives < max_lives and score >= SHOP_RESTORE_COST),
        ("2", f"购买护甲  +1 ◆", SHOP_ARMOR_COST, score >= SHOP_ARMOR_COST),
        ("3", f"购买弹药  +3 ●", SHOP_AMMO_COST, score >= SHOP_AMMO_COST),
    ]

    for key, label, cost, available in options:
        color = WHITE if available else GRAY
        line = font_normal.render(f"[{key}] {label}   {cost} 分", True, color)
        screen.blit(line, (panel_x + 50, cy))
        cy += 50

    cy += 5
    # Armory divider
    gun_label = font_normal.render("── 武器库 ──", True, (200, 200, 100))
    screen.blit(gun_label, (panel_x + 50, cy))
    cy += 30

    gun_options = [
        ("4", "步枪", 800, score >= 800 and "rifle" not in owned_guns,
         "已拥有" if "rifle" in owned_guns else ("800 分" if score >= 800 else "分数不足")),
        ("5", "霰弹枪", 1500, score >= 1500 and "shotgun" not in owned_guns,
         "已拥有" if "shotgun" in owned_guns else ("1500 分" if score >= 1500 else "分数不足")),
        ("6", "狙击枪", 2500, score >= 2500 and "sniper" not in owned_guns,
         "已拥有" if "sniper" in owned_guns else ("2500 分" if score >= 2500 else "分数不足")),
    ]
    for key, label, cost, available, status in gun_options:
        color = WHITE if available else GRAY
        line = font_normal.render(f"[{key}] {label}   {status}", True, color)
        screen.blit(line, (panel_x + 50, cy))
        cy += 32

    cy += 10

    # Redeploy button
    action_text = font_normal.render("[Enter] 再次出发", True, (255, 200, 100))
    screen.blit(action_text, (WIDTH // 2 - action_text.get_width() // 2, cy))

    cy += 50
    help_text = font_small.render("再次出发，保持警惕！", True, GRAY)
    screen.blit(help_text, (WIDTH // 2 - help_text.get_width() // 2, cy))


def show_settings():
    """Draw settings screen"""
    screen.fill(BG_DARK)
    for i in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (20, 25, 45), (0, i), (WIDTH, i), 1)
    for i in range(0, WIDTH, 40):
        pygame.draw.line(screen, (20, 25, 45), (i, 0), (i, HEIGHT), 1)

    cy = 60
    title = font_huge.render("设置", True, (140, 180, 255))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, cy))
    cy += title.get_height() + 40

    # SFX toggle
    toggle_text = "开" if sfx_enabled else "关"
    sfx_line = font_normal.render(f"音效: {toggle_text}  [T] 开关", True, (200, 200, 200))
    screen.blit(sfx_line, (WIDTH // 2 - sfx_line.get_width() // 2, cy))
    cy += 40

    # SFX volume
    bar_w = 200
    bar_x = WIDTH // 2 - bar_w // 2
    sfx_label = font_normal.render(f"音效音量: {int(sfx_volume * 100)}%", True, (200, 200, 200))
    screen.blit(sfx_label, (WIDTH // 2 - sfx_label.get_width() // 2, cy))
    cy += sfx_label.get_height() + 6      # clear of the label's descenders
    pygame.draw.rect(screen, (50, 50, 60), (bar_x, cy, bar_w, 12), border_radius=6)
    pygame.draw.rect(screen, (100, 200, 255), (bar_x, cy, int(bar_w * sfx_volume), 12), border_radius=6)
    hint = font_small.render("[← →] 调节", True, (120, 120, 120))
    screen.blit(hint, (WIDTH // 2 + bar_w // 2 + 10, cy - 2))
    cy += 28

    # BGM volume
    bgm_label = font_normal.render(f"背景音乐音量: {int(bgm_volume * 100)}%", True, (200, 200, 200))
    screen.blit(bgm_label, (WIDTH // 2 - bgm_label.get_width() // 2, cy))
    cy += bgm_label.get_height() + 6
    pygame.draw.rect(screen, (50, 50, 60), (bar_x, cy, bar_w, 12), border_radius=6)
    pygame.draw.rect(screen, (100, 255, 100), (bar_x, cy, int(bar_w * bgm_volume), 12), border_radius=6)
    hint2 = font_small.render("[↑ ↓] 调节", True, (120, 120, 120))
    screen.blit(hint2, (WIDTH // 2 + bar_w // 2 + 10, cy - 2))
    cy += 50

    # Controls
    section = font_normal.render("── 操作说明 ──", True, (255, 200, 100))
    screen.blit(section, (WIDTH // 2 - section.get_width() // 2, cy))
    cy += 28
    controls = [
        ("WASD / 方向键", "移动直升机"),
        ("J", "搜索物资"),
        ("空格", "射击"),
        ("1-4 / Tab / 滚轮", "切换武器"),
        ("ESC", "暂停游戏"),
        ("5", "存档"),
        ("9", "读档"),
        ("Q", "退出游戏"),
    ]
    for key_t, desc in controls:
        ctrl_line = font_small.render(f"  {key_t}:  {desc}", True, (180, 200, 220))
        screen.blit(ctrl_line, (WIDTH // 2 - 200, cy))
        # advance by the real rendered height: font_small(24) with CJK glyphs is
        # taller than 20px, which made these lines overlap each other
        cy += ctrl_line.get_height() + 2

    cy += 20
    back_hint = font_normal.render("[ESC] 返回主菜单", True, (160, 160, 160))
    screen.blit(back_hint, (WIDTH // 2 - back_hint.get_width() // 2, cy))

    # Message hint
    if search_message_timer > 0:
        msg_surf = font_small.render(search_message, True, (100, 220, 255))
        screen.blit(msg_surf, (WIDTH // 2 - msg_surf.get_width() // 2, cy + 30))


def show_tutorial():
    """Draw tutorial/controls guide screen"""
    screen.fill(BG_DARK)
    for i in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (20, 25, 45), (0, i), (WIDTH, i), 1)
    for i in range(0, WIDTH, 40):
        pygame.draw.line(screen, (20, 25, 45), (i, 0), (i, HEIGHT), 1)

    cy = 40
    title = font_huge.render("操作指南", True, (255, 220, 100))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, cy))
    cy += title.get_height() + 24

    instructions = [
        ("目标：", "搜索物资并从战区撤离"),
        ("", ""),
        ("移动：", "WASD 或方向键"),
        ("搜索：", "飞到物资旁按 J（停留1.5秒）"),
        ("射击：", "空格键（自动瞄准最近敌人）"),
        ("切换武器：", "数字键1-4 / Tab / 鼠标滚轮"),
        ("撤离：", "飞到黄色区域停留3秒"),
        ("", ""),
        ("", "!  敌人会巡逻和追击 — Boss非常致命！"),
        ("", "坠机时未撤离的物资会丢失"),
        ("", "撤离后到商店购买装备"),
        ("", ""),
        ("", "按 Enter 出发。祝你好运！"),
    ]

    for key_t, desc in instructions:
        if not desc:
            cy += 18
            continue
        if key_t:
            line = font_normal.render(f"{key_t} {desc}", True, (200, 220, 240))
        else:
            line = font_normal.render(f"  {desc}", True, (180, 180, 180))
        screen.blit(line, (WIDTH // 2 - 280, cy))
        cy += line.get_height() + 2

    # Blinking Enter hint
    if pygame.time.get_ticks() % 1000 < 600:
        enter_hint = font_normal.render("[Enter] 开始游戏", True, (100, 255, 150))
        screen.blit(enter_hint, (WIDTH // 2 - enter_hint.get_width() // 2, HEIGHT - 80))


def show_main_menu():
    """Draw main menu screen (start / after extraction / after failure)"""
    screen.fill(BG_DARK)

    # ---- Background decorative lines ----
    for i in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (20, 25, 45), (0, i), (WIDTH, i), 1)
    for i in range(0, WIDTH, 40):
        pygame.draw.line(screen, (20, 25, 45), (i, 0), (i, HEIGHT), 1)

    cy = 60

    # ---- Game title ----
    title_surf = font_huge.render("HeliOps", True, (255, 220, 50))
    title_x = WIDTH // 2 - title_surf.get_width() // 2
    screen.blit(title_surf, (title_x, cy))
    cy += title_surf.get_height() + 4

    sub_surf = font_small.render("直升机撤离射击", True, (160, 180, 220))
    screen.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, cy))
    cy += sub_surf.get_height() + 30

    # ---- Last result (extraction success indicator) ----
    if last_result is not None and last_result["reason"] == "extract_success":
        result_color = (100, 255, 150)
        panel_w, panel_h = 320, 52
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((20, 50, 30, 200))
        pygame.draw.rect(panel, result_color, (0, 0, panel_w, panel_h), 2, border_radius=10)
        screen.blit(panel, (WIDTH // 2 - panel_w // 2, cy))
        r_surf = font_normal.render("√  撤离成功！", True, result_color)
        screen.blit(r_surf, (WIDTH // 2 - r_surf.get_width() // 2, cy + 10))
        cy += panel_h + 28
    else:
        cy += 10

    # ---- Menu Items ----
    menu_items = [
        ("Enter", "新游戏", (255, 220, 60),  True),
        ("8",     "补给站",   (255, 160, 40),  True),
    ]
    # D-key: always shown, label changes based on mode
    if extreme_mode_active:
        mode_label = "极难模式：开启 ★"
        mode_color = (255, 60, 30)
    elif hard_mode_active:
        mode_label = "困难模式：开启"
        mode_color = (255, 100, 80)
    else:
        if extreme_mode_unlocked:
            mode_label = "模式：普通（按D切换）"
            mode_color = (100, 220, 100)
        elif hard_mode_unlocked:
            mode_label = "模式：普通（按D切换）"
            mode_color = (100, 180, 100)
        else:
            mode_label = "模式：普通（按D切换）"
            mode_color = (100, 100, 100)
    menu_items.append(("D", mode_label, mode_color, True))
    menu_items.append(("S",   "设置",   (140, 180, 255), True))
    menu_items.append(("Q", "退出", (180, 180, 180), True))

    difficulty_y = 0
    for key, label, color, enabled in menu_items:
        alpha_color = color if enabled else (80, 80, 80)
        item_surf = font_normal.render(f"[{key}]  {label}", True, alpha_color)
        screen.blit(item_surf, (WIDTH // 2 - item_surf.get_width() // 2, cy))
        if key == "D":
            difficulty_y = cy  # Track position for token display
        cy += item_surf.get_height() + 18

    # ---- Token display: show to the right of difficulty switch ----
    if hard_mode_unlocked and difficulty_y > 0:
        token_str  = f"信物: {boss_token_count}"
        token_col  = (255, 180, 80)
        token_surf = font_small.render(token_str, True, token_col)
        # Position to the right of the difficulty line
        token_x = WIDTH // 2 + 200
        screen.blit(token_surf, (token_x, difficulty_y + 2))

    # ---- Task panel (P to open / 6 to close) ----
    if show_task_panel:
        # Content-driven panel height + on-screen clamp: the panel used to be a
        # fixed 290px tall box, so on short windows it spilled past the bottom
        # edge and its lower lines were unreadable.
        task_panel_w = 540
        content_h = 6 + 22 + 22 * 3 + 28               # title + 3 normal tasks
        if extreme_mode_permanent:
            content_h += 22 + 22 * 3 + 28 + 22         # advanced tasks + plays left
        task_panel_h = content_h + 10
        panel_x = WIDTH // 2 - task_panel_w // 2
        panel_y = max(12, min(cy, HEIGHT - task_panel_h - 12))
        task_panel = pygame.Surface((task_panel_w, task_panel_h), pygame.SRCALPHA)
        task_panel.fill((15, 18, 38, 220))
        pygame.draw.rect(task_panel, (70, 70, 150), (0, 0, task_panel_w, task_panel_h), 2, border_radius=10)
        screen.blit(task_panel, (panel_x, panel_y))

        cur_y = panel_y + 6

        # Title
        task_title = font_small.render("★ 极难模式解锁任务", True, (255, 180, 70))
        screen.blit(task_title, (WIDTH // 2 - task_title.get_width() // 2, cur_y))
        cur_y += 22

        # Task 1
        if extreme_mode_permanent:
            t1_done = True
            t1_text = f"任务1：困难模式累计击杀Boss  {TASK1_BOSS_KILLS}/{TASK1_BOSS_KILLS} √"
        else:
            t1_done = hm_boss_kills >= TASK1_BOSS_KILLS
            t1_text = f"任务1：困难模式累计击杀Boss  {min(hm_boss_kills, TASK1_BOSS_KILLS)}/{TASK1_BOSS_KILLS}"
            if t1_done:
                t1_text += " √"
        t1_surf = font_small.render(t1_text, True, (100, 255, 100) if t1_done else (190, 190, 200))
        screen.blit(t1_surf, (WIDTH // 2 - task_panel_w // 2 + 16, cur_y))
        cur_y += 22

        # Task 2
        if extreme_mode_permanent:
            t2_done = True
            t2_text = f"任务2：困难模式驱赶超级猎手  {TASK2_SCARED}/{TASK2_SCARED} √"
        else:
            t2_done = hm_super_chaser_scared >= TASK2_SCARED
            t2_text = f"任务2：困难模式驱赶超级猎手  {min(hm_super_chaser_scared, TASK2_SCARED)}/{TASK2_SCARED}"
            if t2_done:
                t2_text += " √"
        t2_surf = font_small.render(t2_text, True, (100, 255, 100) if t2_done else (190, 190, 200))
        screen.blit(t2_surf, (WIDTH // 2 - task_panel_w // 2 + 16, cur_y))
        cur_y += 22

        # Task 3
        if extreme_mode_permanent:
            t3_done = True
            t3_text = f"任务3：困难模式单局击杀Boss  {TASK3_MISSION_BOSS}/{TASK3_MISSION_BOSS} √"
        else:
            t3_done = mission_boss_kills >= TASK3_MISSION_BOSS
            t3_text = f"任务3：困难模式单局击杀Boss  {min(mission_boss_kills, TASK3_MISSION_BOSS)}/{TASK3_MISSION_BOSS}"
            if t3_done:
                t3_text += " √"
        t3_surf = font_small.render(t3_text, True, (100, 255, 100) if t3_done else (190, 190, 200))
        screen.blit(t3_surf, (WIDTH // 2 - task_panel_w // 2 + 16, cur_y))
        cur_y += 28

        # Advanced tasks (shown after Extreme Mode unlock)
        if extreme_mode_permanent:
            adv_title = font_small.render("★ 进阶任务（完成后+15次）", True, (255, 200, 100))
            screen.blit(adv_title, (WIDTH // 2 - adv_title.get_width() // 2, cur_y))
            cur_y += 22

            # Advanced Task 1
            a1_done = adv_boss_kills >= ADV_TASK_BOSS_KILLS
            a1_text = f"进阶1：极难模式击杀Boss  {min(adv_boss_kills, ADV_TASK_BOSS_KILLS)}/{ADV_TASK_BOSS_KILLS}"
            if a1_done:
                a1_text += " √"
            a1_surf = font_small.render(a1_text, True, (100, 255, 100) if a1_done else (200, 200, 220))
            screen.blit(a1_surf, (WIDTH // 2 - task_panel_w // 2 + 16, cur_y))
            cur_y += 22

            # Advanced Task 2
            a2_done = adv_chaser_scared >= ADV_TASK_SCARED
            a2_text = f"进阶2：极难模式驱赶超级猎手  {min(adv_chaser_scared, ADV_TASK_SCARED)}/{ADV_TASK_SCARED}"
            if a2_done:
                a2_text += " √"
            a2_surf = font_small.render(a2_text, True, (100, 255, 100) if a2_done else (200, 200, 220))
            screen.blit(a2_surf, (WIDTH // 2 - task_panel_w // 2 + 16, cur_y))
            cur_y += 22

            # Advanced Task 3
            a3_done = adv_high_extract >= ADV_TASK_HIGH_EXTRACT
            a3_text = f"进阶3：极难模式预估>400撤离  {min(adv_high_extract, ADV_TASK_HIGH_EXTRACT)}/{ADV_TASK_HIGH_EXTRACT}"
            if a3_done:
                a3_text += " √"
            a3_surf = font_small.render(a3_text, True, (100, 255, 100) if a3_done else (200, 200, 220))
            screen.blit(a3_surf, (WIDTH // 2 - task_panel_w // 2 + 16, cur_y))
            cur_y += 28

        # Plays remaining
        if extreme_mode_permanent:
            rem_text = f"极难模式剩余次数: {extreme_plays_remaining}"
            rem_color = (100, 255, 100) if extreme_plays_remaining > 5 else ((255, 200, 50) if extreme_plays_remaining > 0 else (255, 80, 80))
            rem_surf = font_small.render(rem_text, True, rem_color)
            screen.blit(rem_surf, (WIDTH // 2 - task_panel_w // 2 + 16, cur_y))

        cy += task_panel_h + 12

    # ---- Main menu message bar (search_message shown here) ----
    if search_message_timer > 0:
        msg_color = (255, 80, 80) if search_message.startswith("✕") else (100, 220, 255)
        msg_surf = font_small.render(search_message, True, msg_color)
        msg_bg = pygame.Surface((msg_surf.get_width() + 24, msg_surf.get_height() + 12), pygame.SRCALPHA)
        msg_bg.fill((20, 10, 10, 220) if search_message.startswith("✕") else (10, 20, 40, 200))
        msg_bg.set_alpha(min(255, search_message_timer * 3))
        msg_surf.set_alpha(min(255, search_message_timer * 3))
        screen.blit(msg_bg, (WIDTH // 2 - msg_bg.get_width() // 2, HEIGHT - 80))
        screen.blit(msg_surf, (WIDTH // 2 - msg_surf.get_width() // 2, HEIGHT - 74))


def show_death_screen():
    """Extraction failure screen: shows killer, press 7 to return to main menu"""
    screen.fill((10, 5, 5))

    # Background red scan lines
    for i in range(0, HEIGHT, 30):
        pygame.draw.line(screen, (40, 10, 10), (0, i), (WIDTH, i), 1)

    cy = 70

    # Title
    title_surf = font_huge.render("直升机被击毁", True, (255, 60, 60))
    screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, cy))
    cy += title_surf.get_height() + 16

    # Killer info
    if killer:
        # Killer name color mapping
        killer_colors = {
            "巡逻兵":       (220, 100, 60),
            "Boss":        (255, 80, 200),
            "猎手":      (255, 150, 0),
            "超级猎手": (200, 0, 255),
            "Boss炮弹": (255, 80, 200),
            "敌方子弹": (220, 100, 60),
            "时间耗尽": (255, 200, 50),
        }
        k_color = killer_colors.get(killer, (255, 180, 80))

        k_label = font_normal.render("击毁者：", True, (140, 140, 140))
        screen.blit(k_label, (WIDTH // 2 - k_label.get_width() // 2, cy))
        cy += k_label.get_height() + 6

        # Killer name large text
        k_name = font_big.render(killer, True, k_color)
        # Border glow effect
        for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
            glow = font_big.render(killer, True, (k_color[0]//3, k_color[1]//3, k_color[2]//3))
            screen.blit(glow, (WIDTH // 2 - k_name.get_width() // 2 + dx, cy + dy))
        screen.blit(k_name, (WIDTH // 2 - k_name.get_width() // 2, cy))
        cy += k_name.get_height() + 20

        # Killer description
        killer_desc = {
            "巡逻兵":        "被巡逻守卫击落",
            "Boss":         "被Boss直升机撞击摧毁",
            "猎手":       "被猎手追上击落",
            "超级猎手": "被超级猎手击落",
            "Boss炮弹":  "被Boss炮火命中",
            "敌方子弹": "被敌方枪火命中",
            "时间耗尽": "任务时间耗尽 - 撤离失败",
        }
        desc = killer_desc.get(killer, "")
        if desc:
            desc_surf = font_small.render(desc, True, (160, 120, 120))
            screen.blit(desc_surf, (WIDTH // 2 - desc_surf.get_width() // 2, cy))
            cy += desc_surf.get_height() + 30

    # Score
    sc_surf = font_normal.render(f"本局得分: {score} 分", True, (200, 200, 200))
    screen.blit(sc_surf, (WIDTH // 2 - sc_surf.get_width() // 2, cy))
    cy += sc_surf.get_height() + 40

    # Action hint
    hint_surf = font_normal.render("[ 7 ]  返回主菜单", True, (180, 180, 180))
    screen.blit(hint_surf, (WIDTH // 2 - hint_surf.get_width() // 2, cy))


def show_game_over():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    if game_over_reason == "time_up":
        title       = "时间耗尽！"
        title_color = (255, 180, 80)
        subtitle    = "撤离次数不足 - 任务失败"
    else:
        title       = "任务失败"
        title_color = (255, 60, 60)
        subtitle    = "直升机被击毁"

    go_text      = font_huge.render(title, True, title_color)
    sub_text     = font_normal.render(subtitle, True, GRAY)
    sc_text      = font_big.render(f"最终得分: {score}", True, WHITE)
    restart_text = font_normal.render("R 重开  |  9 读档  |  Q 退出", True, GRAY)

    screen.blit(go_text,      (WIDTH // 2 - go_text.get_width() // 2,      HEIGHT // 2 - 100))
    screen.blit(sub_text,     (WIDTH // 2 - sub_text.get_width() // 2,     HEIGHT // 2 - 50))
    screen.blit(sc_text,      (WIDTH // 2 - sc_text.get_width() // 2,      HEIGHT // 2))
    screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 60))


def reset_game(reset_score=True):
    global player_x, player_y, cam_x, cam_y, bullets, enemies, supplies, backpack, enemy_bullets
    global score, lives, armor, extract_zone, extract_multiplier
    global danger_level, supply_spawn_timer, enemy_spawn_timer, bullet_cooldown
    global ammo_bonus, extraction_message, extraction_message_timer, game_over
    global mission_timer, game_over_reason, extract_hold_timer, in_shop
    global searching_supply, search_timer, search_message, search_message_timer
    global estimated_value, in_transfer, walls, bullet_count, boss, boss_respawn_timer
    global chaser, chaser_respawn_timer, super_chaser, super_chaser_respawn_timer
    global super_chaser_broadcast, super_chaser_broadcast_timer, super_chaser_spawn_chance
    global in_death_screen, killer, awaiting_departure
    global mission_boss_kills
    global current_gun, owned_guns
    global extreme_plays_remaining, extreme_mode_active, search_message, search_message_timer

    awaiting_departure = False
    player_x = float(WORLD_W // 2)
    player_y = float(WORLD_H // 2)
    cam_x    = player_x - WIDTH  // 2
    cam_y    = player_y - HEIGHT // 2
    bullets  = []
    enemy_bullets = []
    enemies  = []
    supplies = []
    backpack = []
    if reset_score:
        score = 0    # Only zero on death/fail, keep on redeploy
    lives    = max_lives
    armor    = 0
    extract_multiplier  = 1.0
    extract_hold_timer  = 0
    danger_level        = 0.0
    supply_spawn_timer  = 0
    enemy_spawn_timer   = 0
    bullet_cooldown     = 0
    ammo_bonus          = 0
    bullet_count        = max_bullets
    search_message = f"! Reset - Ammo: {bullet_count}"
    search_message_timer = 180
    ammo_empty_timer    = 0
    extraction_message  = ""
    extraction_message_timer = 0
    in_shop             = False
    estimated_value     = 0
    in_transfer         = False
    searching_supply    = None
    current_gun         = "pistol"
    owned_guns          = {"pistol"}
    search_timer        = 0
    search_message      = ""
    search_message_timer = 0
    mission_timer  = MISSION_TIME
    game_over_reason = ""
    game_over = False
    in_death_screen = False
    killer = ""
    # Decides whether to zero score based on param (zero on death, keep on new game)
    auto_load(reset_score=reset_score)
    # Random extraction point near player spawn (avoid overlap)
    extract_zone = [float(random.randint(40, WORLD_W - extract_size - 40)),
                    float(random.randint(80, WORLD_H - extract_size - 40))]
    # Regenerate walls
    spawn_walls()
    # Reset Boss
    boss = None
    boss_respawn_timer = 0
    spawn_boss()
    # Reset Chaser
    chaser = None
    chaser_respawn_timer = 0
    spawn_chaser()
    # Reset Super Chaser
    super_chaser = None
    super_chaser_respawn_timer = 0
    super_chaser_broadcast = ""
    super_chaser_broadcast_timer = 0
    super_chaser_spawn_chance = 0.55 if extreme_mode_active else (0.40 if hard_mode_active else 0.25)
    # Reset per-run task progress
    mission_boss_kills = 0
    # Extreme mode: deduct play count at start
    if extreme_mode_active:
        extreme_plays_remaining -= 1
        if extreme_plays_remaining <= 0:
            extreme_mode_active = False
            search_message = "极难模式次数耗尽！完成进阶任务可获得+15次。"
            search_message_timer = 200


def restart_mission():
    """Redeploy: refresh extraction zone, walls, enemies, auto-load saved character data"""
    global extract_zone, boss, boss_respawn_timer
    global chaser, chaser_respawn_timer
    global super_chaser, super_chaser_respawn_timer
    global super_chaser_broadcast, super_chaser_broadcast_timer, super_chaser_spawn_chance
    global in_shop, in_main_menu, awaiting_departure
    global mission_timer
    global mission_boss_kills
    global search_message, search_message_timer

    auto_load()   # Auto-load character growth data from last extraction
    search_message = f"读档完成 - 弹药: {bullet_count}"
    search_message_timer = 180
    mission_timer = MISSION_TIME   # Timer reset
    extract_zone = [float(random.randint(40, WORLD_W - extract_size - 40)),
                    float(random.randint(80, WORLD_H - extract_size - 40))]
    spawn_walls()
    boss = None
    boss_respawn_timer = 0
    spawn_boss()
    chaser = None
    chaser_respawn_timer = 0
    spawn_chaser()
    super_chaser = None
    super_chaser_respawn_timer = 0
    super_chaser_broadcast = ""
    super_chaser_broadcast_timer = 0
    super_chaser_spawn_chance = 0.25
    in_shop = False
    in_main_menu = False
    awaiting_departure = False
    mission_boss_kills = 0


def spawn_boss():
    """Spawn Boss from map edge, avoiding player spawn and walls"""
    global boss
    side = random.randint(0, 3)
    if side == 0:       # Top edge
        x = random.randint(100, WORLD_W - 100)
        y = random.randint(40, 100)
    elif side == 1:     # Bottom edge
        x = random.randint(100, WORLD_W - 100)
        y = random.randint(WORLD_H - 100, WORLD_H - 40 - BOSS_SIZE)
    elif side == 2:     # Left edge
        x = random.randint(40, 100)
        y = random.randint(100, WORLD_H - 100)
    else:               # Right edge
        x = random.randint(WORLD_W - 100, WORLD_W - 40 - BOSS_SIZE)
        y = random.randint(100, WORLD_H - 100)

    # Avoid player spawn point
    spawn_safe = pygame.Rect(WORLD_W // 2 - 80, WORLD_H // 2 - 80, 160, 160)
    boss_rect = pygame.Rect(x, y, BOSS_SIZE, BOSS_SIZE)
    if boss_rect.colliderect(spawn_safe):
        # Re-randomize position
        x = random.randint(100, WORLD_W - 100 - BOSS_SIZE)
        y = random.randint(100, WORLD_H - 100 - BOSS_SIZE)

    # Wall collision pushback
    boss_x, boss_y = resolve_wall_collision(float(x), float(y), BOSS_SIZE, BOSS_SIZE, walls)
    boss_x = max(0.0, min(float(WORLD_W - BOSS_SIZE), boss_x))
    boss_y = max(0.0, min(float(WORLD_H - BOSS_SIZE), boss_y))
    boss_hp = int(BOSS_MAX_HP * _dm(HM_HP_MULT, EM_HP_MULT))
    boss_max_hp = boss_hp  # Store max HP for health bar display
    boss = [boss_x, boss_y, boss_hp, 0, False, boss_max_hp]  # Index 4: target acquired, Index 5: max HP


def spawn_chaser():
    """Spawn Chaser from map edge, avoiding player spawn"""
    global chaser
    side = random.randint(0, 3)
    margin = 60
    if side == 0:
        x = random.randint(margin, WORLD_W - margin - CHASER_SIZE)
        y = random.randint(margin, margin + 60)
    elif side == 1:
        x = random.randint(margin, WORLD_W - margin - CHASER_SIZE)
        y = random.randint(WORLD_H - margin - 60, WORLD_H - margin - CHASER_SIZE)
    elif side == 2:
        x = random.randint(margin, margin + 60)
        y = random.randint(margin, WORLD_H - margin - CHASER_SIZE)
    else:
        x = random.randint(WORLD_W - margin - 60, WORLD_W - margin - CHASER_SIZE)
        y = random.randint(margin, WORLD_H - margin - CHASER_SIZE)

    # Avoid player spawn point
    spawn_safe = pygame.Rect(WORLD_W // 2 - 80, WORLD_H // 2 - 80, 160, 160)
    chaser_rect = pygame.Rect(x, y, CHASER_SIZE, CHASER_SIZE)
    if chaser_rect.colliderect(spawn_safe):
        x = random.randint(100, WORLD_W - 100 - CHASER_SIZE)
        y = random.randint(100, WORLD_H - 100 - CHASER_SIZE)

    # Wall collision pushback
    cx, cy = resolve_wall_collision(float(x), float(y), CHASER_SIZE, CHASER_SIZE, walls)
    cx = max(0.0, min(float(WORLD_W - CHASER_SIZE), cx))
    cy = max(0.0, min(float(WORLD_H - CHASER_SIZE), cy))
    chaser_hp = int(CHASER_HP * _dm(HM_CHASER_MULT, EM_CHASER_MULT))
    chaser = [cx, cy, chaser_hp, False]  # [x, y, hp, detected]


def spawn_super_chaser():
    """Spawn Super Chaser (invincible) from map edge, avoiding player spawn"""
    global super_chaser, super_chaser_broadcast, super_chaser_broadcast_timer
    side = random.randint(0, 3)
    margin = 60
    if side == 0:
        x = random.randint(margin, WORLD_W - margin - SUPER_CHASER_SIZE)
        y = random.randint(margin, margin + 60)
    elif side == 1:
        x = random.randint(margin, WORLD_W - margin - SUPER_CHASER_SIZE)
        y = random.randint(WORLD_H - margin - 60, WORLD_H - margin - SUPER_CHASER_SIZE)
    elif side == 2:
        x = random.randint(margin, margin + 60)
        y = random.randint(margin, WORLD_H - margin - SUPER_CHASER_SIZE)
    else:
        x = random.randint(WORLD_W - margin - 60, WORLD_W - margin - SUPER_CHASER_SIZE)
        y = random.randint(margin, WORLD_H - margin - SUPER_CHASER_SIZE)

    # Avoid player spawn point
    spawn_safe = pygame.Rect(WORLD_W // 2 - 80, WORLD_H // 2 - 80, 160, 160)
    sc_rect = pygame.Rect(x, y, SUPER_CHASER_SIZE, SUPER_CHASER_SIZE)
    if sc_rect.colliderect(spawn_safe):
        x = random.randint(100, WORLD_W - 100 - SUPER_CHASER_SIZE)
        y = random.randint(100, WORLD_H - 100 - SUPER_CHASER_SIZE)

    # Wall collision pushback
    scx, scy = resolve_wall_collision(float(x), float(y), SUPER_CHASER_SIZE, SUPER_CHASER_SIZE, walls)
    scx = max(0.0, min(float(WORLD_W - SUPER_CHASER_SIZE), scx))
    scy = max(0.0, min(float(WORLD_H - SUPER_CHASER_SIZE), scy))
    super_chaser = [scx, scy, False]  # [x, y, detected] - invincible, no HP
    # Fullscreen broadcast
    super_chaser_broadcast = "！超级猎手来袭！"
    super_chaser_broadcast_timer = 180  # 3 seconds


def spawn_enemy():
    """Spawn enemy: 40% chance in map center, 60% from edges"""
    if random.random() < 0.40:
        # Center region (20%-80% range)
        ex = random.randint(int(WORLD_W * 0.20), int(WORLD_W * 0.80) - enemy_size)
        ey = random.randint(int(WORLD_H * 0.20), int(WORLD_H * 0.80) - enemy_size)
    else:
        # Spawn from world edges
        side = random.randint(0, 3)
        if side == 0:
            ex = random.randint(0, WORLD_W - enemy_size)
            ey = random.randint(0, 80)
        elif side == 1:
            ex = random.randint(0, WORLD_W - enemy_size)
            ey = random.randint(WORLD_H - 80, WORLD_H)
        elif side == 2:
            ex = random.randint(0, 80)
            ey = random.randint(0, WORLD_H - enemy_size)
        else:
            ex = random.randint(WORLD_W - 80, WORLD_W)
            ey = random.randint(0, WORLD_H - enemy_size)

    # Mid-range patrol: +/-350px horizontal range
    p_start = max(0, ex - 350)
    p_end   = min(WORLD_W - enemy_size, ex + 350)
    enemy_hp = int(ENEMY_HP * _dm(HM_HP_MULT, EM_HP_MULT))
    enemies.append([float(ex), float(ey), float(p_start), float(p_end), "patrol", 0, CHASE_DURATION, enemy_hp, 0])


def spawn_walls():
    """Randomly generate non-overlapping walls on the map"""
    global walls
    walls = []
    attempts = 0
    max_attempts = 500

    while len(walls) < WALL_COUNT and attempts < max_attempts:
        attempts += 1
        w = random.randint(60, 150)
        h = random.randint(20, 80)
        x = random.randint(40, WORLD_W - w - 40)
        y = random.randint(40, WORLD_H - h - 40)

        new_rect = pygame.Rect(x, y, w, h)

        # Check 1: no overlap with existing walls
        overlap = False
        for ew in walls:
            if new_rect.colliderect(pygame.Rect(ew[0], ew[1], ew[2], ew[3])):
                overlap = True
                break
        if overlap:
            continue

        # Check 2: don't cover player spawn (100x100 safe zone)
        spawn_safe = pygame.Rect(WORLD_W // 2 - 50, WORLD_H // 2 - 50, 100, 100)
        if new_rect.colliderect(spawn_safe):
            continue

        # Check 3: don't cover extraction zone (40px margin)
        extract_rect = pygame.Rect(extract_zone[0] - 20, extract_zone[1] - 20,
                                   extract_size + 40, extract_size + 40)
        if new_rect.colliderect(extract_rect):
            continue

        # Check 4: limit max size
        if w > 300 or h > 120:
            continue

        walls.append([float(x), float(y), float(w), float(h)])


def spawn_supply():
    for _ in range(10):
        x = random.randint(40, WORLD_W - SUPPLY_SIZE - 40)
        y = random.randint(80, WORLD_H - SUPPLY_SIZE - 40)

        # Check wall overlap
        supply_rect = pygame.Rect(x, y, SUPPLY_SIZE, SUPPLY_SIZE)
        collision = False
        for w in walls:
            if supply_rect.colliderect(pygame.Rect(w[0], w[1], w[2], w[3])):
                collision = True
                break
        if collision:
            continue

        # No overlap, spawn supply
        roll = random.random()
        if roll < 0.05:
            stype = "rare"
        elif roll < 0.15:
            stype = "bonus"     # 10% chance
        elif roll < 0.30:
            stype = "heal"
        elif roll < 0.55:
            stype = "ammo"
        else:
            stype = "common"
        supplies.append([float(x), float(y), stype, 600])
        return


def do_extraction():
    global score, extract_multiplier, backpack, extraction_message, extraction_message_timer
    global extract_zone, extract_hold_timer, in_shop, mission_timer, estimated_value
    global in_main_menu, last_result, mission_boss_kills
    global adv_high_extract
    if len(backpack) == 0:
        extraction_message = "背包是空的！"
        extraction_message_timer = 60
        extract_hold_timer = 0
        return False
    bonus = int(estimated_value * extract_multiplier)   # Settle estimated value (with multiplier)
    score += bonus
    extract_multiplier = min(5.0, extract_multiplier + (0.72 if extreme_mode_active else (0.45 if hard_mode_active else 0.3)))
    # Advanced task 3: est>400 extraction success in extreme mode (check before zeroing)
    ev_before = estimated_value
    backpack = []
    estimated_value = 0    # Zero estimated value after extraction
    extract_hold_timer = 0
    mission_timer = MISSION_TIME  # Reset timer after extraction
    # Extraction success -> record result, go to main menu, then supply station after confirm
    last_result = {"reason": "extract_success", "score": score}
    if extreme_mode_active and ev_before > 400:
        adv_high_extract += 1
        check_adv_tasks()
    # Task 3: 2 Boss kills in single hard run - zero on extract (fail if incomplete)
    mission_boss_kills = 0
    auto_save()   # Auto-save on extraction success (character growth data)
    in_main_menu = True
    return True


# ==============================
# Save / Load
# ==============================
def save_game():
    global save_message, save_message_timer
    state = {
        "player_x": player_x, "player_y": player_y,
        "cam_x": cam_x, "cam_y": cam_y,
        "bullets": bullets, "enemy_bullets": enemy_bullets,
        "enemies": enemies, "supplies": supplies, "backpack": backpack,
        "score": score, "lives": lives, "armor": armor,
        "extract_zone": extract_zone, "extract_multiplier": extract_multiplier,
        "extract_hold_timer": extract_hold_timer,
        "danger_level": danger_level,
        "supply_spawn_timer": supply_spawn_timer,
        "enemy_spawn_timer": enemy_spawn_timer,
        "bullet_cooldown": bullet_cooldown,
        "ammo_bonus": ammo_bonus, "bullet_count": bullet_count, "max_bullets": max_bullets,
        "ammo_empty_timer": ammo_empty_timer,
        "mission_timer": mission_timer,
        "walls": walls,
        "boss": boss, "boss_respawn_timer": boss_respawn_timer,
        "chaser": chaser, "chaser_respawn_timer": chaser_respawn_timer,
        "super_chaser": super_chaser, "super_chaser_respawn_timer": super_chaser_respawn_timer,
        "super_chaser_spawn_chance": super_chaser_spawn_chance,
        "extreme_mode_unlocked": extreme_mode_unlocked,
        "extreme_mode_active": extreme_mode_active,
        "extreme_mode_permanent": extreme_mode_permanent,
        "extreme_plays_remaining": extreme_plays_remaining,
        "adv_boss_kills": adv_boss_kills,
        "adv_chaser_scared": adv_chaser_scared,
        "adv_high_extract": adv_high_extract,
        "hm_boss_kills": hm_boss_kills,
        "hm_super_chaser_scared": hm_super_chaser_scared,
        "searching_supply": searching_supply, "search_timer": search_timer,
        "search_message": search_message, "search_message_timer": search_message_timer,
        "extraction_message": extraction_message,
        "extraction_message_timer": extraction_message_timer,
        "estimated_value": estimated_value,
        "current_gun": current_gun, "owned_guns": list(owned_guns),
    }
    try:
        with open(SAVE_FILE, "wb") as f:
            pickle.dump(state, f)
        save_message = "游戏已存档！"
        save_message_timer = 120
    except Exception as e:
        save_message = f"存档失败: {e}"
        save_message_timer = 120


def auto_save():
    """Auto-save after successful extraction: save character growth data (score/lives/armor/ammo/mult/danger)"""
    state = {
        "score": score,
        "lives": lives,
        "armor": armor,
        "ammo_bonus": ammo_bonus,
        "bullet_count": bullet_count,
        "max_bullets": max_bullets,
        "extract_multiplier": extract_multiplier,
        "danger_level": danger_level,
        "boss_token_count": boss_token_count,
        "hard_mode_unlocked": hard_mode_unlocked,
        "hm_boss_kills": hm_boss_kills,
        "hm_super_chaser_scared": hm_super_chaser_scared,
        "extreme_mode_permanent": extreme_mode_permanent,
        "extreme_plays_remaining": extreme_plays_remaining,
        "adv_boss_kills": adv_boss_kills,
        "adv_chaser_scared": adv_chaser_scared,
        "adv_high_extract": adv_high_extract,
        "current_gun": current_gun, "owned_guns": list(owned_guns),
        "sfx_volume": sfx_volume, "bgm_volume": bgm_volume,
        "tutorial_shown": tutorial_shown,
    }
    try:
        with open(AUTO_SAVE_FILE, "wb") as f:
            pickle.dump(state, f)
    except Exception:
        pass   # Auto-save failure silently handled, don't interrupt gameplay


def auto_load(reset_score=False):
    """Load character growth data, regenerating map/enemies/coordinates.
    If reset_score=True, clear estimated value but keep other data (post-failure restart).
    """
    global score, lives, armor, ammo_bonus, bullet_count, max_bullets
    global current_gun, owned_guns
    global extract_multiplier, danger_level
    global boss_token_count, hard_mode_unlocked
    global hm_boss_kills, hm_super_chaser_scared, extreme_mode_permanent, extreme_mode_unlocked
    global extreme_plays_remaining, adv_boss_kills, adv_chaser_scared, adv_high_extract
    global sfx_volume, bgm_volume
    global tutorial_shown
    if not os.path.exists(AUTO_SAVE_FILE):
        return
    try:
        with open(AUTO_SAVE_FILE, "rb") as f:
            state = pickle.load(f)
        if not reset_score:
            score = state.get("score", 0)
        else:
            score = 0   # Clear budget after failure (score to zero)
        lives             = state.get("lives", max_lives)
        armor             = state.get("armor", 0)
        ammo_bonus        = state.get("ammo_bonus", 0)
        bullet_count      = state.get("bullet_count", max_bullets)
        max_bullets       = state.get("max_bullets", max_bullets)
        extract_multiplier = state.get("extract_multiplier", 1.0)
        danger_level      = state.get("danger_level", 0.0)
        boss_token_count  = state.get("boss_token_count", 0)
        hard_mode_unlocked = state.get("hard_mode_unlocked", False)
        hm_boss_kills      = state.get("hm_boss_kills", 0)
        hm_super_chaser_scared = state.get("hm_super_chaser_scared", 0)
        extreme_mode_permanent = state.get("extreme_mode_permanent", False)
        extreme_plays_remaining = state.get("extreme_plays_remaining", 0)
        current_gun = state.get("current_gun", "pistol")
        owned_guns = set(state.get("owned_guns", ["pistol"]))
        adv_boss_kills = state.get("adv_boss_kills", 0)
        adv_chaser_scared = state.get("adv_chaser_scared", 0)
        adv_high_extract = state.get("adv_high_extract", 0)
        sfx_volume = state.get("sfx_volume", 0.6)
        bgm_volume = state.get("bgm_volume", 0.3)
        tutorial_shown = state.get("tutorial_shown", False)
        extreme_mode_unlocked = extreme_mode_permanent
    except Exception:
        pass   # Auto-load failure silently handled


def load_game():
    global player_x, player_y, cam_x, cam_y, bullets, enemy_bullets
    global enemies, supplies, backpack, score, lives, armor
    global extract_zone, extract_multiplier, extract_hold_timer
    global danger_level, supply_spawn_timer, enemy_spawn_timer
    global bullet_cooldown, ammo_bonus, bullet_count, max_bullets, ammo_empty_timer
    global mission_timer, walls
    global boss, boss_respawn_timer
    global chaser, chaser_respawn_timer
    global super_chaser, super_chaser_respawn_timer
    global super_chaser_spawn_chance
    global extreme_mode_unlocked, extreme_mode_active
    global extreme_mode_permanent, hm_boss_kills, hm_super_chaser_scared
    global extreme_plays_remaining, adv_boss_kills, adv_chaser_scared, adv_high_extract
    global searching_supply, search_timer
    global search_message, search_message_timer
    global extraction_message, extraction_message_timer
    global estimated_value
    global save_message, save_message_timer
    global current_gun, owned_guns
    global in_shop, in_transfer, game_over, paused, in_main_menu, in_death_screen, killer, awaiting_departure
    if not os.path.exists(SAVE_FILE):
        save_message = "没有找到存档！"
        save_message_timer = 120
        return
    try:
        with open(SAVE_FILE, "rb") as f:
            state = pickle.load(f)
        player_x = state["player_x"]
        player_y = state["player_y"]
        cam_x = state["cam_x"]
        cam_y = state["cam_y"]
        bullets = state["bullets"]
        enemy_bullets = state["enemy_bullets"]
        enemies = state["enemies"]
        supplies = state["supplies"]
        backpack = state["backpack"]
        score = state["score"]
        lives = state["lives"]
        armor = state["armor"]
        extract_zone = state["extract_zone"]
        extract_multiplier = state["extract_multiplier"]
        extract_hold_timer = state["extract_hold_timer"]
        danger_level = state["danger_level"]
        supply_spawn_timer = state["supply_spawn_timer"]
        enemy_spawn_timer = state["enemy_spawn_timer"]
        bullet_cooldown = state["bullet_cooldown"]
        ammo_bonus = state["ammo_bonus"]
        bullet_count = state["bullet_count"]
        max_bullets = state.get("max_bullets", 600)
        ammo_empty_timer = state.get("ammo_empty_timer", 0)
        mission_timer = state["mission_timer"]
        walls = state["walls"]
        boss = state["boss"]
        boss_respawn_timer = state["boss_respawn_timer"]
        chaser = state["chaser"]
        chaser_respawn_timer = state["chaser_respawn_timer"]
        super_chaser = state.get("super_chaser")
        super_chaser_respawn_timer = state.get("super_chaser_respawn_timer", 0)
        super_chaser_spawn_chance = state.get("super_chaser_spawn_chance", 0.25)
        extreme_mode_unlocked = False  # No longer loaded from save, derived from extreme_mode_permanent only
        extreme_mode_active = state.get("extreme_mode_active", False)
        extreme_mode_permanent = state.get("extreme_mode_permanent", False)
        extreme_mode_unlocked = extreme_mode_permanent
        hm_boss_kills = state.get("hm_boss_kills", 0)
        hm_super_chaser_scared = state.get("hm_super_chaser_scared", 0)
        extreme_plays_remaining = state.get("extreme_plays_remaining", 0)
        current_gun = state.get("current_gun", "pistol")
        owned_guns = set(state.get("owned_guns", ["pistol"]))
        adv_boss_kills = state.get("adv_boss_kills", 0)
        adv_chaser_scared = state.get("adv_chaser_scared", 0)
        adv_high_extract = state.get("adv_high_extract", 0)
        searching_supply = state["searching_supply"]
        search_timer = state["search_timer"]
        search_message = state["search_message"]
        search_message_timer = state["search_message_timer"]
        extraction_message = state.get("extraction_message", "")
        extraction_message_timer = state.get("extraction_message_timer", 0)
        estimated_value = state["estimated_value"]
        current_gun = state.get("current_gun", "pistol")
        owned_guns = set(state.get("owned_guns", ["pistol"]))
        # Restore normal game state after loading
        in_shop = False
        in_transfer = False
        game_over = False
        paused = False
        in_main_menu = False   # Load directly into game
        in_death_screen = False
        killer = ""
        save_message = "游戏已读取！"
        save_message_timer = 120
    except Exception as e:
        save_message = f"读档失败: {e}"
        save_message_timer = 120


# ==============================
# Main game loop
# ==============================
# Create initial extraction point on game start
extract_zone = [float(random.randint(40, WORLD_W - extract_size - 40)),
                float(random.randint(80, WORLD_H - extract_size - 40))]
spawn_walls()
spawn_boss()
spawn_chaser()
auto_load()  # Load save on startup (restore task progress/extreme unlock etc)

running = True
try:
    while running:
        clock.tick(60)

        # ---------- Event handling ----------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            # ---- Mouse wheel / Tab key weapon switch ----
            wheel_event = False
            wheel_dir = 0  # 1=next, -1=previous
            if event.type == pygame.MOUSEWHEEL and not in_shop and not in_transfer and not in_death_screen and not in_main_menu:
                wheel_event = True
                wheel_dir = event.y  # >0 up, <0 down
            elif event.type == pygame.MOUSEBUTTONDOWN and not in_shop and not in_transfer and not in_death_screen and not in_main_menu:
                if event.button == 4:
                    wheel_event = True; wheel_dir = 1
                elif event.button == 5:
                    wheel_event = True; wheel_dir = -1
            elif event.type == pygame.KEYDOWN and not in_shop and not in_transfer and not in_death_screen and not in_main_menu:
                if event.key == pygame.K_TAB:
                    wheel_event = True; wheel_dir = 1   # Tab=next
            if wheel_event:
                owned_gun_list = [g for g in ["pistol", "rifle", "shotgun", "sniper"] if g in owned_guns]
                if len(owned_gun_list) > 1:
                    cur_idx = owned_gun_list.index(current_gun) if current_gun in owned_gun_list else 0
                    if wheel_dir > 0:   # Down/next
                        cur_idx = (cur_idx + 1) % len(owned_gun_list)
                    else:               # Up/previous
                        cur_idx = (cur_idx - 1) % len(owned_gun_list)
                    current_gun = owned_gun_list[cur_idx]
                    search_message = f"切换: {GUN_TYPES[current_gun]['name']}"
                    search_message_timer = 60
            if event.type == pygame.KEYDOWN:
                # ---- Global pause toggle (ESC during gameplay) ----
                if event.key == pygame.K_ESCAPE and not in_shop and not in_transfer and not in_death_screen and not in_main_menu and not in_settings and not game_over:
                    paused = not paused
                    if paused:
                        search_message = "游戏暂停 | ESC继续 M主菜单 Q退出"
                        search_message_timer = 0
                    continue
                # ---- Pause menu keys ----
                if paused:
                    if event.key == pygame.K_ESCAPE:
                        paused = False
                    elif event.key == pygame.K_m:
                        paused = False
                        in_main_menu = True
                        game_over = False
                    elif event.key == pygame.K_q:
                        running = False
                        break
                    continue
                # ---- Settings screen keys ----
                if in_settings:
                    if event.key == pygame.K_ESCAPE:
                        in_settings = False
                        in_main_menu = True
                    elif event.key == pygame.K_t:
                        sfx_enabled = not sfx_enabled
                        search_message = f"SFX: {'ON' if sfx_enabled else 'OFF'}"
                        search_message_timer = 60
                    elif event.key == pygame.K_LEFT:
                        set_sfx_volume(sfx_volume - 0.05)
                    elif event.key == pygame.K_RIGHT:
                        set_sfx_volume(sfx_volume + 0.05)
                    elif event.key == pygame.K_UP:
                        set_bgm_volume(bgm_volume + 0.05)
                    elif event.key == pygame.K_DOWN:
                        set_bgm_volume(bgm_volume - 0.05)
                    continue
                # ---- Tutorial screen keys ----
                if showing_tutorial:
                    if event.key == pygame.K_RETURN:
                        showing_tutorial = False
                        tutorial_shown = True
                        auto_save()
                    elif event.key == pygame.K_q:
                        running = False
                        break
                    continue
                if event.key == pygame.K_q:
                    running = False
                    break
                # ---- Death screen keys ----
                if in_death_screen:
                    if event.key == pygame.K_7:
                        in_death_screen = False
                        in_main_menu = True
                    continue   # All other keys disabled on death screen

                # ---- Main menu keys ----
                if in_main_menu:
                    if event.key == pygame.K_RETURN:
                        # New game / enter supply station (after extract) / reset (after fail) / redeploy
                        if in_shop:
                            # After extract -> main menu -> Enter to supply station
                            in_main_menu = False
                        elif game_over:
                            reset_game(reset_score=False)  # Keep existing score after death
                            in_main_menu = False
                        elif awaiting_departure:
                            # Return from shop to main menu, redeploy (keep score and gear)
                            restart_mission()
                        else:
                            # Check selected mode is unlocked before new game
                            if hard_mode_active and not hard_mode_unlocked:
                                search_message = "✕ 困难模式未解锁！击杀Boss获取信物。"
                                search_message_timer = 150
                            elif extreme_mode_active and not extreme_mode_unlocked:
                                search_message = "✕ 极难模式未解锁！完成P键任务栏目标后解锁。"
                                search_message_timer = 150
                            elif extreme_mode_active and extreme_plays_remaining <= 0:
                                search_message = f"✕ Extreme mode: {extreme_plays_remaining} plays left! Complete adv tasks for +15."
                                search_message_timer = 150
                            else:
                                reset_game(reset_score=False)  # New game restore full save (incl. score)
                                in_main_menu = False
                                if not tutorial_shown:
                                    showing_tutorial = True
                    elif event.key == pygame.K_8:
                        # Enter shop (supply station)
                        in_main_menu = False
                        in_shop = True
                    elif event.key == pygame.K_d:
                        # Cycle mode: Normal -> Hard -> Extreme -> Normal (unconditional)
                        if not hard_mode_active and not extreme_mode_active:
                            hard_mode_active = True      # Normal -> Hard
                        elif hard_mode_active and not extreme_mode_active:
                            hard_mode_active = False
                            extreme_mode_active = True   # Hard -> Extreme
                        else:
                            extreme_mode_active = False  # Extreme -> Normal
                    elif event.key == pygame.K_p:
                        # Main menu: P to toggle task panel
                        show_task_panel = not show_task_panel
                    elif event.key == pygame.K_6:
                        # Main menu: 6 to close task panel
                        show_task_panel = False
                    elif event.key == pygame.K_s:
                        in_settings = True
                        in_main_menu = False
                    continue   # All other keys disabled on main menu, skip processing
                if game_over:
                    if event.key == pygame.K_r:
                        reset_game()
                elif in_shop:
                    # Supply station key handling
                    if event.key == pygame.K_0:
                        # Press 0 to exit shop, return to main menu (keep score, ready to redeploy)
                        in_shop = False
                        in_main_menu = True
                        awaiting_departure = True
                    elif event.key == pygame.K_1:
                        if lives < max_lives and score >= SHOP_RESTORE_COST:
                            score -= SHOP_RESTORE_COST
                            lives += 1
                    elif event.key == pygame.K_2:
                        if score >= SHOP_ARMOR_COST:
                            score -= SHOP_ARMOR_COST
                            armor += 1
                    elif event.key == pygame.K_3:
                        if score >= SHOP_AMMO_COST:
                            score -= SHOP_AMMO_COST
                            ammo_bonus = min(5, ammo_bonus + 3)
                            bullet_count += 50
                            auto_save()
                            search_message = f"弹药+50 当前: {bullet_count}"
                            search_message_timer = 120
                    elif event.key == pygame.K_4:
                        if score >= 800 and "rifle" not in owned_guns:
                            score -= 800; owned_guns.add("rifle"); auto_save()
                    elif event.key == pygame.K_5:
                        if score >= 1500 and "shotgun" not in owned_guns:
                            score -= 1500; owned_guns.add("shotgun"); auto_save()
                    elif event.key == pygame.K_6:
                        if score >= 2500 and "sniper" not in owned_guns:
                            score -= 2500; owned_guns.add("sniper"); auto_save()
                    elif event.key == pygame.K_RETURN:
                        restart_mission()
                elif in_transfer:
                    # Transfer station key handling
                    if event.key == pygame.K_1:
                        if lives < max_lives and score >= SHOP_RESTORE_COST:
                            score -= SHOP_RESTORE_COST
                            lives += 1
                    elif event.key == pygame.K_2:
                        if score >= SHOP_ARMOR_COST:
                            score -= SHOP_ARMOR_COST
                            armor += 1
                    elif event.key == pygame.K_3:
                        if score >= SHOP_AMMO_COST:
                            score -= SHOP_AMMO_COST
                            ammo_bonus = min(5, ammo_bonus + 3)
                            bullet_count += 50
                            auto_save()
                            search_message = f"弹药+50 当前: {bullet_count}"
                            search_message_timer = 120
                    elif event.key == pygame.K_4:
                        if score >= 800 and "rifle" not in owned_guns:
                            score -= 800; owned_guns.add("rifle"); auto_save()
                    elif event.key == pygame.K_5:
                        if score >= 1500 and "shotgun" not in owned_guns:
                            score -= 1500; owned_guns.add("shotgun"); auto_save()
                    elif event.key == pygame.K_6:
                        if score >= 2500 and "sniper" not in owned_guns:
                            score -= 2500; owned_guns.add("sniper"); auto_save()
                    elif event.key == pygame.K_RETURN:
                        extract_zone = [float(random.randint(40, WORLD_W - extract_size - 40)),
                                        float(random.randint(80, WORLD_H - extract_size - 40))]
                        spawn_walls()
                        boss = None
                        boss_respawn_timer = 0
                        spawn_boss()
                        chaser = None
                        chaser_respawn_timer = 0
                        spawn_chaser()
                        super_chaser = None
                        super_chaser_respawn_timer = 0
                        super_chaser_broadcast = ""
                        super_chaser_broadcast_timer = 0
                        super_chaser_spawn_chance = 0.25
                        in_transfer = False
                else:
                    if event.key == pygame.K_p:
                        paused = not paused

        if not running:
            break

        # ---- Global timer decrement (also needed for main/death screens) ----
        if search_message_timer > 0:
            search_message_timer -= 1
        if save_message_timer > 0:
            save_message_timer -= 1

        # ---- Main menu ----
        if in_main_menu:
            show_main_menu()
            pygame.display.flip()
            continue

        # ---- Settings screen ----
        if in_settings:
            show_settings()
            pygame.display.flip()
            continue

        # ---- Tutorial ----
        if showing_tutorial:
            show_tutorial()
            pygame.display.flip()
            continue

        # ---- Death screen (extraction failure) ----
        if in_death_screen:
            show_death_screen()
            pygame.display.flip()
            continue

        if paused and not game_over and not in_shop and not in_transfer:
            screen.fill(BG_DARK)
            p_title = font_big.render("已暂停", True, WHITE)
            screen.blit(p_title, (WIDTH // 2 - p_title.get_width() // 2, HEIGHT // 2 - 90))
            p_hint = font_small.render("P 继续  |  Q 退出  |  5 存档  |  9 读档", True, GRAY)
            screen.blit(p_hint, (WIDTH // 2 - p_hint.get_width() // 2, HEIGHT // 2 + 10))
            pygame.display.flip()
            continue

        # ---------- Supply station screen ----------
        if in_shop:
            screen.fill(BG_DARK)
            # Draw static map background
            grid_off_x = int(cam_x) % 40
            grid_off_y = int(cam_y) % 40
            for gx in range(-grid_off_x, WIDTH + 40, 40):
                pygame.draw.line(screen, (25, 28, 45), (gx, 0), (gx, HEIGHT))
            for gy in range(-grid_off_y, HEIGHT + 40, 40):
                pygame.draw.line(screen, (25, 28, 45), (0, gy), (WIDTH, gy))
            # Static draw player in world
            draw_walls()
            draw_player(player_x, player_y)
            draw_extract_zone(extract_zone)
            draw_shop()
            draw_hud()
            pygame.display.flip()
            continue

        # ---------- Transfer station screen ----------
        if in_transfer:
            screen.fill(BG_DARK)
            grid_off_x = int(cam_x) % 40
            grid_off_y = int(cam_y) % 40
            for gx in range(-grid_off_x, WIDTH + 40, 40):
                pygame.draw.line(screen, (25, 28, 45), (gx, 0), (gx, HEIGHT))
            for gy in range(-grid_off_y, HEIGHT + 40, 40):
                pygame.draw.line(screen, (25, 28, 45), (0, gy), (WIDTH, gy))
            draw_walls()
            draw_player(player_x, player_y)
            draw_extract_zone(extract_zone)
            draw_transfer_station()
            draw_hud()
            pygame.display.flip()
            continue

        # ---------- Game logic ----------
        # BGM disabled (user feedback: atmosphere too oppressive)

        if not game_over and not paused:

            # ---- Movement (world coords) ----
            keys = pygame.key.get_pressed()
            
            # Update movement direction
            move_dx, move_dy = 0, 0
            if keys[pygame.K_LEFT]  or keys[pygame.K_a]: 
                player_x -= player_speed
                move_dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: 
                player_x += player_speed
                move_dx = 1
            if keys[pygame.K_UP]    or keys[pygame.K_w]: 
                player_y -= player_speed
                move_dy = -1
            if keys[pygame.K_DOWN]  or keys[pygame.K_s]: 
                player_y += player_speed
                move_dy = 1
            
            # Update facing angle + footstep sound
            if move_dx != 0 or move_dy != 0:
                face_angle = math.degrees(math.atan2(move_dy, move_dx))
                footstep_timer += 1
                if footstep_timer >= 18:  # Approx 0.3s interval
                    play_sfx('footstep')
                    footstep_timer = 0
            else:
                footstep_timer = 0

            # World bounds
            player_x, player_y = resolve_wall_collision(player_x, player_y,
                                                         player_size, player_size, walls)
            player_x = max(0.0, min(float(WORLD_W - player_size), player_x))
            player_y = max(0.0, min(float(WORLD_H - player_size), player_y))

            # Camera follow (player always at screen center)
            cam_x = player_x - WIDTH  // 2
            cam_y = player_y - HEIGHT // 2
            cam_x = max(0.0, min(float(WORLD_W - WIDTH),  cam_x))
            cam_y = max(0.0, min(float(WORLD_H - HEIGHT), cam_y))

            # ---- Shooting (Space, auto-aim + gun differences) ----
            gun = GUN_TYPES[current_gun]
            effective_cooldown = max(2, gun["cooldown"] - ammo_bonus * 2)
            if keys[pygame.K_SPACE] and bullet_cooldown == 0 and bullet_count > 0:
                play_sfx('shoot')
                pcx = player_x + player_size // 2
                pcy = player_y + player_size // 2
                target_cx, target_cy = None, None

                if boss is not None and boss[4]:
                    target_cx = boss[0] + BOSS_SIZE // 2
                    target_cy = boss[1] + BOSS_SIZE // 2

                if target_cx is None:
                    best_cx, best_cy, best_dist = None, None, float("inf")
                    if chaser is not None:
                        ccx = chaser[0] + CHASER_SIZE // 2
                        ccy = chaser[1] + CHASER_SIZE // 2
                        d = math.hypot(ccx - pcx, ccy - pcy)
                        if d < best_dist:
                            best_dist = d; best_cx, best_cy = ccx, ccy
                    if super_chaser is not None:
                        sccx = super_chaser[0] + SUPER_CHASER_SIZE // 2
                        sccy = super_chaser[1] + SUPER_CHASER_SIZE // 2
                        d = math.hypot(sccx - pcx, sccy - pcy)
                        if d < best_dist:
                            best_dist = d; best_cx, best_cy = sccx, sccy
                    for e in enemies:
                        ecx = e[0] + enemy_size // 2
                        ecy = e[1] + enemy_size // 2
                        d = math.hypot(ecx - pcx, ecy - pcy)
                        if d < best_dist:
                            best_dist = d; best_cx, best_cy = ecx, ecy
                    if best_cx is not None:
                        target_cx, target_cy = best_cx, best_cy

                if target_cx is None and boss is not None:
                    target_cx = boss[0] + BOSS_SIZE // 2
                    target_cy = boss[1] + BOSS_SIZE // 2

                if target_cx is not None:
                    ddx = target_cx - pcx
                    ddy = target_cy - pcy
                    dist_t = math.hypot(ddx, ddy)
                    if dist_t > 0:
                        base_dx = ddx / dist_t * gun["speed"]
                        base_dy = ddy / dist_t * gun["speed"]
                        n = gun["bullets"]
                        for bi in range(n):
                            if n == 1:
                                bdx, bdy = base_dx, base_dy
                            else:
                                spread_angle = gun["spread"] * (bi - (n - 1) / 2)
                                cos_a = math.cos(spread_angle)
                                sin_a = math.sin(spread_angle)
                                bdx = base_dx * cos_a - base_dy * sin_a
                                bdy = base_dx * sin_a + base_dy * cos_a
                            bullets.append([pcx - 3, pcy - 3, bdx, bdy, gun["damage"]])
                        bullet_count -= 1
                        bullet_cooldown = effective_cooldown
            elif keys[pygame.K_SPACE] and bullet_count == 0 and bullet_cooldown == 0:
                play_sfx('ammo_empty')
                # Ammo depleted, trigger hint (can retrigger every 60 frames)
                ammo_empty_timer = 120
                bullet_cooldown = 20  # Prevent refresh every frame

            if bullet_cooldown > 0:
                bullet_cooldown -= 1
            # ---- Weapon switch (1-4) ----
            if not in_shop and not in_transfer:
                gun_keys = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]
                gun_list = ["pistol", "rifle", "shotgun", "sniper"]
                for ki, gn in zip(gun_keys, gun_list):
                    if keys[ki] and gn in owned_guns and current_gun != gn:
                        current_gun = gn
                        search_message = f"切换: {GUN_TYPES[gn]['name']}"
                        search_message_timer = 60
            if ammo_empty_timer > 0:
                ammo_empty_timer -= 1

            # ---- Move bullets ----
            for b in bullets[:]:
                b[0] += b[2]
                b[1] += b[3]
                # Wall collision
                hit_wall = False
                bullet_rect = pygame.Rect(b[0], b[1], 6, 14)
                for w in walls:
                    if bullet_rect.colliderect(pygame.Rect(w[0], w[1], w[2], w[3])):
                        bullets.remove(b)
                        hit_wall = True
                        break
                if hit_wall:
                    continue
                if (b[0] < -50 or b[0] > WORLD_W + 50 or
                        b[1] < -50 or b[1] > WORLD_H + 50):
                    bullets.remove(b)

            # ---- Move enemy bullets ----
            for eb in enemy_bullets[:]:
                eb[0] += eb[2]
                eb[1] += eb[3]
                # Wall collision
                hit_wall = False
                eb_rect = pygame.Rect(eb[0] - 2, eb[1] - 2, 5, 5)
                for w in walls:
                    if eb_rect.colliderect(pygame.Rect(w[0], w[1], w[2], w[3])):
                        enemy_bullets.remove(eb)
                        hit_wall = True
                        break
                if hit_wall:
                    continue
                if (eb[0] < -50 or eb[0] > WORLD_W + 50 or
                        eb[1] < -50 or eb[1] > WORLD_H + 50):
                    enemy_bullets.remove(eb)

            # ---- Spawn enemies ----
            # Enemy spawn rate: Normal 1.0, Hard 0.6, Extreme 0.48
            if extreme_mode_active:
                spd = 0.48
            elif hard_mode_active:
                spd = 0.6
            else:
                spd = 1.0
            enemy_spawn_hm = int(enemy_spawn_interval * spd)
            enemy_spawn_timer += 1
            if enemy_spawn_timer >= enemy_spawn_hm and len(enemies) < int(max_enemies * _dm(HM_SPAWN_MULT, EM_SPAWN_MULT)):
                spawn_enemy()
                enemy_spawn_timer = 0

            # ---- Boss respawn ----
            if boss is None and boss_respawn_timer > 0:
                boss_respawn_timer -= 1
                if boss_respawn_timer <= 0:
                    spawn_boss()

            # ---- Spawn supplies ----
            supply_spawn_timer += 1
            if supply_spawn_timer >= supply_spawn_interval and len(supplies) < max_supplies_on_map:
                spawn_supply()
                supply_spawn_timer = 0

            # ---- Supply lifetime ----
            for s in supplies[:]:
                s[3] -= 1
                if s[3] <= 0:
                    supplies.remove(s)

            # ---- Extraction zone logic (hold timer) ----
            if extract_zone:
                player_rect_now = pygame.Rect(player_x, player_y, player_size, player_size)
                in_zone = pygame.Rect(extract_zone[0], extract_zone[1],
                                      extract_size, extract_size).colliderect(player_rect_now)
                if in_zone:
                    extract_hold_timer += 1
                    if extract_hold_timer >= EXTRACT_HOLD_FRAMES:
                        play_sfx('extract')
                        do_extraction()
                else:
                    # Reset progress if leaving zone
                    extract_hold_timer = 0

            if extraction_message_timer > 0:
                extraction_message_timer -= 1
            if super_chaser_broadcast_timer > 0:
                super_chaser_broadcast_timer -= 1
            if save_message_timer > 0:
                save_message_timer -= 1

            # ---- Enemy AI ----
            pcx = player_x + player_size // 2
            pcy = player_y + player_size // 2

            for e in enemies:
                ex_c = e[0] + enemy_size // 2
                ey_c = e[1] + enemy_size // 2
                dist = math.hypot(pcx - ex_c, pcy - ey_c)

                if e[4] == "patrol":
                    if e[0] <= e[2]:
                        e[0] = e[2] + 1
                    elif e[0] >= e[3]:
                        e[0] = e[3] - 1
                    e[0] += random.choice([-1, 1]) * enemy_patrol_speed * (2 if random.random() < 0.02 else 0.3)
                    if dist < enemy_vision_range:
                        e[4] = "alert"
                        e[5] = 30
                        e[6] = CHASE_DURATION

                elif e[4] == "alert":
                    e[5] -= 1
                    if e[5] <= 0:
                        e[4] = "chase"
                    elif dist > enemy_vision_range * 1.3:
                        e[4] = "patrol"
                        e[5] = 0

                elif e[4] == "chase":
                    if dist > 0:
                        e[0] += (pcx - ex_c) / dist * enemy_chase_speed
                        e[1] += (pcy - ey_c) / dist * enemy_chase_speed
                    e[6] -= 1
                    if e[6] <= 0:
                        e[4] = "tired"
                        e[5] = 90
                        e[2] = max(0, e[0] - 180)
                        e[3] = min(WORLD_W - enemy_size, e[0] + 180)
                    elif dist > enemy_vision_range * 2:
                        e[4] = "patrol"
                        e[2] = max(0, e[0] - 180)
                        e[3] = min(WORLD_W - enemy_size, e[0] + 180)

                elif e[4] == "tired":
                    e[5] -= 1
                    if e[5] <= 0:
                        e[4] = "patrol"

                # Enemy shooting (during chase, very inaccurate)
                if e[4] == "chase" and dist < enemy_vision_range * 1.5:
                    e[8] -= 1
                    if e[8] <= 0:
                        e[8] = enemy_shoot_cd + random.randint(0, 30)
                        # Fire toward player with large random deviation
                        dx = pcx - ex_c
                        dy = pcy - ey_c
                        base_angle = math.atan2(dy, dx)
                        spread = random.uniform(-0.8, 0.8)  # +/-45deg random deviation
                        angle = base_angle + spread
                        ebx = ex_c + math.cos(base_angle) * (enemy_size // 2)
                        eby = ey_c + math.sin(base_angle) * (enemy_size // 2)
                        enemy_bullets.append([ebx, eby,
                                              math.cos(angle) * enemy_bullet_speed,
                                              math.sin(angle) * enemy_bullet_speed])

                # Wall collision
                e[0], e[1] = resolve_wall_collision(e[0], e[1],
                                                     enemy_size, enemy_size, walls)

                e[0] = max(0.0, min(float(WORLD_W - enemy_size), e[0]))
                e[1] = max(0.0, min(float(WORLD_H - enemy_size), e[1]))

            # ---- Boss AI ----
            if boss is not None:
                bcx = boss[0] + BOSS_SIZE // 2
                bcy = boss[1] + BOSS_SIZE // 2
                bdist = math.hypot(bcx - pcx, bcy - pcy)

                # Target detection: mark when entering range, cancel when leaving
                if bdist < BOSS_VISION_RANGE:
                    boss[4] = True
                else:
                    boss[4] = False

                if boss[4]:  # Only chase and shoot when target acquired
                    # Move toward player
                    if bdist > 0:
                        boss[0] += (pcx - bcx) / bdist * BOSS_SPEED
                        boss[1] += (pcy - bcy) / bdist * BOSS_SPEED

                    # Shoot (3 shots/sec, small deviation)
                    boss[3] -= 1
                    if boss[3] <= 0:
                        boss[3] = BOSS_SHOOT_CD
                        bcx2 = boss[0] + BOSS_SIZE // 2
                        bcy2 = boss[1] + BOSS_SIZE // 2
                        dx = pcx - bcx2
                        dy = pcy - bcy2
                        base_angle = math.atan2(dy, dx)
                        spread = random.uniform(-BOSS_SPREAD, BOSS_SPREAD)
                        angle = base_angle + spread
                        ebx = bcx2 + math.cos(base_angle) * (BOSS_SIZE // 2)
                        eby = bcy2 + math.sin(base_angle) * (BOSS_SIZE // 2)
                        enemy_bullets.append([ebx, eby,
                                              math.cos(angle) * enemy_bullet_speed,
                                              math.sin(angle) * enemy_bullet_speed,
                                              "boss"])  # Source tag
                boss[0], boss[1] = resolve_wall_collision(boss[0], boss[1],
                                                           BOSS_SIZE, BOSS_SIZE, walls)
                # World bounds
                boss[0] = max(0.0, min(float(WORLD_W - BOSS_SIZE), boss[0]))
                boss[1] = max(0.0, min(float(WORLD_H - BOSS_SIZE), boss[1]))

            # ---- Chaser AI (hunter) ----
            if chaser is not None:
                ccx = chaser[0] + CHASER_SIZE // 2
                ccy = chaser[1] + CHASER_SIZE // 2
                cdist = math.hypot(ccx - pcx, ccy - pcy)

                # Target: permanent lock after entering range
                if cdist < CHASER_VISION_RANGE:
                    chaser[3] = True

                if chaser[3]:
                    # Check if near extraction zone -> scare away
                    if extract_zone is not None:
                        ez_cx = extract_zone[0] + extract_size // 2
                        ez_cy = extract_zone[1] + extract_size // 2
                        if math.hypot(ccx - ez_cx, ccy - ez_cy) < extract_size // 2 + 100:
                            # Chaser scared by extraction zone
                            score += 200  # Scare bonus
                            chaser = None
                            chaser_respawn_hm = int(CHASER_RESPAWN_DELAY * (0.4 if extreme_mode_active else (0.5 if hard_mode_active else 1.0)))
                            chaser_respawn_timer = chaser_respawn_hm
                            # Skip remaining AI
                            continue

                    # Chase player (no shooting, ramming only)
                    if cdist > 0:
                        chaser[0] += (pcx - ccx) / cdist * CHASER_SPEED
                        chaser[1] += (pcy - ccy) / cdist * CHASER_SPEED
                else:
                    # Not locked: slow drift patrol
                    drift_angle = math.sin(pygame.time.get_ticks() * 0.001 + chaser[0] * 0.01) * 0.5
                    chaser[0] += math.cos(drift_angle) * 1.2
                    chaser[1] += math.sin(drift_angle) * 0.8

                # Wall collision
                chaser[0], chaser[1] = resolve_wall_collision(chaser[0], chaser[1],
                                                               CHASER_SIZE, CHASER_SIZE, walls)
                # World bounds
                chaser[0] = max(0.0, min(float(WORLD_W - CHASER_SIZE), chaser[0]))
                chaser[1] = max(0.0, min(float(WORLD_H - CHASER_SIZE), chaser[1]))

            # ---- Super Chaser AI (invincible hunter) ----
            if super_chaser is not None:
                scx = super_chaser[0] + SUPER_CHASER_SIZE // 2
                scy = super_chaser[1] + SUPER_CHASER_SIZE // 2
                scdist = math.hypot(scx - pcx, scy - pcy)

                # Target: permanent lock after entering range
                if scdist < SUPER_CHASER_VISION_RANGE:
                    super_chaser[2] = True

                if super_chaser[2]:
                    # Check if near extraction zone -> scare away
                    if extract_zone is not None:
                        ez_cx = extract_zone[0] + extract_size // 2
                        ez_cy = extract_zone[1] + extract_size // 2
                        if math.hypot(scx - ez_cx, scy - ez_cy) < extract_size // 2 + 120:
                            # Super Chaser scared by extraction zone
                            score += 300  # Scare bonus (higher than normal Chaser)
                            super_chaser = None
                            chaser_respawn_hm = int(CHASER_RESPAWN_DELAY * (0.4 if extreme_mode_active else (0.5 if hard_mode_active else 1.0)))
                            chaser_respawn_timer = chaser_respawn_hm
                            # Task progress: scare Super Chaser in hard mode
                            if hard_mode_active:
                                hm_super_chaser_scared += 1
                                check_tasks()
                                auto_save()  # Persist task progress immediately
                            # Advanced task: scare Super Chaser in extreme mode
                            if extreme_mode_active:
                                adv_chaser_scared += 1
                                check_adv_tasks()
                                auto_save()  # Persist advanced progress immediately
                            # Scare broadcast
                            super_chaser_broadcast = "超级猎手已被驱离！"
                            super_chaser_broadcast_timer = 120
                            continue

                    # Check nearby supplies -> leave when encountering
                    near_supply = False
                    for s in supplies:
                        scx_s = s[0] + SUPPLY_SIZE // 2
                        scy_s = s[1] + SUPPLY_SIZE // 2
                        if math.hypot(scx - scx_s, scy - scy_s) < SUPPLY_SIZE + 40:
                            near_supply = True
                            break
                    if near_supply:
                        super_chaser = None
                        chaser_respawn_timer = CHASER_RESPAWN_DELAY
                        # Task progress: scare Super Chaser in hard mode
                        if hard_mode_active:
                            hm_super_chaser_scared += 1
                            check_tasks()
                            auto_save()  # Persist task progress immediately
                        # Advanced task: scare Super Chaser in extreme mode
                        if extreme_mode_active:
                            adv_chaser_scared += 1
                            check_adv_tasks()
                            auto_save()  # Persist advanced progress immediately
                        super_chaser_broadcast = "超级猎手被物资引开了！"
                        super_chaser_broadcast_timer = 120
                        continue

                    # Chase player (ram only, no shooting)
                    if scdist > 0:
                        super_chaser[0] += (pcx - scx) / scdist * SUPER_CHASER_SPEED
                        super_chaser[1] += (pcy - scy) / scdist * SUPER_CHASER_SPEED
                else:
                    # Not locked: slow drift patrol (slower than Chaser)
                    drift_angle = math.sin(pygame.time.get_ticks() * 0.0008 + super_chaser[0] * 0.01) * 0.5
                    super_chaser[0] += math.cos(drift_angle) * 1.0
                    super_chaser[1] += math.sin(drift_angle) * 0.7

                # Wall collision
                super_chaser[0], super_chaser[1] = resolve_wall_collision(
                    super_chaser[0], super_chaser[1],
                    SUPER_CHASER_SIZE, SUPER_CHASER_SIZE, walls)
                # World bounds
                super_chaser[0] = max(0.0, min(float(WORLD_W - SUPER_CHASER_SIZE), super_chaser[0]))
                super_chaser[1] = max(0.0, min(float(WORLD_H - SUPER_CHASER_SIZE), super_chaser[1]))

            # ---- Chaser/Super Chaser respawn ----
            if chaser is None and super_chaser is None and chaser_respawn_timer > 0:
                chaser_respawn_timer -= 1
                if chaser_respawn_timer <= 0:
                    # Small chance: spawn Super Chaser instead of Chaser (pity increase)
                    hm_chance = super_chaser_spawn_chance * (2.08 if extreme_mode_active else (1.6 if hard_mode_active else 1.0))
                    if random.random() < hm_chance:
                        spawn_super_chaser()
                        super_chaser_spawn_chance = 0.55 if extreme_mode_active else (0.40 if hard_mode_active else 0.25)  # Reset to new base value after spawn
                    else:
                        spawn_chaser()
                        super_chaser_spawn_chance = min(super_chaser_spawn_chance + 0.10, 1.0)  # +10% on fail, cap at 100%

            # ---- Danger level ----
            chasing_count = sum(1 for e in enemies if e[4] == "chase")
            # Extra danger when Chaser has acquired target
            if chaser is not None and chaser[3]:
                chasing_count += 2
            # Major danger increase when Super Chaser has acquired target (invincible threat)
            if super_chaser is not None and super_chaser[2]:
                chasing_count += 3
            danger_level += (min(1.0, chasing_count / 3.0) - danger_level) * 0.05

            # ---- Mission timer ----
            mission_timer -= 1
            if mission_timer <= 0:
                mission_timer = 0
                auto_save()           # Persist current score
                game_over = True
                game_over_reason = "time_up"
                last_result = None
                killer = "时间耗尽"
                in_death_screen = True
                mission_boss_kills = 0  # Task 3: time expired, zero

            # ---- Bullets vs Boss (priority, when acquired) ----
            boss_just_hit = False
            if boss is not None and boss[4]:  # Target acquired: bullets prioritize Boss
                boss_rect = pygame.Rect(boss[0], boss[1], BOSS_SIZE, BOSS_SIZE)
                for b in bullets[:]:
                    if boss_rect.collidepoint(b[0] + 3, b[1] + 7):
                        if b in bullets:
                            bullets.remove(b)
                        boss[2] -= b[4] if len(b) > 4 else 1
                        boss_just_hit = True
                        if boss[2] <= 0:
                            # Boss killed
                            score += int(500 * _dm(HM_REWARD_MULT, EM_REWARD_MULT))
                            for _ in range(3):
                                supplies.append([float(boss[0] + random.randint(0, BOSS_SIZE - SUPPLY_SIZE)),
                                                 float(boss[1] + random.randint(0, BOSS_SIZE - SUPPLY_SIZE)),
                                                 "boss_drop", 900])
                            boss = None
                            # Boss death random gun drop
                            gun_drop_roll = random.random()
                            if gun_drop_roll < 0.4:
                                drop_gun = random.choice(["rifle", "shotgun", "sniper"])
                                if drop_gun not in owned_guns:
                                    owned_guns.add(drop_gun)
                                    search_message = f"Boss掉落: {GUN_TYPES[drop_gun]['name']}！"
                                    search_message_timer = 120
                                    auto_save()  # Persist guns immediately
                            boss_respawn_timer = BOSS_RESPAWN_DELAY
                            # Task progress: cumulative Boss kills in hard mode
                            if hard_mode_active:
                                hm_boss_kills += 1
                                mission_boss_kills += 1
                                check_tasks()
                                auto_save()  # Persist task progress immediately
                            # Advanced task: cumulative Boss kills in extreme mode
                            if extreme_mode_active:
                                adv_boss_kills += 1
                                check_adv_tasks()
                                auto_save()  # Persist advanced progress immediately
                        break  # Max 1 hit per frame

            # ---- Bullets vs Chaser (priority over normal enemies) ----
            chaser_just_hit = False
            if chaser is not None:
                chaser_rect = pygame.Rect(chaser[0], chaser[1], CHASER_SIZE, CHASER_SIZE)
                for b in bullets[:]:
                    if chaser_rect.collidepoint(b[0] + 3, b[1] + 7):
                        if b in bullets:
                            bullets.remove(b)
                        chaser[2] -= b[4] if len(b) > 4 else 1
                        chaser_just_hit = True
                        if chaser[2] <= 0:
                            # Chaser killed
                            score += int(300 * _dm(HM_REWARD_MULT, EM_REWARD_MULT))
                            for _ in range(2):
                                supplies.append([float(chaser[0] + random.randint(0, CHASER_SIZE - SUPPLY_SIZE)),
                                                 float(chaser[1] + random.randint(0, CHASER_SIZE - SUPPLY_SIZE)),
                                                 "enemy_drop", 900])
                            chaser = None
                            chaser_respawn_hm = int(CHASER_RESPAWN_DELAY * (0.4 if extreme_mode_active else (0.5 if hard_mode_active else 1.0)))
                            chaser_respawn_timer = chaser_respawn_hm
                        break

            # ---- Bullets vs enemies ----
            if not boss_just_hit and not chaser_just_hit:  # When Boss/Chaser hit first, skip enemy check
                bullets_hit = []  # (bullet, enemy) pairs
                for b in bullets[:]:
                    for e in enemies[:]:
                        if (e[0] < b[0] < e[0] + enemy_size and
                                e[1] < b[1] < e[1] + enemy_size):
                            bullets_hit.append((b, e))
                            break
                enemies_killed = set()
                for b, e in bullets_hit:
                    if b in bullets:
                        bullets.remove(b)
                    eid = id(e)
                    if eid not in enemies_killed:
                        dmg = b[4] if len(b) > 4 else 1
                        e[7] -= dmg
                        play_sfx('hit')
                        if e[7] <= 0:
                            if e in enemies:
                                enemies.remove(e)
                            enemies_killed.add(eid)
                            score += int(50 * _dm(HM_REWARD_MULT, EM_REWARD_MULT))
                            # Enemy death drop supply point
                            supplies.append([float(e[0]), float(e[1]), "enemy_drop", 900])

            # ---- Bullets vs Boss (can still be hit when not acquired) ----
            if boss is not None and not boss[4]:
                boss_rect = pygame.Rect(boss[0], boss[1], BOSS_SIZE, BOSS_SIZE)
                for b in bullets[:]:
                    if boss_rect.collidepoint(b[0] + 3, b[1] + 7):
                        if b in bullets:
                            bullets.remove(b)
                        boss[2] -= b[4] if len(b) > 4 else 1
                        play_sfx('hit')
                        if boss[2] <= 0:
                            play_sfx('boss_die')
                            score += int(500 * _dm(HM_REWARD_MULT, EM_REWARD_MULT))
                            for _ in range(3):
                                supplies.append([float(boss[0] + random.randint(0, BOSS_SIZE - SUPPLY_SIZE)),
                                                 float(boss[1] + random.randint(0, BOSS_SIZE - SUPPLY_SIZE)),
                                                 "boss_drop", 900])
                            boss = None
                            # Boss death random gun drop
                            gun_drop_roll = random.random()
                            if gun_drop_roll < 0.4:
                                drop_gun = random.choice(["rifle", "shotgun", "sniper"])
                                if drop_gun not in owned_guns:
                                    owned_guns.add(drop_gun)
                                    search_message = f"Boss掉落: {GUN_TYPES[drop_gun]['name']}！"
                                    search_message_timer = 120
                                    auto_save()  # Persist guns immediately
                            boss_respawn_timer = BOSS_RESPAWN_DELAY
                            # Task progress: cumulative Boss kills in hard mode
                            if hard_mode_active:
                                hm_boss_kills += 1
                                mission_boss_kills += 1
                                check_tasks()
                                auto_save()  # Persist task progress immediately
                            # Advanced task: cumulative Boss kills in extreme mode
                            if extreme_mode_active:
                                adv_boss_kills += 1
                                check_adv_tasks()
                                auto_save()  # Persist advanced progress immediately
                        break
                        break

            # ---- Bullets vs Super Chaser (invincible: bullets vanish, no damage) ----
            if super_chaser is not None:
                sc_rect = pygame.Rect(super_chaser[0], super_chaser[1],
                                      SUPER_CHASER_SIZE, SUPER_CHASER_SIZE)
                for b in bullets[:]:
                    if sc_rect.collidepoint(b[0] + 3, b[1] + 7):
                        if b in bullets:
                            bullets.remove(b)
                        # Invincible hint (brief flash)
                        break

            # ---- Player vs enemy collision ----
            player_rect   = pygame.Rect(player_x, player_y, player_size, player_size)
            hit_this_frame = False
            for e in enemies[:]:
                if pygame.Rect(e[0], e[1], enemy_size, enemy_size).colliderect(player_rect):
                    if e in enemies: enemies.remove(e)
                    # Collision kills also drop supply point
                    supplies.append([float(e[0]), float(e[1]), "enemy_drop", 900])
                    if not hit_this_frame:
                        if armor > 0:
                            armor -= 1          # Armor absorbs one hit
                        else:
                            lives -= 1
                            play_sfx('hurt')
                        hit_this_frame = True
                        if lives <= 0:
                            play_sfx('death')
                            estimated_value = 0   # Clear estimated value
                            backpack = []          # Clear backpack
                            lives = max_lives     # Restore lives
                            armor = 0             # Clear armor
                            mission_timer = MISSION_TIME  # Reset time
                            auto_save()           # Persist current score
                            game_over = True
                            killer = "巡逻兵"
                            in_death_screen = True
                            last_result = None
                            searching_supply = None
                            search_timer = 0
                            mission_boss_kills = 0  # Task 3: zero on death

            # ---- Boss vs player collision ----
            if boss is not None:
                boss_rect = pygame.Rect(boss[0], boss[1], BOSS_SIZE, BOSS_SIZE)
                if player_rect.colliderect(boss_rect):
                    if not hit_this_frame:
                        if armor > 0:
                            armor -= 1
                        else:
                            lives -= 1
                            play_sfx('hurt')
                        hit_this_frame = True
                        if lives <= 0:
                            play_sfx('death')
                            estimated_value = 0
                            backpack = []
                            lives = max_lives
                            armor = 0
                            mission_timer = MISSION_TIME
                            auto_save()           # Persist current score
                            game_over = True
                            killer = "Boss"
                            in_death_screen = True
                            last_result = None
                            searching_supply = None
                            search_timer = 0
                            mission_boss_kills = 0  # Task 3: zero on death

            # ---- Chaser vs player collision ----
            if chaser is not None:
                chaser_rect2 = pygame.Rect(chaser[0], chaser[1], CHASER_SIZE, CHASER_SIZE)
                if player_rect.colliderect(chaser_rect2):
                    if not hit_this_frame:
                        if armor > 0:
                            armor -= 1
                        else:
                            lives -= 1
                            play_sfx('hurt')
                        hit_this_frame = True
                        if lives <= 0:
                            play_sfx('death')
                            estimated_value = 0
                            backpack = []
                            lives = max_lives
                            armor = 0
                            mission_timer = MISSION_TIME
                            auto_save()           # Persist current score
                            game_over = True
                            killer = "猎手"
                            in_death_screen = True
                            last_result = None
                            searching_supply = None
                            search_timer = 0
                            mission_boss_kills = 0  # Task 3: zero on death

            # ---- Super Chaser vs player collision ----
            if super_chaser is not None:
                sc_rect = pygame.Rect(super_chaser[0], super_chaser[1],
                                      SUPER_CHASER_SIZE, SUPER_CHASER_SIZE)
                if player_rect.colliderect(sc_rect):
                    if not hit_this_frame:
                        if armor > 0:
                            armor -= 1
                        else:
                            lives -= 1
                            play_sfx('hurt')
                        hit_this_frame = True
                        if lives <= 0:
                            play_sfx('death')
                            estimated_value = 0
                            backpack = []
                            lives = max_lives
                            armor = 0
                            mission_timer = MISSION_TIME
                            auto_save()           # Persist current score
                            game_over = True
                            killer = "超级猎手"
                            in_death_screen = True
                            last_result = None
                            searching_supply = None
                            search_timer = 0
                            mission_boss_kills = 0  # Task 3: zero on death

            # ---- Enemy bullets vs player ----
            eb_hit = False
            for eb in enemy_bullets[:]:
                if player_rect.collidepoint(eb[0], eb[1]):
                    enemy_bullets.remove(eb)
                    if not eb_hit:
                        if armor > 0:
                            armor -= 1
                        else:
                            lives -= 1
                            play_sfx('hurt')
                        eb_hit = True
                        if lives <= 0:
                            play_sfx('death')
                            estimated_value = 0   # Clear estimated value
                            backpack = []          # Clear backpack
                            lives = max_lives     # Restore lives
                            armor = 0             # Clear armor
                            mission_timer = MISSION_TIME  # Reset time
                            auto_save()           # Persist current score
                            game_over = True
                            # Determine killer from bullet source tag
                            killer = "Boss炮弹" if (len(eb) > 4 and eb[4] == "boss") else "敌方子弹"
                            in_death_screen = True
                            last_result = None
                            searching_supply = None
                            search_timer = 0
                            mission_boss_kills = 0  # Task 3: zero on death

            # ---- Player vs supplies (J to search nearest) ----
            pcx2 = player_x + player_size // 2
            pcy2 = player_y + player_size // 2

            if searching_supply is not None:
                # Rescan nearest supply each frame to avoid stale index from expired supplies
                nearest_i = None
                for i, s in enumerate(supplies):
                    scx = s[0] + SUPPLY_SIZE // 2
                    scy = s[1] + SUPPLY_SIZE // 2
                    if math.hypot(scx - pcx2, scy - pcy2) < 60:
                        nearest_i = i
                        break  # Found one in range, continue

                if nearest_i is None:
                    # No supplies in range -> cancel search
                    searching_supply = None
                    search_timer = 0
                    search_message = "搜索已取消！"
                    search_message_timer = 45
                else:
                    # Update to valid index, continue search timer
                    searching_supply = nearest_i
                    s = supplies[searching_supply]
                    search_timer -= 1
                    if search_timer <= 0:
                        # Search complete!
                        play_sfx('pickup')
                        stype = s[2]
                        if stype == "boss_drop":
                            # Boss drop: chance to get token
                            if random.random() < TOKEN_DROP_CHANCE:
                                boss_token_count += 1
                                if not hard_mode_unlocked:
                                    hard_mode_unlocked = True
                                    search_message = "获得Boss信物！困难模式已解锁！"
                                else:
                                    search_message = f"获得Boss信物！（共 {boss_token_count} 个）"
                                search_message_timer = 150
                            # Then normal random supply effect
                            stype = random.choice(["common", "rare", "ammo", "heal"])
                        elif stype == "enemy_drop":
                            # Purple drop: random supply effect
                            stype = random.choice(["common", "rare", "ammo", "heal"])
                            # Fall through to corresponding branch below
                        if stype == "heal":
                            # Blue heal: directly restore lives, no score/backpack
                            lives = min(max_lives, lives + 1)
                            search_message = "生命+1♥"
                            search_message_timer = 60
                            supplies.pop(searching_supply)
                            searching_supply = None
                        elif stype == "ammo":
                            # Red ammo: replenish ammo supply
                            ammo_bonus = min(5, ammo_bonus + 2)
                            bullet_count = min(max_bullets, bullet_count + 50)
                            search_message = f"弹药+50 ●"
                            search_message_timer = 60
                            supplies.pop(searching_supply)
                            searching_supply = None
                        elif stype == "bonus":
                            # Red diamond: likely 10-100, rare 800-2000
                            if random.random() < 0.15:
                                pts = random.randint(800, 2000)
                                search_message = f"◆ Super Bonus +{pts}!"
                            else:
                                pts = random.randint(10, 100)
                                search_message = f"红包 +{pts}"
                            score += pts
                            search_message_timer = 60
                            supplies.pop(searching_supply)
                            searching_supply = None
                        elif stype in ("common", "rare"):
                            # Green/Gold: add points and put in backpack
                            if len(backpack) >= backpack_max:
                                # Backpack full during search (rare case)
                                search_message = "背包已满！物资丢失"
                                search_message_timer = 60
                                supplies.pop(searching_supply)
                                searching_supply = None
                            else:
                                score_ranges = {
                                    "common": (30, 120),
                                    "rare":   (150, 400),
                                }
                                low, high = score_ranges[stype]
                                pts = random.randint(low, high)
                                estimated_value += pts   # Only add to estimate, not real score
                                backpack.append(stype)
                                search_message = f"{SUPPLY_TYPES[stype]['label']} +{pts}"
                                search_message_timer = 60
                                supplies.pop(searching_supply)
                                searching_supply = None
            else:
                # Not searching: press J to start searching nearest supply
                if keys[pygame.K_j]:
                    nearest_i = None
                    nearest_d = float("inf")
                    for i, s in enumerate(supplies):
                        scx = s[0] + SUPPLY_SIZE // 2
                        scy = s[1] + SUPPLY_SIZE // 2
                        d = math.hypot(scx - pcx2, scy - pcy2)
                        if d < 60 and d < nearest_d:
                            nearest_d = d
                            nearest_i = i
                    if nearest_i is not None:
                        stype = supplies[nearest_i][2]
                        # Check backpack space before searching green/gold supplies
                        if stype in ("common", "rare") and len(backpack) >= backpack_max:
                            search_message = "背包已满！无法搜索"
                            search_message_timer = 60
                        else:
                            # Heal packs: direct pickup, no search needed
                            if stype == "heal":
                                lives = min(max_lives, lives + 1)
                                search_message = "生命+1♥"
                                search_message_timer = 60
                                supplies.pop(nearest_i)
                            else:
                                searching_supply = nearest_i
                                search_timer = SEARCH_DURATION
                                search_message = f"正在搜索 {SUPPLY_TYPES[stype]['label']}..."
                                search_message_timer = 0

            if ammo_bonus > 0 and bullet_cooldown == 0 and random.random() < 0.001:
                ammo_bonus -= 1

            # ---- Enemy out-of-bounds cleanup ----
            for e in enemies[:]:
                if (e[0] < -200 or e[0] > WORLD_W + 200 or
                        e[1] < -200 or e[1] > WORLD_H + 200):
                    enemies.remove(e)

        # ---------- Render ----------
        screen.fill(BG_DARK)
        draw_grass_texture()  # Draw grass texture

        # Background grid (follows camera) - dark green for visibility on green bg
        grid_off_x = int(cam_x) % 40
        grid_off_y = int(cam_y) % 40
        for gx in range(-grid_off_x, WIDTH + 40, 40):
            pygame.draw.line(screen, (35, 100, 40), (gx, 0), (gx, HEIGHT), 1)
        for gy in range(-grid_off_y, HEIGHT + 40, 40):
            pygame.draw.line(screen, (35, 100, 40), (0, gy), (WIDTH, gy), 1)

        # World bounds hint lines
        bx0 = int(-cam_x)
        by0 = int(-cam_y)
        bx1 = int(WORLD_W - cam_x)
        by1 = int(WORLD_H - cam_y)
        border_col = (40, 50, 80)
        pygame.draw.line(screen, border_col, (bx0, max(0, by0)), (bx0, min(HEIGHT, by1)), 2)
        pygame.draw.line(screen, border_col, (bx1, max(0, by0)), (bx1, min(HEIGHT, by1)), 2)
        pygame.draw.line(screen, border_col, (max(0, bx0), by0), (min(WIDTH, bx1), by0), 2)
        pygame.draw.line(screen, border_col, (max(0, bx0), by1), (min(WIDTH, bx1), by1), 2)

        # Walls
        draw_walls()

        # Supplies (only draw on-screen)
        for i, s in enumerate(supplies):
            if on_screen(s[0], s[1]):
                draw_supply(s[0], s[1], s[2], searching=(i == searching_supply))

        # Extraction zone
        if extract_zone:
            draw_extract_zone(extract_zone)

        # Bullets (round, same style as enemy bullets)
        for b in bullets:
            sx, sy = w2s(b[0], b[1])
            pygame.draw.circle(screen, BULLET_COLOR, (int(sx), int(sy)), 4)
            pygame.draw.circle(screen, (255, 200, 100), (int(sx), int(sy)), 2)

        # Enemy bullets
        for eb in enemy_bullets:
            sx, sy = w2s(eb[0], eb[1])
            pygame.draw.circle(screen, (255, 80, 60), (int(sx), int(sy)), 4)

        # Enemy patrol route (only draw on-screen)
        for e in enemies:
            if e[4] == "patrol" and on_screen(e[0], e[1], 200):
                ys = int(w2s(0, e[1] + enemy_size // 2)[1])
                xs0 = int(w2s(e[2], 0)[0])
                xs1 = int(w2s(e[3], 0)[0])
                for px in range(xs0, xs1, 15):
                    if px % 30 < 15:
                        pygame.draw.circle(screen, (40, 40, 40), (px, ys), 1)

        # Enemies
        for e in enemies:
            if on_screen(e[0], e[1]):
                draw_enemy(e[0], e[1], e[4])

        # Alert range
        for e in enemies:
            state = e[4]
            if state in ("alert", "chase") and on_screen(e[0], e[1], enemy_vision_range):
                vs = _vision_surf_chase if state == "chase" else _vision_surf_alert
                esx, esy = w2s(e[0], e[1])
                screen.blit(vs, (esx + enemy_size // 2 - enemy_vision_range,
                                 esy + enemy_size // 2 - enemy_vision_range))
                if state == "chase":
                    psx = player_x + player_size // 2 - cam_x
                    psy = player_y + player_size // 2 - cam_y
                    pygame.draw.line(screen, (255, 100, 50),
                                     (esx + enemy_size // 2, esy + enemy_size // 2),
                                     (psx, psy), 1)

        # Boss
        if boss is not None and on_screen(boss[0], boss[1], BOSS_SIZE):
            draw_boss(boss)
            # Show alert range
            bsx, bsy = w2s(boss[0], boss[1])
            screen.blit(_vision_surf_chase,
                        (bsx + BOSS_SIZE // 2 - enemy_vision_range,
                         bsy + BOSS_SIZE // 2 - enemy_vision_range))
            psx = player_x + player_size // 2 - cam_x
            psy = player_y + player_size // 2 - cam_y
            pygame.draw.line(screen, (255, 50, 50),
                             (bsx + BOSS_SIZE // 2, bsy + BOSS_SIZE // 2),
                             (psx, psy), 2)

        # Chaser
        if chaser is not None and on_screen(chaser[0], chaser[1], CHASER_SIZE):
            draw_chaser(chaser)
            # Show alert circle when target acquired
            if chaser[3]:
                csx, csy = w2s(chaser[0], chaser[1])
                vision_surf = pygame.Surface((CHASER_VISION_RANGE * 2, CHASER_VISION_RANGE * 2), pygame.SRCALPHA)
                pygame.draw.circle(vision_surf, (255, 60, 20, 20), (CHASER_VISION_RANGE, CHASER_VISION_RANGE), CHASER_VISION_RANGE)
                screen.blit(vision_surf,
                            (csx + CHASER_SIZE // 2 - CHASER_VISION_RANGE,
                             csy + CHASER_SIZE // 2 - CHASER_VISION_RANGE))

        # Super Chaser
        if super_chaser is not None and on_screen(super_chaser[0], super_chaser[1], SUPER_CHASER_SIZE):
            draw_super_chaser(super_chaser)
            # Show alert circle when target acquired (green)
            if super_chaser[2]:
                scsx, scsy = w2s(super_chaser[0], super_chaser[1])
                sc_vision = pygame.Surface((SUPER_CHASER_VISION_RANGE * 2, SUPER_CHASER_VISION_RANGE * 2), pygame.SRCALPHA)
                pygame.draw.circle(sc_vision, (30, 220, 80, 20), (SUPER_CHASER_VISION_RANGE, SUPER_CHASER_VISION_RANGE), SUPER_CHASER_VISION_RANGE)
                screen.blit(sc_vision,
                            (scsx + SUPER_CHASER_SIZE // 2 - SUPER_CHASER_VISION_RANGE,
                             scsy + SUPER_CHASER_SIZE // 2 - SUPER_CHASER_VISION_RANGE))

        # Player (always at screen center)
        draw_player(player_x, player_y)

        # HUD
        draw_hud()

        if game_over:
            show_game_over()

        # ---- Pause screen ----
        if paused and not in_main_menu and not in_shop and not in_transfer:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            # Pause menu panel
            pw, ph = 400, 260
            panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
            panel.fill((20, 25, 45, 230))
            pygame.draw.rect(panel, (100, 140, 220), (0, 0, pw, ph), 2, border_radius=12)
            px = WIDTH // 2 - pw // 2
            py = HEIGHT // 2 - ph // 2
            screen.blit(panel, (px, py))
            # Title
            t_surf = font_huge.render("游戏已暂停", True, (255, 220, 100))
            screen.blit(t_surf, (WIDTH // 2 - t_surf.get_width() // 2, py + 20))
            # Options
            opts = [
                ("ESC", "继续游戏", (100, 255, 150)),
                ("M",   "主菜单", (255, 180, 100)),
                ("Q",   "退出游戏", (255, 100, 100)),
            ]
            oy = py + 80
            for key, label, color in opts:
                o_surf = font_normal.render(f"[{key}]  {label}", True, color)
                screen.blit(o_surf, (WIDTH // 2 - o_surf.get_width() // 2, oy))
                oy += 50

        pygame.display.flip()

except Exception as e:
    import traceback
    err_log = os.path.join(GAME_SAVE_DIR, "error.log")
    with open(err_log, "w") as f:
        f.write(traceback.format_exc())
    # Try to show error in game window
    try:
        screen.fill((0, 0, 0))
        err_msg = f"游戏出错，详见日志:\n{err_log}"
        surf = font_normal.render(err_msg, True, (255, 100, 100))
        screen.blit(surf, (50, HEIGHT // 2 - 30))
        detail = font_small.render(str(e)[:80], True, (200, 200, 200))
        screen.blit(detail, (50, HEIGHT // 2 + 20))
        pygame.display.flip()
        pygame.time.wait(5000)
    except:
        pass

try:
    pygame.display.quit()
    pygame.quit()
except:
    pass
sys.exit()