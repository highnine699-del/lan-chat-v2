import sys
sys.path.insert(0, 'backend')
print("TEST: Starting import")
try:
    import app
    print("TEST: Import successful")
except Exception as e:
    print(f"TEST: Import failed: {e}")
    import traceback
    traceback.print_exc()
