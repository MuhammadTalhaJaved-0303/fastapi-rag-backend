#!/usr/bin/env python3
"""
High-Performance Load Testing Script for RAG Application
Supports 1000+ requests per minute with detailed monitoring
"""

import asyncio
import aiohttp
import time
import json
import random
import argparse
from datetime import datetime
from typing import List, Dict, Any
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor
import os

class PerformanceTester:
    def __init__(self, base_url: str, log_file: str = "performance_test.jsonl"):
        self.base_url = base_url.rstrip('/')
        self.log_file = log_file
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'start_time': None,
            'errors': []
        }
        self.lock = threading.Lock()
    
    async def create_test_users(self, num_users: int, admin_user: str, admin_pass: str):
        """Create test users asynchronously"""
        print(f"Creating {num_users} test users...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_users):
                user_id = f"perf_user_{i}"
                password = "test123"
                task = self.add_user_async(session, admin_user, admin_pass, user_id, password)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if not isinstance(r, Exception))
            print(f"Created {successful}/{num_users} users successfully")
    
    async def add_user_async(self, session: aiohttp.ClientSession, admin_user: str, admin_pass: str, user_id: str, password: str):
        """Add user asynchronously"""
        url = f"{self.base_url}/admin/users/add"
        auth = aiohttp.BasicAuth(admin_user, admin_pass)
        data = {"user_id": user_id, "password": password}
        
        try:
            async with session.post(url, auth=auth, data=data) as response:
                return await response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def query_async(self, session: aiohttp.ClientSession, user_id: str, password: str, query: str, conversation_id: str = None):
        """Send query asynchronously"""
        url = f"{self.base_url}/query/"
        auth = aiohttp.BasicAuth(user_id, password)
        data = {"query": query}
        if conversation_id:
            data["conversation_id"] = conversation_id
        
        start_time = time.time()
        try:
            async with session.post(url, auth=auth, data=data, timeout=aiohttp.ClientTimeout(total=120)) as response:
                end_time = time.time()
                response_data = await response.json()
                
                # Log the result
                log_entry = {
                    "timestamp_start": datetime.fromtimestamp(start_time).isoformat(),
                    "timestamp_end": datetime.fromtimestamp(end_time).isoformat(),
                    "duration": round(end_time - start_time, 4),
                    "user_id": user_id,
                    "question": query,
                    "status_code": response.status,
                    "success": response.status == 200,
                    "conversation_id": conversation_id
                }
                
                if response.status == 200:
                    log_entry.update({
                        "answer": response_data.get('response', 'NO_RESPONSE'),
                        "prompt": response_data.get('prompt', 'NO_PROMPT')
                    })
                else:
                    log_entry["error"] = response_data.get('detail', 'Unknown error')
                
                with self.lock:
                    self.stats['total_requests'] += 1
                    self.stats['response_times'].append(end_time - start_time)
                    
                    if response.status == 200:
                        self.stats['successful_requests'] += 1
                    else:
                        self.stats['failed_requests'] += 1
                        self.stats['errors'].append(f"Status {response.status}: {response_data}")
                    
                    # Write to log file
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_entry) + '\n')
                
                return log_entry
                
        except Exception as e:
            end_time = time.time()
            error_entry = {
                "timestamp_start": datetime.fromtimestamp(start_time).isoformat(),
                "timestamp_end": datetime.fromtimestamp(end_time).isoformat(),
                "duration": round(end_time - start_time, 4),
                "user_id": user_id,
                "question": query,
                "success": False,
                "error": str(e),
                "conversation_id": conversation_id
            }
            
            with self.lock:
                self.stats['total_requests'] += 1
                self.stats['failed_requests'] += 1
                self.stats['response_times'].append(end_time - start_time)
                self.stats['errors'].append(str(e))
                
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(error_entry) + '\n')
            
            return error_entry
    
    async def run_user_session(self, session: aiohttp.ClientSession, user_id: str, password: str, questions: List[str], duration_minutes: int, requests_per_minute: int):
        """Run a continuous session for one user"""
        conversation_id = f"conv_{user_id}_{int(time.time())}"
        interval = 60.0 / requests_per_minute  # seconds between requests
        
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            query = random.choice(questions)
            await self.query_async(session, user_id, password, query, conversation_id)
            
            # Wait for next request
            await asyncio.sleep(interval + random.uniform(-0.1, 0.1))  # Add small jitter
    
    async def run_load_test(self, num_users: int, questions: List[str], duration_minutes: int, target_rpm: int, admin_user: str, admin_pass: str):
        """Run the main load test"""
        print(f"Starting load test:")
        print(f"  Users: {num_users}")
        print(f"  Duration: {duration_minutes} minutes")
        print(f"  Target RPM: {target_rpm}")
        print(f"  Questions: {len(questions)}")
        
        # Clear log file
        with open(self.log_file, 'w') as f:
            pass
        
        self.stats['start_time'] = time.time()
        
        # Create test users
        await self.create_test_users(num_users, admin_user, admin_pass)
        
        # Calculate requests per minute per user
        rpm_per_user = max(1, target_rpm // num_users)
        
        print(f"Each user will make ~{rpm_per_user} requests per minute")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_progress, daemon=True)
        monitor_thread.start()
        
        # Create sessions and run tests
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i in range(num_users):
                user_id = f"perf_user_{i}"
                password = "test123"
                task = self.run_user_session(session, user_id, password, questions, duration_minutes, rpm_per_user)
                tasks.append(task)
            
            # Run all user sessions concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.print_final_stats()
    
    def monitor_progress(self):
        """Monitor and print progress statistics"""
        while True:
            time.sleep(10)  # Print stats every 10 seconds
            
            with self.lock:
                if self.stats['start_time'] is None:
                    continue
                
                elapsed = time.time() - self.stats['start_time']
                if elapsed < 1:
                    continue
                
                current_rpm = (self.stats['total_requests'] / elapsed) * 60
                success_rate = (self.stats['successful_requests'] / max(1, self.stats['total_requests'])) * 100
                
                if self.stats['response_times']:
                    avg_response_time = statistics.mean(self.stats['response_times'])
                    p95_response_time = statistics.quantiles(self.stats['response_times'], n=20)[18] if len(self.stats['response_times']) > 20 else avg_response_time
                else:
                    avg_response_time = 0
                    p95_response_time = 0
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Requests: {self.stats['total_requests']}, "
                      f"RPM: {current_rpm:.1f}, "
                      f"Success: {success_rate:.1f}%, "
                      f"Avg Response: {avg_response_time:.2f}s, "
                      f"P95: {p95_response_time:.2f}s")
    
    def print_final_stats(self):
        """Print final test statistics"""
        print("\n" + "="*60)
        print("FINAL TEST RESULTS")
        print("="*60)
        
        elapsed = time.time() - self.stats['start_time']
        actual_rpm = (self.stats['total_requests'] / elapsed) * 60
        success_rate = (self.stats['successful_requests'] / max(1, self.stats['total_requests'])) * 100
        
        print(f"Total Duration: {elapsed/60:.1f} minutes")
        print(f"Total Requests: {self.stats['total_requests']}")
        print(f"Successful Requests: {self.stats['successful_requests']}")
        print(f"Failed Requests: {self.stats['failed_requests']}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Actual RPM: {actual_rpm:.1f}")
        
        if self.stats['response_times']:
            response_times = self.stats['response_times']
            print(f"Average Response Time: {statistics.mean(response_times):.2f}s")
            print(f"Median Response Time: {statistics.median(response_times):.2f}s")
            print(f"Min Response Time: {min(response_times):.2f}s")
            print(f"Max Response Time: {max(response_times):.2f}s")
            
            if len(response_times) > 20:
                quantiles = statistics.quantiles(response_times, n=20)
                print(f"P95 Response Time: {quantiles[18]:.2f}s")
                print(f"P99 Response Time: {quantiles[19]:.2f}s")
        
        if self.stats['errors']:
            print(f"\nTop Errors:")
            error_counts = {}
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {count}x: {error}")
        
        print(f"\nDetailed logs saved to: {self.log_file}")

def load_questions(file_path: str) -> List[str]:
    """Load questions from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            questions = [line.strip() for line in f if line.strip()]
        return questions
    except FileNotFoundError:
        print(f"Questions file not found: {file_path}")
        # Return default questions
        return [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "What are the benefits of cloud computing?",
            "Explain natural language processing.",
            "What is the difference between AI and ML?"
        ] * 100  # Repeat to have enough questions

async def main():
    parser = argparse.ArgumentParser(description="High-Performance RAG Load Tester")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of the RAG API")
    parser.add_argument("--users", type=int, default=300, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=10, help="Test duration in minutes")
    parser.add_argument("--rpm", type=int, default=1000, help="Target requests per minute")
    parser.add_argument("--questions", default="test_data/questions.txt", help="Path to questions file")
    parser.add_argument("--admin-user", default="admin", help="Admin username")
    parser.add_argument("--admin-pass", default="admin", help="Admin password")
    parser.add_argument("--log-file", default="performance_test.jsonl", help="Log file path")
    
    args = parser.parse_args()
    
    # Load questions
    questions = load_questions(args.questions)
    print(f"Loaded {len(questions)} questions")
    
    # Create tester
    tester = PerformanceTester(args.url, args.log_file)
    
    # Run test
    await tester.run_load_test(
        num_users=args.users,
        questions=questions,
        duration_minutes=args.duration,
        target_rpm=args.rpm,
        admin_user=args.admin_user,
        admin_pass=args.admin_pass
    )

if __name__ == "__main__":
    asyncio.run(main())