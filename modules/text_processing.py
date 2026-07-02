def clean_text(text):
    text = text.strip()
    text = text.replace("\n\n", "\n")
    text = " ".join(text.split())
    return text