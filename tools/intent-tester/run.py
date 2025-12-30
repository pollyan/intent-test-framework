import sys
import os

# sys.path is already set up to include the current directory (tools/intent-tester)
# which allows 'import backend' to work.

from backend.app import create_app

try:
    app = create_app()
    print("Application created successfully!")
except Exception as e:
    print(f"Failed to create app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == '__main__':
    print("Starting Flask app on port 5002...")
    app.run(debug=True, port=5002)
