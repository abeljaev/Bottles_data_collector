#!/usr/bin/env python3
"""
Генератор статистики по собранному датасету.
Создает файл STATS.md с таблицами статистики по каждому классу.
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def load_csv_safe(csv_path: Path, encoding='utf-8-sig'):
    """Безопасная загрузка CSV с обработкой отсутствующих файлов."""
    if not csv_path.exists():
        return None
    try:
        return pd.read_csv(csv_path, encoding=encoding)
    except Exception as e:
        print(f"⚠️  Ошибка чтения {csv_path.name}: {e}")
        return None


def generate_class_stats(df, class_name, attributes_to_track):
    """
    Генерирует статистику по классу.

    Args:
        df: DataFrame с данными класса
        class_name: Название класса
        attributes_to_track: Список атрибутов для отслеживания

    Returns:
        str: Markdown таблица со статистикой
    """
    if df is None or df.empty:
        return f"## {class_name}\n\n*Нет данных*\n\n"

    # Группировка по container_name
    grouped = df.groupby('container_name', dropna=False)

    # Заменяем NaN на пустую строку для container_name
    df_filled = df.copy()
    df_filled['container_name'] = df_filled['container_name'].fillna('(не указано)')
    grouped = df_filled.groupby('container_name')

    stats_lines = [f"## {class_name}\n"]
    stats_lines.append(f"**Всего записей:** {len(df)}\n")
    stats_lines.append(f"**Уникальных тар:** {len(grouped)}\n")

    # Таблица: container_name -> количество по каждому атрибуту
    table_lines = ["| Название тары | Всего |"]

    # Добавляем заголовки для каждого атрибута
    for attr in attributes_to_track:
        if attr in df.columns:
            table_lines[0] += f" {attr} |"

    # Разделитель таблицы
    separator = "|" + "-" * 15 + "|" + "-" * 7 + "|"
    for attr in attributes_to_track:
        if attr in df.columns:
            separator += "-" * (len(attr) + 2) + "|"
    table_lines.append(separator)

    # Данные по каждому container_name
    for name, group in grouped:
        row = f"| {name} | {len(group)} |"

        for attr in attributes_to_track:
            if attr in df.columns:
                # Подсчет уникальных значений атрибута
                value_counts = group[attr].value_counts().to_dict()
                # Форматируем как "значение: кол-во"
                if len(value_counts) == 0:
                    cell_content = "-"
                elif len(value_counts) == 1:
                    val, count = list(value_counts.items())[0]
                    cell_content = f"{val}" if count == len(group) else f"{val}:{count}"
                else:
                    # Несколько значений - показываем все
                    parts = [f"{val}:{cnt}" for val, cnt in sorted(value_counts.items(), key=lambda x: -x[1])]
                    cell_content = ", ".join(parts)
                row += f" {cell_content} |"

        table_lines.append(row)

    stats_lines.extend(table_lines)
    stats_lines.append("\n")

    # Дополнительная статистика по атрибутам
    stats_lines.append("### Детальная статистика по атрибутам\n")

    for attr in attributes_to_track:
        if attr in df.columns:
            value_counts = df[attr].value_counts()
            if not value_counts.empty:
                stats_lines.append(f"**{attr}:**")
                for val, count in value_counts.items():
                    percentage = (count / len(df)) * 100
                    stats_lines.append(f"  - {val}: {count} ({percentage:.1f}%)")
                stats_lines.append("")

    return "\n".join(stats_lines)


def main():
    """Основная функция генерации статистики."""

    dataset_dir = Path("dataset")
    stats_file = Path("STATS.md")

    print("📊 Генерация статистики датасета...")

    # Загрузка CSV файлов
    pet_df = load_csv_safe(dataset_dir / "pet.csv")
    can_df = load_csv_safe(dataset_dir / "can.csv")
    foreign_df = load_csv_safe(dataset_dir / "foreign.csv")

    # Определяем атрибуты для отслеживания по каждому классу
    # Порядок атрибутов соответствует важности для анализа
    pet_attrs = ['deformation', 'fill', 'transparency', 'label', 'volume', 'wet', 'condensate', 'glare', 'dirt']
    can_attrs = ['deformation', 'fill', 'finish', 'decoration', 'volume', 'wet', 'glare', 'label_attached', 'dirt']
    foreign_attrs = ['subtype', 'is_container', 'material', 'multiple_items']

    # Генерация markdown
    output = []
    output.append("# 📊 Статистика датасета\n")
    output.append(f"*Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    output.append("---\n")

    # PET статистика
    if pet_df is not None:
        print(f"  ✓ PET: {len(pet_df)} записей")
        output.append(generate_class_stats(pet_df, "PET — Пластиковые бутылки", pet_attrs))
    else:
        print("  - PET: нет данных")
        output.append("## PET — Пластиковые бутылки\n\n*Нет данных*\n\n")

    output.append("---\n")

    # CAN статистика
    if can_df is not None:
        print(f"  ✓ CAN: {len(can_df)} записей")
        output.append(generate_class_stats(can_df, "CAN — Алюминиевые банки", can_attrs))
    else:
        print("  - CAN: нет данных")
        output.append("## CAN — Алюминиевые банки\n\n*Нет данных*\n\n")

    output.append("---\n")

    # FOREIGN статистика
    if foreign_df is not None:
        print(f"  ✓ FOREIGN: {len(foreign_df)} записей")
        output.append(generate_class_stats(foreign_df, "FOREIGN — Посторонние объекты", foreign_attrs))
    else:
        print("  - FOREIGN: нет данных")
        output.append("## FOREIGN — Посторонние объекты\n\n*Нет данных*\n\n")

    # Сохранение в файл
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("".join(output))

    print(f"\n✅ Статистика сохранена в {stats_file}")


if __name__ == "__main__":
    main()
