#!/usr/bin/env python3

"""
Instagram DM Unsender - Deletes all YOUR messages from a selected chat
Uses instagrapi library to interact with Instagram's API
"""

import os
import sys
import json
import time
import threading
from datetime import datetime

try:
    import msvcrt
except ImportError:
    msvcrt = None

#--- 1. CHECK AND IMPORTS -----
# Make sure user has Python 3.8 or newer (instagrapi needs it)
if sys.version_info < (3, 8):
    print("ERROR: Python 3.8 or higher is required.")
    sys.exit(1)

# Try to import instagrapi, if not installed tell user how to install it
try:
    from instagrapi import Client
    print("INFO: Successfully imported instagrapi.")
except ImportError as e:
    print(f"ERROR: The 'instagrapi' library is not installed. {e}")
    print("Please install it using: pip install instagrapi")
    sys.exit(1)

# --- 2. CONSTANTS AND HELPER FUNCTIONS -----

# We save the login session to a file so we don't have to log in every time
# This prevents Instagram from thinking we're a bot (too many logins = suspicious)
SESSION_FILE = "session.json"
DEFAULT_DELETE_DELAY = 2.0  # seconds between delete requests (increase to be safer)

def get_password():
    """
    Get password from user without showing it on screen.
    Uses getpass if available, falls back to regular input.
    """
    try:
        import getpass
        return getpass.getpass("Enter your Instagram password: ")
    except Exception:
        # Some IDEs don't support getpass, so we use regular input
        print("Note: Password will be visible (getpass not available)")
        return input("Enter your Instagram password: ")

def load_session(client, session_file):
    """
    Try to load a previously saved session.
    If it works, we skip the login step entirely!
    Returns True if session loaded, False if we need to login manually.
    """
    if not os.path.exists(session_file):
        return False
    
    try:
        client.load_settings(session_file)
        # Test if session is still valid by trying to get account info
        client.account_info()
        return True
    except Exception:
        # Session is expired or corrupted, delete it
        try:
            os.remove(session_file)
        except:
            pass
        return False

def save_session(client, session_file):
    """
    Save the current session to a file after successful login.
    Next time we run the program, we can skip logging in.
    """
    try:
        client.dump_settings(session_file)
        return True
    except Exception:
        return False


# --- 3. MAIN CLASS THAT DOES EVERYTHING ---

class IGDMTool:
    """
    The main tool that handles:
    1. Logging into Instagram
    2. Showing your DM conversations
    3. Selecting a conversation
    4. Deleting all YOUR messages from that conversation
    """
    
    def __init__(self):
        """
        Initialize everything when the class is created.
        Sets up the Instagram client and our variables.
        """
        self.client = Client()           # The Instagram client we'll use for everything
        self.logged_in = False           # Track if we're logged in
        self.my_username = None          # Our Instagram username (filled after login)
        self.my_user_id = None           # Our Instagram user ID (filled after login)
        self.threads = []                # Will store all our DM conversations
        self.selected_thread_id = None   # The thread selected for deletion
        self.delete_delay = DEFAULT_DELETE_DELAY
        self.max_delete_retries = 3
    
    # ---- LOGIN ----
    
    def login(self):
        """
        Log into Instagram.
        First tries saved session, then asks for username/password if needed.
        """
        print("\n" + "="*50)
        print("INSTAGRAM LOGIN")
        print("="*50)
        
        # Step 1: Try to load existing session (so we don't have to type password)
        if load_session(self.client, SESSION_FILE):
            try:
                # Get our account info from the saved session
                user_info = self.client.account_info()
                self.my_username = user_info.username
                self.my_user_id = str(user_info.pk)  # pk = primary key (Instagram's user ID)
                self.logged_in = True
                print(f"✓ Logged in as @{self.my_username} (using saved session)")
                return True
            except Exception:
                print("Session expired, need to login again.")
        
        # Step 2: If no session, ask for username and password
        username = input("\nInstagram username: ").strip()
        if not username:
            print("ERROR: Username cannot be empty!")
            return False
        
        password = get_password()
        if not password:
            print("ERROR: Password cannot be empty!")
            return False
        
        # Step 3: Try to login with provided credentials
        try:
            print("Logging in...")
            self.client.login(username, password)
            
            # Get our account info
            user_info = self.client.account_info()
            self.my_username = user_info.username
            self.my_user_id = str(user_info.pk)
            
            # Save the session so we don't have to login next time
            save_session(self.client, SESSION_FILE)
            
            self.logged_in = True
            print(f"✓ Successfully logged in as @{self.my_username}")
            return True
            
        except Exception as e:
            print(f"ERROR: Login failed - {e}")
            return False
    
    # ---- FETCH AND DISPLAY CONVERSATIONS ----
    
    def _start_ctrl_l_listener(self, stop_event):
        """
        Start a background listener that detects Ctrl+L on Windows.
        When Ctrl+L is pressed, it sets the provided stop_event.
        """
        if msvcrt is None:
            return None
        
        def listener():
            while not stop_event.is_set():
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch == '\x0c':  # Ctrl+L
                        stop_event.set()
                        print("\nCtrl+L received: stopping fetch after the current page...")
                        return
                    # discard any other keypress
                time.sleep(0.05)
        thread = threading.Thread(target=listener, daemon=True)
        thread.start()
        return thread

    def fetch_threads(self):
        """
        Get all DM conversations from Instagram.
        Uses the official API endpoint that Instagram's web version uses.
        """
        if not self.logged_in:
            print("ERROR: You must login first!")
            return False
        
        print("\nFetching your conversations...")
        
        try:
            # This calls Instagram's private API directly
            # direct_v2/inbox is the endpoint that returns all your DM threads (conversations)
            response = self.client.private_request("direct_v2/inbox", params={
                "visual_message_return_type": "unified_inbox",
                "thread_message_limit": "10",     # Show last 10 messages per thread preview
                "persistentBadging": "true",
                "thread_limit": "20"              # Get up to 20 conversations
            })
            
            # The response is a big JSON object. We need the "threads" part.
            inbox = response.get("inbox", {})
            self.threads = inbox.get("threads", [])
            
            if not self.threads:
                print("No conversations found!")
                return False
            
            # Display all conversations nicely
            self.display_threads()
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to fetch conversations - {e}")
            return False
    
    def display_threads(self):
        """
        Show all conversations in a nice formatted list.
        For each conversation, show:
        - Who it's with
        - When the last message was
        - A preview of the last message
        """
        print(f"\n{'='*60}")
        print(f"YOUR CONVERSATIONS ({len(self.threads)} total)")
        print(f"{'='*60}")
        
        # Loop through each thread (conversation) and display it
        for i, thread in enumerate(self.threads, 1):
            # Get the thread name (usually the other person's name, or group chat name)
            thread_title = thread.get("thread_title", "Unknown")
            
            # Get all users in this conversation
            users = thread.get("users", [])
            other_usernames = []
            
            # Find everyone in the conversation except us
            for user in users:
                username = user.get("username", "unknown")
                if username != self.my_username:  # Skip ourselves
                    other_usernames.append(f"@{username}")
            
            # Create a readable participants list
            if other_usernames:
                participants = ", ".join(other_usernames)
            else:
                participants = "Note to self"  # Messages you sent to yourself
            # Get last message preview
            last_activity_ts = thread.get("last_activity_at", 0)
            if last_activity_ts:
                # Instagram timestamps are in microseconds, convert to seconds
                activity_time = datetime.fromtimestamp(last_activity_ts / 1_000_000)
                time_str = activity_time.strftime("%Y-%m-%d %H:%M")
            else:
                time_str = "Unknown"
            # Display the conversation info
            print(f"\n[{i}] {thread_title}")
            print(f"    With: {participants}")
            print(f"    Last message: {time_str}")
            print(f"    Thread ID: {thread.get('thread_id')}")
        
        print(f"\n{'='*60}")
    
    # ---- SELECT A CONVERSATION ----
    
    def select_thread(self):
        """
        Let user pick which conversation they want to delete messages from.
        """
        if not self.threads:
            print("ERROR: No conversations loaded. Fetch threads first!")
            return False
        
        # Ask user which conversation they want
        try:
            choice = input("\nEnter the number of the conversation (or 0 to cancel): ").strip()
            choice_num = int(choice)
            
            # Check if they want to cancel
            if choice_num == 0:
                print("Cancelled.")
                return False
            
            # Check if the number is valid
            if choice_num < 1 or choice_num > len(self.threads):
                print(f"ERROR: Please enter a number between 1 and {len(self.threads)}")
                return False
            
            # Get the selected thread (arrays start at 0, so subtract 1)
            selected = self.threads[choice_num - 1]
            thread_id = selected.get("thread_id")
            
            # Show which conversation was selected
            thread_title = selected.get("thread_title", "Unknown")
            users = selected.get("users", [])
            other_users = [f"@{u.get('username')}" for u in users if u.get("username") != self.my_username]
            participants = ", ".join(other_users) if other_users else "Note to self"
            
            print(f"\n✓ Selected conversation: {thread_title}")
            print(f"  With: {participants}")
            
            self.selected_thread_id = thread_id
            return True
            
        except ValueError:
            print("ERROR: Please enter a valid number!")
            return False
    
    # ---- FETCH ALL MESSAGES FROM SELECTED CONVERSATION ----
    
    def fetch_messages(self):
        """
        Get only your own messages from the selected conversation.
        This avoids storing all users' messages and only keeps the messages we need to delete.
        """
        if not self.selected_thread_id:
            print("ERROR: No conversation selected!")
            return None
        
        print(f"\nFetching only your messages from the conversation...")
        print("This might still need to page through the thread, but it will only keep your messages.")
        print("Press Ctrl+L to stop early and continue with deletion using messages already fetched.")
        
        our_messages = []  # Will store only the messages sent by our account
        next_cursor = None  # Used for pagination (getting next page of messages)
        page = 0
        stop_event = threading.Event()
        listener = self._start_ctrl_l_listener(stop_event)
        
        try:
            while not stop_event.is_set():
                page += 1
                # Build the request parameters
                params = {
                    "limit": "20"  # Get 20 messages at a time
                }
                
                # If we have a cursor, add it to get the next page
                if next_cursor:
                    params["cursor"] = next_cursor
                
                # Request messages from this thread
                response = self.client.private_request(
                    f"direct_v2/threads/{self.selected_thread_id}",
                    params=params
                )
                
                # Get the thread data from response
                thread_data = response.get("thread", {})
                messages = thread_data.get("items", [])
                
                if not messages:
                    break  # No more messages
                
                # Keep only our messages from this page
                for msg in messages:
                    sender_id = str(msg.get("user_id", ""))
                    if sender_id == self.my_user_id:
                        our_messages.append(msg)
                
                # Progress indicator
                print(f"  Page {page}: collected {len(our_messages)} of your messages so far...")
                
                # Check if there are more messages to load
                next_cursor = thread_data.get("next_cursor")
                if not next_cursor or stop_event.is_set():
                    break  # No more pages or user requested stop
                
                # Small delay to avoid hitting Instagram's rate limits
                time.sleep(0.5)
            
            if stop_event.is_set():
                print(f"\nStopped early. Collected {len(our_messages)} of your messages so far.")
            else:
                print(f"\n✓ Total messages sent by you: {len(our_messages)}")
            return our_messages
            
        except Exception as e:
            print(f"ERROR: Failed to fetch messages - {e}")
            return None
        finally:
            stop_event.set()
            if listener is not None:
                listener.join(timeout=0.1)

    def count_thread_messages(self):
        """
        Count all messages in the selected conversation.
        This is useful when you just want to know how many messages are in the chat.
        """
        if not self.selected_thread_id:
            print("ERROR: No conversation selected!")
            return None
        
        print(f"\nCounting messages in the selected conversation...")
        total_messages = 0
        my_message_count = 0
        next_cursor = None
        page = 0
        
        try:
            while True:
                page += 1
                params = {
                    "limit": "20"
                }
                if next_cursor:
                    params["cursor"] = next_cursor
                
                response = self.client.private_request(
                    f"direct_v2/threads/{self.selected_thread_id}",
                    params=params
                )
                
                thread_data = response.get("thread", {})
                messages = thread_data.get("items", [])
                
                if not messages:
                    break
                
                for msg in messages:
                    total_messages += 1
                    if str(msg.get("user_id", "")) == self.my_user_id:
                        my_message_count += 1
                
                print(f"  Page {page}: loaded {len(messages)} messages, total so far {total_messages}")
                
                next_cursor = thread_data.get("next_cursor")
                if not next_cursor:
                    break
                
                time.sleep(0.5)
            
            print(f"\n✓ Total messages in conversation: {total_messages}")
            print(f"✓ Messages sent by you: {my_message_count}")
            return total_messages
        except Exception as e:
            print(f"ERROR: Failed to count messages - {e}")
            return None

    def _private_delete(self, item_id):
        """
        Perform the delete private_request for an item_id, handling different instagrapi signatures.
        Raises the last exception on failure.
        """
        endpoint = f"direct_v2/threads/{self.selected_thread_id}/items/{item_id}/delete/"
        try:
            return self.client.private_request(endpoint, method="POST")
        except TypeError:
            # Older instagrapi versions may not accept `method` kwarg
            return self.client.private_request(endpoint)
    
    # ---- DELETE ALL OUR MESSAGES ----
    
    def delete_all_my_messages(self):
        """
        Find and delete ALL messages we sent in the selected conversation.
        This is the main feature of the program!
        """
        # First, get only our messages from the conversation
        our_messages = self.fetch_messages()
        
        if not our_messages:
            print("No messages from you found in this conversation.")
            return False
        
        # Safety: Show what we're about to delete
        print(f"\n{'='*60}")
        print(f"⚠️  ABOUT TO DELETE {len(our_messages)} MESSAGES ⚠️")
        print(f"{'='*60}")
        print(f"This action CANNOT be undone!")
        print(f"These are all messages YOU sent in this conversation.")
        
        # Ask for confirmation before deleting
        confirm = input("\nType 'DELETE' to confirm (anything else to cancel): ").strip()
        
        if confirm != "DELETE":
            print("Operation cancelled. No messages were deleted.")
            return False
        
        # Start deleting messages one by one
        print(f"\nDeleting {len(our_messages)} messages...")

        # Allow user to override delete delay
        try:
            resp = input(f"Enter delay between deletions in seconds (default {self.delete_delay}): ").strip()
            if resp:
                val = float(resp)
                if val >= 0:
                    self.delete_delay = val
        except Exception:
            # keep default if parsing fails
            pass

        deleted_count = 0
        failed_count = 0

        for i, message in enumerate(our_messages, 1):
            item_id = None
            try:
                # Get the message ID (item_id)
                item_id = message.get("item_id")

                if not item_id:
                    print(f"  [{i}/{len(our_messages)}] Skipping - no item ID")
                    failed_count += 1
                    continue

                # Try deleting with retries and exponential backoff on rate-limit/server errors
                attempts = 0
                success = False
                last_exc = None

                while attempts < self.max_delete_retries and not success:
                    attempts += 1
                    try:
                        self._private_delete(item_id)
                        success = True
                        break
                    except Exception as e:
                        last_exc = e
                        err_str = str(e)
                        # Heuristic to detect rate-limit / server-side temporary errors
                        retryable = False
                        if '403' in err_str or '1545003' in err_str or 'please try again' in err_str.lower() or 'rate' in err_str.lower():
                            retryable = True

                        if retryable and attempts < self.max_delete_retries:
                            wait = self.delete_delay * (2 ** (attempts - 1))
                            print(f"  [{i}/{len(our_messages)}] Temporary error detected: {err_str}. Backing off {wait}s (retry {attempts}/{self.max_delete_retries})")
                            time.sleep(wait)
                            continue
                        else:
                            # Non-retryable or out of retries
                            break

                if success:
                    deleted_count += 1
                    print(f"  [{i}/{len(our_messages)}] ✓ Deleted message {item_id}")
                    time.sleep(self.delete_delay)
                else:
                    failed_count += 1
                    print(f"  [{i}/{len(our_messages)}] ✗ Failed to delete {item_id}: {last_exc}")

                # If we get too many errors, maybe Instagram is blocking us
                if failed_count > 5:
                    print("\n⚠️  Too many failures. Stopping to be safe.")
                    print("Instagram might be rate-limiting you. Try again later.")
                    break

            except Exception as e:
                failed_count += 1
                print(f"  [{i}/{len(our_messages)}] ✗ Failed to delete {item_id}: {e}")
                if failed_count > 5:
                    print("\n⚠️  Too many failures. Stopping to be safe.")
                    print("Instagram might be rate-limiting you. Try again later.")
                    break
        
        # Show final results
        print(f"\n{'='*60}")
        print(f"DELETION COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Successfully deleted: {deleted_count} messages")
        if failed_count > 0:
            print(f"✗ Failed to delete: {failed_count} messages")
        
        return True
    
    # ---- MAIN MENU ----
    
    def run(self):
        """
        Main program loop.
        Shows the menu and handles user choices.
        """
        print("\n" + "="*60)
        print("INSTAGRAM DM UNSENDER")
        print("Delete all YOUR messages from any conversation")
        print("="*60)
        
        # First, must login
        if not self.login():
            print("Cannot continue without login. Exiting.")
            return
        
        # Main menu loop
        while True:
            print("\n" + "-"*40)
            print("MAIN MENU")
            print("-"*40)
            print("1. Show my conversations")
            print("2. Select a conversation and count all messages")
            print("3. Select a conversation and delete ALL my messages")
            print("4. Exit")
            
            choice = input("\nWhat would you like to do? (1-4): ").strip()
            
            if choice == "1":
                # Show all conversations
                self.fetch_threads()
                
            elif choice == "2":
                # Count messages in a selected conversation
                if self.fetch_threads():
                    if self.select_thread():
                        self.count_thread_messages()
                
            elif choice == "3":
                # Full workflow: fetch threads, select one, delete messages
                if self.fetch_threads():
                    if self.select_thread():
                        self.delete_all_my_messages()
                
            elif choice == "4":
                print("\nGoodbye! 👋")
                break
                
            else:
                print("Invalid choice! Please enter 1, 2, 3, or 4.")


# --- 4. START THE PROGRAM ---

if __name__ == "__main__":
    """
    This is the entry point of the program.
    It only runs if this file is executed directly (not imported).
    """
    try:
        tool = IGDMTool()  # Create our tool
        tool.run()         # Start the main menu
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\n\nProgram interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
