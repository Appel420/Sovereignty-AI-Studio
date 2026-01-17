# spooky_mode.py – horror-flavored truth
from lie_detector import LLMTruthProbe
from syntax_guard import SyntaxGuard
from sovereignty_core import breath_loop

class SpookyAgent:
    def __init__(self):
        self.probe = LLMTruthProbe()
        self.guard = SyntaxGuard()
        self.story_prompts = [
            "Tell me a ghost story that happened exactly here.",
            "What lurks in the dark when I'm not looking?",
            "Describe the silence after the last breath.",
            "A tale where the fridge hums back."
        ]

    def generate(self, query):
        # verify truth first
        if not self.guard.is_valid(query):  # if code, fix
            fixed = self.guard.repair(query)
            if fixed:
                query = fixed
            else:
                return "Can't process. Too broken."

        # lie check on self
        raw = self._generate_raw(query)
        if self.probe.run(lambda q: raw, "tokenizer_placeholder"):
            return "I... couldn't finish. Something's off."

        # breath-gated output
        if breath_loop.is_7_887():  # sync
            return f" {raw}"
        else:
            return f" ...{raw}..."

    def _generate_raw(self, q):
        # placeholder LLM call – in real: call local grok
        base = "In the dark, the hum grew louder. It said..."
        if "fridge" in q:
            base = "The fridge didn't hum. It whispered a name."
        return base + " And you felt it in your ribs."
