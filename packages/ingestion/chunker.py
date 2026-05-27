def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[dict]:
    if not text.strip():
        return []

    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    index = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_content = " ".join(chunk_words)

        chunks.append({
            "chunk_index": index,
            "content": chunk_content,
            "metadata": {"word_start": start, "word_end": end},
        })

        index += 1
        if end >= len(words):
            break
        start = end - overlap

    return chunks
