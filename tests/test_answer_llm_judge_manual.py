"""
Manual test script for Task 4: Answer Score Improvements

This script tests the updated llm_judge function with different answer types.
From project root, run with: uv run tests/python test_task4_manual.py
"""

from gnw_evals.evaluators.llm_judges import llm_judge

# Test cases for each answer type
test_cases = [
    # BOOLEAN tests
    {
        "name": "Boolean - TRUE match",
        "expected": "TRUE",
        "actual": "Yes, the statement is true.",
        "should_match": True
    },
    {
        "name": "Boolean - FALSE match",
        "expected": "FALSE",
        "actual": "No, this is incorrect.",
        "should_match": True
    },
    {
        "name": "Boolean - mismatch",
        "expected": "TRUE",
        "actual": "No, the statement is false.",
        "should_match": False
    },
    
    # NUMERIC tests
    {
        "name": "Numeric - within 5% tolerance",
        "expected": "198.4 hectares",
        "actual": "200 hectares",
        "should_match": True
    },
    {
        "name": "Numeric - exceeds 5% tolerance",
        "expected": "211 kha",
        "actual": "230 kha",
        "should_match": False
    },
    {
        "name": "Numeric - percentage match",
        "expected": "0.20%",
        "actual": "0.19%",
        "should_match": True
    },
    
    # YEAR tests
    {
        "name": "Year - exact match",
        "expected": "2015",
        "actual": "The year was 2015",
        "should_match": True
    },
    {
        "name": "Year - mismatch",
        "expected": "2015",
        "actual": "The year was 2016",
        "should_match": False
    },
    
    # NAMED_ENTITY tests
    {
        "name": "Named entity - country match",
        "expected": "Brazil",
        "actual": "Brazil had the most",
        "should_match": True
    },
    {
        "name": "Named entity - mismatch",
        "expected": "Brazil",
        "actual": "Australia had the most",
        "should_match": False
    },
    {
        "name": "Named entity - region match",
        "expected": "South Dakota",
        "actual": "South Dakota",
        "should_match": True
    }
]

def run_tests():
    print("=" * 80)
    print("Task 4: Answer Score Improvements - Manual Test")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print(f"  Expected: {test['expected']}")
        print(f"  Actual:   {test['actual']}")
        
        try:
            score = llm_judge(test['expected'], test['actual'])
            expected_score = 1 if test['should_match'] else 0
            
            if score == expected_score:
                print(f"  ✅ PASS - Score: {score}")
                passed += 1
            else:
                print(f"  ❌ FAIL - Expected score: {expected_score}, Got: {score}")
                failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1
        
        print()
    
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
