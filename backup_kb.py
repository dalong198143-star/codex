"""本地知识库备份与恢复工具

用法:
  python backup_kb.py export                   # 导出全量 JSONL
  python backup_kb.py import <文件.jsonl>       # 从 JSONL 恢复（追加，不覆盖）

备份位置: D:/hermes-tools/backups/kb_backup_YYYYMMDD_HHMMSS.jsonl
"""

import json
import sys
import os
import shutil
import tempfile
from datetime import datetime
import shutil
import tempfile

BACKUP_DIR = "D:/hermes-tools/kb-backup"   # kb-backup 有写权限
FALLBACK_DIR = "D:/hermes-tools/backups"     # 旧目录只读，仅作 fallback
KB_PATH = "D:/hermes-tools/kb-vector"
COLLECTION = "general"


def export_kb():
    from chromadb import PersistentClient
    client = PersistentClient(path=KB_PATH)
    col = client.get_collection(COLLECTION)
    data = col.get()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"kb_backup_{timestamp}.jsonl"
    filepath = os.path.join(BACKUP_DIR, filename)

    ids = data["ids"]
    docs = data["documents"] or []
    metas = data["metadatas"] or []

    count = 0
    # 先写临时目录（确保可写），再复制到目标目录
    tmp_path = os.path.join(tempfile.gettempdir(), filename)
    with open(tmp_path, "w", encoding="utf-8") as f:
        for doc_id, doc, meta in zip(ids, docs, metas):
            record = {
                "id": doc_id,
                "document": doc,
                "metadata": meta,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    size_kb = os.path.getsize(tmp_path) / 1024
    print(f"已导出 {count} 条 → {tmp_path} ({size_kb:.1f} KB)")

    # 尝试复制到 BACKUP_DIR
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        target_path = os.path.join(BACKUP_DIR, filename)
        shutil.copy2(tmp_path, target_path)
        print(f"已同步至 → {target_path}")
    except (PermissionError, OSError) as e:
        print(f"⚠ 无法写入 {BACKUP_DIR}（{e}），备份文件仅在临时目录: {tmp_path}")


def import_kb(filepath: str):
    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        sys.exit(1)

    from chromadb import PersistentClient
    from sentence_transformers import SentenceTransformer

    client = PersistentClient(path=KB_PATH)
    col = client.get_or_create_collection(COLLECTION)
    model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

    # 读取已有 ID，避免重复导入
    existing_ids = set(col.get().get("ids", []))

    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    new_records = [r for r in records if r["id"] not in existing_ids]
    if not new_records:
        print(f"所有 {len(records)} 条已存在，无需导入")
        return

    ids = [r["id"] for r in new_records]
    documents = [r["document"] for r in new_records]
    metadatas = [r["metadata"] for r in new_records]

    # 备份文件不含 embedding，需重新生成
    embeddings = model.encode(documents, normalize_embeddings=True)

    col.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )

    print(f"已导入 {len(new_records)} 条（跳过 {len(records) - len(new_records)} 条重复）")
    print(f"集合总数: {col.count()}")


def list_backups():
    if not os.path.isdir(BACKUP_DIR):
        print("暂无备份")
        return
    files = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.endswith(".jsonl")],
        reverse=True,
    )
    if not files:
        print("暂无备份文件")
        return
    print("备份文件:")
    for f in files[:10]:
        fp = os.path.join(BACKUP_DIR, f)
        size_kb = os.path.getsize(fp) / 1024
        lines = sum(1 for _ in open(fp, "r", encoding="utf-8"))
        print(f"  {f}  ({size_kb:.1f} KB, {lines} 条)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    if action == "export":
        export_kb()
    elif action == "import":
        if len(sys.argv) < 3:
            print("用法: python backup_kb.py import <文件.jsonl>")
            sys.exit(1)
        import_kb(sys.argv[2])
    elif action == "list":
        list_backups()
    else:
        print(f"未知操作: {action}")
        print(__doc__)
