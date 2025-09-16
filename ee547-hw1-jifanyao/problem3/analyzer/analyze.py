#!/usr/bin/env python3
import os
import json
import time
from datetime import datetime, timezone
from collections import Counter


INPUT_DIR = "/shared/processed"
STATUS_DIR = "/shared/status"
OUTPUT_DIR = "/shared/analysis"

PROCESS_FLAG = os.path.join(STATUS_DIR, "process_complete.json")
REPORT_FILE = os.path.join(OUTPUT_DIR, "final_report.json")


os.makedirs(OUTPUT_DIR, exist_ok=True)


def jaccard_score(tokens_a, tokens_b):
    
    set_a, set_b = set(tokens_a), set(tokens_b)
    if not (set_a or set_b):
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def make_ngrams(words, n=2):

    return [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]


def main():

    while not os.path.exists(PROCESS_FLAG):
        time.sleep(2)

    file_list = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".json"))

    docs_tokens = {}
    total_counter = Counter()
    bigram_counter = Counter()
    texts_raw = [] 

    for fname in file_list:
        with open(os.path.join(INPUT_DIR, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        tokens = data["text"].split()

        docs_tokens[fname] = tokens
        total_counter.update(tokens)
        bigram_counter.update(make_ngrams(tokens, 2))
        texts_raw.append(data["text"])


    sim_results = []
    for i in range(len(file_list)):
        for j in range(i + 1, len(file_list)):
            sim_results.append({
                "doc1": file_list[i],
                "doc2": file_list[j],
                "similarity": jaccard_score(docs_tokens[file_list[i]], docs_tokens[file_list[j]])
            })

   
    total_words = sum(total_counter.values())
    vocab_size = len(total_counter)
    top_words = [
        {"word": w, "count": c, "frequency": c / total_words}
        for w, c in total_counter.most_common(100)
    ]

  
    est_sentence_count = sum(txt.count(".") + txt.count("!") + txt.count("?") for txt in texts_raw)
    avg_sentence_len = total_words / max(est_sentence_count, 1)
    avg_word_len = sum(len(w) for w in total_counter.elements()) / total_words if total_words else 0
    complexity = avg_sentence_len * avg_word_len

    
    report = {
        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
        "documents_processed": len(file_list),
        "total_words": total_words,
        "unique_words": vocab_size,
        "top_100_words": top_words,
        "document_similarity": sim_results,
        "top_bigrams": [{"bigram": bg, "count": c} for bg, c in bigram_counter.most_common(50)],
        "readability": {
            "avg_sentence_length": avg_sentence_len,
            "avg_word_length": avg_word_len,
            "complexity_score": complexity
        }
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)



if __name__ == "__main__":
    main()
