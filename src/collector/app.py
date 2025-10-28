"""Main application entry point with camera selection and Gradio UI."""

# IMPORTANT: Set OpenCV environment variables BEFORE importing cv2
import os

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ.setdefault("OPENCV_VIDEOIO_DEBUG", "0")

# IMPORTANT: Clear proxy environment variables BEFORE importing gradio
for proxy_var in [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
]:
    os.environ.pop(proxy_var, None)

from datetime import datetime
from typing import List, Dict, Any
import sys
import cv2 as cv
import numpy as np
import gradio as gr
from rich.console import Console
from rich.prompt import IntPrompt
from rich.panel import Panel
from rich.table import Table
from loguru import logger

from .web_ui import GradioCollectorUI
from .config import AppConfig

console = Console()


class SuppressStderr:
    """Context manager to suppress stderr output."""

    def __enter__(self):
        self._original_stderr = sys.stderr
        sys.stderr = open(os.devnull, "w")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr.close()
        sys.stderr = self._original_stderr


def find_cameras(max_tested: int) -> List[int]:
    """Find available camera devices."""
    available = []
    with SuppressStderr():
        for i in range(max_tested):
            cap = cv.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
    return available


def get_camera_modes(cam_id: int) -> List[Dict[str, Any]]:
    """Get supported camera modes (resolution + FPS)."""
    with SuppressStderr():
        cap = cv.VideoCapture(cam_id)
        cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc(*"MJPG"))
        if not cap.isOpened():
            return []

        # Common resolutions to test
        test_resolutions = [
            (640, 480),
            (800, 600),
            (1280, 720),
            (1920, 1080),
            (2592, 1944),
            (2560, 1440),
            (3840, 2160),
        ]

        # Common FPS values to test
        test_fps = [15, 24, 30, 60]

        modes = []
        seen = set()

        for width, height in test_resolutions:
            cap.set(cv.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv.CAP_PROP_FRAME_HEIGHT, height)

            actual_w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

            if (actual_w, actual_h) == (width, height):
                for fps in test_fps:
                    cap.set(cv.CAP_PROP_FPS, fps)
                    actual_fps = cap.get(cv.CAP_PROP_FPS)

                    mode_key = (actual_w, actual_h, int(actual_fps))
                    if mode_key not in seen:
                        seen.add(mode_key)
                        modes.append(
                            {
                                "width": actual_w,
                                "height": actual_h,
                                "fps": int(actual_fps),
                            }
                        )

        cap.release()

        # Sort by resolution (width * height)
        modes.sort(key=lambda m: (m["width"] * m["height"], m["fps"]))

    return modes


def select_camera(max_devices: int = 10) -> int:
    """Interactive camera selection menu."""
    console.print(Panel.fit("🔍 [bold cyan]ПОИСК ДОСТУПНЫХ КАМЕР...[/bold cyan]"))

    logger.info("Searching for available cameras...")
    cameras = find_cameras(max_devices)

    if not cameras:
        console.print("[bold red]❌ Камеры не найдены![/bold red]")
        logger.error("No cameras found")
        exit(1)

    logger.success(f"Found {len(cameras)} camera(s)")

    table = Table(
        title=f"✓ Найдено камер: {len(cameras)}",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("№", style="cyan", justify="center")
    table.add_column("ID Камеры", style="green")

    for idx, cam_id in enumerate(cameras, 1):
        table.add_row(str(idx), f"Камера {cam_id}")

    console.print(table)

    while True:
        try:
            choice = IntPrompt.ask(
                f"\n[bold yellow]Выберите камеру[/bold yellow]",
                choices=[str(i) for i in range(1, len(cameras) + 1)],
            )
            selected_cam = cameras[choice - 1]
            logger.info(f"Selected camera {selected_cam}")
            return selected_cam
        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]👋 Прервано пользователем[/bold yellow]")
            logger.warning("User interrupted camera selection")
            exit(0)


def select_mode(cam_id: int) -> Dict[str, Any]:
    """Interactive mode selection menu."""
    console.print(
        Panel.fit(f"🎥 [bold cyan]ОПРЕДЕЛЕНИЕ РЕЖИМОВ КАМЕРЫ {cam_id}...[/bold cyan]")
    )

    logger.info(f"Detecting camera modes for camera {cam_id}")
    modes = get_camera_modes(cam_id)

    if not modes:
        console.print("[bold red]❌ Не удалось определить режимы камеры![/bold red]")
        logger.warning("Could not detect camera modes, using default")
        default_mode = {"width": 1280, "height": 720, "fps": 30}
        console.print(
            f"[yellow]Используется режим по умолчанию: {default_mode['width']}x{default_mode['height']} @ {default_mode['fps']} FPS[/yellow]"
        )
        return default_mode

    logger.success(f"Found {len(modes)} mode(s)")

    table = Table(
        title=f"✓ Найдено режимов: {len(modes)}",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("№", style="cyan", justify="center")
    table.add_column("Разрешение", style="green")
    table.add_column("FPS", style="yellow", justify="right")

    for idx, mode in enumerate(modes, 1):
        table.add_row(str(idx), f"{mode['width']}x{mode['height']}", str(mode["fps"]))

    console.print(table)

    while True:
        try:
            choice = IntPrompt.ask(
                f"\n[bold yellow]Выберите режим[/bold yellow]",
                choices=[str(i) for i in range(1, len(modes) + 1)],
            )
            selected_mode = modes[choice - 1]
            logger.info(
                f"Selected mode: {selected_mode['width']}x{selected_mode['height']} @ {selected_mode['fps']} FPS"
            )
            return selected_mode
        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]👋 Прервано пользователем[/bold yellow]")
            logger.warning("User interrupted mode selection")
            exit(0)


def create_gradio_interface(
    ui: GradioCollectorUI, cam_id: int, mode: Dict[str, Any], show_stats: bool = True
) -> gr.Blocks:
    """Create the Gradio interface."""

    # Custom CSS for layout
    custom_css = """
    /* Video output centering */
    #video-output {
        display: flex;
        justify-content: center;
        align-items: flex-start;
    }

    #video-output img {
        max-width: 100%;
        height: auto;
        object-fit: contain;
    }
    """

    with gr.Blocks(
        title="Bottles Classifier Data Collector",
        theme=gr.themes.Soft(),
        css=custom_css,
    ) as demo:
        gr.Markdown("# 🎥 Сборщик данных для классификатора бутылок")

        with gr.Row(equal_height=True):
            # Left column: Video stream
            with gr.Column(scale=2, elem_id="video-container"):
                video_output = gr.Image(
                    label=f"Камера {cam_id} — {mode['width']}x{mode['height']} @ {mode['fps']} FPS",
                    show_label=True,
                    elem_id="video-output",
                    container=True,
                )

                gr.Markdown(
                    """### Советы по съёмке
- Держите объект в центре кадра
- Следите за фокусом и бликами
- Перед сохранением проверьте правильность атрибутов
"""
                )

            # Right column: Controls
            with gr.Column(scale=1, elem_id="controls-container"):
                current_class_state = gr.State(ui.current_class)

                gr.Markdown("## Быстрый старт")
                gr.Markdown(
                    "1. Выберите класс объекта\n"
                    "2. Заполните ключевые атрибуты\n"
                    "3. Нажмите **Сохранить кадр**"
                )

                class_labels = {
                    "PET": "🔵 PET — пластиковая тара",
                    "CAN": "🟢 CAN — алюминиевая банка",
                    "FOREIGN": "🟡 FOREIGN — посторонний объект",
                }

                for class_name in ui.specs.keys():
                    class_labels.setdefault(class_name, class_name)

                class_choices = list(ui.specs.keys())

                class_radio = gr.Radio(
                    choices=class_choices,
                    value=ui.current_class,
                    label="Класс объекта",
                    interactive=True,
                    info="Выбор влияет на состав атрибутов",
                )

                gr.Markdown(
                    "\n".join(f"- {class_labels[name]}" for name in class_choices)
                )

                gr.Markdown("## Атрибуты")

                class_groups = {}
                pending_attribute_handlers = []
                attribute_components_order = []

                for class_name, spec in ui.specs.items():
                    with gr.Group(
                        visible=(class_name == ui.current_class)
                    ) as class_group:
                        for attr in spec["attributes"]:
                            attr_name = attr["name"]
                            attr_label = attr.get("label", attr_name)
                            attr_type = attr["type"]

                            if attr_type == "enum":
                                widget = gr.Radio(
                                    choices=attr["options"],
                                    value=ui.class_attributes[class_name].get(
                                        attr_name,
                                        attr.get("default", attr["options"][0]),
                                    ),
                                    label=attr_label,
                                    interactive=True,
                                )
                            elif attr_type == "bool":
                                widget = gr.Checkbox(
                                    value=ui.class_attributes[class_name].get(
                                        attr_name, attr.get("default", False)
                                    ),
                                    label=attr_label,
                                    interactive=True,
                                )
                            elif attr_type == "text":
                                widget = gr.Textbox(
                                    value=ui.class_attributes[class_name].get(
                                        attr_name, attr.get("default", "")
                                    ),
                                    label=attr_label,
                                    lines=1,
                                    interactive=True,
                                    placeholder="Введите текст...",
                                )
                            else:
                                continue

                            pending_attribute_handlers.append(
                                (widget, class_name, attr_name)
                            )
                            attribute_components_order.append(
                                (class_name, attr_name, widget)
                            )

                        class_groups[class_name] = class_group

                class_group_keys = list(class_groups.keys())
                class_group_list = [class_groups[name] for name in class_group_keys]
                attribute_component_list = [
                    component for (_, _, component) in attribute_components_order
                ]

                reset_button = gr.Button(
                    "↩️ Сбросить атрибуты", variant="secondary", size="sm"
                )

                gr.Markdown("---")

                save_button = gr.Button(
                    "💾 Сохранить кадр", variant="primary", size="lg"
                )
                save_status = gr.Markdown(value="Готово к сохранению")

                for component, class_name, attr_name in pending_attribute_handlers:

                    def make_attr_handler(attribute_name: str, target_class: str):
                        def _handler(value):
                            ui.update_attribute(target_class, attribute_name, value)
                            attr_label = (
                                ui.class_attribute_specs.get(target_class, {})
                                .get(attribute_name, {})
                                .get("label", attribute_name)
                            )
                            message = f"✏️ Изменено: {attr_label} ({class_labels.get(target_class, target_class)})"
                            return message

                        return _handler

                    component.change(
                        make_attr_handler(attr_name, class_name),
                        inputs=[component],
                        outputs=[save_status],
                        queue=False,
                    )

                # Statistics panel (if enabled)
                if show_stats:
                    gr.Markdown("---")
                    statistics_display = gr.Markdown(
                        value=ui.get_statistics(), label="Статистика"
                    )

        # Video streaming using timer
        timer = gr.Timer(value=0.033, active=True)  # ~30 FPS

        def update_video():
            return ui.get_video_frame()

        timer.tick(update_video, outputs=video_output)

        # Class selection
        def on_class_change(new_class):
            ui.update_class(new_class)

            state_update = new_class
            status_message = (
                f"✅ Активный класс: {class_labels.get(new_class, new_class)}"
            )

            group_updates = []
            for idx, name in enumerate(class_group_keys):
                group_updates.append(gr.update(visible=(name == new_class)))

            component_updates = []
            for idx, (class_name, attr_name, _) in enumerate(
                attribute_components_order
            ):
                if class_name == new_class:
                    value = ui.class_attributes[class_name].get(attr_name)
                    component_updates.append(gr.update(value=value))
                else:
                    component_updates.append(gr.update())

            return [state_update, status_message, *group_updates, *component_updates]

        class_radio.change(
            on_class_change,
            inputs=class_radio,
            outputs=[
                current_class_state,
                save_status,
                *class_group_list,
                *attribute_component_list,
            ],
        )

        # Save button
        if show_stats:

            def save_and_update_stats():
                result = ui.save_current_frame()
                stats = ui.get_statistics()
                return result, stats

            save_button.click(
                save_and_update_stats,
                outputs=[save_status, statistics_display],
            )
        else:
            save_button.click(ui.save_current_frame, outputs=save_status)

        def on_reset(class_name):
            ui.reset_attributes(class_name)
            status_message = (
                f"🔄 Атрибуты сброшены для: {class_labels.get(class_name, class_name)}"
            )

            component_updates = []
            for idx, (attr_class, attr_name, _) in enumerate(
                attribute_components_order
            ):
                if attr_class == class_name:
                    value = ui.class_attributes[attr_class].get(attr_name)
                    component_updates.append(gr.update(value=value))
                else:
                    component_updates.append(gr.update())

            return [status_message, *component_updates]

        reset_button.click(
            on_reset,
            inputs=current_class_state,
            outputs=[
                save_status,
                *attribute_component_list,
            ],
            queue=False,
        )

    return demo


def main():
    # Load configuration
    config = AppConfig.load()

    # Update OpenCV warning suppression based on config
    if config.suppress_camera_warnings:
        os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

    # Configure logger
    logger.remove()  # Remove default handler
    logger.add(
        lambda msg: console.print(msg, end=""),
        format=config.log_format,
        level=config.log_level,
    )

    logger.info(f"Starting {config.app_title} v{config.app_version}")

    # Interactive camera selection
    cam_id = select_camera(config.max_camera_devices)

    # Interactive mode selection
    mode = select_mode(cam_id)

    # Display startup configuration
    config_table = Table(
        title="⚙️  Конфигурация сборщика", show_header=True, header_style="bold cyan"
    )
    config_table.add_column("Параметр", style="magenta")
    config_table.add_column("Значение", style="green")

    config_table.add_row("📷 Камера", str(cam_id))
    config_table.add_row("🎥 Разрешение", f"{mode['width']}x{mode['height']}")
    config_table.add_row("⚡ FPS", str(mode["fps"]))
    config_table.add_row("💾 Директория", config.output_dir)

    console.print()
    console.print(
        Panel(
            config_table,
            title="[bold green]ЗАПУСК СБОРЩИКА ДАННЫХ[/bold green]",
            border_style="green",
        )
    )
    console.print()

    # Initialize UI
    ui = GradioCollectorUI(
        config.pet_spec, config.can_spec, config.foreign_spec, config.output_dir, config
    )

    # Setup camera
    if not ui.setup_camera(cam_id, mode["width"], mode["height"], mode["fps"]):
        console.print("[bold red]❌ Не удалось инициализировать камеру[/bold red]")
        return

    # Create and launch Gradio interface
    demo = create_gradio_interface(ui, cam_id, mode, config.show_statistics)

    try:
        logger.info("Launching Gradio interface...")

        demo.queue()  # Enable queue for better stability
        demo.launch(
            server_name=config.server_host,
            server_port=config.server_port,
            share=False,
            inbrowser=config.auto_open_browser,
            show_error=True,
            prevent_thread_lock=False,  # Block until closed
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error launching Gradio: {e}")
        console.print(f"[bold red]❌ Ошибка запуска: {e}[/bold red]")
    finally:
        ui.cleanup()
        logger.success("Data collector stopped successfully")


if __name__ == "__main__":
    main()
