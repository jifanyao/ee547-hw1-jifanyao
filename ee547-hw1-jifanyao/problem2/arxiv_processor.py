#!/usr/bin/env python3
import sys
import json 
import os 
import re
import time
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import Counter

STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
    'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
    'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some',
    'such', 'as', 'also', 'very', 'too', 'only', 'so', 'than', 'not'
}

def text_processing(text):
    words = re.findall(r'\b\w+\b', text)
    total_words_count = len(words)
    words_lower = []
    for w in words:
        word = w.lower()
        if word not in STOPWORDS:
            words_lower.append(word)
    unique_words = len(set(words_lower))
    words_length = sum(len(w)for w in words)
    avg_word_length = words_length/ total_words_count if total_words_count >0 else 0

    sentences = re.split(r'[.!?]', text)
    clean_sentences = []
    for s in sentences:
        stripped = s.strip()   
        if stripped:          
            clean_sentences.append(stripped)
    sentences = clean_sentences
    total_sentences = len(sentences)
    avg_words_per_sentence = total_words_count / total_sentences if total_sentences > 0 else 0
    longest_sentence = max(sentences, key=lambda s: len(s.split()), default='')
    shortest_sentence = min(sentences, key=lambda s: len(s.split()), default='')

    uppercase_letters = list(set(re.findall(r'\b[A-Z][A-Z0-9]+\b', text)))
    numeric_words = list(set(re.findall(r'\b\w*\d\w*\b', text)))
    hyphenated_terms = list(set(re.findall(r'\b\w+(?:-\w+)+\b', text)))

    return {
        "total_words": total_words_count,
        "unique_words": unique_words,
        "avg_word_length": avg_word_length,
        "total_sentences": total_sentences,
        "avg_words_per_sentence": avg_words_per_sentence,
        "longest_sentence": longest_sentence,
        "shortest_sentence": shortest_sentence,
        "uppercase_terms": uppercase_letters,
        "numeric_terms": numeric_words,
        "hyphenated_terms": hyphenated_terms,
        "words_filtered": words_lower
    }

def extract_papers_metadata(query, max_results, log_file):
    base_url = "http://export.arxiv.org/api/query"
    start = 0
    retry_count = 0
    while retry_count < 3:
        try:
            url = f"{base_url}?search_query={query}&start={start}&max_results={max_results}"
            with open(log_file, 'a') as log:
                log.write(f"{datetime.utcnow().isoformat()}Z Starting ArXiv query: {query}\n")
            req = Request(url, headers={"User-Agent": "PythonArxivFetcher"})
            with urlopen(req, timeout=10) as response:
                data = response.read()
            return data
        except HTTPError as e:
            if e.code == 429:
                retry_count += 1
                time.sleep(3)
            else:
                with open(log_file, 'a') as log:
                    log.write(f"{datetime.utcnow().isoformat()}Z HTTP Error {e.code}\n")
                return None
        except URLError as e:
            with open(log_file, 'a') as log:
                log.write(f"{datetime.utcnow().isoformat()}Z Network error: {e.reason}\n")
            sys.exit(1)
    return None

def parse_papers_xml(xml_data,log_file):
    try:
        root = ET.fromstring(xml_data)   
    except ET.ParseError as e:          
        with open(log_file, 'a') as log: 
            log.write(f"{datetime.utcnow().isoformat()}Z XML parse error: {str(e)}\n")          
        return []                   

    namespace = {'atom': 'http://www.w3.org/2005/Atom'}
    entries = []
    entry_list = root.findall('atom:entry',namespace)
    for entry in entry_list:
        try:
            arxiv_id = entry.find('atom:id', namespace).text
            title = entry.find('atom:title', namespace).text.strip()
            authors = [a.find('atom:name', namespace).text for a in entry.findall('atom:author', namespace)]
            abstract = entry.find('atom:summary', namespace).text.strip()
            categories = [c.attrib.get('term') for c in entry.findall('atom:category', namespace)]
            published = entry.find('atom:published', namespace).text
            updated = entry.find('atom:updated', namespace).text

            stats =text_processing(abstract)

            entry_data = {
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "categories": categories,
                "published": published,
                "updated": updated,
                "abstract_stats": {
                    "total_words": stats["total_words"],
                    "unique_words": stats["unique_words"],
                    "total_sentences": stats["total_sentences"],
                    "avg_words_per_sentence": stats["avg_words_per_sentence"],
                    "avg_word_length": stats["avg_word_length"]
                },
                "technical_terms": {
                    "uppercase_terms": stats["uppercase_terms"],
                    "numeric_terms": stats["numeric_terms"],
                    "hyphenated_terms": stats["hyphenated_terms"]
                },
                "words_filtered": stats["words_filtered"]
            }
            entries.append(entry_data)

            with open(log_file, 'a') as log:
                log.write(f"{datetime.utcnow().isoformat()}Z Processing paper: {arxiv_id}\n")
        except Exception as e:
            with open(log_file, 'a') as log:
                log.write(f"{datetime.utcnow().isoformat()}Z Warning: missing field, skipping: {str(e)}\n")
            continue
    return entries

def abstract_analysis(entries, query):

    all_words = []         
    category_frequency = {}    

    for paper in entries:
        all_words.extend(paper["words_filtered"])
        for cat in paper["categories"]:
            category_frequency[cat] = category_frequency.get(cat, 0) + 1

    word_counter = Counter(all_words)
    
    top_50_words = []
    top_to_word = word_counter.most_common(50)
    for word_freq in top_to_word:
        word = word_freq[0]
        freq = word_freq[1]
        count= 0
        for w in entries:
            if word in w['words_filtered']:
                count +=1 
        top_50_words.append({
            "word": word,
            "frequency": freq,
            "documents": count
        })


    if entries:  
        abstract_lengths = [len(paper["words_filtered"]) for paper in entries]
        avg_length = sum(abstract_lengths) / len(entries)
        longest = max(abstract_lengths)
        shortest = min(abstract_lengths)
    else:
        avg_length = longest = shortest = 0

    corpus_stats = {
        "total_abstracts": len(entries),
        "total_words": len(all_words),
        "unique_words_global": len(set(all_words)),
        "avg_abstract_length": avg_length,
        "longest_abstract_words": longest,
        "shortest_abstract_words": shortest
    }


    uppercase_terms = set()
    numeric_terms = set()
    hyphenated_terms = set()

    for paper in entries:
        uppercase_terms.update(paper["technical_terms"]["uppercase_terms"])
        numeric_terms.update(paper["technical_terms"]["numeric_terms"])
        hyphenated_terms.update(paper["technical_terms"]["hyphenated_terms"])

    technical_terms = {
        "uppercase_terms": list(uppercase_terms),
        "numeric_terms": list(numeric_terms),
        "hyphenated_terms": list(hyphenated_terms)
    }

    result = {
        "query": query,
        "papers_processed": len(entries),
        "processing_timestamp": datetime.utcnow().isoformat() + "Z",
        "corpus_stats": corpus_stats,
        "top_50_words": top_50_words,
        "technical_terms": technical_terms,
        "category_distribution": category_frequency
    }

    return result

def main():
    if len(sys.argv)!= 4:
        print("Usage:python arxiv_processor.py<query><max_result><output_dir>")
        sys.exit(1)
    
    query = sys.argv[1]
    max_results = int(sys.argv[2])
    output_dir = sys.argv[3]

    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, "processing.log")

    xml_data = extract_papers_metadata(query, max_results, log_file)
    if not xml_data:
        sys.exit(1)

    papers =parse_papers_xml (xml_data, log_file)
    with open(os.path.join(output_dir, "papers.json"), "w") as f:
        json.dump(papers, f, indent=2)

    corpus = abstract_analysis(papers, query)
    with open(os.path.join(output_dir, "corpus_analysis.json"), "w") as f:
        json.dump(corpus, f, indent=2)

    with open(log_file, 'a') as log:
        log.write(f"{datetime.utcnow().isoformat()}Z Completed processing: {len(papers)} papers\n")

if __name__ == "__main__":
    main()





