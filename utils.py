import re

import re

def extract_answer(text: str) -> str:
    # 1. Remove <think>...</think> completely
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # 2. Extract <answer> if present
    match = re.search(r"<answer>\s*(.*?)\s*</answer>", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 3. Otherwise return remaining text
    return text.strip()

