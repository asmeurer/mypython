from functools import lru_cache

from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion

DEFAULT_MODEL = "deepseek-coder-v2:16b-lite-base-fp16"

CURRENT_MODEL = DEFAULT_MODEL

MODELS = {
    "deepseek-coder-v2:16b-lite-base-fp16": {
        "prompt_template": "<｜fim▁begin｜>{prefix}<｜fim▁hole｜>{suffix}<｜fim▁end｜>",
        "options": {
            "stop": [
                "<｜fim▁begin｜>",
                "<｜fim▁hole｜>",
                "<｜fim▁end｜>",
                "//",
                "<｜end▁of▁sentence｜>",
            ],
        },
        "model_aliases": ["deepseek-coder-v2"],
    },

    "deepseek-coder-v2:16b-lite-base-q4_0": {
        "prompt_template": "<｜fim▁begin｜>{prefix}<｜fim▁hole｜>{suffix}<｜fim▁end｜>",
        "options": {
            "stop": [
                "<｜fim▁begin｜>",
                "<｜fim▁hole｜>",
                "<｜fim▁end｜>",
                "//",
                "<｜end▁of▁sentence｜>",
            ],
        },
        "model_aliases": [],
    },

    "starcoder2": {
        "prompt_template": "<fim_prefix>{prefix}<fim_suffix>{suffix}<fim_middle>",
        "options": {
            "stop": [
                "<fim_prefix>",
                "<fim_suffix>",
                "<fim_middle>",
                "<file_sep>",
                "<|endoftext|>",
            ],
        },
        "model_aliases": [],
    },
}

# @lru_cache(1024)
def get_ai_completion(prefix, suffix, model_name):
    import ollama

    model = MODELS[model_name]
    prompt_template = model['prompt_template']
    prompt = prompt_template.format(prefix=prefix, suffix=suffix)
    options = model['options']
    output = ollama.generate(model=model_name, prompt=prompt, options=options)

    # normalize
    out = output['response']
    out = out.rstrip()
    out = out.replace('\r\n', '\n')

    return out

class OllamaSuggester(AutoSuggest):
    """
    Ollama Completer
    """
    def __init__(self):
        super().__init__()

        # self.get_globals = get_globals
        # self.get_locals = get_locals
        # self.session = session

    def get_suggestion(self, buffer, document):

        text_before_cursor = document.text_before_cursor
        text_after_cursor = document.text_after_cursor

        model_name = CURRENT_MODEL
        completion = get_ai_completion(text_before_cursor, text_after_cursor, model_name)
        return completion