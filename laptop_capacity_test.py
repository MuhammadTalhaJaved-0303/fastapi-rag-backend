#!/usr/bin/env python3
"""
Laptop Capacity Test - Find your local system's RPM limit
Tests gradually increasing load to find the breaking point
"""

import requests
import time
import threading
import json
from datetime import datetime
from collections import deque
import statistics

class LaptopCapacityTester:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': [],
            'start_time': None
        }
        self.lock = threading.Lock()
        self.stop_test = False
    
    def setup_test_user(self):
        """Create a test user for capacity testing"""
        try:
            response = requests.post(
                f"{self.base_url}/admin/users/add",
                auth=("admin", "admin"),
                data={"user_id": "capacity_test", "password": "test123"},
                timeout=10
            )
            if response.status_code in [200, 400]:  # 400 = user already exists
                print("✅ Test user ready")
                return True
            else:
                print(f"❌ Failed to create test user: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error creating test user: {e}")
            return False
    
    def send_query(self, query_id):
        """Send a single query and record results"""
        query = f"What is artificial intelligence? (Query #{query_id})"
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/query/",
                auth=("capacity_test", "test123"),
                data={"query": query},
                timeout=60  # 1 minute timeout
            )
            end_time = time.time()
            duration = end_time - start_time
            
            with self.lock:
                self.stats['total_requests'] += 1
                self.stats['response_times'].append(duration)
                
                if response.status_code == 200:
                    self.stats['successful_requests'] += 1
                    result = response.json()
                    # Check if using local or cloud
                    is_local = "🏠" in str(result) or "local" in str(result).lower()
                    model_type = "Local Ollama" if is_local else "Cloud API"
                    print(f"✅ Query {query_id}: {duration:.1f}s ({model_type})")
                else:
                    self.stats['failed_requests'] += 1
                    self.stats['errors'].append(f"HTTP {response.status_code}")
                    print(f"❌ Query {query_id}: Failed ({response.status_code})")
        
        except requests.exceptions.Timeout:
            end_time = time.time()
            duration = end_time - start_time
            with self.lock:
                self.stats['total_requests'] += 1
                self.stats['failed_requests'] += 1
                self.stats['response_times'].append(duration)
                self.stats['errors'].append("Timeout")
                print(f"⏰ Query {query_id}: Timeout after {duration:.1f}s")
        
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            with self.lock:
                self.stats['total_requests'] += 1
                self.stats['failed_requests'] += 1
                self.stats['response_times'].append(duration)
                self.stats['errors'].append(str(e))
                print(f"❌ Query {query_id}: Error - {e}")
    
    def test_sequential_capacity(self):
        """Test how many sequential requests we can handle"""
        print("\n🔄 Testing Sequential Capacity (one after another)")
        print("-" * 50)
        
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': [],
            'start_time': time.time()
        }
        
        # Send 10 requests one after another
        for i in range(1, 11):
            if self.stop_test:
                break
            print(f"Sending query {i}/10...")
            self.send_query(i)
        
        self.print_results("Sequential")
    
    def test_concurrent_capacity(self, max_concurrent=5):
        """Test concurrent request handling"""
        print(f"\n🔄 Testing Concurrent Capacity ({max_concurrent} simultaneous)")
        print("-" * 50)
        
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': [],
            'start_time': time.time()
        }
        
        # Send concurrent requests
        threads = []
        for i in range(1, max_concurrent + 1):
            thread = threading.Thread(target=self.send_query, args=(i,))
            threads.append(thread)
            thread.start()
            print(f"Started query {i}")
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        self.print_results("Concurrent")
    
    def test_sustained_load(self, duration_minutes=2, target_rpm=10):
        """Test sustained load over time"""
        print(f"\n🔄 Testing Sustained Load ({target_rpm} RPM for {duration_minutes} min)")
        print("-" * 50)
        
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': [],
            'start_time': time.time()
        }
        
        interval = 60.0 / target_rpm  # seconds between requests
        end_time = time.time() + (duration_minutes * 60)
        query_id = 1
        
        print(f"Sending 1 request every {interval:.1f} seconds...")
        
        while time.time() < end_time and not self.stop_test:
            # Send request in background thread
            thread = threading.Thread(target=self.send_query, args=(query_id,))
            thread.start()
            
            query_id += 1
            time.sleep(interval)
        
        # Wait a bit for last requests to complete
        print("Waiting for remaining requests to complete...")
        time.sleep(30)
        
        self.print_results("Sustained Load")
    
    def print_results(self, test_type):
        """Print test results"""
        elapsed = time.time() - self.stats['start_time']
        actual_rpm = (self.stats['total_requests'] / elapsed) * 60 if elapsed > 0 else 0
        success_rate = (self.stats['successful_requests'] / max(1, self.stats['total_requests'])) * 100
        
        print(f"\n📊 {test_type} Test Results:")
        print(f"Duration: {elapsed/60:.1f} minutes")
        print(f"Total Requests: {self.stats['total_requests']}")
        print(f"Successful: {self.stats['successful_requests']}")
        print(f"Failed: {self.stats['failed_requests']}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Actual RPM: {actual_rpm:.1f}")
        
        if self.stats['response_times']:
            response_times = self.stats['response_times']
            print(f"Avg Response Time: {statistics.mean(response_times):.1f}s")
            print(f"Min Response Time: {min(response_times):.1f}s")
            print(f"Max Response Time: {max(response_times):.1f}s")
        
        if self.stats['errors']:
            error_counts = {}
            for error in self.stats['errors']:
                error_counts[error] = error_counts.get(error, 0) + 1
            print(f"Errors: {dict(list(error_counts.items())[:3])}")  # Show top 3 errors
        
        # Capacity assessment
        if success_rate >= 90 and actual_rpm > 0:
            print(f"✅ Your laptop can handle ~{actual_rpm:.0f} RPM reliably")
        elif success_rate >= 70:
            print(f"⚠️ Your laptop can handle ~{actual_rpm:.0f} RPM with some issues")
        else:
            print(f"❌ Your laptop is overloaded at this rate")
    
    def run_full_capacity_test(self):
        """Run complete capacity assessment"""
        print("🚀 Laptop Capacity Assessment")
        print("=" * 50)
        print("This will test your local system's limits")
        print("Make sure your server is running and Ollama is ready")
        
        # Setup
        if not self.setup_test_user():
            return
        
        try:
            # Test 1: Sequential capacity
            self.test_sequential_capacity()
            
            input("\nPress Enter to continue to concurrent test...")
            
            # Test 2: Concurrent capacity
            self.test_concurrent_capacity(max_concurrent=3)
            
            input("\nPress Enter to continue to sustained load test...")
            
            # Test 3: Sustained load
            self.test_sustained_load(duration_minutes=2, target_rpm=6)
            
            # Final recommendations
            self.print_recommendations()
            
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted by user")
            self.stop_test = True
    
    def print_recommendations(self):
        """Print capacity recommendations"""
        print("\n💡 Capacity Recommendations:")
        print("-" * 30)
        
        if self.stats['successful_requests'] > 0:
            avg_response_time = statistics.mean(self.stats['response_times'])
            
            if avg_response_time < 10:
                print("🚀 Excellent: Your system is very responsive")
                print("   Recommended max: 15-20 RPM")
            elif avg_response_time < 20:
                print("✅ Good: Your system handles requests well")
                print("   Recommended max: 8-12 RPM")
            elif avg_response_time < 30:
                print("⚠️ Moderate: Your system is working but slow")
                print("   Recommended max: 4-6 RPM")
            else:
                print("🐌 Slow: Your system is struggling")
                print("   Recommended max: 2-3 RPM")
                print("   Consider adding cloud API keys for better performance")
        
        print("\n🎯 For 1000 RPM performance:")
        print("   • Deploy to AWS with auto-scaling")
        print("   • Use cloud APIs (OpenAI/Gemini)")
        print("   • Add your API keys to backend/.env")

def main():
    print("Laptop Capacity Tester")
    print("=" * 30)
    
    # Check if server is running
    try:
        response = requests.get("http://127.0.0.1:8000/docs", timeout=5)
        if response.status_code != 200:
            print("❌ Server not responding. Please start it first:")
            print("   cd backend && python main.py")
            return
    except:
        print("❌ Cannot connect to server. Please start it first:")
        print("   cd backend && python main.py")
        return
    
    tester = LaptopCapacityTester()
    
    print("\nChoose test type:")
    print("1. Quick test (5 sequential requests)")
    print("2. Concurrent test (3 simultaneous requests)")
    print("3. Sustained load test (6 RPM for 2 minutes)")
    print("4. Full capacity assessment (all tests)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        tester.setup_test_user()
        print("\n🔄 Quick Sequential Test")
        tester.stats['start_time'] = time.time()
        for i in range(1, 6):
            tester.send_query(i)
        tester.print_results("Quick Sequential")
    
    elif choice == "2":
        tester.setup_test_user()
        tester.test_concurrent_capacity(max_concurrent=3)
    
    elif choice == "3":
        tester.setup_test_user()
        tester.test_sustained_load(duration_minutes=2, target_rpm=6)
    
    elif choice == "4":
        tester.run_full_capacity_test()
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()