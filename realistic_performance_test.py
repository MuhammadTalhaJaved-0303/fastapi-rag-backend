#!/usr/bin/env python3
"""
Realistic Performance Testing for RAG Application
Tests both local Ollama limits and cloud API scaling
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

class RealisticPerformanceTester:
    def __init__(self, base_url: str, log_file: str = "realistic_performance_test.jsonl"):
        self.base_url = base_url.rstrip('/')
        self.log_file = log_file
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cloud_requests': 0,
            'local_requests': 0,
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
                user_id = f"test_user_{i}"
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
            async with session.post(url, auth=auth, data=data, timeout=aiohttp.ClientTimeout(total=60)) as response:
                end_time = time.time()
                response_data = await response.json()
                
                # Detect if cloud or local was used
                response_text = response_data.get('response', '')
                is_cloud = any(indicator in str(response_data) for indicator in ['🚀', 'cloud', 'Gemini', 'OpenAI'])
                
                # Log the result
                log_entry = {
                    "timestamp_start": datetime.fromtimestamp(start_time).isoformat(),
                    "timestamp_end": datetime.fromtimestamp(end_time).isoformat(),
                    "duration": round(end_time - start_time, 4),
                    "user_id": user_id,
                    "question": query,
                    "status_code": response.status,
                    "success": response.status == 200,
                    "conversation_id": conversation_id,
                    "model_type": "cloud" if is_cloud else "local"
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
                        if is_cloud:
                            self.stats['cloud_requests'] += 1
                        else:
                            self.stats['local_requests'] += 1
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
                "conversation_id": conversation_id,
                "model_type": "unknown"
            }
            
            with self.lock:
                self.stats['total_requests'] += 1
                self.stats['failed_requests'] += 1
                self.stats['response_times'].append(end_time - start_time)
                self.stats['errors'].append(str(e))
                
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(error_entry) + '\n')
            
            return error_entry
    
    async def run_gradual_load_test(self, questions: List[str], admin_user: str, admin_pass: str):
        """Run a gradual load test to find the breaking point"""
        print("🧪 Running Gradual Load Test")
        print("=" * 40)
        
        # Clear log file
        with open(self.log_file, 'w') as f:
            pass
        
        self.stats['start_time'] = time.time()
        
        # Test phases: gradually increase load
        test_phases = [
            {"users": 1, "rpm": 5, "duration": 1, "name": "Warmup"},
            {"users": 2, "rpm": 10, "duration": 1, "name": "Light Load"},
            {"users": 5, "rpm": 25, "duration": 2, "name": "Medium Load"},
            {"users": 10, "rpm": 50, "duration": 2, "name": "Heavy Load"},
            {"users": 20, "rpm": 100, "duration": 3, "name": "Stress Test"},
            {"users": 50, "rpm": 200, "duration": 3, "name": "Breaking Point"}
        ]
        
        for phase in test_phases:
            print(f"\n🔄 Phase: {phase['name']}")
            print(f"   Users: {phase['users']}, Target RPM: {phase['rpm']}, Duration: {phase['duration']}min")
            
            # Create users for this phase
            await self.create_test_users(phase['users'], admin_user, admin_pass)
            
            # Reset stats for this phase
            phase_start_time = time.time()
            phase_stats = {
                'requests': 0,
                'successes': 0,
                'cloud_usage': 0,
                'local_usage': 0,
                'avg_response_time': 0
            }
            
            # Run the phase
            await self.run_phase(phase['users'], questions, phase['duration'], phase['rpm'])
            
            # Calculate phase results
            phase_duration = time.time() - phase_start_time
            with self.lock:
                phase_requests = self.stats['total_requests']
                phase_successes = self.stats['successful_requests']
                phase_cloud = self.stats['cloud_requests']
                phase_local = self.stats['local_requests']
                
                if self.stats['response_times']:
                    avg_response = statistics.mean(self.stats['response_times'][-phase_requests:])
                else:
                    avg_response = 0
                
                actual_rpm = (phase_requests / phase_duration) * 60 if phase_duration > 0 else 0
                success_rate = (phase_successes / max(1, phase_requests)) * 100
                
                print(f"   ✅ Results:")
                print(f"      Actual RPM: {actual_rpm:.1f}")
                print(f"      Success Rate: {success_rate:.1f}%")
                print(f"      Avg Response Time: {avg_response:.2f}s")
                print(f"      Cloud Requests: {phase_cloud}")
                print(f"      Local Requests: {phase_local}")
                
                # Stop if success rate drops below 80%
                if success_rate < 80:
                    print(f"   ⚠️  Success rate too low, stopping test")
                    break
        
        self.print_final_stats()
    
    async def run_phase(self, num_users: int, questions: List[str], duration_minutes: int, target_rpm: int):
        """Run a single test phase"""
        rpm_per_user = max(1, target_rpm // num_users)
        interval = 60.0 / rpm_per_user
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_progress, daemon=True)
        monitor_thread.start()
        
        # Create sessions and run tests
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for i in range(num_users):
                user_id = f"test_user_{i}"
                password = "test123"
                task = self.run_user_session(session, user_id, password, questions, duration_minutes, rpm_per_user)
                tasks.append(task)
            
            # Run all user sessions concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def run_user_session(self, session: aiohttp.ClientSession, user_id: str, password: str, questions: List[str], duration_minutes: int, requests_per_minute: int):
        """Run a continuous session for one user"""
        conversation_id = f"conv_{user_id}_{int(time.time())}"
        interval = 60.0 / requests_per_minute
        
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            query = random.choice(questions)
            await self.query_async(session, user_id, password, query, conversation_id)
            
            # Wait for next request with jitter
            await asyncio.sleep(interval + random.uniform(-0.1, 0.1))
    
    def monitor_progress(self):
        """Monitor and print progress statistics"""
        while True:
            time.sleep(5)  # Print stats every 5 seconds
            
            with self.lock:
                if self.stats['start_time'] is None:
                    continue
                
                elapsed = time.time() - self.stats['start_time']
                if elapsed < 1:
                    continue
                
                current_rpm = (self.stats['total_requests'] / elapsed) * 60
                success_rate = (self.stats['successful_requests'] / max(1, self.stats['total_requests'])) * 100
                cloud_percentage = (self.stats['cloud_requests'] / max(1, self.stats['successful_requests'])) * 100
                
                if self.stats['response_times']:
                    avg_response_time = statistics.mean(self.stats['response_times'])
                else:
                    avg_response_time = 0
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"RPM: {current_rpm:.1f}, "
                      f"Success: {success_rate:.1f}%, "
                      f"Cloud: {cloud_percentage:.1f}%, "
                      f"Avg: {avg_response_time:.2f}s")
    
    def print_final_stats(self):
        """Print final test statistics"""
        print("\n" + "="*60)
        print("REALISTIC PERFORMANCE TEST RESULTS")
        print("="*60)
        
        elapsed = time.time() - self.stats['start_time']
        actual_rpm = (self.stats['total_requests'] / elapsed) * 60
        success_rate = (self.stats['successful_requests'] / max(1, self.stats['total_requests'])) * 100
        cloud_percentage = (self.stats['cloud_requests'] / max(1, self.stats['successful_requests'])) * 100
        local_percentage = (self.stats['local_requests'] / max(1, self.stats['successful_requests'])) * 100
        
        print(f"Total Duration: {elapsed/60:.1f} minutes")
        print(f"Total Requests: {self.stats['total_requests']}")
        print(f"Successful Requests: {self.stats['successful_requests']}")
        print(f"Failed Requests: {self.stats['failed_requests']}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Actual RPM: {actual_rpm:.1f}")
        print(f"Cloud API Usage: {cloud_percentage:.1f}% ({self.stats['cloud_requests']} requests)")
        print(f"Local Model Usage: {local_percentage:.1f}% ({self.stats['local_requests']} requests)")
        
        if self.stats['response_times']:
            response_times = self.stats['response_times']
            print(f"Average Response Time: {statistics.mean(response_times):.2f}s")
            print(f"Median Response Time: {statistics.median(response_times):.2f}s")
            print(f"Min Response Time: {min(response_times):.2f}s")
            print(f"Max Response Time: {max(response_times):.2f}s")
        
        print(f"\n💡 Recommendations:")
        if cloud_percentage > 50:
            print("   ✅ System successfully used cloud APIs for high load")
            print("   💰 Consider API costs for production use")
        else:
            print("   🏠 System primarily used local model")
            print("   ⚡ Local model is the bottleneck for high throughput")
        
        if success_rate > 95:
            print("   🎯 Excellent reliability")
        elif success_rate > 80:
            print("   ⚠️  Good reliability, monitor for improvements")
        else:
            print("   🚨 Poor reliability, system overloaded")
        
        print(f"\nDetailed logs saved to: {self.log_file}")

def load_questions(file_path: str) -> List[str]:
    """Load questions from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            questions = [line.strip() for line in f if line.strip()]
        return questions[:50]  # Limit to 50 questions for realistic testing
    except FileNotFoundError:
        print(f"Questions file not found: {file_path}")
        return [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "What are neural networks?",
            "Explain deep learning.",
            "What is natural language processing?"
        ] * 10

async def main():
    parser = argparse.ArgumentParser(description="Realistic RAG Performance Tester")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of the RAG API")
    parser.add_argument("--questions", default="test_data/questions.txt", help="Path to questions file")
    parser.add_argument("--admin-user", default="admin", help="Admin username")
    parser.add_argument("--admin-pass", default="admin", help="Admin password")
    parser.add_argument("--log-file", default="realistic_performance_test.jsonl", help="Log file path")
    parser.add_argument("--quick", action="store_true", help="Run quick test (lower load)")
    
    args = parser.parse_args()
    
    # Load questions
    questions = load_questions(args.questions)
    print(f"Loaded {len(questions)} questions")
    
    # Create tester
    tester = RealisticPerformanceTester(args.url, args.log_file)
    
    print("🚀 Realistic Performance Testing")
    print("This test will gradually increase load to find your system's limits")
    print("It will automatically switch between local Ollama and cloud APIs")
    print("-" * 60)
    
    # Run gradual load test
    await tester.run_gradual_load_test(questions, args.admin_user, args.admin_pass)

if __name__ == "__main__":
    asyncio.run(main())