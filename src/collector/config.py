"""
Configuration management for the collector application.
"""
import yaml
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class AppConfig:
    """Application configuration loaded from config.yaml"""

    # Paths
    config_path: Path = field(default_factory=lambda: Path("config.yaml"))

    # Application settings
    app_title: str = "Сборщик данных для классификатора бутылок"
    app_version: str = "2.0.0"

    # Server settings
    server_host: str = "127.0.0.1"
    server_port: int = 7860
    auto_open_browser: bool = True

    # Camera settings
    max_camera_devices: int = 10
    suppress_camera_warnings: bool = True

    # Data collection
    output_dir: str = "dataset"
    image_format: str = "jpg"
    image_quality: int = 95

    # Class specifications
    pet_spec: str = "states/pet.yaml"
    can_spec: str = "states/can.yaml"
    foreign_spec: str = "states/foreign.yaml"

    # UI settings
    ui_theme: str = "soft"
    video_update_interval: float = 0.033
    attributes_max_height: str = "70vh"
    show_statistics: bool = True

    # Font
    font_path: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_fallback: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: str = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"

    # Export
    csv_delimiter: str = ","
    csv_encoding: str = "utf-8-sig"
    csv_include_timestamp: bool = True

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "AppConfig":
        """Load configuration from YAML file."""
        path = Path(config_path)

        if not path.exists():
            logger.warning(f"Config file not found: {path}, using defaults")
            return cls()

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            config = cls(config_path=path)

            # Parse and set values
            if 'app' in data:
                config.app_title = data['app'].get('title', config.app_title)
                config.app_version = data['app'].get('version', config.app_version)

            if 'server' in data:
                config.server_host = data['server'].get('host', config.server_host)
                config.server_port = data['server'].get('port', config.server_port)
                config.auto_open_browser = data['server'].get('auto_open_browser', config.auto_open_browser)

            if 'camera' in data:
                config.max_camera_devices = data['camera'].get('max_devices', config.max_camera_devices)
                config.suppress_camera_warnings = data['camera'].get('suppress_warnings', config.suppress_camera_warnings)

            if 'data' in data:
                config.output_dir = data['data'].get('output_dir', config.output_dir)
                if 'image' in data['data']:
                    config.image_format = data['data']['image'].get('format', config.image_format)
                    config.image_quality = data['data']['image'].get('quality', config.image_quality)

            if 'classes' in data:
                config.pet_spec = data['classes'].get('pet', config.pet_spec)
                config.can_spec = data['classes'].get('can', config.can_spec)
                config.foreign_spec = data['classes'].get('foreign', config.foreign_spec)

            if 'ui' in data:
                config.ui_theme = data['ui'].get('theme', config.ui_theme)
                if 'video' in data['ui']:
                    config.video_update_interval = data['ui']['video'].get('update_interval', config.video_update_interval)
                if 'attributes' in data['ui']:
                    config.attributes_max_height = data['ui']['attributes'].get('max_height', config.attributes_max_height)
                if 'statistics' in data['ui']:
                    config.show_statistics = data['ui']['statistics'].get('show', config.show_statistics)

            if 'font' in data:
                config.font_path = data['font'].get('path', config.font_path)
                config.font_fallback = data['font'].get('fallback', config.font_fallback)

            if 'logging' in data:
                config.log_level = data['logging'].get('level', config.log_level)
                config.log_format = data['logging'].get('format', config.log_format)

            if 'export' in data and 'csv' in data['export']:
                config.csv_delimiter = data['export']['csv'].get('delimiter', config.csv_delimiter)
                config.csv_encoding = data['export']['csv'].get('encoding', config.csv_encoding)
                config.csv_include_timestamp = data['export']['csv'].get('include_timestamp', config.csv_include_timestamp)

            logger.info(f"Configuration loaded from {path}")
            return config

        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            return cls()


def load_class_spec(path: str) -> Dict[str, Any]:
    """Load class specification from YAML file."""
    spec_path = Path(path)

    # Try YAML first
    if spec_path.with_suffix('.yaml').exists():
        with open(spec_path.with_suffix('.yaml'), 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    # Fallback to JSON if YAML doesn't exist
    elif spec_path.with_suffix('.json').exists():
        import json
        with open(spec_path.with_suffix('.json'), 'r', encoding='utf-8') as f:
            return json.load(f)

    # Try exact path
    elif spec_path.exists():
        ext = spec_path.suffix.lower()
        with open(spec_path, 'r', encoding='utf-8') as f:
            if ext in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            else:
                import json
                return json.load(f)

    else:
        raise FileNotFoundError(f"Class specification not found: {path}")
