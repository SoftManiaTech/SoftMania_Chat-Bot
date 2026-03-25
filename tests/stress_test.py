import asyncio
import aiohttp
import time
import json
import random
import statistics

import argparse

URL = "http://localhost:7860/query"

# Defaults (can be overridden via CLI)
NUM_USERS = 200
RATE_PER_MIN = 200
REQUEST_TIMEOUT = 300
RETRIES = 1

# To test the response input text and output text properly, we must hit the /query 
# endpoint instead of /webhook (which only returns {"status": "ok"}).
TEST_QUESTIONS = [
    "Hi!",
    "What is the menu?",
    "Tell me about SoftMania.",
    "Can you help me?",
    "How can I contact you?",
    "What services do you provide?",
    "Are you a RAG chatbot?"
]

async def simulate_user(session, user_id, retries=RETRIES):
    question = random.choice(TEST_QUESTIONS)
    session_id = f"stress_test_user_{user_id:04d}"
    
    payload = {
        "question": question,
        "session_id": session_id
    }

    attempt = 0
    start_time = time.time()
    try:
        while True:
            attempt += 1
            try:
                async with session.post(URL, json=payload, headers={"Content-Type": "application/json"}) as response:
                    status = response.status
                    if status == 200:
                        data = await response.json()
                        answer = data.get("answer", "NO ANSWER")
                    else:
                        # Try to parse JSON error if available
                        try:
                            answer = await response.json()
                        except Exception:
                            answer = await response.text()

                    elapsed = time.time() - start_time
                    return elapsed, status, user_id, question, answer
            except Exception as e:
                if attempt <= retries:
                    await asyncio.sleep(1 * attempt)
                    continue
                elapsed = time.time() - start_time
                return elapsed, 500, user_id, question, f"ERROR: {str(e)}"
    except Exception as e:
        return time.time() - start_time, 500, user_id, question, f"ERROR: {str(e)}"

async def main():
    print(f"--- STARTING STRESS TEST ---")
    print(f"Simulating {NUM_USERS} concurrent requests to the /query API...\n")
    
    start_time = time.time()
    connector = aiohttp.TCPConnector(limit_per_host=1000)

    # We use a timeout to prevent the script from hanging forever if the server chokes
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    interval = 60.0 / RATE_PER_MIN

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        for i in range(NUM_USERS):
            tasks.append(asyncio.create_task(simulate_user(session, i, retries=RETRIES)))
            await asyncio.sleep(interval)

        results = await asyncio.gather(*tasks)
        
    times = []
    successes = 0
    errors = 0
    
    # Save the log file completely
    log_name = f"tests/stress_test_{NUM_USERS}_results.log"
    with open(log_name, "w", encoding="utf-8") as log_file:
        log_file.write(f"--- {NUM_USERS} USER STRESS TEST LOG ---\n")
        log_file.write("-" * 80 + "\n\n")
        
        for elapsed, status, user_id, q, a in results:
            times.append(elapsed)
            if status == 200:
                successes += 1
            else:
                errors += 1
                
            # Append each response to the file
            log_file.write(f"User ID: {user_id:04d} | Status: {status} | Time: {elapsed:.2f}s\n")
            log_file.write(f"Input:  {q}\n")
            
            # Ensure the answer is cast to a string (if the response was a JSON error dict)
            formatted_answer = str(a).strip()
            log_file.write(f"Output: {formatted_answer}\n")
            
            log_file.write("-" * 80 + "\n")
                
        total_time = time.time() - start_time

        # Guard against empty times
        if times:
            min_t = min(times)
            max_t = max(times)
            avg_t = statistics.mean(times)
            med_t = statistics.median(times)
        else:
            min_t = max_t = avg_t = med_t = 0.0

        summary = f"""
    ==================================================
    --- STRESS TEST SUMMARY ---
    ==================================================
    Total processing time:     {total_time:.2f} seconds
    Successful Requests (200): {successes}
    Failed Requests:           {errors}
    Minimum response time:     {min_t:.2f} seconds
    Maximum response time:     {max_t:.2f} seconds
    Average response time:     {avg_t:.2f} seconds
    Median response time:      {med_t:.2f} seconds
    ==================================================
    """
        log_file.write(summary)
        print(summary)
        print(f"Detailed logs saved to {log_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stress test the /query endpoint")
    parser.add_argument("--num", type=int, default=NUM_USERS, help="Total number of requests to send")
    parser.add_argument("--rate", type=int, default=RATE_PER_MIN, help="Requests per minute")
    parser.add_argument("--timeout", type=int, default=REQUEST_TIMEOUT, help="Per-request total timeout seconds")
    parser.add_argument("--retries", type=int, default=RETRIES, help="Number of retries on failure")

    args = parser.parse_args()
    NUM_USERS = args.num
    RATE_PER_MIN = args.rate
    REQUEST_TIMEOUT = args.timeout
    RETRIES = args.retries

    asyncio.run(main())
