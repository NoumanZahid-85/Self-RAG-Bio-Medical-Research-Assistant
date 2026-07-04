import sys

from datasets import load_dataset

sys.stdout.reconfigure(encoding='utf-8')

ds = load_dataset('qiaojin/PubMedQA', 'pqa_labeled', split='train', trust_remote_code=False)

keywords = ['statin', 'cardiovascular', 'cholesterol', 'diabetes', 'hypertension', 'aspirin', 'heart', 'blood pressure']

for i, row in enumerate(ds):
    q = row['question'].lower()
    if any(k in q for k in keywords):
        print(i, '-', row['question'][:120])
