# TicTacToe Robot

TicTacToe Robot is a cyber physical system that combines computer vision, game logic, and an **SO-101 robotic arm. A camera observes a physical 3×3 board, OpenCV detects the placed pieces, and the software checks the current game state**. During robot turns, the arm executes recorded joint trajectories to physically place a game piece **(X and O)** on the board.

The project also includes a standalone Pygame version called **Tic Tac Clash**, which allows the game interface and logic to be tested without the physical robot or camera.

The project transforms a simple TicTacToe game to allow software to  interact directly with the physical world. Instead of playing only on a screen, the system combines visual perception, board state recognition, game logic, and robotic movement.

The main goal is to demonstrate how a camera and robotic arm can work together in a closed interaction loop:

**Player move → Camera detection → Game state evaluation → Robot movement → Camera verification**

---

## Table of Contents
* [TicTacToe Robot](#tictactoe-robot)
* [Project Structure](#project-structure)
* [Features](#features)
* [Hardware](#hardware)
* [Software](#software)
* [Dependencies & Setup](#dependencies--setup)
    * [Install Python dependencies](#install-python-dependencies)
    * [Configure the SO-101 arm](#configure-the-so-101-arm)
    * [Connect the camera](#connect-the-camera)
    * [Calibrate the physical board](#calibrate-the-physical-board)
    * [Prepare robot trajectories](#prepare-robot-trajectories)
* [Vision System](#vision-system)
* [Game Logic](#game-logic)
* [Physical Game Sequence](#physical-game-sequence)
* [Running the Main Game](#running-the-main-game)
    * [Controls](#controls)
* [Acknowledgements](#acknowledgements)

---

## Project Structure

The project is organized into Python source files for the game, robot control, and trajectory recording, along with recorded robot trajectories stored as text files.

```text
.
├── Python
│   ├── cps_maingame.py
│   ├── cps_maingameoffline.py
│   ├── cps_moverobot.py
│   └── cps_recordarm.py
├── README.md
└── Txt
    ├── cps_o_pos4.txt
    ├── cps_o_pos5.txt
    ├── cps_x_pos1.txt
    ├── cps_x_pos2.txt
    └── cps_x_pos3.txt
```

| File | Purpose |
| --- | --- |
| `cps_maingame.py` | Main physical TicTacToe application combining camera vision, board detection, game logic, UI, and robot trajectory execution. |
| `cps_maingameoffline.py` | Standalone Pygame implementation for testing the game interface and logic without a camera or robot. |
| `cps_recordarm.py` | Places the SO-101 arm in freemove mode and records all six joint positions every 0.05 seconds. |
| `cps_moverobot.py` | Loads a recorded trajectory from a `.txt` file and replays it on the SO-101 arm at 20 Hz. |
| `cps_x_pos1.txt` | Recorded SO-101 trajectory for an `X` placement sequence. |
| `cps_x_pos2.txt` | Recorded SO-101 trajectory for an `X` placement sequence. |
| `cps_x_pos3.txt` | Recorded SO-101 trajectory for an `X` placement sequence. |
| `cps_o_pos4.txt` | Recorded SO-101 trajectory used by the main game for an `O` placement. |
| `cps_o_pos5.txt` | Recorded SO-101 trajectory used by the main game for an `O` placement. |


---

## Features
| Feature | Description |
|---|---|
| **Live board detection** | Using a camera and OpenCV. |
| **Perspective correction** | Transforms the detected board into a normalized 300 × 300 pixel view. |
| **Automatic cell classification** | Classifies cells as white `O`, black `X`, or empty. |
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
- White `O` game pieces
- Black `X` game pieces
- Computer for vision processing and robot control

The current robot configuration uses the serial port `COM5` and the LeRobot follower ID `my_follower_arm`. These values can be changed in the Python scripts to match the local setup.

---

## Software

- Python 3
- OpenCV (`cv2`) for camera input, calibration, perspective transformation, image processing, and board detection
- NumPy for image and matrix operations
- LeRobot for SO 101 robotic arm communication and control
- Pygame for the standalone TicTacToe interface
- Python `csv` for robot trajectory files
- Python `threading` for non blocking robot execution during the live camera loop
- Python `json` for storing board calibration coordinates
- `msvcrt` for keyboard input in the Windows robot recording utility

---

## Dependencies & Setup

### Install Python dependencies

The project requires the Python packages used by the scripts:

```bash
pip install numpy opencv-python pygame
```

LeRobot must also be installed and configured separately so that the following imports are available:

```python
from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
```

### Configure the SO-101 arm

The robot scripts currently use:

```python
FOLLOWER_PORT = "COM5"
FOLLOWER_ID = "my_follower_arm"
```

Update these values if the arm is connected through a different serial port or uses a different calibration ID.

The robot should already be calibrated before starting the game because the scripts connect using:

```python
robot.connect(calibrate=False)
```

### Connect the camera

The main game currently uses camera index `0`:

```python
CAMERA_INDEX = 0
```

If another camera is being used, change this value in `cps_maingame.py`.

### Calibrate the physical board

Before the first game, the program needs the position of the physical TicTacToe board.

1. Point the camera at the complete board.
2. Start calibration from the main menu.
3. Press `SPACE`, `ENTER`, or `C` to capture the camera frame.
4. Click the four corners in this exact order:
   - Top left
   - Top right
   - Bottom right
   - Bottom left
5. Press `Q` after all four points have been selected.
6. The coordinates are saved automatically to `board_corners.json`.

The calibration is then used to calculate a perspective transformation and generate a square 300 × 300 pixel board image for cell recognition.

### Prepare robot trajectories

Robot moves are stored as recorded joint position sequences. To create a new trajectory, run:

```bash
python cps_recordarm.py
```

The script disables motor torque so the arm can be moved manually. It then records the six joint values every `0.05` seconds and saves them as CSV data inside a `.txt` file.

To test a recorded trajectory independently, run:

```bash
python cps_moverobot.py
```

Enter the trajectory filename when prompted. The arm enables torque, executes the recorded positions at 20 Hz, disables torque, and disconnects when finished.

---

## Vision System

The live game first uses the four calibrated corners to transform the camera image into a top down square view of the board.

The transformed board is split into nine cells. To reduce interference from the grid lines, only the inner region of each cell is analyzed.

Each cell is converted from BGR to HSV color space and classified using color thresholds:

- A sufficiently large **white region** is classified as `O`.
- A sufficiently large **black region** is classified as `X`.
- If neither threshold is reached, the cell is classified as `empty`.

Morphological filtering and contour area checks are used to reduce small visual noise before a symbol is accepted.

---

## Game Logic

The game checks the eight standard TicTacToe winning combinations:

```text
Rows:      0-1-2   3-4-5   6-7-8
Columns:   0-3-6   1-4-7   2-5-8
Diagonals: 0-4-8   2-4-6
```

After each board check phase, the program returns one of three states:

- `WIN`
- `DRAW`
- `ONGOING`

When a winner is detected, the corresponding winning cells are highlighted in the visual interface.

---

## Physical Game Sequence

The current physical demonstration in `cps_maingame.py` uses a timed sequence of player turns, board checks, and prerecorded robot actions:

1. Player turn: 10 seconds
2. Check board: 3 seconds
3. Robot executes `cps_o_pos4.txt`: 20 seconds
4. Check board: 3 seconds
5. Player turn: 10 seconds
6. Check board: 3 seconds
7. Robot executes `cps_o_pos5.txt`: 20 seconds
8. Check board: 3 seconds
9. Player turn: 10 seconds
10. Final board check: 3 seconds

The robot trajectory runs in a separate thread so the camera feed and user interface remain responsive while the arm is moving.

---

## Running the Main Game

Start the physical version with:

```bash
python cps_maingame.py
```

The main menu provides three options:

- **START GAME**
- **RECALIBRATE BOARD**
- **EXIT**

### Controls

| Key | Action |
| --- | --- |
| `S` | Skip the current timed step |
| `C` | Recalibrate the board during the game |
| `R` | Replay after the game has ended |
| `Q` | Return to the menu or exit the current screen |

---

## Acknowledgements

- Developed as part of the **Embedded Systems, Cyber-Physical Systems and Robotics (INHN0018)** course at the Technical University of Munich (Technische Universität München).
- Built using OpenCV for computer vision and board-state recognition.
- Built using the LeRobot framework for SO-101 robotic arm control.
- Pygame is used for the standalone TicTacToe interface.