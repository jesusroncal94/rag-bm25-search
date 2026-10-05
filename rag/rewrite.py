from rag import prompt


def rewrite(model, question: str) -> str:
    generated = model.generate(prompt.render_rewrite(question))

    if generated.failed:
        return question

    lines = generated.text.strip().splitlines()
    query = lines[0].strip().strip('"') if lines else ""

    return query or question
