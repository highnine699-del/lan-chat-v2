import py_compile
import sys

try:
    py_compile.compile('backend/app.py', doraise=True)
    print("SYNTAX CHECK: PASSED - No syntax errors")
except py_compile.PyCompileError as e:
    print(f"SYNTAX CHECK: FAILED - {e}")
    sys.exit(1)
