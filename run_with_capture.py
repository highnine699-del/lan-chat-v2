import sys
import traceback
import os

# Redirect stdout and stderr to a file
log_file = open('execution_log.txt', 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

try:
    print("=" * 60)
    print("EXECUTION START")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current directory: {os.getcwd()}")
    print("=" * 60)
    
    # Change to backend directory
    os.chdir('backend')
    print(f"Changed to: {os.getcwd()}")
    
    # Import and run app
    print("Importing app module...")
    import app
    print("App module imported successfully")
    
    # Check if __name__ is __main__
    print(f"__name__ = {__name__}")
    
    # Run the main block manually
    print("Running main block...")
    import uvicorn
    uvicorn.run(app.app, host="0.0.0.0", port=8000)
    
except Exception as e:
    print("=" * 60)
    print("ERROR OCCURRED")
    print("=" * 60)
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {e}")
    print("=" * 60)
    print("TRACEBACK:")
    print("=" * 60)
    traceback.print_exc()
    print("=" * 60)
finally:
    log_file.close()
