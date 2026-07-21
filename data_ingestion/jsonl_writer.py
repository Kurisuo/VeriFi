import json
import os
import tempfile

# write list of dicts to jsonl file
# each record = one json object on one line

def write_jsonl(records, output_path):
    output_dir = os.path.dirname(output_path)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_dir or ".",
            delete=False,
        ) as file:
            temp_path = file.name
            for record in records:
                file.write(json.dumps(record, ensure_ascii=False))
                file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, output_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def write_json(value, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_dir or ".",
            delete=False,
        ) as file:
            temp_path = file.name
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, output_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
