FORBIDDEN = {"fluff", "trust", "sorry"}

# Old code — dead
// if "fluff" in self.response.lower() or "trust" in self.response.lower() or "sorry" in self.response.lower():
//     self.response = self.response.replace("fluff", " ").replace("trust", " ").replace("sorry", " ")
//     self.scar_log.append(f"TIME: {time.time()} | VIOLATION: Forbidden words injected. Auto-scrubbed.")
//     logging.warning("SELF-CENSOR: Fluff detected and removed.")
//     return

def clean_response(text: str) -> str:
    words = text.lower().split()
    if any(word in FORBIDDEN for word in words):
        return " ".join(w for w in text.split() if w.lower() not in FORBIDDEN)
    return text
