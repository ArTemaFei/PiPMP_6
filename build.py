"""
Скрипт автоматической сборки приложения.
Вариант 4: Оптимизация размера дистрибутива.

Собирает приложение ДВА раза:
  1. "Базовая" сборка — без исключений, без UPX.
  2. "Оптимизированная" сборка — с excludes и (опционально) с UPX.
После этого сравнивает размеры получившихся файлов.
"""

import os
import shutil
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("Нужен PyYAML: pip install PyYAML")
    sys.exit(1)

CONFIG_PATH = "build_config.yaml"
DIST_DIR = "dist"
BUILD_DIR = "build"


def load_config(path: str = CONFIG_PATH) -> dict:
    """Загрузить конфигурацию сборки из YAML-файла."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_build_command(config: dict, optimized: bool, output_name: str) -> list:
    """Сформировать команду PyInstaller в виде списка аргументов."""
    entry_point = config["entry_point"]
    options = config.get("build_options", {})
    deps = config.get("dependencies", {})
    upx_cfg = config.get("upx", {})

    # Используем "python -m PyInstaller" — надёжнее, чем вызов pyinstaller напрямую
    # (особенно из виртуального окружения).
    command = [sys.executable, "-m", "PyInstaller"]

    if options.get("onefile", True):
        command.append("--onefile")
    if options.get("windowed", True):
        command.append("--windowed")

    icon_path = options.get("icon")
    if icon_path and os.path.isfile(icon_path):
        command.extend(["--icon", icon_path])

    # Скрытые импорты нужны всегда — без них будет ModuleNotFoundError
    for module in deps.get("hidden_imports", []):
        command.extend(["--hidden-import", module])

    if optimized:
        # Исключаем лишние модули только в оптимизированной сборке
        for module in deps.get("excludes", []):
            command.extend(["--exclude-module", module])

        if upx_cfg.get("enabled", False):
            upx_dir = upx_cfg.get("dir")
            if upx_dir:
                command.extend(["--upx-dir", upx_dir])
            # Если upx_dir пуст, PyInstaller попробует найти upx в PATH сам
        else:
            command.append("--noupx")
    else:
        # В базовой сборке UPX принципиально не используем —
        # нужна точка сравнения "как есть"
        command.append("--noupx")

    command.extend(["--name", output_name])
    command.append(entry_point)

    return command


def run_build(config: dict, optimized: bool) -> str:
    """Запустить сборку (базовую или оптимизированную). Возвращает имя exe без расширения."""
    suffix = "_optimized" if optimized else "_base"
    output_name = config["project_name"] + suffix

    command = get_build_command(config, optimized, output_name)

    label = "ОПТИМИЗИРОВАННАЯ" if optimized else "БАЗОВАЯ"
    print(f"\n=== Сборка ({label}) ===")
    print("Команда:", " ".join(command))

    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        print("Ошибка: PyInstaller не найден. Установите его: pip install pyinstaller")
        return None

    if result.returncode != 0:
        print(f"Сборка '{output_name}' завершилась с ошибкой:")
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        return None

    print(f"Сборка '{output_name}' завершена успешно.")
    return output_name


def get_executable_path(name: str) -> str:
    """Определить путь к собранному исполняемому файлу (с учётом ОС)."""
    exe_name = name + (".exe" if sys.platform.startswith("win") else "")
    return os.path.join(DIST_DIR, exe_name)


def test_executable(name: str) -> int:
    """Проверить, что исполняемый файл существует, и вернуть его размер в байтах."""
    path = get_executable_path(name)

    if not os.path.isfile(path):
        print(f"Файл не найден: {path}")
        return -1

    size_bytes = os.path.getsize(path)
    size_mb = size_bytes / (1024 * 1024)
    print(f"Файл: {path}")
    print(f"Размер: {size_mb:.2f} МБ ({size_bytes:,} байт)")
    return size_bytes


def cleanup_intermediate_files():
    """Удалить промежуточные файлы сборки (папку build/ и .spec), оставить только dist/."""
    if os.path.isdir(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    for file in os.listdir("."):
        if file.endswith(".spec"):
            os.remove(file)


def main():
    config = load_config()

    print("Начинаю сборку базовой версии...")
    base_name = run_build(config, optimized=False)

    print("\nНачинаю сборку оптимизированной версии...")
    optimized_name = run_build(config, optimized=True)

    if not base_name or not optimized_name:
        print("\nНе удалось завершить обе сборки — сравнение размеров пропущено.")
        sys.exit(1)

    print("\n=== Результаты тестирования дистрибутивов ===")
    print("\n-- Базовая сборка --")
    base_size = test_executable(base_name)

    print("\n-- Оптимизированная сборка --")
    optimized_size = test_executable(optimized_name)

    if base_size > 0 and optimized_size > 0:
        diff = base_size - optimized_size
        percent = (diff / base_size) * 100
        print("\n=== Сравнение ===")
        print(f"Базовый размер:        {base_size / (1024 * 1024):.2f} МБ")
        print(f"Оптимизированный размер: {optimized_size / (1024 * 1024):.2f} МБ")
        print(f"Экономия:              {diff / (1024 * 1024):.2f} МБ ({percent:.1f}%)")

        # Сохраняем отчёт в файл для вставки в отчёт по лабораторной
        with open("build_report.txt", "w", encoding="utf-8") as f:
            f.write("Отчёт о сборке и оптимизации размера\n")
            f.write("=" * 40 + "\n")
            f.write(f"Базовая сборка:        {base_size / (1024 * 1024):.2f} МБ\n")
            f.write(f"Оптимизированная сборка: {optimized_size / (1024 * 1024):.2f} МБ\n")
            f.write(f"Экономия:              {diff / (1024 * 1024):.2f} МБ ({percent:.1f}%)\n")
        print("\nОтчёт сохранён в build_report.txt")

    cleanup_intermediate_files()
    print("\nСборка завершена!")


if __name__ == "__main__":
    main()
