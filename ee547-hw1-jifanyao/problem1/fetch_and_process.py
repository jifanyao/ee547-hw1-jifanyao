#!/usr/bin/env python3
import sys
import os
import json
import time
import datetime
import re
import urllib.request
import urllib.error


def count_words(text):
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def fetch_url(url, timeout=10):
    start_time = time.time()
    result = {
        'url': url,
        'status_code': None,
        'response_time_ms': None,
        'content_length': None,
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'error': None,
        'word_count': None
    }
    try:
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            end_time = time.time()
            content = response.read()

            result['status_code'] = response.getcode()
            result['response_time_ms'] = round((end_time - start_time) * 1000, 2)
            result['content_length'] = len(content)

            content_type = response.headers.get("Content-Type", "")
            if 'text' in content_type:
                text = content.decode("utf-8", errors='ignore')
                result['word_count'] = count_words(text)
    except Exception as e:
        end_time = time.time()
        result['response_time_ms'] = round((end_time - start_time) * 1000, 2)
        result['error'] = str(e)

    return result


def main():
    if len(sys.argv) != 3:
        print("Usage: python fetch_and_process.py <input_file> <output_dir>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.isfile(input_file):
        print(f"Error: input file '{input_file}' does not exist")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    with open(input_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    responses = []
    errors = []
    processing_start = datetime.datetime.utcnow().isoformat() + 'Z'
    status_count = {}

    successful_requests = 0
    failed_requests = 0
    total_bytes_downloaded = 0
    total_response_time_ms = 0.0

    for url in urls:
        result = fetch_url(url)
        responses.append(result)

        status = result['status_code']
        if status is not None:
            status_count[str(status)] = status_count.get(str(status), 0) + 1

        if result['error']:
            failed_requests += 1
            errors.append(f"{datetime.datetime.utcnow().isoformat()}Z {url}: {result['error']}")
        else:
            successful_requests += 1
            total_bytes_downloaded += result['content_length'] or 0
            total_response_time_ms += result['response_time_ms'] or 0.0


    average_response_time_ms = (total_response_time_ms / successful_requests) if successful_requests > 0 else 0.0
    processing_end = datetime.datetime.utcnow().isoformat() + 'Z'

    with open(os.path.join(output_dir, 'responses.json'), 'w') as f:
        json.dump(responses, f, indent=2)

    with open(os.path.join(output_dir, 'errors.log'), 'w') as f:
        for line in errors:
            f.write(line + '\n')

    summary = {
        "total_urls": len(urls),
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "average_response_time_ms": average_response_time_ms,
        "total_bytes_downloaded": total_bytes_downloaded,
        "status_code_distribution": status_count,
        "processing_start": processing_start,
        "processing_end": processing_end
    }

    with open(os.path.join(output_dir, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()


            

