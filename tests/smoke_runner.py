import subprocess
import sys
import time
from typing import List, Dict

class SmokeTestRunner:
    def __init__(self):
        self.test_modules = [
            "test_auth", "test_course", "test_exam", "test_school",
            "test_billing", "test_trading", "test_curriculum", 
            "test_enrollment", "test_course_progress", "test_admin",
            "test_role", "test_permission", "test_account",
            "test_notification", "test_report", "test_reward_rating",
            "test_stock_options", "test_utility", "test_webhooks"
        ]
        
    def run_all_smoke_tests(self, verbose: bool = False) -> Dict[str, bool]:
        results = {}
        total_start = time.time()
        
        print("🔥 Running comprehensive smoke test suite...")
        print(f"📋 Testing {len(self.test_modules)} modules\n")
        
        for module in self.test_modules:
            start_time = time.time()
            success = self._run_module_tests(module, verbose)
            duration = time.time() - start_time
            
            results[module] = success
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {module} ({duration:.2f}s)")
        
        total_duration = time.time() - total_start
        passed = sum(results.values())
        failed = len(results) - passed
        
        print(f"\n🏁 Smoke test results:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏱️  Total time: {total_duration:.2f}s")
        
        return results
    
    def run_critical_only(self) -> Dict[str, bool]:
        critical_modules = [
            "test_auth", "test_billing", "test_trading", 
            "test_course", "test_enrollment"
        ]
        
        results = {}
        print("🔥 Running critical smoke tests only...\n")
        
        for module in critical_modules:
            success = self._run_module_tests(module, verbose=False)
            results[module] = success
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {module}")
        
        return results
    
    def _run_module_tests(self, module: str, verbose: bool) -> bool:
        cmd = ["pytest", f"tests/endpoints/{module}.py", "-v" if verbose else "-q"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"⚠️  {module} timed out")
            return False
        except Exception as e:
            print(f"⚠️  {module} error: {e}")
            return False

def main():
    runner = SmokeTestRunner()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--critical":
        results = runner.run_critical_only()
    else:
        verbose = "--verbose" in sys.argv
        results = runner.run_all_smoke_tests(verbose)
    
    failed_tests = [module for module, passed in results.items() if not passed]
    
    if failed_tests:
        print(f"\n❌ Failed modules: {', '.join(failed_tests)}")
        sys.exit(1)
    else:
        print(f"\n✅ All smoke tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()