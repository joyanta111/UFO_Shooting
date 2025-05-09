from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math
import random


# Game State
player_pos = [0, 0, 0]
gun_angle = 0
camera_pos = [0, 500, 500]
camera_angle = 0
camera_height = 600
first_person = False
cheat_mode = False
game_paused = False
enemies_paused = False
enemy_fire_paused = False

bullets = []  # [x, y, z, angle]
ufos = []     # [x, y, z, landed]
enemy_fireballs = []  # UFO bullets
powerups = []  # [x, y, z, type]
score = 0
lives = 3
game_over = False

# Power-ups
shield_active = False
shield_timer = 0
bullet_speed_active = False
bullet_speed_timer = 0
BULLET_SPEED = 10
DEFAULT_BULLET_SPEED = 10
POWERUP_DURATION = 300

# Constants
GRID_LIMIT = 600
UFO_SPEED = 0.1
UFO_FALL_SPEED = 0.2
FIREBALL_SPEED = 5
SPAWN_INTERVAL = 150
bullet_radius = 5
ufo_radius = 20
fireball_radius = 7
powerup_radius = 10

# Sentient UFO Boss
mothership = {
    "active": False,
    "x": 0,
    "y": 0,
    "z": 800,
    "health": 1000,
    "phase": 1,
    "shield": True,
    "pattern_memory": [],
    "last_dodge_time": 0,
    "minion_spawn_timer": 0
}

# Quantum Clone
time_clone = {
    "active": False,
    "positions": [],
    "current_step": 0,
    "cooldown": 0,
    "duration": 300  # 10 seconds at 30fps
}

frame_count = 0
fovY = 120

def clamp(val, low, high): 
    return max(low, min(val, high))

def distance(p1, p2):
    return math.sqrt(sum((p1[i] - p2[i]) ** 2 for i in range(3)))

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# Sentient UFO Functions
def spawn_mothership():
    mothership["active"] = True
    mothership["x"] = random.randint(-GRID_LIMIT, GRID_LIMIT)
    mothership["y"] = random.randint(-GRID_LIMIT, GRID_LIMIT)
    mothership["z"] = 800
    mothership["health"] = 1000
    mothership["phase"] = 1
    mothership["shield"] = True
    mothership["pattern_memory"] = []
    mothership["last_dodge_time"] = 0
    mothership["minion_spawn_timer"] = 100

def update_mothership():
    if not mothership["active"] or game_paused:
        return
    
    # Phase-based behavior
    if mothership["phase"] == 1:
        # Shielded phase - spawn minions
        mothership["minion_spawn_timer"] -= 1
        if mothership["minion_spawn_timer"] <= 0:
            ufos.append([mothership["x"] + random.randint(-100, 100),
                         mothership["y"] + random.randint(-100, 100),
                         mothership["z"] - 50, False])
            mothership["minion_spawn_timer"] = 100
        
        # Learn player patterns
        if len(bullets) > 0:
            last_bullet = bullets[-1]
            angle = last_bullet[3]
            mothership["pattern_memory"].append(angle)
            if len(mothership["pattern_memory"]) > 10:
                mothership["pattern_memory"].pop(0)
            
            # Dodge if pattern recognized
            if mothership["pattern_memory"].count(angle) > 3 and frame_count - mothership["last_dodge_time"] > 60:
                mothership["x"] += random.choice([-150, 150])
                mothership["y"] += random.choice([-150, 150])
                mothership["last_dodge_time"] = frame_count
        
        # Move toward player but maintain distance
        dx = player_pos[0] - mothership["x"]
        dy = player_pos[1] - mothership["y"]
        dist = math.hypot(dx, dy)
        if dist > 300:
            mothership["x"] += dx * 0.01
            mothership["y"] += dy * 0.01
        elif dist < 200:
            mothership["x"] -= dx * 0.01
            mothership["y"] -= dy * 0.01
        
        # Check for phase transition
        if mothership["health"] < 700:
            mothership["phase"] = 2
            mothership["shield"] = False
    
    elif mothership["phase"] == 2:
        # Aggressive phase - chase player and fire frequently
        dx = player_pos[0] - mothership["x"]
        dy = player_pos[1] - mothership["y"]
        mothership["x"] += dx * 0.02
        mothership["y"] += dy * 0.02
        
        # Fire at player
        if random.random() < 0.03:
            enemy_fireballs.append([mothership["x"], mothership["y"], mothership["z"]])
        
        # Phase transition
        if mothership["health"] < 300:
            mothership["phase"] = 3
            # Split into 3 smaller UFOs
            for _ in range(3):
                ufos.append([mothership["x"], mothership["y"], mothership["z"], False])
            mothership["active"] = False
    
    # Descend slowly
    if mothership["z"] > 200:
        mothership["z"] -= 0.5

def draw_mothership():
    if not mothership["active"]:
        return
    
    glPushMatrix()
    glTranslatef(mothership["x"], mothership["y"], mothership["z"])
    
    # Phase-based appearance
    if mothership["phase"] == 1:
        glColor3f(0.8, 0.2, 0.8)  # Purple with shield
        if mothership["shield"]:
            glColor4f(0.8, 0.2, 0.8, 0.3)
            glutWireSphere(60, 16, 16)
            glColor3f(0.8, 0.2, 0.8)
    elif mothership["phase"] == 2:
        glColor3f(1, 0.1, 0.1)  # Red when aggressive
    
    glutSolidSphere(40, 20, 20)
    
    # Health indicator
    glColor3f(1, 0, 0)
    glBegin(GL_LINES)
    glVertex3f(-40, -50, 0)
    glVertex3f(-40 + 80 * (mothership["health"] / 1000), -50, 0)
    glEnd()
    
    glPopMatrix()

# Quantum Clone Functions
def record_player_movement():
    if time_clone["cooldown"] > 0:
        return
    
    # Record current position and angle
    time_clone["positions"].append([player_pos[0], player_pos[1], player_pos[2], gun_angle])
    
    # Keep only the last 10 seconds of data
    if len(time_clone["positions"]) > time_clone["duration"]:
        time_clone["positions"].pop(0)

def activate_time_clone():
    if time_clone["cooldown"] <= 0 and len(time_clone["positions"]) >= time_clone["duration"]:
        time_clone["active"] = True
        time_clone["current_step"] = 0
        time_clone["cooldown"] = 900  # 30 second cooldown

def update_time_clone():
    if time_clone["cooldown"] > 0:
        time_clone["cooldown"] -= 1
    
    if not time_clone["active"]:
        return
    
    time_clone["current_step"] += 1
    if time_clone["current_step"] >= len(time_clone["positions"]):
        time_clone["active"] = False

def draw_time_clone():
    if not time_clone["active"]:
        return
    
    if time_clone["current_step"] < len(time_clone["positions"]):
        clone_data = time_clone["positions"][time_clone["current_step"]]
        glPushMatrix()
        glTranslatef(clone_data[0], clone_data[1], clone_data[2])
        glColor4f(0, 1, 1, 0.7)  # Semi-transparent cyan
        glutSolidCube(40)
        
        # Draw clone's gun
        glColor4f(0, 0, 1, 0.7)
        glRotatef(clone_data[3], 0, 0, 1)
        glTranslatef(20, 0, 20)
        glRotatef(90, 0, 1, 0)
        gluCylinder(gluNewQuadric(), 5, 5, 40, 10, 10)
        glPopMatrix()

# Enemy Management
def spawn_ufo():
    x = random.randint(-GRID_LIMIT+50, GRID_LIMIT-50)
    y = random.randint(-GRID_LIMIT+50, GRID_LIMIT-50)
    ufos.append([x, y, 400, False])

def maintain_ufo_count():
    while len(ufos) < 5 and not mothership["active"]:
        spawn_ufo()

def spawn_enemy_fireballs():
    if not enemy_fire_paused and not enemies_paused:
        for u in ufos:
            if random.random() < 0.01:
                enemy_fireballs.append([u[0], u[1], u[2]])
        
        if mothership["active"] and mothership["phase"] == 2 and random.random() < 0.03:
            enemy_fireballs.append([mothership["x"], mothership["y"], mothership["z"]])

def spawn_powerups():
    if random.random() < 0.002:
        x = random.randint(-GRID_LIMIT+50, GRID_LIMIT-50)
        y = random.randint(-GRID_LIMIT+50, GRID_LIMIT-50)
        z = 20
        power_type = random.choice([0, 1, 2])
        powerups.append([x, y, z, power_type])

def move_ufos():
    global lives, game_over
    if enemies_paused:
        return
        
    for u in ufos[:]:
        if not u[3]:
            u[2] -= UFO_FALL_SPEED
            if u[2] <= 40:
                u[2] = 40
                u[3] = True
        else:
            dx, dy = player_pos[0] - u[0], player_pos[1] - u[1]
            dist = math.hypot(dx, dy)
            if dist > 0:
                u[0] += UFO_SPEED * dx / dist
                u[1] += UFO_SPEED * dy / dist
            if distance(u[:3], player_pos) < 30:
                if not shield_active:
                    lives -= 1
                    if lives <= 0:
                        game_over = True
                ufos.remove(u)
                spawn_ufo()

def move_enemy_fireballs():
    global lives, game_over
    if enemy_fire_paused or enemies_paused:
        return
        
    for f in enemy_fireballs[:]:
        f[2] -= FIREBALL_SPEED
        if distance(f, player_pos) < 30:
            if not shield_active:
                lives -= 1
                if lives <= 0:
                    game_over = True
            enemy_fireballs.remove(f)
        if f[2] <= 0:
            enemy_fireballs.remove(f)

def pickup_powerups():
    global lives, BULLET_SPEED, shield_active, shield_timer, bullet_speed_active, bullet_speed_timer
    for p in powerups[:]:
        if distance(p[:3], player_pos) < 30:
            if p[3] == 0:
                lives += 1
            elif p[3] == 1:
                BULLET_SPEED = 20
                bullet_speed_active = True
                bullet_speed_timer = POWERUP_DURATION
            elif p[3] == 2:
                shield_active = True
                shield_timer = POWERUP_DURATION
            powerups.remove(p)

def fire_bullet():
    rad = math.radians(gun_angle)
    x = player_pos[0] + math.cos(rad) * 40
    y = player_pos[1] + math.sin(rad) * 40
    bullets.append([x, y, 20, gun_angle])

def auto_fire():
    global gun_angle
    for u in ufos:
        dx, dy = u[0] - player_pos[0], u[1] - player_pos[1]
        angle = math.degrees(math.atan2(dy, dx))
        gun_angle = angle
        fire_bullet()
        break

def move_bullets():
    global score
    for b in bullets[:]:
        rad = math.radians(b[3])
        b[0] += math.cos(rad) * BULLET_SPEED
        b[1] += math.sin(rad) * BULLET_SPEED
        if (abs(b[0]) > GRID_LIMIT or abs(b[1]) > GRID_LIMIT):
            bullets.remove(b)
            continue
        
        # Check for UFO hits
        for u in ufos[:]:
            if distance(b[:3], u[:3]) < ufo_radius + bullet_radius:
                bullets.remove(b)
                ufos.remove(u)
                score += 10
                if mothership["active"] and len(ufos) == 0:
                    mothership["health"] -= 50
                spawn_ufo()
                break
        
        # Check for mothership hits
        if mothership["active"] and not mothership["shield"]:
            if distance(b[:3], [mothership["x"], mothership["y"], mothership["z"]]) < 40 + bullet_radius:
                bullets.remove(b)
                mothership["health"] -= 10
                if mothership["health"] <= 0:
                    mothership["active"] = False
                    score += 500
                break

# Drawing Functions
def draw_player():
    glPushMatrix()
    glTranslatef(*player_pos)
    glColor3f(1, 0, 0)
    glutSolidCube(40)
    glColor3f(0, 0, 1)
    glRotatef(gun_angle, 0, 0, 1)
    glTranslatef(20, 0, 20)
    glRotatef(90, 0, 1, 0)
    gluCylinder(gluNewQuadric(), 5, 5, 40, 10, 10)
    if shield_active:
        glColor4f(0, 0.5, 1, 0.3)
        glutWireSphere(30, 10, 10)
    glPopMatrix()

def draw_bullets():
    if bullet_speed_active:
        glColor3f(1, 0.5, 0)
    else:
        glColor3f(1, 1, 0)
    for b in bullets:
        glPushMatrix()
        glTranslatef(*b[:3])
        gluSphere(gluNewQuadric(), bullet_radius, 10, 10)
        glPopMatrix()

def draw_ufos():
    for u in ufos:
        glPushMatrix()
        glTranslatef(u[0], u[1], u[2])
        glColor3f(1, 0, 0)
        gluSphere(gluNewQuadric(), 20, 20, 20)
        glTranslatef(0, 0, 25)
        glColor3f(0, 0, 0)
        gluSphere(gluNewQuadric(), 10, 10, 10)
        glPopMatrix()

def draw_enemy_fireballs():
    glColor3f(1, 0.5, 0)
    for f in enemy_fireballs:
        glPushMatrix()
        glTranslatef(*f)
        gluSphere(gluNewQuadric(), fireball_radius, 10, 10)
        glPopMatrix()

def draw_powerups():
    for p in powerups:
        glPushMatrix()
        glTranslatef(*p[:3])
        if p[3] == 0:
            glColor3f(0, 1, 0)
        elif p[3] == 1:
            glColor3f(1, 1, 0)
        else:
            glColor3f(0, 1, 1)
        glutSolidCube(20)
        glPopMatrix()

def draw_grid():
    glPushMatrix()
    for x in range(-GRID_LIMIT, GRID_LIMIT, 50):
        for y in range(-GRID_LIMIT, GRID_LIMIT, 50):
            if ((x+y) // 50) % 2 == 0:
                glColor3f(0.9, 0.9, 1)
            else:
                glColor3f(0.6, 0.3, 1)
            glBegin(GL_QUADS)
            glVertex3f(x, y, 0)
            glVertex3f(x + 50, y, 0)
            glVertex3f(x + 50, y + 50, 0)
            glVertex3f(x, y + 50, 0)
            glEnd()
    glPopMatrix()
    colors = [(0,1,0), (0,1,1), (0,0,1), (1,0,1)]
    for i, (x1, y1, x2, y2) in enumerate([
        (-GRID_LIMIT, -GRID_LIMIT, GRID_LIMIT, -GRID_LIMIT),
        (-GRID_LIMIT, GRID_LIMIT, GRID_LIMIT, GRID_LIMIT),
        (-GRID_LIMIT, -GRID_LIMIT, -GRID_LIMIT, GRID_LIMIT),
        (GRID_LIMIT, -GRID_LIMIT, GRID_LIMIT, GRID_LIMIT)
    ]):
        glColor3fv(colors[i])
        glBegin(GL_QUADS)
        glVertex3f(x1, y1, 0)
        glVertex3f(x2, y2, 0)
        glVertex3f(x2, y2, 200)
        glVertex3f(x1, y1, 200)
        glEnd()

def setup_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1000 / 800, 1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    if first_person:
        rad = math.radians(gun_angle)
        eye_x = player_pos[0] + math.cos(rad) * 30
        eye_y = player_pos[1] + math.sin(rad) * 30
        target_x = eye_x + math.cos(rad)
        target_y = eye_y + math.sin(rad)
        gluLookAt(eye_x, eye_y, 40, target_x, target_y, 40, 0, 0, 1)
    else:
        cam_x = math.cos(math.radians(camera_angle)) * 800
        cam_y = math.sin(math.radians(camera_angle)) * 800
        gluLookAt(cam_x, cam_y, camera_height, 0, 0, 0, 0, 0, 1)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, 1000, 800)
    setup_camera()
    draw_grid()
    draw_player()
    draw_bullets()
    draw_ufos()
    draw_enemy_fireballs()
    draw_powerups()
    draw_mothership()
    draw_time_clone()
    
    # Status display
    draw_text(10, 770, f"Score: {score}")
    draw_text(10, 740, f"Lives: {lives}")
    draw_text(10, 710, f"Cheat Mode: {'ON' if cheat_mode else 'OFF'}")
    draw_text(10, 680, f"View: {'First Person' if first_person else 'Third Person'}")
    
    # Power-up status indicators
    if shield_active:
        draw_text(10, 650, f"Shield: {shield_timer//30} sec")
    if bullet_speed_active:
        draw_text(10, 620, f"Bullet Speed: {bullet_speed_timer//30} sec")
    if time_clone["active"]:
        draw_text(10, 590, f"Clone Active: {(time_clone['duration']-time_clone['current_step'])//30} sec")
    elif time_clone["cooldown"] > 0:
        draw_text(10, 590, f"Clone Cooldown: {time_clone['cooldown']//30} sec")
    
    # Mothership status
    if mothership["active"]:
        draw_text(400, 770, f"Mothership: Phase {mothership['phase']} - Health {mothership['health']}")
    
    # Pause messages
    if enemy_fire_paused:
        draw_text(400, 550, "ENEMY FIRE PAUSED - Press 'Z' to Resume")
    if enemies_paused:
        draw_text(400, 500, "ENEMIES PAUSED - Press 'H' to Resume")
    if game_paused:
        draw_text(400, 450, "GAME PAUSED - Press 'P' to Resume")
    if game_over:
        draw_text(400, 400, "GAME OVER - Press 'R' to Restart")
    
    glutSwapBuffers()

def update():
    global frame_count, shield_timer, shield_active, bullet_speed_timer, bullet_speed_active, BULLET_SPEED, score
    
    if game_over or game_paused:
        glutPostRedisplay()
        return
        
    if not enemies_paused:
        move_ufos()
    
    move_bullets()
    move_enemy_fireballs()
    pickup_powerups()
    
    frame_count += 1
    
    # Spawn systems
    if frame_count % SPAWN_INTERVAL == 0 and not enemies_paused:
        spawn_ufo()
    
    # Mothership spawn
    if score >= 500 and not mothership["active"] and random.random() < 0.01:
        spawn_mothership()
    
    # Update special features
    update_mothership()
    record_player_movement()
    update_time_clone()
    
    spawn_enemy_fireballs()
    spawn_powerups()
    
    if cheat_mode:
        auto_fire()
    
    # Power-up timers
    if shield_active:
        shield_timer -= 1
        if shield_timer <= 0:
            shield_active = False
    
    if bullet_speed_active:
        bullet_speed_timer -= 1
        if bullet_speed_timer <= 0:
            bullet_speed_active = False
            BULLET_SPEED = DEFAULT_BULLET_SPEED
    
    glutPostRedisplay()

def keyboard(key, x, y):
    global gun_angle, cheat_mode, first_person, game_over, game_paused, enemies_paused, enemy_fire_paused
    
    if game_over and key == b'r':
        reset_game()
        return
    
    if key == b'z':
        enemy_fire_paused = not enemy_fire_paused
        return
    
    if key == b'h':
        enemies_paused = not enemies_paused
        return
    
    if key == b'p':
        game_paused = not game_paused
        return
    
    if key == b'q' and time_clone["cooldown"] <= 0:
        activate_time_clone()
        return
    
    if game_over or game_paused:
        return
    
    if key == b'a': 
        gun_angle += 5
    if key == b'd': 
        gun_angle -= 5
    if key == b'w':
        rad = math.radians(gun_angle)
        player_pos[0] = clamp(player_pos[0] + math.cos(rad) * 10, -GRID_LIMIT, GRID_LIMIT)
        player_pos[1] = clamp(player_pos[1] + math.sin(rad) * 10, -GRID_LIMIT, GRID_LIMIT)
    if key == b's':
        rad = math.radians(gun_angle)
        player_pos[0] = clamp(player_pos[0] - math.cos(rad) * 10, -GRID_LIMIT, GRID_LIMIT)
        player_pos[1] = clamp(player_pos[1] - math.sin(rad) * 10, -GRID_LIMIT, GRID_LIMIT)
    if key == b' ': 
        fire_bullet()
    if key == b'f': 
        first_person = not first_person
    if key == b'c': 
        cheat_mode = not cheat_mode
    if key == b'v': 
        first_person = not first_person


def special(key, x, y):
    global camera_angle, camera_height
    
    if game_paused:
        return
    
    if key == GLUT_KEY_LEFT: 
        camera_angle -= 5  # Fixed line - removed 'p'
    elif key == GLUT_KEY_RIGHT: 
        camera_angle += 5
    elif key == GLUT_KEY_UP:
        camera_height += 20
    elif key == GLUT_KEY_DOWN:
        camera_height = max(100, camera_height - 20)

def mouseListener(button, state, x, y):
    if game_paused:
        return
    
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        fire_bullet()

def reset_game():
    global bullets, ufos, enemy_fireballs, powerups, score, lives, game_over, game_paused, enemies_paused, enemy_fire_paused
    global shield_active, shield_timer, bullet_speed_active, bullet_speed_timer, BULLET_SPEED, mothership, time_clone
    
    bullets.clear()
    ufos.clear()
    enemy_fireballs.clear()
    powerups.clear()
    score = 0
    lives = 3
    game_over = False
    game_paused = False
    enemies_paused = False
    enemy_fire_paused = False
    shield_active = False
    shield_timer = 0
    bullet_speed_active = False
    bullet_speed_timer = 0
    BULLET_SPEED = DEFAULT_BULLET_SPEED
    player_pos[0] = 0
    player_pos[1] = 0
    player_pos[2] = 0
    
    # Reset special features
    mothership = {
        "active": False,
        "x": 0,
        "y": 0,
        "z": 800,
        "health": 1000,
        "phase": 1,
        "shield": True,
        "pattern_memory": [],
        "last_dodge_time": 0,
        "minion_spawn_timer": 0
    }
    
    time_clone = {
        "active": False,
        "positions": [],
        "current_step": 0,
        "cooldown": 0,
        "duration": 300
    }
    
    maintain_ufo_count()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutCreateWindow(b"UFO Shooter with Sentient AI and Quantum Clone")
    glEnable(GL_DEPTH_TEST)
    glClearColor(0, 0, 0, 1)
    maintain_ufo_count()
    glutDisplayFunc(display)
    glutIdleFunc(update)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special)
    glutMouseFunc(mouseListener)
    glutMainLoop()

if __name__ == "__main__":
    main()