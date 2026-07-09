"""端到端煙霧測試：搜尋 + 四面向 overview（直接呼叫 service，不經 HTTP）。"""
import json

from app.services import overview, search

print("=== 搜尋『台積』 ===")
print(json.dumps(search.search("台積", limit=5), ensure_ascii=False, indent=2))

print("\n=== 搜尋『2330』 ===")
print(json.dumps(search.search("2330", limit=3), ensure_ascii=False, indent=2))

print("\n=== 2330 四面向 overview ===")
ov = overview.get_overview("2330")
print(json.dumps(ov, ensure_ascii=False, indent=2, default=str))
