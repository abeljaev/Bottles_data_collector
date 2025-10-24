# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a data collection tool for a bottles classifier with a **Gradio web interface**. It captures images from a camera and annotates them with class labels (PET, CAN, FOREIGN) and detailed attributes in Russian. The web UI displays a live camera feed on the left and an interactive control panel (with native HTML widgets) on the right, all rendered in a web browser.

## Installation and Setup

```bash
cd collector
uv sync  # Creates .venv and installs dependencies
```

## Running the Application

```bash
uv run collector  # or just: collector
```

The application uses an interactive menu system:
1. Automatically detects available cameras and prompts for selection
2. Probes camera capabilities and displays available modes (resolution + FPS)
3. Launches the data collector with selected configuration

Configuration is loaded from `config.yaml` in project root:
- Application settings (title, version, server host/port)
- Camera settings (max devices to probe, warning suppression)
- Class specification file paths (YAML files in `states/`)
- UI settings (theme, statistics display, scrolling)
- Export settings (CSV delimiter, encoding, timestamp inclusion)

## Architecture

### Module Structure

The codebase is organized into focused modules within `src/collector/`:

- `app.py`: Main entry point with interactive CLI setup (camera/mode selection using rich) and Gradio web interface initialization. Launches web server on http://127.0.0.1:7860
- `web_ui.py`: **Gradio web interface** - GradioCollectorUI class that manages camera, state, statistics tracking, and provides methods for building widgets, saving frames, and exporting data
- `collector.py`: State management (`AppState` dataclass) and YAML/JSON attribute specification loading
- `config.py`: Configuration management with `AppConfig` dataclass and `load_class_spec()` function for loading YAML/JSON specs
- `export.py`: CSV export functionality - export session or all sessions to CSV with configurable encoding and formatting
- `io_utils.py`: File I/O utilities for creating session directories and saving image/metadata pairs
- ~~`ui.py`~~: Legacy OpenCV UI (no longer used, replaced by Gradio)

### Dependencies

- **`gradio>=4.0`**: Web UI framework - provides native HTML widgets, video streaming, and full Cyrillic support
- `opencv-python`: Camera capture
- `Pillow`: Image processing
- `rich`: Beautiful terminal UI for CLI setup (tables, panels, prompts)
- `loguru`: Structured logging
- `pyyaml>=6.0`: YAML configuration file parsing
- `pandas>=2.0`: CSV export functionality

### State Management

The `AppState` dataclass (in `collector.py`) tracks:
- `current_class`: Active class (PET/CAN/FOREIGN)
- `attrs`: Dictionary of current attribute values for the selected class
- `save_requested`, `quit_requested`: UI action flags
- `active_text_field`: Name of currently active text field for editing
- `text_input_buffer`: Temporary buffer for text input

Attribute specifications are loaded from YAML files in `states/` directory (with JSON fallback support), which define:
- `enum` attributes: Radio button selection (e.g., "deformation", "fill", "volume")
- `bool` attributes: Checkbox toggles (e.g., "wet", "condensate", "shadow")
- `text` attributes: Text input fields (e.g., "container_name") with full Unicode support

Statistics tracking:
- Real-time counters for saved frames per class (PET, CAN, FOREIGN)
- Total frame counter
- Updates automatically on each save
- Display can be toggled via `config.yaml`

### Data Flow

1. App loads configuration from `config.yaml` (or uses defaults if not found)
2. App loads three YAML specification files (one per class) at startup
3. Gradio interface captures camera frames at ~30 FPS and displays in browser
4. User interactions with web UI widgets update internal state
5. On save action:
   - Captures current frame + metadata as JPEG + JSON in timestamped session directory
   - Updates statistics counters
   - Displays save confirmation
6. On export action:
   - Scans session directory for JSON metadata files
   - Flattens data structure and creates pandas DataFrame
   - Exports to CSV with configurable encoding (UTF-8 with BOM for Excel compatibility)

### UI Widget System

The UI uses a custom widget system (`Widget` dataclass in `ui.py`) with clickable regions:
- `class_radio`: Class selection (PET/CAN/FOREIGN)
- `attr_enum`: Enumerated attribute selection (radio buttons)
- `attr_bool`: Boolean attribute toggle (checkboxes)
- `attr_text`: Text input fields (click to activate, supports ASCII text input with Backspace, Enter to confirm, ESC to cancel)
- `save`, `quit`: Action buttons

Mouse events are mapped to widget bounding boxes to handle interactions. Text fields show active state with green highlight and cursor when clicked.

### Keyboard Shortcuts

- `1/2/3`: Switch to PET/CAN/FOREIGN class
- `s`: Save current frame with metadata
- `q` or `Esc`: Quit application

## Dataset Output Structure

```
dataset/
└── YYYYMMDD/
    └── session_NN/
        ├── images/
        │   └── YYYYMMDD_HHMMSS_ffffff.jpg
        └── meta/
            └── YYYYMMDD_HHMMSS_ffffff.json
```

Metadata includes timestamp, class, attributes, camera settings, and session directory path.

## Cyrillic Text Rendering

The application uses PIL (Pillow) for rendering Russian text with TrueType fonts. The font path is hardcoded to `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`. The `put_text()` function in `ui.py` handles font rendering and falls back to OpenCV's built-in font if the font file is not found.

## Interactive Camera Setup

The `find_cameras()` function probes camera devices 0-9 to detect available cameras. The `get_camera_modes()` function tests common resolutions (640x480 up to 4K) and frame rates (15, 24, 30, 60 FPS) to determine supported modes. This information is presented in interactive rich-formatted tables for user selection.

## Major Update: Gradio Web Interface

### Migrated from OpenCV to Gradio

**Previous**: OpenCV-based UI with custom drawing (rectangles, circles, PIL text rendering)
**Current**: Full Gradio web interface in browser

### Benefits:

1. **100% Cyrillic Support**: Native HTML text rendering - no font path issues
2. **Professional UI**: Real HTML widgets (radio buttons, checkboxes, text inputs)
3. **No Font Configuration**: Browser handles all text rendering automatically
4. **Responsive Design**: All attributes fit automatically with native scrolling
5. **Cross-Platform**: Works on any device with a browser
6. **Easy to Extend**: Adding new widgets is trivial with Gradio's API

### Technical Details:

- Video streaming via `gr.Timer` (~30 FPS refresh)
- State management in `GradioCollectorUI` class
- Dynamic widget generation based on JSON specifications
- Gradio launches on `http://127.0.0.1:7860` with auto-open browser

### Features:

1. **Text Input Fields**: Native HTML `<input>` elements with full Unicode support
2. **Volume and Container Name**: All three classes (PET, CAN, FOREIGN) include:
   - `volume` (enum): Radio buttons for predefined options
   - `container_name` (text): Text input field
3. **Rich CLI**: Terminal UI for camera/mode selection only
4. **Statistics Panel**: Real-time display of saved frame counts by class
5. **CSV Export**:
   - Export current session metadata to CSV
   - Export all sessions to a single CSV file
   - Boolean values converted to "да"/"нет" for readability
   - UTF-8 with BOM encoding for Excel compatibility
6. **YAML Configuration**: All settings in `config.yaml` with sensible defaults