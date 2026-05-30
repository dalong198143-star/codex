
import re

fp = r"D:\maozhua\Codex\codex\scripts\monitor\main.py"
with open(fp, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 1) ? print("=" * 50) ???????
insert_line = None
for i, line in enumerate(lines):
    if 'print("=" * 50)' in line:
        insert_line = i
        break

if insert_line is not None:
    night_code = [
        "\n",
        "    # ????(0-8?): ??Bing/Google??(?????????), ??RSS\n",
        "    current_hour = _now_c().hour\n",
        "    night_mode = current_hour < 8\n",
        "    if night_mode:\n",
        '        print(f"[{{_now_c():%H:%M}}] \\U0001f319 ????: ??Bing/Google??, ?RSS?")\n',
        "    else:\n",
        '        print(f"[{{_now_c():%H:%M}}] \\u2600\\ufe0f ????: ?????")\n',
    ]
    for j, l in enumerate(reversed(night_code)):
        lines.insert(insert_line + 1, l)
    print("???????? OK")
else:
    print("??????")

# 2) ?? Bing/Google ????? night_mode ??
new_lines = []
skip_bing = False
skip_google = False
for line in lines:
    stripped = line.strip()
    # Bing ????????
    if stripped == "items = bing_search(kw)":
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(f"{indent}if night_mode:\n")
        new_lines.append(f"{indent}    items = []\n")
        new_lines.append(f"{indent}    print(f\"    [{{{{node['name']}}}}] \\U0001f319 ??????Bing??\")\n")
        new_lines.append(f"{indent}else:\n")
        new_lines.append(f"{indent}    items = bing_search(kw)\n")
        skip_bing = True
        continue
    # Google News ????????
    if stripped == "items = google_news_search(kw)":
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(f"{indent}if night_mode:\n")
        new_lines.append(f"{indent}    items = []\n")
        new_lines.append(f"{indent}    print(f\"    [{{{{node['name']}}}}] \\U0001f319 ??????Google News\")\n")
        new_lines.append(f"{indent}else:\n")
        new_lines.append(f"{indent}    items = google_news_search(kw)\n")
        skip_google = True
        continue
    new_lines.append(line)

with open(fp, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"Bing: {skip_bing}, Google: {skip_google}")
print("OK")
