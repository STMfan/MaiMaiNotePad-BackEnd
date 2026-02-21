#!/bin/bash
# 单独运行并行隔离测试
# 这些测试内部会启动并行测试，不应该在主测试套件中运行

echo "=========================================="
echo "Running Parallel Isolation Tests"
echo "=========================================="
echo ""

echo "Test 1: Parallel Execution Isolation"
echo "--------------------------------------"
python -m pytest tests/property/test_parallel_isolation.py::TestParallelIsolation::test_parallel_execution_isolation -v --tb=short --run-parallel-isolation
TEST1_RESULT=$?

echo ""
echo "Test 2: Authenticated Client Isolation"
echo "--------------------------------------"
python -m pytest tests/property/test_parallel_isolation.py::TestDependencyOverrideIsolation::test_authenticated_client_isolation -v --tb=short --run-parallel-isolation
TEST2_RESULT=$?

echo ""
echo "Test 3: Single Test Execution Preservation"
echo "--------------------------------------"
python -m pytest tests/property/test_preservation.py::TestSingleTestExecution::test_single_test_execution_passes -v --tb=short --run-parallel-isolation
TEST3_RESULT=$?

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
if [ $TEST1_RESULT -eq 0 ] && [ $TEST2_RESULT -eq 0 ] && [ $TEST3_RESULT -eq 0 ]; then
    echo "✓ All parallel isolation tests passed"
    exit 0
else
    echo "✗ Some parallel isolation tests failed"
    [ $TEST1_RESULT -ne 0 ] && echo "  - test_parallel_execution_isolation: FAILED"
    [ $TEST2_RESULT -ne 0 ] && echo "  - test_authenticated_client_isolation: FAILED"
    [ $TEST3_RESULT -ne 0 ] && echo "  - test_single_test_execution_passes: FAILED"
    exit 1
fi
