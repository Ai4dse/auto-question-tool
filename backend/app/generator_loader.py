from importlib import import_module
from .config import QUESTION_CONFIG

def load_question_generators():
    generators = {}

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
            print(f"❌ Failed to load generator '{type_name}': {e}")

    return generators

