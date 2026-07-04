import glob
import json
import sys

files = glob.glob("eval_results_*.json")
if not files:
    print("No eval results found")
    sys.exit(1)

latest = max(files, key=lambda f: f.split("_")[-1].replace(".json",""))
with open(latest, encoding="utf-8") as f:
    data = json.load(f)

print("Config:", data["config"])
print("Aggregate:", json.dumps(data["aggregate"], indent=2))
print()
for r in data["results"]:
    q = r["question"][:60]
    path = "->".join(r["graph_path"])
    print(f"  Q: {q}...")
    print(f"    Faith={r['faithfulness']} Rel={r['answer_relevancy']}"
          f" Prec={r['context_precision']} Rec={r['context_recall']}"
          f" Abstain={r['abstained']} Path={path}")
