
from beem import Blurt
from beem.account import Account
from beem.exceptions import AccountDoesNotExistsException
import sys

def verify_blurt_posting_key(username, posting_key):
    """Verify Blurt posting key for the given username"""
    try:
        print(f"Connecting to Blurt blockchain...")
        blurt_instance = Blurt()
        print(f"Connected successfully")
        
        try:
            print(f"Checking if account '{username}' exists...")
            account = Account(username, blockchain_instance=blurt_instance)
            print(f"Account found: {account.name}")
            
            # Check if the posting key is valid for this account
            print(f"Verifying posting key...")
            print(f"Account posting keys: {account.posting_keys}")
            
            is_valid = posting_key in account.posting_keys
            if is_valid:
                print(f"✅ Posting key is valid for account {username}")
            else:
                print(f"❌ Posting key is invalid for account {username}")
            
            return is_valid
        except AccountDoesNotExistsException:
            print(f"❌ Account '{username}' does not exist on Blurt blockchain")
            return False
        except Exception as e:
            print(f"❌ Error verifying account: {str(e)}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to Blurt blockchain: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test_blurt_auth.py <username> <posting_key>")
        sys.exit(1)
    
    username = sys.argv[1]
    posting_key = sys.argv[2]
    
    print(f"Testing Blurt authentication for user: {username}")
    result = verify_blurt_posting_key(username, posting_key)
    
    if result:
        print("Authentication successful")
        sys.exit(0)
    else:
        print("Authentication failed")
        sys.exit(1)
