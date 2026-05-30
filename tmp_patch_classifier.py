content = open(r"D:\maozhua\Codex\codex\scripts\monitor\engine\classifier.py", "r", encoding="utf-8").read()

# 替换 IMPORTANT_PATTERNS
old_imp = (
    "IMPORTANT_PATTERNS = re.compile(\n"
    '    r"(launch|invest|fund|partner|expand|breakthrough|"\n'
    '    r"data center\s*(?:campus|investment|announce|project)|"\n'
    '    r"internet exchange|IXP|"\n'
    '    r"AI\s*(?:infrastructure|data center|chip|model)|"\n'
    '    r"semiconductor|chip\s*(?:manufacturing|factory|plant)|"\n'
    '    r"hyperscale|cloud region|edge\s*node|"\n'
    '    r"satellite|LEO|constellation|"\n'
    '    r"regulation|regulatory|"\n'
    '    r"(?:million|billion)\s*(?:users|deploy|project|investment|funding|deal))", re.IGNORECASE)'
)

new_imp = (
    "IMPORTANT_PATTERNS = re.compile(\n"
    '    r"(launch|invest|fund|partner|expand|breakthrough|"\n'
    '    r"data center\s*(?:campus|investment|announce|project)|"\n'
    '    r"internet exchange|IXP|"\n'
    '    r"AI\s*(?:infrastructure|data center|chip|model|startup|unicorn|funding|investment)|"\n'
    '    r"semiconductor|chip\s*(?:manufacturing|factory|plant|fabrication)|"\n'
    '    r"GPU|NVIDIA|TSMC|AMD|Intel|"\n'
    '    r"hyperscale|cloud region|edge\s*node|"\n'
    '    r"satellite|LEO|constellation|"\n'
    '    r"regulation|regulatory|"\n'
    '    r"venture capital|startup\s*(?:funding|investment|series)|"\n'
    '    r"IPO|stock market|tech stock|fintech|"\n'
    '    r"open source|LLM|foundation model|"\n'
    '    r"(?:million|billion)\s*(?:users|deploy|project|investment|funding|deal|valuation))", re.IGNORECASE)'
)

if old_imp in content:
    content = content.replace(old_imp, new_imp)
    print("IMPORTANT_PATTERNS 替换成功")
else:
    print("IMPORTANT_PATTERNS 未匹配")
    idx = content.find("IMPORTANT_PATTERNS")
    print(repr(content[idx:idx+500]))

# 替换 WATCH_PATTERNS
old_watch = (
    "WATCH_PATTERNS = re.compile(\n"
    '    r"(AI|artificial intelligence|"\n'
    '    r"funding|acquir|investment|"\n'
    '    r"digit(al|ization)|transformation|"\n'
    '    r"emerging market|undersea|submarine|"\n'
    '    r"UAE|Dubai|Saudi|Africa|Southeast Asia|"\n'
    '    r"chip|semiconductor)", re.IGNORECASE)'
)

new_watch = (
    "WATCH_PATTERNS = re.compile(\n"
    '    r"(AI|artificial intelligence|"\n'
    '    r"funding|acquir|investment|"\n'
    '    r"digit(al|ization)|transformation|"\n'
    '    r"emerging market|undersea|submarine|"\n'
    '    r"UAE|Dubai|Saudi|Africa|Southeast Asia|"\n'
    '    r"chip|semiconductor|"\n'
    '    r"fintech|startup|VC|IPO|"\n'
    '    r"open source|LLM|GPU|cloud computing)", re.IGNORECASE)'
)

if old_watch in content:
    content = content.replace(old_watch, new_watch)
    print("WATCH_PATTERNS 替换成功")
else:
    print("WATCH_PATTERNS 未匹配")

open(r"D:\maozhua\Codex\codex\scripts\monitor\engine\classifier.py", "w", encoding="utf-8").write(content)
print("写入完成")
