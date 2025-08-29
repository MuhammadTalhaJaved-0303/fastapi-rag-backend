import os
import sys
import json

# Add the backend directory to the path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services import get_user_db, remove_user_data

def remove_all_users_except_admin():
    """
    Removes all users from the system except for the 'admin' user.
    It iterates through the users and removes them one by one.
    """
    print("Starting the process of removing all non-admin users...")
    
    users_db = get_user_db()
    
    # It's important to create a separate list of users to remove,
    # as you shouldn't modify a dictionary while iterating over it.
    users_to_remove = [user_id for user_id in users_db if user_id != 'admin']
    
    if not users_to_remove:
        print("No users to remove (other than 'admin').")
        return

    print(f"Found the following users to remove: {', '.join(users_to_remove)}")
    
    for user_id in users_to_remove:
        print(f"--- Removing user: {user_id} ---")
        success, message = remove_user_data(user_id)
        if success:
            print(f"Successfully removed '{user_id}' and their data.")
        else:
            # This case might occur if data is in an inconsistent state
            print(f"Could not remove '{user_id}'. Reason: {message}")

    print("\nProcess finished. All specified users have been removed.")

if __name__ == "__main__":
    remove_all_users_except_admin()
