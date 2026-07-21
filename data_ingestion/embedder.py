from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 16


def load_model(model_name=MODEL_NAME):
    try:
        return SentenceTransformer(model_name, local_files_only=True)
    except Exception:
        return SentenceTransformer(model_name)


def add_embeddings(records, model_name=MODEL_NAME, batch_size=BATCH_SIZE):
    if not records:
        return []

    model = load_model(model_name)
    texts = [record.get("embedding_text") or record["text"] for record in records]
    tokenized = model.tokenizer(
        texts,
        padding=False,
        truncation=False,
        add_special_tokens=True,
    )
    token_counts = [len(input_ids) for input_ids in tokenized["input_ids"]]
    max_tokens = int(model.max_seq_length)
    oversized = [
        (index, token_count)
        for index, token_count in enumerate(token_counts)
        if token_count > max_tokens
    ]
    if oversized:
        sample = ", ".join(
            f"chunk {index}: {count} tokens"
            for index, count in oversized[:5]
        )
        raise ValueError(
            f"Embedding input exceeds the {max_tokens}-token model limit ({sample})"
        )

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        show_progress_bar=False
    )

    embedded_records = []

    for record, embedding, token_count in zip(records, embeddings, token_counts):
        embedded_record = record.copy()
        embedded_record["embedding"] = embedding.tolist()
        embedded_record["token_count"] = token_count
        embedded_record["embedding_model"] = model_name
        embedded_record["embedding_max_tokens"] = max_tokens
        embedded_records.append(embedded_record)

    return embedded_records
