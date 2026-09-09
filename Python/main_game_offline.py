import sys
import time
import random
import pygame

# ---------------------------------------------------------------------------
# Modern Color Palette & Geometry Config
# ---------------------------------------------------------------------------
WINDOW_SIZE = 640
BOARD_SIZE = 3
TOP_BAR_HEIGHT = 80
GRID_SIZE = WINDOW_SIZE
TOTAL_HEIGHT = WINDOW_SIZE + TOP_BAR_HEIGHT
CELL_SIZE = GRID_SIZE // BOARD_SIZE

# Color Definitions (RGB)
BG_COLOR = (18, 22, 31)          # Dark Slate
GRID_COLOR = (32, 42, 58)        # Accent Navy
CARD_BG = (26, 33, 46)           # Card Fill
CARD_BORDER = (45, 58, 80)

X_COLOR = (0, 225, 255)          # Neon Cyan
O_COLOR = (255, 110, 80)         # Neon Coral
WIN_LINE_COLOR = (46, 213, 115)  # Vibrant Emerald

TEXT_COLOR = (240, 244, 248)
MUTED_TEXT = (140, 155, 175)

# Default Settings
turn_duration = 5
player_symbol = "X"  # Options: "X" or "O"


# ---------------------------------------------------------------------------
# UI Components: Modern Button & Cards
# ---------------------------------------------------------------------------
class ModernButton:
    def __init__(self, x, y, width, height, text, font, accent_color=None, is_selected=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.accent_color = accent_color or (55, 125, 255)
        self.hover_progress = 1.0 if is_selected else 0.0
        self.is_selected = is_selected

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = self.rect.collidepoint(mouse_pos)

        target = 1.0 if (is_hovered or self.is_selected) else 0.0
        self.hover_progress += (target - self.hover_progress) * 0.25

        r = int(CARD_BG[0] + (self.accent_color[0] - CARD_BG[0]) * 0.25 * self.hover_progress)
        g = int(CARD_BG[1] + (self.accent_color[1] - CARD_BG[1]) * 0.25 * self.hover_progress)
        b = int(CARD_BG[2] + (self.accent_color[2] - CARD_BG[2]) * 0.25 * self.hover_progress)
        bg_col = (r, g, b)

        border_col = self.accent_color if (is_hovered or self.is_selected) else CARD_BORDER

        pygame.draw.rect(screen, bg_col, self.rect, border_radius=12)
        pygame.draw.rect(screen, border_col, self.rect, width=3 if self.is_selected else 2, border_radius=12)

        label_col = TEXT_COLOR if not (is_hovered or self.is_selected) else (255, 255, 255)
        text_surf = self.font.render(self.text, True, label_col)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


def check_game_status(board):
    win_conditions = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Columns
        (0, 4, 8), (2, 4, 6)              # Diagonals
    ]

    for condition in win_conditions:
        a, b, c = condition
        if board[a] != "" and board[a] == board[b] == board[c]:
            return "WIN", board[a], condition

    if "" not in board:
        return "DRAW", None, None

    return "ONGOING", None, None


# ---------------------------------------------------------------------------
# Board Rendering Logic
# ---------------------------------------------------------------------------
def draw_board_grid(screen):
    screen.fill(BG_COLOR)
    for i in range(1, BOARD_SIZE):
        x = i * CELL_SIZE
        pygame.draw.line(screen, GRID_COLOR, (x, TOP_BAR_HEIGHT + 20), (x, TOTAL_HEIGHT - 20), 8)
        y = TOP_BAR_HEIGHT + i * CELL_SIZE
        pygame.draw.line(screen, GRID_COLOR, (20, y), (WINDOW_SIZE - 20, y), 8)


def draw_hover_preview(screen, board, current_turn, game_over):
    """Draws a semi-transparent symbol when hovering over empty board cells on player's turn."""
    if game_over or current_turn != "PLAYER":
        return

    mouse_x, mouse_y = pygame.mouse.get_pos()

    if mouse_y > TOP_BAR_HEIGHT:
        col = mouse_x // CELL_SIZE
        row = (mouse_y - TOP_BAR_HEIGHT) // CELL_SIZE
        board_index = row * BOARD_SIZE + col

        if 0 <= board_index < 9 and board[board_index] == "":
            hover_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            rel_cx = CELL_SIZE // 2
            rel_cy = CELL_SIZE // 2

            if player_symbol == "X":
                preview_color = (0, 225, 255, 80)
                offset = CELL_SIZE // 4
                pygame.draw.line(hover_surface, preview_color, 
                                 (rel_cx - offset, rel_cy - offset), 
                                 (rel_cx + offset, rel_cy + offset), 12)
                pygame.draw.line(hover_surface, preview_color, 
                                 (rel_cx - offset, rel_cy + offset), 
                                 (rel_cx + offset, rel_cy - offset), 12)
            else:
                preview_color = (255, 110, 80, 80)
                radius = CELL_SIZE // 4
                pygame.draw.circle(hover_surface, preview_color, (rel_cx, rel_cy), radius, width=10)

            screen.blit(hover_surface, (col * CELL_SIZE, TOP_BAR_HEIGHT + row * CELL_SIZE))


def draw_robot_thinking_preview(screen, board, current_turn, game_over, robot_preview_idx, robot_symbol):
    """Draws a semi-transparent shape moving through empty cells on the robot's turn."""
    if game_over or current_turn != "ROBOT" or robot_preview_idx is None:
        return

    if 0 <= robot_preview_idx < 9 and board[robot_preview_idx] == "":
        col = robot_preview_idx % BOARD_SIZE
        row = robot_preview_idx // BOARD_SIZE

        hover_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        rel_cx = CELL_SIZE // 2
        rel_cy = CELL_SIZE // 2

        if robot_symbol == "O":
            preview_color = (255, 110, 80, 90)
            radius = CELL_SIZE // 4
            pygame.draw.circle(hover_surface, preview_color, (rel_cx, rel_cy), radius, width=10)
        else:
            preview_color = (0, 225, 255, 90)
            offset = CELL_SIZE // 4
            pygame.draw.line(hover_surface, preview_color, 
                             (rel_cx - offset, rel_cy - offset), 
                             (rel_cx + offset, rel_cy + offset), 12)
            pygame.draw.line(hover_surface, preview_color, 
                             (rel_cx - offset, rel_cy + offset), 
                             (rel_cx + offset, rel_cy - offset), 12)

        screen.blit(hover_surface, (col * CELL_SIZE, TOP_BAR_HEIGHT + row * CELL_SIZE))


def draw_board_symbols(screen, board):
    for idx, symbol in enumerate(board):
        row = idx // BOARD_SIZE
        col = idx % BOARD_SIZE
        center_x = col * CELL_SIZE + CELL_SIZE // 2
        center_y = TOP_BAR_HEIGHT + row * CELL_SIZE + CELL_SIZE // 2

        if symbol == "X":
            offset = CELL_SIZE // 4
            pygame.draw.aaline(screen, X_COLOR, (center_x - offset, center_y - offset),
                              (center_x + offset, center_y + offset), 1)
            pygame.draw.line(screen, X_COLOR, (center_x - offset, center_y - offset),
                             (center_x + offset, center_y + offset), 12)

            pygame.draw.aaline(screen, X_COLOR, (center_x - offset, center_y + offset),
                              (center_x + offset, center_y - offset), 1)
            pygame.draw.line(screen, X_COLOR, (center_x - offset, center_y + offset),
                             (center_x + offset, center_y - offset), 12)

        elif symbol == "O":
            radius = CELL_SIZE // 4
            pygame.draw.circle(screen, O_COLOR, (center_x, center_y), radius, width=10)


def draw_winning_highlight(screen, win_indices):
    start_idx, _, end_idx = win_indices
    r1, c1 = start_idx // BOARD_SIZE, start_idx % BOARD_SIZE
    r2, c2 = end_idx // BOARD_SIZE, end_idx % BOARD_SIZE

    p1 = (c1 * CELL_SIZE + CELL_SIZE // 2, TOP_BAR_HEIGHT + r1 * CELL_SIZE + CELL_SIZE // 2)
    p2 = (c2 * CELL_SIZE + CELL_SIZE // 2, TOP_BAR_HEIGHT + r2 * CELL_SIZE + CELL_SIZE // 2)

    pygame.draw.line(screen, WIN_LINE_COLOR, p1, p2, 12)


def render_header_bar(screen, turn, remaining_seconds, font, robot_symbol):
    header_rect = pygame.Rect(0, 0, WINDOW_SIZE, TOP_BAR_HEIGHT)
    pygame.draw.rect(screen, CARD_BG, header_rect)
    pygame.draw.line(screen, CARD_BORDER, (0, TOP_BAR_HEIGHT), (WINDOW_SIZE, TOP_BAR_HEIGHT), 2)

    current_symbol = player_symbol if turn == "PLAYER" else robot_symbol
    active_color = X_COLOR if current_symbol == "X" else O_COLOR

    turn_text = f"TURN: {turn} ({current_symbol})"
    time_text = f"00:0{remaining_seconds}" if remaining_seconds < 10 else f"00:{remaining_seconds}"

    turn_surf = font.render(turn_text, True, active_color)
    time_surf = font.render(time_text, True, TEXT_COLOR)

    screen.blit(turn_surf, (30, TOP_BAR_HEIGHT // 2 - turn_surf.get_height() // 2))
    screen.blit(time_surf, (WINDOW_SIZE - 30 - time_surf.get_width(), TOP_BAR_HEIGHT // 2 - time_surf.get_height() // 2))


# ---------------------------------------------------------------------------
# Application Screens
# ---------------------------------------------------------------------------
def run_main_menu(screen, title_font, symbol_font, font, small_font):
    global player_symbol

    # Decreased distance between caption (y=328) and Play Game button (y=360)
    play_btn = ModernButton(210, 360, 220, 52, "Play Game", font, accent_color=(0, 225, 255))
    settings_btn = ModernButton(210, 428, 220, 52, "Settings", font, accent_color=(55, 125, 255))
    quit_btn = ModernButton(210, 496, 220, 52, "Quit", font, accent_color=(255, 110, 80))

    while True:
        screen.fill(BG_COLOR)

        title_surf = title_font.render("TIC TAC CLASH", True, TEXT_COLOR)
        title_rect = title_surf.get_rect(center=(WINDOW_SIZE // 2, 85))
        screen.blit(title_surf, title_rect)

        # Player Symbol Selection Header
        choose_surf = font.render("Choose Your Side:", True, TEXT_COLOR)
        choose_rect = choose_surf.get_rect(center=(WINDOW_SIZE // 2, 155))
        screen.blit(choose_surf, choose_rect)

        # Side Selection Card Buttons
        btn_x = ModernButton(170, 185, 130, 110, "X", symbol_font, accent_color=X_COLOR, is_selected=(player_symbol == "X"))
        btn_o = ModernButton(340, 185, 130, 110, "O", symbol_font, accent_color=O_COLOR, is_selected=(player_symbol == "O"))

        btn_x.draw(screen)
        btn_o.draw(screen)

        # Explanatory Caption Underneath
        caption_surf = small_font.render("X starts first, O starts second", True, MUTED_TEXT)
        caption_rect = caption_surf.get_rect(center=(WINDOW_SIZE // 2, 318))
        screen.blit(caption_surf, caption_rect)

        play_btn.draw(screen)
        settings_btn.draw(screen)
        quit_btn.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"

            if btn_x.is_clicked(event):
                player_symbol = "X"
            if btn_o.is_clicked(event):
                player_symbol = "O"

            if play_btn.is_clicked(event):
                return "GAME"
            if settings_btn.is_clicked(event):
                return "SETTINGS"
            if quit_btn.is_clicked(event):
                return "QUIT"

        pygame.display.flip()


def run_settings(screen, title_font, font):
    global turn_duration

    minus_btn = ModernButton(190, 310, 60, 60, "-", title_font, accent_color=(255, 110, 80))
    plus_btn = ModernButton(390, 310, 60, 60, "+", title_font, accent_color=(0, 225, 255))
    back_btn = ModernButton(210, 480, 220, 54, "Save & Return", font, accent_color=(55, 125, 255))

    while True:
        screen.fill(BG_COLOR)

        title_surf = title_font.render("SETTINGS", True, TEXT_COLOR)
        title_rect = title_surf.get_rect(center=(WINDOW_SIZE // 2, 120))
        screen.blit(title_surf, title_rect)

        label_surf = font.render("Turn Time Limit", True, MUTED_TEXT)
        label_rect = label_surf.get_rect(center=(WINDOW_SIZE // 2, 230))
        screen.blit(label_surf, label_rect)

        val_surf = title_font.render(f"{turn_duration} sec", True, X_COLOR)
        val_rect = val_surf.get_rect(center=(WINDOW_SIZE // 2, 340))
        screen.blit(val_surf, val_rect)

        minus_btn.draw(screen)
        plus_btn.draw(screen)
        back_btn.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"

            if minus_btn.is_clicked(event) and turn_duration > 1:
                turn_duration -= 1
            if plus_btn.is_clicked(event) and turn_duration < 30:
                turn_duration += 1
            if back_btn.is_clicked(event):
                return "MENU"

        pygame.display.flip()


def run_game(screen, font, small_font):
    board = [""] * 9
    robot_symbol = "O" if player_symbol == "X" else "X"

    # X always takes the first turn
    current_turn = "PLAYER" if player_symbol == "X" else "ROBOT"
    turn_start_time = time.time()

    game_over = False
    game_result_text = ""
    win_indices = None

    # Robot Preview Animations State
    last_robot_switch_time = 0
    robot_preview_idx = None

    # Vertically Stacked Game Over Buttons
    replay_btn = ModernButton(210, TOTAL_HEIGHT // 2 - 15, 220, 50, "Replay", font, accent_color=(0, 225, 255))
    menu_btn = ModernButton(210, TOTAL_HEIGHT // 2 + 45, 220, 50, "Main Menu", font, accent_color=(55, 125, 255))

    clock = pygame.time.Clock()

    while True:
        elapsed_time = time.time() - turn_start_time
        time_remaining = max(0, int(turn_duration - elapsed_time))

        # Handle Robot Thinking animation switching
        if not game_over and current_turn == "ROBOT":
            now = time.time()
            if now - last_robot_switch_time > 0.12:  # Switch spot every 120ms
                empty_positions = [i for i, cell in enumerate(board) if cell == ""]
                if empty_positions:
                    robot_preview_idx = random.choice(empty_positions)
                last_robot_switch_time = now

        # Handle turn transition timeouts
        if not game_over and elapsed_time >= turn_duration:
            if current_turn == "ROBOT":
                empty_positions = [i for i, cell in enumerate(board) if cell == ""]
                if empty_positions:
                    robot_move = random.choice(empty_positions)
                    board[robot_move] = robot_symbol

                    status, winner, current_win_indices = check_game_status(board)
                    if status == "WIN":
                        game_over = True
                        win_indices = current_win_indices
                        game_result_text = f"ROBOT '{winner}' WINS!"
                    elif status == "DRAW":
                        game_over = True
                        game_result_text = "IT'S A DRAW!"

            current_turn = "ROBOT" if current_turn == "PLAYER" else "PLAYER"
            turn_start_time = time.time()
            time_remaining = turn_duration
            robot_preview_idx = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"

            if not game_over and event.type == pygame.MOUSEBUTTONDOWN:
                if current_turn == "PLAYER" and event.pos[1] > TOP_BAR_HEIGHT:
                    x, y = event.pos
                    col = x // CELL_SIZE
                    row = (y - TOP_BAR_HEIGHT) // CELL_SIZE
                    board_index = row * BOARD_SIZE + col

                    if 0 <= board_index < 9 and board[board_index] == "":
                        board[board_index] = player_symbol

                        status, winner, current_win_indices = check_game_status(board)
                        if status == "WIN":
                            game_over = True
                            win_indices = current_win_indices
                            game_result_text = f"PLAYER '{winner}' WINS!"
                        elif status == "DRAW":
                            game_over = True
                            game_result_text = "IT'S A DRAW!"
                        else:
                            current_turn = "ROBOT"
                            turn_start_time = time.time()
                            robot_preview_idx = None

            if game_over:
                if replay_btn.is_clicked(event):
                    board = [""] * 9
                    current_turn = "PLAYER" if player_symbol == "X" else "ROBOT"
                    turn_start_time = time.time()
                    game_over = False
                    game_result_text = ""
                    win_indices = None
                    robot_preview_idx = None
                if menu_btn.is_clicked(event):
                    return "MENU"

        # Render Game Field
        draw_board_grid(screen)
        draw_hover_preview(screen, board, current_turn, game_over)
        draw_robot_thinking_preview(screen, board, current_turn, game_over, robot_preview_idx, robot_symbol)
        draw_board_symbols(screen, board)

        if game_over:
            if win_indices:
                draw_winning_highlight(screen, win_indices)

            # Draw Game Over Modal Panel
            panel_rect = pygame.Rect(110, TOTAL_HEIGHT // 2 - 110, WINDOW_SIZE - 220, 230)
            pygame.draw.rect(screen, CARD_BG, panel_rect, border_radius=16)
            pygame.draw.rect(screen, CARD_BORDER, panel_rect, width=2, border_radius=16)

            res_surf = font.render(game_result_text, True, WIN_LINE_COLOR)
            res_rect = res_surf.get_rect(center=(WINDOW_SIZE // 2, TOTAL_HEIGHT // 2 - 60))
            screen.blit(res_surf, res_rect)

            replay_btn.draw(screen)
            menu_btn.draw(screen)
        else:
            render_header_bar(screen, current_turn, time_remaining, font, robot_symbol)

        pygame.display.flip()
        clock.tick(60)


# ---------------------------------------------------------------------------
# Main Controller Entry Point
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_SIZE, TOTAL_HEIGHT))
    pygame.display.set_caption("Tic Tac Clash")

    # Load System Fonts
    title_font = pygame.font.SysFont("Segoe UI", 32, bold=True)
    symbol_font = pygame.font.SysFont("Segoe UI", 56, bold=True)
    font = pygame.font.SysFont("Segoe UI", 22, bold=True)
    small_font = pygame.font.SysFont("Segoe UI", 16)

    state = "MENU"

    while True:
        if state == "MENU":
            state = run_main_menu(screen, title_font, symbol_font, font, small_font)
        elif state == "SETTINGS":
            state = run_settings(screen, title_font, font)
        elif state == "GAME":
            state = run_game(screen, font, small_font)
        elif state == "QUIT":
            pygame.quit()
            sys.exit()


if __name__ == "__main__":
    main()