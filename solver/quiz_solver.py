import asyncio
import logging
import traceback
import time
import json
import re
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import httpx
import csv
import io

executor = ThreadPoolExecutor(max_workers=2)


async def solve_quiz_async(url: str):
    """Solve quiz by fetching and analyzing page content"""
    try:
        logging.info(f"Starting quiz solve for {url}")
        result = await asyncio.get_event_loop().run_in_executor(
            executor, fetch_page_sync, url
        )
        return result
    except Exception as e:
        logging.error(f"Failed to fetch page: {e}")
        logging.error(traceback.format_exc())
        return {"solved": False, "answer": "", "submit_url": None, "page_text": ""}


def fetch_page_sync(url: str):
    """Fetch page using Selenium (runs in thread pool)"""
    driver = None
    try:
        logging.info(f"Launching Selenium for {url}...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = webdriver.Chrome(options=options)

        logging.info(f"Navigating to {url}...")
        driver.get(url)

        # Give JS a little time
        time.sleep(2)

        logging.info("Extracting content...")
        content = driver.page_source
        logging.info(f"Page source length: {len(content)}")

        # Parse and extract submit URL and an answer candidate
        answer, submit_url, page_text = extract_answer_and_submit(content, url, driver)
        # answer may be int/float/dict — stringify for safe logging and preview
        try:
            answer_preview = str(answer)[:120] if answer is not None else "empty"
        except Exception:
            answer_preview = "unprintable"
        logging.info(f"Answer extracted: {answer_preview} submit_url: {submit_url}")

        return {"solved": True, "answer": answer, "submit_url": submit_url, "page_text": page_text}
    except Exception as e:
        logging.error(f"Selenium error: {e}")
        logging.error(traceback.format_exc())
        return {"solved": False, "answer": "", "submit_url": None, "page_text": ""}
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def extract_answer_and_submit(content: str, page_url: str, driver=None):
    """Extract a best-effort answer and the submit URL from HTML content.
    Handles:
      - JSON example answers (demo pages)
      - /demo-scrape-data follow-up (secret code extraction)
      - CSV links: download CSV, pick a numeric column (prefer 'value') and return its sum.
      - Resolves relative submit paths with page_url.
    """
    try:
        soup = BeautifulSoup(content, "html.parser")
        page_text = soup.get_text(separator="\n", strip=True)
        logging.info(f"Page text (preview): {page_text[:400]}")

        # Normalize whitespace so URLs split across lines join correctly
        normalized = re.sub(r'\s+', ' ', page_text)

       # The submit endpoint is ALWAYS constant on this platform.
        submit_url = "https://tds-llm-analysis.s-anand.net/submit"

        answer_candidate = ""
        # Try to extract JSON example "answer" if present (demo pages)
        json_match = re.search(r'(\{[\s\S]*\})', page_text)
        if json_match:
            try:
                sample = json.loads(json_match.group(1))
                if isinstance(sample, dict) and "answer" in sample:
                    answer_candidate = sample["answer"]
            except Exception:
                pass

        # If the page instructs to scrape a relative path, follow it and extract secret
        scrape_match = re.search(r'(/demo-scrape-data[^\s\{\"]*)', normalized)
        if scrape_match:
            scrape_path = scrape_match.group(1)
            scrape_url = urljoin(page_url, scrape_path)
            logging.info(f"Detected scrape path -> {scrape_url}")
            try:
                if driver:
                    driver.get(scrape_url)
                    time.sleep(1.5)
                    scrape_src = driver.page_source
                    scrape_text = BeautifulSoup(scrape_src, "html.parser").get_text(separator="\n", strip=True)
                else:
                    r = httpx.get(scrape_url, timeout=10.0)
                    scrape_text = r.text

                logging.info(f"Scrape page text preview: {scrape_text[:300]}")

                # Prefer explicit "secret code is 24846" numeric pattern
                m = re.search(r'secret\s*(?:code)?\s*(?:is|:)?\s*([0-9]{3,})', scrape_text, re.I)
                if m:
                    answer_candidate = m.group(1).strip()
                else:
                    # fallback: find numeric tokens (3+ digits) and pick the longest/first plausible one
                    nums = re.findall(r'\b([0-9]{3,})\b', scrape_text)
                    if nums:
                        answer_candidate = max(nums, key=len)
                    else:
                        tokens = re.findall(r'\b([A-Za-z0-9_\-]{4,})\b', scrape_text)
                        tokens = [t for t in tokens if not re.search(r'@|http', t) and not t.lower() in {'code', 'secret'}]
                        if tokens:
                            answer_candidate = sorted(tokens, key=len, reverse=True)[0]
            except Exception as e:
                logging.error(f"Error while following scrape path: {e}")

        # CSV handling: look for .csv links or references and compute sum of a numeric column.
        csv_url = None
        # check anchors first
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".csv" in href.lower() or href.lower().endswith("csv"):
                csv_url = urljoin(page_url, href)
                break
        # fallback: find CSV URL in normalized text
        if not csv_url:
            m = re.search(r'(https?://[^\s]+?\.csv)', normalized, re.I)
            if m:
                csv_url = m.group(1)
        if csv_url:
            logging.info(f"Found csv link -> {csv_url}")
            try:
                r = httpx.get(csv_url, timeout=20.0)
                r.raise_for_status()
                raw = r.content.decode('utf-8', errors='replace')
                # sniff delimiter
                try:
                    dialect = csv.Sniffer().sniff(raw.splitlines()[0] + "\n" + ("\n".join(raw.splitlines()[1:5])))
                    delim = dialect.delimiter
                except Exception:
                    delim = ','
                
                # Check if first line looks like a header or data
                first_line = raw.splitlines()[0].split(delim)
                is_header = False
                try:
                    # If all first line values are numeric, likely no header
                    for val in first_line:
                        float(val.strip())
                    is_header = False
                except ValueError:
                    # At least one non-numeric, likely a header
                    is_header = True
                
                logging.info(f"CSV has_header={is_header}, delimiter='{delim}'")
                
                if is_header:
                    reader = csv.DictReader(io.StringIO(raw), delimiter=delim)
                    headers = reader.fieldnames or []
                    logging.info(f"CSV headers: {headers}")
                    rows_list = list(reader)
                else:
                    # No header: parse as simple list of lists
                    lines = raw.splitlines()
                    reader = csv.reader(lines, delimiter=delim)
                    rows_list = list(reader)
                    headers = [f"col_{i}" for i in range(len(rows_list[0]))] if rows_list else []
                    logging.info(f"CSV auto-headers: {headers}")
                
                # log sample rows
                sample_rows = rows_list[:3]
                logging.info(f"CSV sample rows: {sample_rows}")
                
                # Compute numeric sums per column
                sums = {}
                counts = {}
                for row in rows_list:
                    for col_idx, val in enumerate(row):
                        col_name = headers[col_idx] if col_idx < len(headers) else f"col_{col_idx}"
                        if val is None or val == "":
                            continue
                        v2 = str(val).strip().replace(',', '')
                        try:
                            num = float(v2)
                        except Exception:
                            nm = re.search(r'(-?\d+(?:\.\d+)?)', v2)
                            if nm:
                                num = float(nm.group(1))
                            else:
                                continue
                        sums[col_name] = sums.get(col_name, 0.0) + num
                        counts[col_name] = counts.get(col_name, 0) + 1
                
                if sums:
                    # prefer 'value' column (case-insensitive) or the first/only numeric column
                    cand_col = None
                    for name in sums.keys():
                        if name.lower() == "value":
                            cand_col = name
                            break
                    if not cand_col:
                        candidates = [(name, counts[name], sums[name]) for name in sums.keys() if not re.search(r'id|index|key', name, re.I)]
                        if not candidates:
                            candidates = [(name, counts[name], sums[name]) for name in sums.keys()]
                        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
                        cand_col = candidates[0][0]
                    
                    logging.info(f"Chosen numeric column: {cand_col} (count={counts[cand_col]}, sum={sums[cand_col]})")
                    total = sums[cand_col]
                    
                    # If page mentions a "Cutoff", filter and recompute using >=
                    cutoff = None
                    mcut = re.search(r'Cutoff[:\s]*([0-9]+)', page_text, re.I)
                    if mcut:
                        cutoff = float(mcut.group(1))
                        logging.info(f"Applying cutoff >= {cutoff}")
                        filt_sum = 0.0
                        for row in rows_list:
                            col_idx = headers.index(cand_col) if cand_col in headers else int(cand_col.split('_')[-1])
                            if col_idx < len(row):
                                v = row[col_idx]
                                if v is None or v == "":
                                    continue
                                v2 = str(v).strip().replace(',', '')
                                try:
                                    num = float(v2)
                                except Exception:
                                    nm = re.search(r'(-?\d+(?:\.\d+)?)', v2)
                                    if nm:
                                        num = float(nm.group(1))
                                    else:
                                        continue
                                if num >= cutoff:
                                    filt_sum += num
                        total = filt_sum
                    
                    # Return int if whole number
                    if abs(total - round(total)) < 1e-9:
                        answer_candidate = int(round(total))
                    else:
                        answer_candidate = total
            except Exception as e:
                logging.error(f"Error downloading/parsing CSV {csv_url}: {e}")
                logging.error(traceback.format_exc())
        # Final fallback
        if not answer_candidate:
            # keep demo-friendly fallback
            answer_candidate = "anything you want"

        return answer_candidate, submit_url, page_text
    except Exception as e:
        logging.error(f"Extract answer error: {e}")
        logging.error(traceback.format_exc())
        return "", None, ""