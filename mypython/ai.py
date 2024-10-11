import threading

DEFAULT_MODEL = "deepseek-coder-v2:16b-lite-base-q4_0"

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
        "model_aliases": ["deepseek-coder-v2", "deepseek-coder", "deepseek"],
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
                "<|end_of_text|>",
            ],
        },
        "model_aliases": [],
    },

    "codellama:7b-code": {
        "prompt_template": "<PRE> {prefix} <SUF>{suffix} <MID>",
        "options": {
            "stop": ["<PRE>", "<SUF>", "<MID>", "<EOT>"],
        },
        "model_aliases": ['codellama', 'codellama:7b'],
    },

    "codellama:13b-code": {
        "prompt_template": "<PRE> {prefix} <SUF>{suffix} <MID>",
        "options": {
            "stop": ["<PRE>", "<SUF>", "<MID>", "<EOT>"],
        },
        "model_aliases": ['codellama:13b'],
    },

    "codeqwen:7b-code-v1.5-fp16": {
        "prompt_template": "<fim_prefix>{prefix}<fim_suffix>{suffix}<fim_middle>",
        "options": {
            "stop": [
                "<fim_prefix>",
                "<fim_suffix>",
                "<fim_middle>",
                "<file_sep>",
                "<|endoftext|>",
                "</fim_middle>",
                "</code>",
            ],
        },
        "model_aliases": ["codeqwen", "codeqwen1.5"],
    },

    "qwen2.5-coder:1.5b-base-q4_K_M": {
        "prompt_template": "<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>",
        "options": {
            "stop": [
                "<|endoftext|>",
                "<fim_prefix>",
                "<fim_suffix>",
                "<fim_middle>",
            ],
        },
        "model_aliases": [],
    },

    "qwen2.5-coder:1.5b-base-fp16": {
        "prompt_template": (qwen_template := "<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>"),
        "options": {
            "stop": (qwen_stop := [
                "<|endoftext|>",
                "<|fim_prefix|>",
                "<|fim_middle|>",
                "<|fim_suffix|>",
                "<|fim_pad|>",
                "<|repo_name|>",
                "<|file_sep|>",
                "<|im_start|>",
                "<|im_end|>",
            ]),
        },
        "model_aliases": ["qwen2.5-coder:1.5b-base", "qwen2.5-coder:1.5b"],
    },

    "qwen2.5-coder:7b-base-q4_K_M": {
        "prompt_template": qwen_template,
        "options": {
            "stop": qwen_stop,
        },
        "model_aliases": ["qwen2.5-coder:7b-base", "qwen2.5-coder:7b",
                          'qwen2.5-coder', 'qwen2.5'],
    },

}

CONTEXT_PREFIX = """\
#/usr/bin/python3

# Coding conventions:
#
# - Always include a space after a comma
# - Never put a space between a function call and its parentheses
# - Never end a line in a semicolon
# - Use four spaces for indentation
# - Do not add extraneous comments


"""


CONTEXT_SUFFIX = """\


if __name__ == '__main__':
    def main():
"""

def load_model(model):
    import ollama
    ollama.generate(model, '', options={'num_predict': 0})

# @lru_cache(1024)
async def get_ai_completion(prefix, suffix, model_name, context=()):
    import ollama

    model = MODELS[model_name]
    prompt_template = model['prompt_template']
    prompt = prompt_template.format(
        # system=CONTEXT_PREFIX,
        prefix=CONTEXT_PREFIX + context + prefix,
        suffix=suffix + CONTEXT_SUFFIX)
    options = model['options']
    client = ollama.AsyncClient()
    output = await client.generate(model=model_name, prompt=prompt, options=options)

    # normalize
    out = output['response']
    out = out.rstrip()
    out = out.replace('\r\n', '\n')
    out = out.replace('\t', '    ')

    if model_name == "codeqwen:7b-code-v1.5-fp16" and out.startswith(' '):
        # codeqwen always adds a spaces before the generation for some reason
        out = out[1:]

    return out

def get_context(buffer, limit_chars=10000):
    N = 0
    context = list(buffer.session.In.values())
    i = None
    for i in range(len(context) - 1, -1, -1):
        N += len(context[i])
        if N > limit_chars:
            i += 1
            break
    return '\n\n'.join(list(buffer.session.In.values()))[i:]

class OllamaSuggester:
    """
    Ollama Completer
    """
    def __init__(self, get_ai_completion=get_ai_completion):
        self.get_ai_completion = get_ai_completion

    async def get_suggestion_async(self, buffer, document):

        text_before_cursor = document.text_before_cursor
        text_after_cursor = document.text_after_cursor

        model_name = CURRENT_MODEL
        completion = await self.get_ai_completion(text_before_cursor, text_after_cursor,
                                       model_name, context=get_context(buffer))
        return completion

def get_ai_models(include_aliases=True):
    yield from list(MODELS)
    if include_aliases:
        for model in MODELS:
            yield from MODELS[model]['model_aliases']

def set_current_model(model):
    global CURRENT_MODEL

    for m in MODELS:
        if model == m:
            break
        if model in MODELS[m]['model_aliases']:
            model = m
            break
    else:
        raise ValueError(f"Model {model} not found")

    CURRENT_MODEL = model

    # Asynchronously Load the model into memory
    threading.Thread(target=load_model, args=(model,), daemon=True).start()
