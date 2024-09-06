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
