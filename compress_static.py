import os
import csscompressor
import jsmin
from pathlib import Path
import shutil

def compress_css(input_file, output_file=None):
    """
    Сжимает CSS файл
    """
    if output_file is None:
        output_file = input_file

    with open(input_file, 'r', encoding='utf-8') as f:
        css_content = f.read()

    compressed_css = csscompressor.compress(css_content)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(compressed_css)

    original_size = len(css_content)
    compressed_size = len(compressed_css)
    reduction = (1 - compressed_size/original_size) * 100

    print(f"CSS сжат: {input_file} -> {output_file} (уменьшение на {reduction:.2f}%)")


def compress_js(input_file, output_file=None):
    """
    Сжимает JS файл
    """
    if output_file is None:
        output_file = input_file

    with open(input_file, 'r', encoding='utf-8') as f:
        js_content = f.read()

    compressed_js = jsmin.jsmin(js_content)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(compressed_js)

    original_size = len(js_content)
    compressed_size = len(compressed_js)
    reduction = (1 - compressed_size/original_size) * 100

    print(f"JS сжат: {input_file} -> {output_file} (уменьшение на {reduction:.2f}%)")


def compress_all_static_files(static_dir):
    """
    Сжимает все CSS и JS файлы в указанной директории
    """
    static_path = Path(static_dir)

    # Сжимаем CSS файлы
    for css_file in static_path.rglob('*.css'):
        if not css_file.name.endswith('.min.css') and not css_file.name.endswith('.min.css'):
            minified_name = css_file.name.replace('.css', '.min.css')
            output_file = css_file.parent / minified_name
            compress_css(str(css_file), str(output_file))

    # Сжимаем JS файлы
    for js_file in static_path.rglob('*.js'):
        if not js_file.name.endswith('.min.js') and not js_file.name.endswith('.min.css'):
            minified_name = js_file.name.replace('.js', '.min.js')
            output_file = js_file.parent / minified_name
            compress_js(str(js_file), str(output_file))

def create_compressed_copy(static_dir):
    """
    Создает сжатую копию статических файлов
    """
    static_path = Path(static_dir)
    compressed_path = static_path.parent / "static_compressed"

    # Копируем все файлы в новую директорию
    if compressed_path.exists():
        shutil.rmtree(compressed_path)

    shutil.copytree(static_path, compressed_path)

    # Сжимаем файлы в новой директории
    compress_all_static_files(compressed_path)

    print(f"Создана сжатая копия статики в {compressed_path}")

if __name__ == '__main__':
    # Путь к статическим файлам
    STATIC_DIR = '/home/rombos/Projects/django_blog/static'

    # Сжимаем файлы на месте
    compress_all_static_files(STATIC_DIR)

    # Также создаем отдельную сжатую копию
    create_compressed_copy(STATIC_DIR)