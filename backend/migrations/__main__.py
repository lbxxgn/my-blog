"""迁移运行器入口：python -m backend.migrations [status]"""
import sys

from backend.migrations import apply_migrations, print_status

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        print_status()
    else:
        _, _, failed = apply_migrations()
        sys.exit(1 if failed else 0)
