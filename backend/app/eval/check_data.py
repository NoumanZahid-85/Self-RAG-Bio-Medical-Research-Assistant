import sys

from datasets import load_dataset

sys.stdout.reconfigure(encoding='utf-8')

ds = load_dataset('qiaojin/PubMedQA', 'pqa_labeled', split='train', trust_remote_code=False)
print('Columns:', ds.column_names)
print('Size:', len(ds))

row = ds[0]
print('pubid:', row['pubid'])
print('question:', row['question'])
print('final_decision:', row['final_decision'])

ctx = row['context']
if isinstance(ctx, dict):
    print('context keys:', list(ctx.keys()))
    print('contexts count:', len(ctx.get('contexts', [])))

long_ans = str(row['long_answer'])
print('long_answer (first 200):', long_ans[:200])
