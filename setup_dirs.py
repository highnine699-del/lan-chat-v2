import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
events_dir = os.path.join(backend_dir, "events")
core_dir = os.path.join(backend_dir, "core")

os.makedirs(events_dir, exist_ok=True)
os.makedirs(core_dir, exist_ok=True)

# Create __init__.py files
open(os.path.join(events_dir, "__init__.py"), "w").close()
open(os.path.join(core_dir, "__init__.py"), "w").close()

print(f"Created {events_dir}")
print(f"Created {core_dir}")
