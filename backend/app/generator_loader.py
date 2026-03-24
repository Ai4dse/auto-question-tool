from importlib import import_module
import logging

from .config import QUESTION_CONFIG


logger = logging.getLogger(__name__)


def load_question_generators(strict: bool = False):
    generators = {}
    errors = []

    for type_name, config in QUESTION_CONFIG.items():
        try:
            module_path, class_name = config["class_path"].rsplit(".", 1)
            module = import_module(module_path)
            klass = getattr(module, class_name)

            generators[type_name] = {
                "class": klass,  
                "metadata": config.get("metadata", {}) 
            }

        except Exception as e:
            errors.append((type_name, str(e)))
            logger.exception("Failed to load generator", extra={"type_name": type_name})

    if strict and errors:
        failed = ", ".join(type_name for type_name, _ in errors)
        raise RuntimeError(f"Failed to load question generators: {failed}")

    return generators
