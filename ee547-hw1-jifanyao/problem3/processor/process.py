#!/usr/bin/env python3
import os
import json
import time
import re
from datetime import datetime, timezone

HTML_files = "/shared/raw"
processed_data_dir = "/shared/processed"  
tempor = "/shared/status"
fetch_complete_file = os.path.join(tempor, "fetch_complete.json")
process_complete_file = os.path.join(tempor, "process_complete.json")

os.makedirs(processed_data_dir, exist_ok=True)

def strip_html(html_content):
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

    links = re.findall(r'href=[\'"]?([^\'" >]+)', html_content, flags=re.IGNORECASE)
    images = re.findall(r'src=[\'"]?([^\'" >]+)', html_content, flags=re.IGNORECASE)

    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = re.sub(r'\s+', ' ', text).strip()
    return text, links, images

def get_statistics(text):
    words = text.split()
    word_count = len(words)
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    paragraph_count = len([p for p in text.split("\n\n") if p.strip()])
    total_word_length = sum(len(w) for w in words)
    avg_word_length = total_word_length / word_count if word_count else 0

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "avg_word_length": avg_word_length
    }

def main():
    print("[Processor] Waiting for fetch_complete.json...", flush=True)
    while not os.path.exists(fetch_complete_file):
        time.sleep(2)

    if not os.path.exists(HTML_files):
        os.makedirs(HTML_files, exist_ok=True)

    html_files = sorted([f for f in os.listdir(HTML_files) if f.endswith(".html")])
    print(f"[Processor] Found {len(html_files)} HTML files", flush=True)

    processed_files = [] 
    for file in html_files:   
        file_path = os.path.join(HTML_files, file)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        text, links, images = strip_html(content)
        stats = get_statistics(text)

        result = {
            'source_file': file,
            'text': text,
            'statistics': stats,   
            'links': links,
            'images': images,
            'processed_at': datetime.now(timezone.utc).isoformat()
        }
        
        output_file = os.path.join(processed_data_dir, file.replace(".html", ".json"))  
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        processed_files.append(output_file)
        print(f"[Processor] Processed {file} -> {output_file}", flush=True)
    
    with open(process_complete_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processed_files": processed_files
        }, f, indent=2)

    print("[Processor] Processing complete", flush=True)

if __name__=="__main__":
    main()
