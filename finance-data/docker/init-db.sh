#!/bin/sh
# 数据中台一次性初始化脚本：
#   1. 等待 MySQL 就绪
#   2. 若 finance 库已有数据则跳过（幂等，避免 docker compose up 反复重建）
#   3. 否则导入 schema + 生成默认数据
set -e

echo "[db-init] 等待 MySQL 就绪 ..."
python - <<'PY'
import os, time, pymysql

host = os.environ["DB_HOST"]
port = int(os.environ["DB_PORT"])
user = os.environ["DB_USER"]
password = os.environ["DB_PASSWORD"]

for _ in range(120):
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password)
        conn.close()
        print("[db-init] MySQL 已就绪")
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit("[db-init] MySQL 长时间未就绪，初始化失败")
PY

echo "[db-init] 检查 finance 库是否已有数据 ..."
TABLE_COUNT=$(python - <<'PY'
import os, pymysql
conn = pymysql.connect(
    host=os.environ["DB_HOST"],
    port=int(os.environ["DB_PORT"]),
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
)
with conn.cursor() as cur:
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s",
        (os.environ["DB_NAME"],),
    )
    table_count = cur.fetchone()[0]
conn.close()
print(table_count)
PY
)

if [ "${TABLE_COUNT}" != "0" ]; then
    echo "[db-init] finance 库已有数据，跳过初始化（如需重建请执行 docker compose down -v 后重试）"
    exit 0
fi

echo "[db-init] 初始化 schema ..."
python init_db.py

echo "[db-init] 生成默认数据 (profile=${PROFILE:-smoke}) ..."
python -m generate.main --profile "${PROFILE:-smoke}"

echo "[db-init] 数据导入完成"
