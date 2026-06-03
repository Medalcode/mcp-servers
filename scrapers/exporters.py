import csv
import io
import json


_FORMULA_CHARS = ("=", "+", "-", "@")


def _sanitize(val: str) -> str:
    if val and val[0] in _FORMULA_CHARS:
        return "'" + val
    return val


def to_csv(data) -> str:
    if isinstance(data, list) and data and isinstance(data[0], dict):
        headers = list(data[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        for item in data:
            writer.writerow({k: _sanitize(str(v)) for k, v in item.items()})
        return buf.getvalue().strip()
    if isinstance(data, dict) and "items" in data and data["items"]:
        return to_csv(data["items"])
    return json.dumps(data, indent=2)


def to_markdown(data) -> str:
    if isinstance(data, list) and data and isinstance(data[0], dict):
        headers = list(data[0].keys())
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for item in data:
            lines.append("| " + " | ".join(str(item.get(h, "")) for h in headers) + " |")
        return "\n".join(lines)
    if isinstance(data, dict):
        result = []
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                result.append(f"## {key}")
                result.append(to_markdown(value))
            elif isinstance(value, list):
                result.append(f"**{key}**: {', '.join(str(v) for v in value)}")
            else:
                result.append(f"**{key}**: {value}")
        return "\n\n".join(result)
    return str(data)
