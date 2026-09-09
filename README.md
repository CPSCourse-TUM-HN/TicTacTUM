# TicTacToe Robot

TicTacToe Robot is a cyber physical system that combines computer vision, game logic, and an **SO-101 robotic arm. A camera observes a physical 3×3 board, OpenCV detects the placed pieces, and the software checks the current game state**. During robot turns, the arm executes recorded joint trajectories to physically place a game piece **(X and O)** on the board.

The project also includes a standalone Pygame version called **Tic Tac Clash**, which allows the game interface and logic to be tested without the physical robot or camera.

The project transforms a simple TicTacToe game to allow software to  interact directly with the physical world. Instead of playing only on a screen, the system combines visual perception, board state recognition, game logic, and robotic movement.

The main goal is to demonstrate how a camera and robotic arm can work together in a closed interaction loop:

**Player move → Camera detection → Game state evaluation → Robot movement → Camera verification**

---

## Table of Contents

* [Project Structure](#project-structure)
* [Features](#features)
* [Hardware](#hardware)
* [Software](#software)
* [Dependencies & Setup](#dependencies--setup)
    * [Install Python dependencies](#install-python-dependencies)
    * [Configure the SO-101 arm](#configure-the-so-101-arm)
    * [Connect the camera](#connect-the-camera)
    * [Optional background GIF](#optional-background-gif)
    * [Calibrate the physical board](#calibrate-the-physical-board)
    * [Prepare robot trajectories](#prepare-robot-trajectories)
* [Vision System](#vision-system)
* [Game Logic](#game-logic)
* [Physical Game Cycle](#physical-game-cycle)
* [Running the Main Game](#running-the-main-game)
    * [Main Game Controls](#main-game-controls)
* [Robot Utility Scripts](#robot-utility-scripts)
* [Demo Video](#demo-video)
* [Acknowledgements](#acknowledgements)
---

## Project Structure

The project is organized into Python source files for the game, robot control, and trajectory recording, along with recorded robot trajectories stored as text files.

```text
.
├── Python
│   ├── main_game.py
│   ├── main_game_offline.py
│   ├── move_robot.py
│   └── record_arm.py
├── README.md
└── Txt
    ├── o_end_pos_1.txt   
    ├── o_end_pos_3.txt   
    ├── o_end_pos_5.txt   
    ├── o_end_pos_7.txt   
    ├── o_end_pos_9.txt   
    ├── o_start_pos_2.txt 
    ├── o_start_pos_4.txt
    ├── o_end_pos_2.txt   
    ├── o_end_pos_4.txt   
    ├── o_end_pos_6.txt   
    ├── o_end_pos_8.txt   
    ├── o_start_pos_1.txt 
    ├── o_start_pos_3.txt 
    ├── o_start_pos_5.txt
```

| File | Purpose |
| --- | --- |
| `main_game.py` | Main physical TicTacToe application combining camera vision, board detection, game logic, UI, and robot trajectory execution. |
| `main_game_offline.py` | Standalone Pygame implementation for testing the game interface and logic without a camera or robot. |
| `record_arm.py` | Places the SO-101 arm in freemove mode and records all six joint positions every 0.05 seconds. |
| `move_robot.py` | Loads a recorded trajectory from a `.txt` file and replays it on the SO-101 arm at 20 Hz. |



---

## Features
| Feature | Description |
|---|---|
| **Live board detection** | Using a camera and OpenCV. |
| **Perspective correction** | Transforms the detected board into a normalized 300 × 300 pixel view. |
| **Automatic cell classification** | Classifies cells as black `O`, yellow `X`, or empty. |
| **Win and draw detection** | Detects wins and draws across all rows, columns, and diagonals. |
| **SO-101 robotic arm control** | Controls the SO-101 robotic arm using the LeRobot framework. |
| **Recorded trajectory playback** | Enables repeatable physical robot movements using recorded trajectories. |
| **Six joint trajectory control** | Controls shoulder, elbow, wrist, and gripper movement across six joints. |
| **20 Hz robot recording and playback** | Provides smooth motion execution through 20 Hz recording and playback. |
| **Interactive board calibration** | Allows selection of the four board corners directly from the camera image. |
| **Live visual feedback** | Displays the camera stream and warped board detector in real time. |
| **Standalone Pygame mode** | Allows testing TicTacToe without the physical robot setup. |
| **Replay, recalibration, and main menu controls** | Provides controls for replaying the game, recalibrating the board, and returning to the main menu. |

---

## Hardware

- SO-101 follower robotic arm
- Camera connected to the host computer
- Physical 3×3 TicTacToe board
- black `O` game pieces
- yellow `X` game pieces
- Computer for vision processing and robot control

The current robot configuration uses the serial port `COM5` and the LeRobot follower ID `my_follower_arm`. These values can be changed in the Python scripts to match the local setup.

---

## Software

- Python 3
- OpenCV (`cv2`) for camera input, calibration, perspective transformation, image processing, board recognition, and the physical-game UI
- NumPy for image and matrix operations
- LeRobot for SO-101 communication and control
- `pyttsx3` for text-to-speech feedback in `main_game.py`
- Python `csv` for trajectory files
- Python `json` for board calibration coordinates
- Python `threading` and `queue` for non-blocking robot execution and speech handling
- Python `math` for Minimax scoring
- Python `random` for the generated fallback background
- `tkinter` for screen-resolution detection when available
- `msvcrt` for non-blocking keyboard input in `record_arm.py`

`record_arm.py` uses `msvcrt`, so that recording utility is intended for Windows.

---

## Dependencies & Setup

### Install Python dependencies

Install the directly imported third-party Python packages:

```bash
pip install numpy opencv-python pyttsx3
```

LeRobot must be installed and configured separately for physical SO-101 control.

`main_game.py` handles a missing LeRobot installation by switching arm playback to a simple simulation mode. However, `move_robot.py` and `record_arm.py` import LeRobot directly and therefore require it to be installed.

### Configure the SO-101 arm

The physical robot scripts currently use:

```python
FOLLOWER_PORT = "COM5"
FOLLOWER_ID = "my_follower_arm"
```

The scripts connect with:

```python
robot.connect(calibrate=False)
```

The SO-101 should therefore already be calibrated before physical playback or recording.

Robot playback enables torque before movement and disables torque again before disconnecting. `record_arm.py` disables torque while recording so the arm can be moved manually.

### Connect the camera

The physical game uses camera index `0`:

```python
CAMERA_INDEX = 0
```

Change this value in `main_game.py` if another camera should be used.

### Optional background GIF

The main interface looks for:

```text
space_bg.gif
```

If the GIF exists and can be opened, it is used as the animated fullscreen background. If it is missing or cannot be opened, the program generates a dark cosmic background with stars instead.

### Calibrate the physical board

Before the first physical game, the program needs the four board corners.

1. Point the camera at the complete board.
2. Select **CALIBRATE BOARD** from the main menu, or start a game when no calibration file exists.
3. Press `SPACE`, `ENTER`, or `C` to capture the current camera frame.
4. Click the four board corners in this order:
   - Top left
   - Top right
   - Bottom right
   - Bottom left
5. Press `SPACE` or `ENTER` after all four points have been selected to confirm them.
6. Press `R` during point selection to clear the selected points and start again.
7. The coordinates are stored in `board_corners.json`.

The saved corners are used to generate a 300 × 300 pixel top-down board image.

### Prepare robot trajectories

Robot positions are stored as CSV-formatted rows inside `.txt` files in:

```text
XO_Positions/
```

To record a new trajectory:

```bash
python record_arm.py
```

`record_arm.py`:

- creates the `XO_Positions` directory if necessary
- asks for a filename
- automatically adds `.txt` when omitted
- overwrites an existing file with the same name
- writes a six-joint CSV header
- disables torque so the arm can be moved manually
- reads the arm at 20 Hz
- automatically saves one position every 0.05 seconds
- exits with `Q` or `Ctrl+C`

The recorded joint order is:

```text
shoulder_pan
shoulder_lift
elbow_flex
wrist_flex
wrist_roll
gripper
```

To replay one recorded file independently:

```bash
python move_robot.py
```

`move_robot.py` asks for a filename, automatically adds `.txt` if needed, looks for the file inside `XO_Positions`, enables torque, replays the recorded positions at 20 Hz, then disables torque and disconnects.

For the physical game, each robot move plays two trajectory files sequentially:

```text
XO_Positions/o_start_pos_<robot_turn_number>.txt
XO_Positions/o_end_pos_<target_cell>.txt
```

`target_cell` is numbered from `1` to `9`.

The current `main_game.py` uses the `o_start_pos_*` and `o_end_pos_*` filename pattern for robot trajectory playback regardless of whether the robot is currently assigned `X` or `O`. This README describes that behavior exactly as implemented.

---

## Vision System

The physical game uses the four calibrated corners to transform the camera image into a square top-down board view.

The 300 × 300 pixel board is divided into nine cells. Only the inner part of each cell is analyzed to reduce interference from grid lines.

Each cell is converted from BGR to HSV color space.

### `X` detection

A yellow mask is used:

```text
Hue:        22–38
Saturation: 70–255
Value:      110–255
```

A cell is accepted as `X` when the yellow region exceeds the configured pixel-ratio threshold and contains a sufficiently large contour.

### `O` detection

`O` detection combines two masks:

**Black / dark mask**

```text
Hue:        0–180
Saturation: 0–255
Value:      0–75
```

**Orangish-grey mask**

```text
Hue:        5–25
Saturation: 20–160
Value:      60–180
```

The two masks are combined before classification.

For both `X` and `O`, the implementation requires:

- detected pixels above 12% of the analyzed cell
- largest accepted contour area above 40 pixels

Morphological opening with a 3 × 3 kernel is used to reduce small visual noise.

If neither piece is detected, the cell is classified as:

```text
empty
```

---

## Game Logic

Both game implementations check the eight standard TicTacToe winning combinations:

```text
Rows:      0-1-2   3-4-5   6-7-8
Columns:   0-3-6   1-4-7   2-5-8
Diagonals: 0-4-8   2-4-6
```

The physical game represents unused cells as `empty`.

After a board check, the physical game returns one of:

```text
WIN
DRAW
ONGOING
```

### Physical-game robot strategy

`main_game.py` uses Minimax to select the robot's best available board position.

If the player chooses to move first:

```text
Player = X
Robot  = O
```

If the player chooses to move second:

```text
Robot  = X
Player = O
```

The physical game therefore preserves the standard rule that `X` moves first.

---

## Physical Game Cycle

The physical game uses a repeating four-phase cycle instead of a fixed number of turns.

### When the player goes first

1. **Player turn**: 8.0 seconds
2. **Board check**: 1.5 seconds
3. **Robot turn**: 13.0 seconds
4. **Board check after robot move**: 1.5 seconds
5. Repeat until the game ends

### When the robot goes first

The game begins directly with the robot-turn phase. The robot is assigned `X`, then the normal cycle continues.

During a robot turn:

1. Minimax selects the best currently empty cell.
2. The target board index is converted to cell numbering `1` through `9`.
3. The program starts a background thread.
4. The thread plays:
   - `o_start_pos_<robot_turn_number>.txt`
   - `o_end_pos_<target_cell>.txt`
5. The camera UI remains responsive while the robot thread runs.
6. The next board-check phase verifies the physical result.

Board recognition is actively refreshed during board-check phases.

The game ends when a win or draw is detected. Text-to-speech announces turns, board checks, and the final result.

---

## Running the Main Game

Start the physical version with:

```bash
python main_game.py
```

The main menu contains:

- **PLAY GAME**
- **CALIBRATE BOARD**
- **QUIT GAME**

Selecting **PLAY GAME** opens a submenu with:

- **PLAY FIRST (PLAYER)**
- **PLAY SECOND (ROBOT)**
- **BACK TO MAIN MENU**

The main game uses a fullscreen OpenCV window titled:

```text
TIC-TAC-TUM
```

### Main Game Controls

| Screen | Key | Action |
| --- | --- | --- |
| Main menu | `Q` or `Esc` | Exit the program |
| Play-mode submenu | `Q` or `Esc` | Return to the main menu |
| Calibration capture | `SPACE`, `ENTER`, or `C` | Freeze the current camera frame |
| Calibration points | `R` | Reset selected corner points |
| Calibration points | `SPACE` or `ENTER` | Confirm after four corners are selected |
| Physical game | `S` | Skip the current timed phase |
| Physical game | `Q` or `Esc` | Return from the game to the menu |

There is no `R` replay shortcut or in-game `C` recalibration shortcut in the current `main_game.py`.

---

---

## Robot Utility Scripts

### `record_arm.py`

Purpose:

- record SO-101 joint positions into `XO_Positions`
- disable torque for manual arm movement
- sample at 20 Hz
- save every 0.05 seconds
- stop with `Q` or `Ctrl+C`

Run:

```bash
python record_arm.py
```

### `move_robot.py`

Purpose:

- select a `.txt` file from `XO_Positions`
- load six joint values from each valid CSV row
- enable robot torque
- replay positions at 20 Hz
- allow interruption with `Ctrl+C`
- disable torque and disconnect after playback

Run:

```bash
python move_robot.py
```

---

## Demo Video

A demonstration of the physical TicTacToe Robot system can be viewed here:

https://youtu.be/q9TCwiyJYFE


---

## Acknowledgements

- Developed as part of the **Embedded Systems, Cyber-Physical Systems and Robotics (INHN0018)** course at the Technical University of Munich (Technische Universität München).
- OpenCV is used for computer vision, calibration, board-state recognition, and the physical-game interface.
- LeRobot is used for SO-101 robotic arm communication and control.
- `pyttsx3` is used for text-to-speech feedback in the physical game.
