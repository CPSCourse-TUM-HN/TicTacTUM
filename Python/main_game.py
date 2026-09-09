import csv
import json
import math
import os
import platform
import random
import time
import threading
import queue
import cv2
import numpy as np
import pyttsx3

# Optional LeRobot imports
try:
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
    LEROBOT_AVAILABLE = True
except ImportError:
    LEROBOT_AVAILABLE = False
    print("[WARN] LeRobot library not found. Running in simulation mode for arm playback.")

CALIBRATION_FILE = "board_corners.json"
XO_POSITIONS_DIR = "XO_Positions"
WARPED_SIZE = 300 
SPACE_GIF_PATH = "space_bg.gif" 

# Robot Arm Configuration
FOLLOWER_PORT = "COM5" 
FOLLOWER_ID = "my_follower_arm" 
PLAYBACK_HZ = 20 

JOINT_ORDER = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper"
]

# ---------------------------------------------------------------------------
# Deep Blue & Electric Cyan Theme Palette (BGR Format for OpenCV)
# ---------------------------------------------------------------------------
COLOR_SPACE_BG = (28, 14, 8)         # Deep Midnight Navy
COLOR_CARD = (60, 32, 16)            # Dark Sapphire Card Background
COLOR_TEXT = (255, 250, 245)         # Ice White
COLOR_ACCENT = (235, 190, 100)       # Soft Electric Cyan
COLOR_NEON_CYAN = (255, 220, 0)      # High-Glow Pure Cyan / Aqua
COLOR_NEON_BLUE = (250, 120, 30)     # Neon Royal Blue
COLOR_BUTTON = (85, 42, 20)          # Dark Ocean Blue Button
COLOR_HOVER = (150, 85, 35)          # Bright Indigo/Azure Hover

# Video-Game Arcade & HUD Typography Selection
FONT_PRIMARY = cv2.FONT_HERSHEY_COMPLEX_SMALL
FONT_TITLE = cv2.FONT_HERSHEY_TRIPLEX


# ---------------------------------------------------------------------------
# Robust Non-Blocking Speech Engine
# ---------------------------------------------------------------------------
class SpeechEngine:
    """Thread-safe speech queue manager using fresh engine instances per phrase."""
    def __init__(self):
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        while True:
            text = self.queue.get()
            if text is None:
                break
            try:
                # Re-initialize fresh engine per phrase to prevent thread lockups
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.say(text)
                engine.runAndWait()
                del engine
            except Exception as e:
                print(f"[TTS ERROR] {e}")
            finally:
                self.queue.task_done()

    def speak(self, text):
        # Clear backlog of old speech events
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except queue.Empty:
                break
        self.queue.put(text)

# Global Speech Engine Instance
tts = SpeechEngine()


# ---------------------------------------------------------------------------
# Helper Functions: Screen Geometry
# ---------------------------------------------------------------------------
def get_screen_resolution():
    """Detects primary monitor resolution dynamically."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return w, h
    except Exception:
        return 1920, 1080


# ---------------------------------------------------------------------------
# Unbeatable Minimax Algorithm
# ---------------------------------------------------------------------------
def minimax(board, depth, is_maximizing, player_symbol, robot_symbol):
    status, winner, _ = check_game_status(board)
    
    if status == "WIN":
        if winner == robot_symbol:
            return 10 - depth
        elif winner == player_symbol:
            return depth - 10
    elif status == "DRAW":
        return 0

    if is_maximizing:
        best_score = -math.inf
        for i in range(9):
            if board[i] == "empty":
                board[i] = robot_symbol
                score = minimax(board, depth + 1, False, player_symbol, robot_symbol)
                board[i] = "empty"
                best_score = max(score, best_score)
        return best_score
    else:
        best_score = math.inf
        for i in range(9):
            if board[i] == "empty":
                board[i] = player_symbol
                score = minimax(board, depth + 1, True, player_symbol, robot_symbol)
                board[i] = "empty"
                best_score = min(score, best_score)
        return best_score


def get_best_move(board, robot_symbol, player_symbol):
    best_score = -math.inf
    best_move = None
    
    for i in range(9):
        if board[i] == "empty":
            board[i] = robot_symbol
            score = minimax(board, 0, False, player_symbol, robot_symbol)
            board[i] = "empty"
            
            if score > best_score:
                best_score = score
                best_move = i
                
    return best_move


# ---------------------------------------------------------------------------
# Robot Trajectory Playback Helpers
# ---------------------------------------------------------------------------
def load_positions_from_file(filepath):
    if not os.path.exists(filepath):
        print(f"[ROBOT ERROR] File '{filepath}' not found.")
        return []

    positions = []
    with open(filepath, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].strip() == "shoulder_pan":
                continue
            if len(row) >= 6:
                try:
                    pos_dict = {
                        f"{joint}.pos": float(val.strip())
                        for joint, val in zip(JOINT_ORDER, row[:6])
                    }
                    positions.append(pos_dict)
                except ValueError:
                    continue
    return positions


def execute_robot_sequence(start_filepath, end_filepath):
    files_to_play = [start_filepath, end_filepath]

    if not LEROBOT_AVAILABLE:
        print(f"[SIMULATION] Playing arm trajectory {start_filepath} -> {end_filepath}")
        time.sleep(2.0)
        return

    try:
        config = SO101FollowerConfig(port=FOLLOWER_PORT, id=FOLLOWER_ID)
        robot = SO101Follower(config)
        robot.connect(calibrate=False)
        robot.bus.enable_torque()

        frame_duration = 1.0 / PLAYBACK_HZ

        for filepath in files_to_play:
            positions = load_positions_from_file(filepath)
            if not positions:
                continue

            for pos_target in positions:
                start_time = time.time()
                robot.send_action(pos_target)
                elapsed = time.time() - start_time
                sleep_time = max(0.0, frame_duration - elapsed)
                time.sleep(sleep_time)

    except Exception as e:
        print(f"[ROBOT ERROR] {e}")
    finally:
        try:
            robot.bus.disable_torque()
            robot.disconnect()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Calibration & Vision Functions
# ---------------------------------------------------------------------------
def calibrate_corners(camera_index=0, window_name="TIC-TAC-TUM"):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("[ERROR] Could not open camera.")
        return None

    frozen_frame = None
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        disp = frame.copy()
        cv2.putText(disp, "CALIBRATION: Point at board and press SPACE/ENTER", (30, 50),
                    FONT_PRIMARY, 1.2, COLOR_NEON_CYAN, 2)
        cv2.imshow(window_name, disp)
        key = cv2.waitKey(30) & 0xFF
        if key in (32, 13, ord('c')):
            frozen_frame = frame.copy()
            break
        elif key in (ord('q'), 27):
            cap.release()
            return None

    cap.release()

    points = []
    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) < 4:
                points.append([x, y])

    cv2.setMouseCallback(window_name, on_click)

    while True:
        display = frozen_frame.copy()
        for i, p in enumerate(points):
            cv2.circle(display, tuple(p), 7, COLOR_NEON_CYAN, -1)
            cv2.putText(display, str(i + 1), (p[0] + 10, p[1] - 10),
                        FONT_PRIMARY, 1.2, COLOR_NEON_CYAN, 2)

        if len(points) == 4:
            pts = np.array(points, dtype=np.int32)
            cv2.polylines(display, [pts], True, COLOR_NEON_CYAN, 2)
            cv2.putText(display, "Press ENTER/SPACE to Confirm, 'R' to Reset", (30, 50),
                        FONT_PRIMARY, 1.2, COLOR_NEON_CYAN, 2)

        cv2.imshow(window_name, display)
        key = cv2.waitKey(20) & 0xFF
        if key in (ord('r'), ord('R')):
            points.clear()
        elif key in (ord('q'), 27) or (key in (32, 13) and len(points) == 4):
            if len(points) == 4:
                break

    if len(points) == 4:
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(points, f)
        return points
    return None


def load_corners():
    if not os.path.exists(CALIBRATION_FILE):
        return None
    with open(CALIBRATION_FILE) as f:
        return json.load(f)


def get_perspective_transform(corners):
    src = np.array(corners, dtype=np.float32)
    dst = np.array([
        [0, 0],
        [WARPED_SIZE, 0],
        [WARPED_SIZE, WARPED_SIZE],
        [0, WARPED_SIZE]
    ], dtype=np.float32)
    return cv2.getPerspectiveTransform(src, dst)


def classify_cell(cell_bgr):
    hsv = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2HSV)
    cell_h, cell_w = cell_bgr.shape[:2]
    total_pixels = cell_h * cell_w
    kernel = np.ones((3, 3), np.uint8)

    # --- Standard & Bright Yellow Piece Detection ('X') ---
    # Hue: 22 to 38 (explicity excludes dark yellow/amber below 22)
    # Saturation: 70 to 255 (prevents capturing white/near-white)
    # Value: 110 to 255 (ensures well-lit standard and bright yellow detection)
    lower_yellow = np.array([22, 70, 110])
    upper_yellow = np.array([38, 255, 255])
    
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
    yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN, kernel)
    yellow_pixels = cv2.countNonZero(yellow_mask)

    if (yellow_pixels / float(total_pixels)) > 0.12:
        contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours and cv2.contourArea(max(contours, key=cv2.contourArea)) > 40:
            return "X"

    # --- Black or Orangish-Grey Piece Detection ('O') ---
    # 1. Pure Black / Dark Grey Mask
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, 75])
    black_mask = cv2.inRange(hsv, lower_black, upper_black)

    # 2. Orangish-Grey Mask (Hue: 5-25, Low/Medium Saturation, Medium/High Value)
    lower_orange_grey = np.array([5, 20, 60])
    upper_orange_grey = np.array([25, 160, 180])
    orange_grey_mask = cv2.inRange(hsv, lower_orange_grey, upper_orange_grey)

    # Combine both black and orangish-grey detections into a single mask for 'O'
    combined_o_mask = cv2.bitwise_or(black_mask, orange_grey_mask)
    combined_o_mask = cv2.morphologyEx(combined_o_mask, cv2.MORPH_OPEN, kernel)
    o_pixels = cv2.countNonZero(combined_o_mask)

    if (o_pixels / float(total_pixels)) > 0.12:
        contours, _ = cv2.findContours(combined_o_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours and cv2.contourArea(max(contours, key=cv2.contourArea)) > 40:
            return "O"

    return "empty"


def read_board(frame, corners):
    transform = get_perspective_transform(corners)
    warped = cv2.warpPerspective(frame, transform, (WARPED_SIZE, WARPED_SIZE))

    cell_size = WARPED_SIZE // 3
    board = []

    for row in range(3):
        for col in range(3):
            y0, y1 = row * cell_size, (row + 1) * cell_size
            x0, x1 = col * cell_size, (col + 1) * cell_size

            pad = cell_size // 5
            cell = warped[y0 + pad:y1 - pad, x0 + pad:x1 - pad]
            board.append(classify_cell(cell))

    return board, warped


def check_game_status(board):
    win_conditions = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8), 
        (0, 3, 6), (1, 4, 7), (2, 5, 8), 
        (0, 4, 8), (2, 4, 6)             
    ]

    for condition in win_conditions:
        a, b, c = condition
        if board[a] != "empty" and board[a] == board[b] == board[c]:
            return "WIN", board[a], condition

    if "empty" not in board:
        return "DRAW", None, None

    return "ONGOING", None, None


# ---------------------------------------------------------------------------
# Dynamic Background Manager (Blue Cosmic Theme)
# ---------------------------------------------------------------------------
class SpaceBackgroundManager:
    def __init__(self, filepath, width=1920, height=1080):
        self.width = width
        self.height = height
        self.use_gif = False
        self.gif_cap = None

        if os.path.exists(filepath):
            self.gif_cap = cv2.VideoCapture(filepath)
            if self.gif_cap.isOpened():
                self.use_gif = True

        if not self.use_gif:
            self.stars = [
                (random.randint(0, width), random.randint(0, height), random.uniform(1, 3), random.uniform(0.1, 0.8))
                for _ in range(120)
            ]

    def get_frame(self, target_w=None, target_h=None):
        w = target_w or self.width
        h = target_h or self.height

        if self.use_gif:
            ok, frame = self.gif_cap.read()
            if not ok:
                self.gif_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.gif_cap.read()

            if ok and frame is not None:
                return cv2.resize(frame, (w, h))

        img = np.full((h, w, 3), COLOR_SPACE_BG, dtype=np.uint8)

        # Draw Celestial Orb
        cv2.circle(img, (int(w * 0.85), int(h * 0.15)), 60, (120, 60, 20), -1)
        cv2.circle(img, (int(w * 0.85), int(h * 0.15)), 64, COLOR_NEON_CYAN, 2)

        # Twinkling Stars
        t = time.time()
        for x, y, size, speed in self.stars:
            if x < w and y < h:
                brightness = int(170 + 85 * np.sin(t * speed * 5))
                color = (brightness, int(brightness * 0.85), int(brightness * 0.5))
                cv2.circle(img, (x, y), int(size), color, -1)

        return img

    def release(self):
        if self.gif_cap is not None:
            self.gif_cap.release()


def draw_space_button(img, text, pos, size, is_hovered):
    x, y = pos
    w, h = size

    overlay = img.copy()
    color = COLOR_HOVER if is_hovered else COLOR_BUTTON
    border_color = COLOR_NEON_CYAN if is_hovered else COLOR_NEON_BLUE

    cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
    cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)

    cv2.rectangle(img, (x, y), (x + w, y + h), border_color, 3)

    icon_color = COLOR_NEON_CYAN if is_hovered else COLOR_ACCENT
    cv2.circle(img, (x + 35, y + h // 2), 9, icon_color, -1)
    cv2.circle(img, (x + w - 35, y + h // 2), 9, icon_color, -1)

    text_size = cv2.getTextSize(text, FONT_PRIMARY, 1.4, 2)[0]
    tx = x + (w - text_size[0]) // 2
    ty = y + (h + text_size[1]) // 2
    cv2.putText(img, text, (tx, ty), FONT_PRIMARY, 1.4, COLOR_TEXT, 2)


# ---------------------------------------------------------------------------
# Single-Window UI Screens (Main Menu & Game Submenu)
# ---------------------------------------------------------------------------
def play_game_submenu(bg_manager, menu_win, width, height):
    btn_w, btn_h = 580, 80
    btn_x = (width - btn_w) // 2
    btn_first = (btn_x, int(height * 0.42))
    btn_second = (btn_x, int(height * 0.55))
    btn_back = (btn_x, int(height * 0.68))

    mouse_pos = (-1, -1)
    clicked = False

    def on_mouse(event, x, y, flags, param):
        nonlocal mouse_pos, clicked
        mouse_pos = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            clicked = True

    cv2.setMouseCallback(menu_win, on_mouse)

    while True:
        menu_img = bg_manager.get_frame(width, height)

        card_w, card_h = int(width * 0.70), int(height * 0.24)
        card_x, card_y = (width - card_w) // 2, int(height * 0.12)
        overlay = menu_img.copy()
        cv2.rectangle(overlay, (card_x, card_y), (card_x + card_w, card_y + card_h), COLOR_CARD, -1)
        cv2.addWeighted(overlay, 0.75, menu_img, 0.25, 0, menu_img)
        cv2.rectangle(menu_img, (card_x, card_y), (card_x + card_w, card_y + card_h), COLOR_NEON_CYAN, 3)

        # Video-Game Arcade Style Big Header
        cv2.putText(menu_img, "SELECT GAME MODE", (width // 2 - 380, card_y + 85),
                    FONT_TITLE, 2.2, COLOR_NEON_CYAN, 4)
        cv2.putText(menu_img, "Who moves first?", (width // 2 - 140, card_y + 145),
                    FONT_PRIMARY, 1.4, COLOR_ACCENT, 2)

        mx, my = mouse_pos
        hover_first = (btn_first[0] <= mx <= btn_first[0] + btn_w) and (btn_first[1] <= my <= btn_first[1] + btn_h)
        hover_second = (btn_second[0] <= mx <= btn_second[0] + btn_w) and (btn_second[1] <= my <= btn_second[1] + btn_h)
        hover_back = (btn_back[0] <= mx <= btn_back[0] + btn_w) and (btn_back[1] <= my <= btn_back[1] + btn_h)

        draw_space_button(menu_img, "PLAY FIRST (PLAYER)", btn_first, (btn_w, btn_h), hover_first)
        draw_space_button(menu_img, "PLAY SECOND (ROBOT)", btn_second, (btn_w, btn_h), hover_second)
        draw_space_button(menu_img, "BACK TO MAIN MENU", btn_back, (btn_w, btn_h), hover_back)

        cv2.imshow(menu_win, menu_img)
        key = cv2.waitKey(30) & 0xFF

        if clicked:
            clicked = False
            if hover_first:
                return "START_FIRST"
            elif hover_second:
                return "START_SECOND"
            elif hover_back:
                return "BACK"

        if key in (ord('q'), 27):
            return "BACK"


def main_menu(camera_index=0):
    menu_win = "TIC-TAC-TUM"
    cv2.namedWindow(menu_win, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(menu_win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    width, height = get_screen_resolution()
    bg_manager = SpaceBackgroundManager(SPACE_GIF_PATH, width=width, height=height)

    mouse_pos = (-1, -1)
    clicked = False

    def on_mouse(event, x, y, flags, param):
        nonlocal mouse_pos, clicked
        mouse_pos = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            clicked = True

    cv2.setMouseCallback(menu_win, on_mouse)

    btn_w, btn_h = 580, 80
    btn_x = (width - btn_w) // 2
    btn_play = (btn_x, int(height * 0.42))
    btn_calib = (btn_x, int(height * 0.55))
    btn_quit = (btn_x, int(height * 0.68))

    while True:
        menu_img = bg_manager.get_frame(width, height)

        card_w, card_h = int(width * 0.75), int(height * 0.25)
        card_x, card_y = (width - card_w) // 2, int(height * 0.11)

        overlay = menu_img.copy()
        cv2.rectangle(overlay, (card_x, card_y), (card_x + card_w, card_y + card_h), COLOR_CARD, -1)
        cv2.addWeighted(overlay, 0.75, menu_img, 0.25, 0, menu_img)
        cv2.rectangle(menu_img, (card_x, card_y), (card_x + card_w, card_y + card_h), COLOR_NEON_CYAN, 3)

        # Video-Game Arcade Style Big Title Header
        cv2.putText(menu_img, "TIC-TAC-TUM", (width // 2 - 340, card_y + 90),
                    FONT_TITLE, 2.5, COLOR_NEON_CYAN, 5)
        cv2.putText(menu_img, "Yellow Piece = X   |   Black/Dark Piece = O", (width // 2 - 380, card_y + 155),
                    FONT_PRIMARY, 1.4, COLOR_ACCENT, 2)

        mx, my = mouse_pos
        hover_play = (btn_play[0] <= mx <= btn_play[0] + btn_w) and (btn_play[1] <= my <= btn_play[1] + btn_h)
        hover_calib = (btn_calib[0] <= mx <= btn_calib[0] + btn_w) and (btn_calib[1] <= my <= btn_calib[1] + btn_h)
        hover_quit = (btn_quit[0] <= mx <= btn_quit[0] + btn_w) and (btn_quit[1] <= my <= btn_quit[1] + btn_h)

        draw_space_button(menu_img, "PLAY GAME", btn_play, (btn_w, btn_h), hover_play)
        draw_space_button(menu_img, "CALIBRATE BOARD", btn_calib, (btn_w, btn_h), hover_calib)
        draw_space_button(menu_img, "QUIT GAME", btn_quit, (btn_w, btn_h), hover_quit)

        cv2.imshow(menu_win, menu_img)
        key = cv2.waitKey(30) & 0xFF

        if clicked:
            clicked = False
            if hover_play:
                sub_choice = play_game_submenu(bg_manager, menu_win, width, height)
                cv2.setMouseCallback(menu_win, on_mouse)
                if sub_choice in ("START_FIRST", "START_SECOND"):
                    bg_manager.release()
                    return sub_choice
            elif hover_calib:
                bg_manager.release()
                return "CALIBRATE"
            elif hover_quit:
                bg_manager.release()
                return "EXIT"

        if key in (ord('q'), 27):
            bg_manager.release()
            return "EXIT"


# ---------------------------------------------------------------------------
# Single Window Fullscreen Game Loop
# ---------------------------------------------------------------------------
def play_game(camera_index=0, player_goes_first=True):
    window_name = "TIC-TAC-TUM"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    screen_w, screen_h = get_screen_resolution()

    corners = load_corners()
    if corners is None:
        corners = calibrate_corners(camera_index, window_name)
        if corners is None:
            return

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("[ERROR] Could not open camera.")
        return

    if player_goes_first:
        current_step_type = "STEP_1_PLAYER"
        player_symbol, robot_symbol = "X", "O"
        tts.speak("Player turn")
    else:
        current_step_type = "STEP_3_ROBOT"
        player_symbol, robot_symbol = "O", "X"
        tts.speak("Robot turn")

    step_start_time = time.time()
    robot_thread_started = False
    skip_requested = False
    robot_turn_count = 1

    board = ["empty"] * 9
    transform = get_perspective_transform(corners)

    game_over = False
    game_result_text = ""
    win_indices = None
    audio_played = False

    bg_manager = SpaceBackgroundManager(SPACE_GIF_PATH, width=screen_w, height=screen_h)

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Error: Could not grab camera frame.")
            break

        warped = cv2.warpPerspective(frame, transform, (WARPED_SIZE, WARPED_SIZE))
        elapsed = time.time() - step_start_time

        if not game_over:
            # --- STEP 1: PLAYER TURN (8.0s) ---
            if current_step_type == "STEP_1_PLAYER":
                duration = 8.0
                time_remaining = max(0.0, duration - elapsed)
                msg = f"Phase 1: Player's Turn | Window: {time_remaining:.1f}s (Press 'S' to Skip)"
                banner_color = COLOR_NEON_CYAN

                if elapsed >= duration or skip_requested:
                    skip_requested = False
                    current_step_type = "STEP_2_CHECK"
                    tts.speak("Checking board")
                    step_start_time = time.time()

            # --- STEP 2: CHECK BOARD STATUS (1.5s) ---
            elif current_step_type == "STEP_2_CHECK":
                duration = 1.5
                time_remaining = max(0.0, duration - elapsed)
                msg = f"Phase 2: Checking board... | {time_remaining:.1f}s"
                banner_color = COLOR_ACCENT

                board, warped = read_board(frame, corners)
                status, winner, current_win_indices = check_game_status(board)

                if status == "WIN":
                    game_over = True
                    win_indices = current_win_indices
                    game_result_text = f"GAME OVER: '{winner}' WINS!"
                elif status == "DRAW":
                    game_over = True
                    game_result_text = "GAME OVER: IT'S A DRAW!"

                if not game_over and (elapsed >= duration or skip_requested):
                    skip_requested = False
                    current_step_type = "STEP_3_ROBOT"
                    tts.speak("Robot turn")
                    step_start_time = time.time()
                    robot_thread_started = False

            # --- STEP 3: UNBEATABLE ROBOT TURN (13.0s) ---
            elif current_step_type == "STEP_3_ROBOT":
                duration = 13.0
                time_remaining = max(0.0, duration - elapsed)

                if not robot_thread_started:
                    best_move = get_best_move(board, robot_symbol, player_symbol)

                    if best_move is None:
                        game_over = True
                        game_result_text = "GAME OVER: NO SECTORS LEFT!"
                    else:
                        target_cell = best_move + 1
                        start_file_path = os.path.join(XO_POSITIONS_DIR, f"o_start_pos_{robot_turn_count}.txt")
                        end_file_path = os.path.join(XO_POSITIONS_DIR, f"o_end_pos_{target_cell}.txt")

                        thread = threading.Thread(
                            target=execute_robot_sequence,
                            args=(start_file_path, end_file_path),
                            daemon=True
                        )
                        thread.start()
                        robot_thread_started = True

                msg = f"Phase 3: Robot's Turn #{robot_turn_count} | {time_remaining:.1f}s (Press 'S' to Skip)"
                banner_color = COLOR_NEON_BLUE

                if elapsed >= duration or skip_requested:
                    skip_requested = False
                    robot_turn_count += 1
                    current_step_type = "STEP_4_CHECK_POST_ROBOT"
                    tts.speak("Checking board")
                    step_start_time = time.time()

            # --- STEP 4: CHECK BOARD STATUS POST-ROBOT (1.5s) ---
            elif current_step_type == "STEP_4_CHECK_POST_ROBOT":
                duration = 1.5
                time_remaining = max(0.0, duration - elapsed)
                msg = f"Phase 4: Checking board... | {time_remaining:.1f}s"
                banner_color = COLOR_ACCENT

                board, warped = read_board(frame, corners)
                status, winner, current_win_indices = check_game_status(board)

                if status == "WIN":
                    game_over = True
                    win_indices = current_win_indices
                    game_result_text = f"GAME OVER: '{winner}' WINS!"
                elif status == "DRAW":
                    game_over = True
                    game_result_text = "GAME OVER: IT'S A DRAW!"

                if not game_over and (elapsed >= duration or skip_requested):
                    skip_requested = False
                    current_step_type = "STEP_1_PLAYER"
                    tts.speak("Player turn")
                    step_start_time = time.time()

        # Handle Audio End Triggers
        else:
            if not audio_played:
                status, winner, _ = check_game_status(board)
                if status == "WIN":
                    if winner == player_symbol:
                        tts.speak("Player wins")
                    else:
                        tts.speak("Robot wins")
                elif status == "DRAW":
                    tts.speak("A draw")
                audio_played = True

        # Render Game Board Overlay
        cell_size = WARPED_SIZE // 3
        for idx, symbol in enumerate(board):
            r, c = idx // 3, idx % 3
            cx = c * cell_size + cell_size // 2
            cy = r * cell_size + cell_size // 2

            if symbol == "X":
                cv2.putText(warped, "X", (cx - 18, cy + 18),
                            FONT_TITLE, 1.8, COLOR_NEON_CYAN, 3)
                cv2.circle(warped, (cx, cy), 24, COLOR_NEON_CYAN, 2)
            elif symbol == "O":
                cv2.putText(warped, "O", (cx - 18, cy + 18),
                            FONT_TITLE, 1.8, COLOR_NEON_BLUE, 3)

        for i in range(1, 3):
            cv2.line(warped, (i * cell_size, 0), (i * cell_size, WARPED_SIZE), COLOR_CARD, 2)
            cv2.line(warped, (0, i * cell_size), (WARPED_SIZE, i * cell_size), COLOR_CARD, 2)

        if game_over and win_indices:
            p1 = (win_indices[0] % 3 * cell_size + cell_size // 2, win_indices[0] // 3 * cell_size + cell_size // 2)
            p2 = (win_indices[2] % 3 * cell_size + cell_size // 2, win_indices[2] // 3 * cell_size + cell_size // 2)
            cv2.line(warped, p1, p2, COLOR_NEON_CYAN, 4)

        # Draw Polygon on Primary Camera Stream
        display_cam = frame.copy()
        pts = np.array(corners, dtype=np.int32)
        cv2.polylines(display_cam, [pts], True, COLOR_NEON_CYAN, 2)

        # Build Fullscreen Single Canvas View
        canvas = bg_manager.get_frame(screen_w, screen_h)

        # Layout geometry
        cam_h_raw, cam_w_raw = display_cam.shape[:2]
        cam_aspect = (cam_w_raw / float(cam_h_raw)) if cam_h_raw > 0 else (4.0 / 3.0)

        view_h = int(screen_h * 0.6)
        cam_w = max(1, int(view_h * cam_aspect))

        cam_resized = cv2.resize(display_cam, (cam_w, view_h))
        warped_resized = cv2.resize(warped, (view_h, view_h))

        gap = 40
        total_content_w = cam_w + view_h + gap
        
        start_x = max(0, (screen_w - total_content_w) // 2)
        start_y = max(0, int(screen_h * 0.25))

        end_x_cam = min(screen_w, start_x + cam_w)
        end_y_cam = min(screen_h, start_y + view_h)

        end_x_board = min(screen_w, start_x + cam_w + gap + view_h)
        board_start_x = start_x + cam_w + gap

        canvas[start_y:end_y_cam, start_x:end_x_cam] = cam_resized[0:(end_y_cam - start_y), 0:(end_x_cam - start_x)]
        if board_start_x < screen_w:
            canvas[start_y:end_y_cam, board_start_x:end_x_board] = warped_resized[0:(end_y_cam - start_y), 0:(end_x_board - board_start_x)]

        # Draw View Borders
        cv2.rectangle(canvas, (start_x, start_y), (end_x_cam, end_y_cam), COLOR_NEON_BLUE, 2)
        if board_start_x < screen_w:
            cv2.rectangle(canvas, (board_start_x, start_y), (end_x_board, end_y_cam), COLOR_NEON_CYAN, 2)

        # Top Information Banner
        banner_w = total_content_w
        banner_x = start_x
        banner_y = int(screen_h * 0.08)
        
        overlay = canvas.copy()
        cv2.rectangle(overlay, (banner_x, banner_y), (banner_x + banner_w, banner_y + 80), COLOR_SPACE_BG, -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

        if not game_over:
            cv2.rectangle(canvas, (banner_x, banner_y), (banner_x + banner_w, banner_y + 80), banner_color, 2)
            cv2.putText(canvas, msg, (banner_x + 25, banner_y + 52),
                        FONT_PRIMARY, 1.3, banner_color, 2)
        else:
            cv2.rectangle(canvas, (banner_x, banner_y), (banner_x + banner_w, banner_y + 80), COLOR_NEON_CYAN, 2)
            cv2.putText(canvas, f"{game_result_text} | Press 'Q' to Return", 
                        (banner_x + 25, banner_y + 52), FONT_PRIMARY, 1.3, COLOR_NEON_CYAN, 2)

        cv2.imshow(window_name, canvas)
        key = cv2.waitKey(30) & 0xFF

        if key in (ord('s'), ord('S')):
            skip_requested = True

        elif key in (ord('q'), ord('Q'), 27):
            cap.release()
            bg_manager.release()
            return

    cap.release()
    bg_manager.release()


# ---------------------------------------------------------------------------
# Program Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    CAMERA_INDEX = 0
    while True:
        action = main_menu(CAMERA_INDEX)
        if action == "START_FIRST":
            play_game(CAMERA_INDEX, player_goes_first=True)
        elif action == "START_SECOND":
            play_game(CAMERA_INDEX, player_goes_first=False)
        elif action == "CALIBRATE":
            calibrate_corners(CAMERA_INDEX)
        elif action == "EXIT":
            break