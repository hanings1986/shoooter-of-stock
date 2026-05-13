"""简单测试"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime

print("=" * 50)
print("Stock Scout - Quick Test")
print("=" * 50)

# 测试时间
now = datetime.now()
print(f"\nCurrent time: {now}")
print(f"Weekday: {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][now.weekday()]}")

# 交易时段
from datetime import time as dtime
MORNING_START = dtime(9, 30)
MORNING_END = dtime(11, 30)
AFTERNOON_START = dtime(13, 0)
AFTERNOON_END = dtime(14, 55)

current_time = now.time()
is_morning = MORNING_START <= current_time <= MORNING_END
is_afternoon = AFTERNOON_START <= current_time <= AFTERNOON_END
is_trading = (is_morning or is_afternoon) and now.weekday() < 5

print(f"\nCurrent time: {current_time}")
print(f"Morning session? {is_morning}")
print(f"Afternoon session? {is_afternoon}")
print(f"Trading? {is_trading}")

# 测试增量追踪器
print("\n" + "=" * 50)
print("Testing Incremental Tracker")
print("=" * 50)

import json
from pathlib import Path

cache_file = Path('data/sent_signals.json')
cache_file.parent.mkdir(parents=True, exist_ok=True)

# 读取
if cache_file.exists():
    with open(cache_file, 'r', encoding='utf-8') as f:
        signals = json.load(f)
    print(f"Existing records: {len(signals)}")
    for k, v in signals.items():
        print(f"  {k}: {v}")
else:
    print("No records yet (normal)")

# 写入测试
test_signal = {
    '000001_MA10': {
        'timestamp': datetime.now().isoformat(),
        'score': 68
    }
}

with open(cache_file, 'w', encoding='utf-8') as f:
    json.dump(test_signal, f, ensure_ascii=False, indent=2)

print("\nTest record written")

# 测试数据源
print("\n" + "=" * 50)
print("Testing Data Source")
print("=" * 50)

try:
    import requests

    url = "https://qt.gtimg.cn/q=sz000001"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=10)

    if resp.status_code == 200:
        # 解析数据
        data = resp.text.strip().split('~')
        if len(data) > 5:
            print(f"\n[OK] Tencent Finance: Success")
            print(f"  Stock: {data[1] if len(data) > 1 else 'N/A'}")
            print(f"  Price: {data[3] if len(data) > 3 else 'N/A'}")
            print(f"  Change: {data[31] if len(data) > 31 else 'N/A'}%")
        else:
            print(f"\n[WARNING] Data format error: {resp.text[:100]}")
    else:
        print(f"\n[ERROR] Request failed: {resp.status_code}")

except Exception as e:
    print(f"\n[ERROR] {e}")

print("\n" + "=" * 50)
print("Test Complete!")
print("=" * 50)
