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

## Generating Statistics

To analyze collected data, run the statistics generator:

```bash
python3 generate_stats.py
```

This creates/updates `STATS.md` with tables showing:
- Records count per `container_name` for each class
- Attribute value distributions for each container type
- Overall statistics across all attributes

The file is auto-generated and listed in `.gitignore`.

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

Attribute specifications are loaded from YAML files in `states/` directory, which define:
- `enum` attributes: Radio button selection (e.g., "deformation", "fill", "volume", "neck_direction")
- `bool` attributes: Checkbox toggles (e.g., "wet", "condensate", "cap_present", "glare", "shadow")
- `text` attributes: Text input fields (e.g., "container_name") with full Unicode support

**Current attribute counts:**
- PET: 13 attributes (deformation, fill, transparency, label, position, neck_direction, cap_present, wet, condensate, glare, shadow, volume, container_name)
- CAN: 11 attributes (deformation, fill, finish, label, position, wet, condensate, glare, shadow, volume, container_name)
- FOREIGN: 9 attributes (subtype, is_container, material, multiple_items, reason, position, wet, volume, container_name)

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

The UI uses Gradio's native widget system:
- `class_radio`: Class selection (PET/CAN/FOREIGN) - gr.Radio
- `attr_enum`: Enumerated attribute selection - gr.Radio
- `attr_bool`: Boolean attribute toggle - gr.Checkbox
- `attr_text`: Text input fields - gr.Textbox (supports full Unicode/Cyrillic)
- `save`, `quit`: Action buttons - gr.Button

Widget events are handled via Gradio's `.change()` and `.click()` callbacks. All attribute changes are immediately synchronized to internal state.

## Dataset Output Structure

```
dataset/
├── images/
│   └── YYYYMMDD_HHMMSS_ffffff.jpg
├── meta/
│   └── YYYYMMDD_HHMMSS_ffffff.json
├── pet.csv      # Auto-generated for PET class
├── can.csv      # Auto-generated for CAN class
└── foreign.csv  # Auto-generated for FOREIGN class
```

Metadata includes timestamp, class, attributes, camera settings, and image filename.

## CSV Export System

The application uses a simple class-based CSV export system:

1. **Auto-export on save** (`io_utils.py:append_to_class_csv()`):
   - Automatically appends each saved frame to the appropriate class CSV
   - Creates `pet.csv`, `can.csv`, or `foreign.csv` with headers if not exists
   - Immediate availability for analysis without manual export
   - Statistics loaded from these files on startup

2. **Manual full export** (`export.py:export_all_sessions_to_csv()`):
   - Available for batch export of all historical data
   - Creates timestamped file with all sessions aggregated
   - Useful for creating complete dataset snapshots

CSV features:
- Boolean values converted to "да"/"нет" for readability
- UTF-8 with BOM encoding for Excel compatibility
- Configurable delimiter and timestamp inclusion via `config.yaml`
- Direct attribute columns (no `attr_` prefix in class-based CSVs)

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
- Dynamic widget generation based on YAML specifications
- Gradio launches on `http://127.0.0.1:7860` with auto-open browser

## Important Implementation Details

### Image Format Handling

**Critical**: The application maintains BGR format from camera throughout the pipeline:
- Frames are captured in BGR format from OpenCV
- BGR frames are stored in `self.current_frame` without conversion
- Only converted to RGB for Gradio display in `get_video_frame()`
- **Images are saved in BGR format** via `cv.imwrite()` in `io_utils.py:save_sample()`

This ensures correct color representation in saved images and avoids unnecessary conversions.

### Configuration System

The `AppConfig` dataclass uses a fallback pattern:
- Attempts to load `config.yaml` with structured parsing
- Falls back to defaults if file missing or invalid
- Supports nested YAML structure with clear hierarchy
- Logger warnings for missing config, not errors

### Attribute Specification Loading

The `load_class_spec()` function in `config.py` implements a flexible loading strategy:
1. Try YAML with `.yaml` extension first
2. Fallback to JSON with `.json` extension (legacy support)
3. Try exact path with extension detection
4. Raise `FileNotFoundError` only if all attempts fail

**Note**: JSON specifications have been removed. All classes now use YAML format exclusively (pet.yaml, can.yaml, foreign.yaml).

### Statistics Panel

Statistics are tracked in `GradioCollectorUI.statistics` dictionary and updated via:
- Increment counters in `save_current_frame()` after successful save
- Format display string in `get_statistics()` method
- Auto-update in UI via Gradio's output binding when `show_statistics=True`

### Video Frame Updates

The Gradio interface uses `gr.Timer` for video streaming:
- Timer set to 0.033s (~30 FPS) in `create_gradio_interface()`
- Each tick calls `update_video()` which returns `ui.get_video_frame()`
- Frame capture and display are decoupled from save operations
- Placeholder image shown if camera unavailable

## Extending the Application

### Adding New Attributes

1. Edit the relevant YAML file in `states/` (pet.yaml, can.yaml, or foreign.yaml)
2. Add new attribute definition:
   ```yaml
   - name: new_attribute
     label: Название атрибута
     type: enum  # or bool, text
     options:  # only for enum
       - option1
       - option2
     default: option1
   ```
3. No code changes required - UI will auto-generate widgets

### Adding New Classes

1. Create new YAML specification file in `states/`
2. Update `config.yaml` to reference new spec file
3. Update `specs_and_defaults()` in `collector.py` to include new class
4. Update class radio choices in `create_gradio_interface()` in `app.py`

### Customizing Export Format

Edit `config.yaml`:
```yaml
export:
  csv:
    delimiter: ";"  # Change to semicolon
    encoding: "utf-8"  # Remove BOM
    include_timestamp: false  # Hide timestamps
```
