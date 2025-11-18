import requests
import time
import json
import argparse
from typing import Dict, List, Optional
import statistics
from datetime import datetime


class EndpointTester:
    """Automated endpoint testing tool for comparing Flask and Rust server performance."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:3000"):
        self.base_url = base_url.rstrip('/')
        self.results = []
    
    def measure_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                       headers: Optional[Dict] = None) -> Dict:
        """
        Execute a single request and measure client-side latency.
        
        Returns dict with timing information and response details.
        """
        url = f"{self.base_url}{endpoint}"
        
        # Measure client-side latency
        start_time = time.time()
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            return {
                'success': True,
                'status_code': response.status_code,
                'latency_ms': latency_ms,
                'response_size': len(response.content),
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            return {
                'success': False,
                'error': str(e),
                'latency_ms': latency_ms,
                'timestamp': datetime.now().isoformat()
            }
    
    def test_endpoint(self, method: str, endpoint: str, iterations: int = 100,
                     data: Optional[Dict] = None, delay_ms: int = 10) -> Dict:
        """
        Test an endpoint multiple times and collect statistics.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            iterations: Number of times to call the endpoint
            data: Request body data (for POST/PUT)
            delay_ms: Delay between requests in milliseconds
        
        Returns:
            Dictionary with aggregated statistics
        """
        print(f"\n{'='*60}")
        print(f"Testing: {method.upper()} {endpoint}")
        print(f"Iterations: {iterations}")
        print(f"{'='*60}\n")
        
        latencies = []
        successes = 0
        failures = 0

        start_time = time.time()
        
        for i in range(iterations):
            # Add client latency header for server-side correlation
            headers = {'x-client-latency-ms': '0'}  # Placeholder
            
            result = self.measure_request(method, endpoint, data, headers)
            
            if result['success']:
                successes += 1
                latencies.append(result['latency_ms'])
            else:
                failures += 1
                print(f"  ❌ Iteration {i+1} failed: {result.get('error', 'Unknown error')}")
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i+1}/{iterations} requests completed")
            
            # Delay between requests
            if delay_ms > 0 and i < iterations - 1:
                time.sleep(delay_ms / 1000.0)

        end_time = time.time()
        total_duration = end_time - start_time
        throughput = iterations / total_duration if total_duration > 0 else 0
        
        # Calculate statistics
        stats = {
            'endpoint': f"{method.upper()} {endpoint}",
            'total_requests': iterations,
            'successful': successes,
            'failed': failures,
            'success_rate': (successes / iterations) * 100 if iterations > 0 else 0,
            'total_duration_sec': total_duration,
            'throughput_rps': throughput,
        }
        
        if latencies:
            stats.update({
                'min_latency_ms': min(latencies),
                'max_latency_ms': max(latencies),
                'mean_latency_ms': statistics.mean(latencies),
                'median_latency_ms': statistics.median(latencies),
                'stddev_latency_ms': statistics.stdev(latencies) if len(latencies) > 1 else 0,
                'p95_latency_ms': self._percentile(latencies, 95),
                'p99_latency_ms': self._percentile(latencies, 99),
            })
        
        self.results.append(stats)
        self._print_stats(stats)
        
        return stats
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a list."""
        sorted_data = sorted(data)
        index = (percentile / 100) * len(sorted_data)
        if index.is_integer():
            return sorted_data[int(index) - 1]
        else:
            lower = sorted_data[int(index) - 1]
            upper = sorted_data[int(index)]
            return lower + (upper - lower) * (index - int(index))
    
    def _print_stats(self, stats: Dict):
        """Pretty print statistics."""
        print(f"\n📊 Results for {stats['endpoint']}:")
        print(f"  Total Requests:  {stats['total_requests']}")
        print(f"  Successful:      {stats['successful']} ({stats['success_rate']:.2f}%)")
        print(f"  Failed:          {stats['failed']}")
        print(f"  Total Duration:  {stats['total_duration_sec']:.2f} s")
        print(f"  Throughput:      {stats['throughput_rps']:.2f} req/s")
        
        if 'mean_latency_ms' in stats:
            print(f"\n  Latency Statistics (ms):")
            print(f"    Min:           {stats['min_latency_ms']:.2f}")
            print(f"    Max:           {stats['max_latency_ms']:.2f}")
            print(f"    Mean:          {stats['mean_latency_ms']:.2f}")
            print(f"    Median:        {stats['median_latency_ms']:.2f}")
            print(f"    Std Dev:       {stats['stddev_latency_ms']:.2f}")
            print(f"    95th %ile:     {stats['p95_latency_ms']:.2f}")
            print(f"    99th %ile:     {stats['p99_latency_ms']:.2f}")
    
    def save_results(self, filename: str = "load_test_results.json"):
        """Save all test results to a JSON file."""
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'results': self.results
            }, f, indent=2)
        print(f"\n✅ Results saved to {filename}")
    
    def print_summary(self):
        """Print a comparative summary of all tested endpoints."""
        if not self.results:
            print("No results to display.")
            return
        
        print(f"\n{'='*80}")
        print("SUMMARY - All Endpoints")
        print(f"{'='*80}\n")
        
        # Sort by mean latency
        sorted_results = sorted(self.results, key=lambda x: x.get('mean_latency_ms', float('inf')))
        
        print(f"{'Endpoint':<40} {'Mean (ms)':<12} {'P95 (ms)':<12} {'Success %':<12}")
        print(f"{'-'*80}")
        
        for result in sorted_results:
            endpoint = result['endpoint'][:38]
            mean = result.get('mean_latency_ms', 0)
            p95 = result.get('p95_latency_ms', 0)
            success = result['success_rate']
            
            print(f"{endpoint:<40} {mean:>10.2f}  {p95:>10.2f}  {success:>10.2f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Automated endpoint load testing tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test READ endpoint 100 times
  python load_tester.py --url http://127.0.0.1:3000 --endpoint /api/read --method GET --iterations 100

  # Test CREATE endpoint 50 times with data
  python load_tester.py --endpoint /api/create --method POST --iterations 50 --data '{"name": "Test", "description": "Test item"}'

  # Run a comprehensive test suite
  python load_tester.py --suite
        """
    )
    
    parser.add_argument('--url', default='http://127.0.0.1:3000',
                       help='Base URL of the server (default: http://127.0.0.1:3000)')
    parser.add_argument('--endpoint', help='API endpoint to test (e.g., /api/read)')
    parser.add_argument('--method', default='GET', choices=['GET', 'POST', 'PUT', 'DELETE'],
                       help='HTTP method (default: GET)')
    parser.add_argument('--iterations', type=int, default=100,
                       help='Number of requests to make (default: 100)')
    parser.add_argument('--delay', type=int, default=10,
                       help='Delay between requests in milliseconds (default: 10)')
    parser.add_argument('--data', type=str,
                       help='JSON data for POST/PUT requests')
    parser.add_argument('--suite', action='store_true',
                       help='Run a comprehensive test suite on all endpoints')
    parser.add_argument('--output', default='load_test_results.json',
                       help='Output file for results (default: load_test_results.json)')
    
    args = parser.parse_args()
    
    tester = EndpointTester(base_url=args.url)
    
    if args.suite:
        # Run comprehensive test suite
        print("🚀 Running comprehensive test suite...\n")
        
        # Test READ operations
        tester.test_endpoint('GET', '/api/read', iterations=args.iterations, delay_ms=args.delay)
        tester.test_endpoint('GET', '/api/database', iterations=args.iterations, delay_ms=args.delay)
        
        # Test CREATE operation
        create_data = {"name": f"LoadTest_{int(time.time())}", "description": "Auto-generated test item"}
        tester.test_endpoint('POST', '/api/create', iterations=args.iterations, 
                           data=create_data, delay_ms=args.delay)
        
        # Test BULK CREATE
        bulk_data = [{"name": f"Bulk_{i}", "description": f"Bulk item {i}"} for i in range(10)]
        tester.test_endpoint('POST', '/api/bulk_create', iterations=20,
                           data=bulk_data, delay_ms=args.delay)
        
        # Print summary
        tester.print_summary()
        
    elif args.endpoint:
        # Test single endpoint
        data = None
        if args.data:
            try:
                data = json.loads(args.data)
            except json.JSONDecodeError:
                print(f"❌ Error: Invalid JSON data: {args.data}")
                return
        
        tester.test_endpoint(args.method, args.endpoint, 
                           iterations=args.iterations, 
                           data=data, 
                           delay_ms=args.delay)
    else:
        parser.print_help()
        return
    
    # Save results
    tester.save_results(args.output)


if __name__ == "__main__":
    main()