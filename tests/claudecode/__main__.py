"""Allow running as: python -m tests.claudecode"""

import sys
from .cli import main

sys.exit(main())
