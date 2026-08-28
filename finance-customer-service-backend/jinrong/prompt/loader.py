from pathlib import Path

import jinja2


def load_prompt_template_content(file_path: str ) :
    prompt_template_file_path = Path(__file__).resolve().parent / 'jinja2' /f'{file_path}.jinja2'

    return prompt_template_file_path.read_text(encoding='utf-8')
