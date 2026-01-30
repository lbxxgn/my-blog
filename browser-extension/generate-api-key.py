#!/usr/bin/env python3
"""
Generate API Key for Browser Extension Testing

This script helps you generate an API key for testing the browser extension.
Run it from the backend directory.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from models import get_user_by_username, generate_api_key, validate_api_key

def main():
    print("=" * 60)
    print("Browser Extension - API Key Generator")
    print("=" * 60)
    print()

    # Get username
    username = input("Enter your username: ").strip()

    if not username:
        print("❌ Username cannot be empty")
        return 1

    # Get user
    print(f"\n🔍 Looking up user '{username}'...")
    user = get_user_by_username(username)

    if not user:
        print(f"❌ User '{username}' not found")
        print("\nAvailable users:")

        from models import get_all_users
        users = get_all_users()

        if users:
            for u in users:
                print(f"  - {u['username']} (ID: {u['id']}, Role: {u['role']})")
        else:
            print("  (No users found)")

        return 1

    user_id = user['id']
    print(f"✅ Found user: {username} (ID: {user_id})")

    # Generate API key
    print(f"\n🔑 Generating API key...")
    api_key = generate_api_key(user_id)

    print(f"\n✅ API Key generated successfully!")
    print()
    print("=" * 60)
    print("YOUR API KEY (copy this):")
    print("=" * 60)
    print()
    print(api_key)
    print()
    print("=" * 60)
    print()

    # Verify it works
    print("🔍 Verifying API key...")
    validated_user_id = validate_api_key(api_key)
    if validated_user_id == user_id:
        print("✅ API key verified successfully!")
    else:
        print("❌ API key validation failed")
        return 1

    # Instructions
    print()
    print("Next Steps:")
    print("1. Copy the API key above")
    print("2. Open the browser extension popup")
    print("3. Click the Settings (⚙️) button")
    print("4. Paste the API key")
    print("5. Start testing!")
    print()
    print("For testing instructions, see: TESTING.md")
    print()

    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
