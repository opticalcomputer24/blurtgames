
import requests
import sys
import time
from datetime import datetime
import json

class BlurtQuestTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.username = None

    def run_test(self, name, method, endpoint, expected_status, data=None, auth=False):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"URL: {url}")
        if data:
            print(f"Data: {json.dumps(data)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"Response: {response.json()}")
                except:
                    print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health check endpoint"""
        return self.run_test("API Health Check", "GET", "", 200)

    def test_login(self, username, posting_key):
        """Test login with Blurt credentials"""
        success, response = self.run_test(
            "Blurt Authentication",
            "POST",
            "auth/login",
            200,
            data={"username": username, "posting_key": posting_key}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.username = response['username']
            print(f"Successfully authenticated as {self.username}")
            return True
        return False

    def test_user_profile(self):
        """Test getting user profile"""
        return self.run_test(
            "User Profile",
            "GET",
            "user/profile",
            200,
            auth=True
        )

    def test_get_level(self, level=1):
        """Test getting level questions"""
        success, response = self.run_test(
            f"Get Level {level} Questions",
            "GET",
            f"game/level/{level}",
            200,
            auth=True
        )
        if success:
            print(f"Retrieved {len(response.get('questions', []))} questions for level {level}")
        return success, response

    def test_leaderboard(self):
        """Test getting leaderboard"""
        success, response = self.run_test(
            "Leaderboard",
            "GET",
            "game/leaderboard",
            200
        )
        if success:
            print(f"Retrieved {len(response.get('leaderboard', []))} leaderboard entries")
        return success, response

def main():
    # Get the backend URL from the frontend .env file
    backend_url = "https://74f4ba7c-e333-4a94-a281-0616ad506de4.preview.emergentagent.com"
    
    # Setup tester
    tester = BlurtQuestTester(backend_url)
    
    # Test credentials from the request
    test_username = "ahp07"
    test_posting_key = "5K9Uc6kkb6gLCwhwyNeu4k7xX539Sg3A4TRebgr2MLtBFucfqFd"

    # Run tests
    print("\n===== TESTING BLURT QUEST API =====")
    print(f"Backend URL: {backend_url}")
    print("==================================\n")

    # Test health check
    health_success, health_data = tester.test_health_check()
    if not health_success:
        print("❌ Health check failed, stopping tests")
        return 1
    else:
        print(f"Health check response: {health_data}")

    # Test authentication
    if not tester.test_login(test_username, test_posting_key):
        print("❌ Authentication failed, stopping tests")
        
        # Try to get more information about the Blurt authentication issue
        print("\n🔍 Checking Blurt authentication mechanism...")
        try:
            # Make a direct request to the Blurt API to verify the account exists
            print(f"Note: This test cannot directly verify the posting key without the Blurt API.")
            print(f"The issue might be with the Blurt blockchain connection or the posting key verification.")
            print(f"Check if the beem library is properly installed and configured in the backend.")
        except Exception as e:
            print(f"Error checking Blurt API: {str(e)}")
        
        return 1

    # Test user profile
    profile_success, profile_data = tester.test_user_profile()
    if not profile_success:
        print("❌ User profile retrieval failed")
    else:
        print(f"User profile data: {profile_data}")

    # Test getting level 1 questions
    level_success, level_data = tester.test_get_level(1)
    if not level_success:
        print("❌ Level 1 questions retrieval failed")
    
    # Test leaderboard
    leaderboard_success, _ = tester.test_leaderboard()
    if not leaderboard_success:
        print("❌ Leaderboard retrieval failed")

    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    # Check if quiz questions were initialized
    if level_success:
        total_questions = len(level_data.get('questions', []))
        if total_questions > 0:
            print(f"✅ Quiz questions were initialized successfully (found {total_questions} questions for level 1)")
        else:
            print("❌ No quiz questions found for level 1")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
