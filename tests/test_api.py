"""
Test suite for the Mergington High School Activities API

Tests cover the main endpoints:
- GET /activities - List all activities
- POST /activities/{activity_name}/signup - Sign up for an activity
- DELETE /activities/{activity_name}/unregister - Unregister from an activity
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {"participants": details["participants"].copy(), **{k: v for k, v in details.items() if k != "participants"}}
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        if name in activities:
            activities[name]["participants"] = details["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test successfully retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Verify structure of activities
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
    
    def test_activities_contain_expected_data(self, client):
        """Test that activities contain expected fields and data types"""
        response = client.get("/activities")
        data = response.json()
        
        # Check that Soccer Team exists (from initial data)
        assert "Soccer Team" in data
        soccer = data["Soccer Team"]
        assert isinstance(soccer["max_participants"], int)
        assert isinstance(soccer["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post("/activities/Soccer%20Team/signup?email=test@mergington.edu")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_duplicate_participant(self, client):
        """Test that signing up twice with same email fails"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Soccer%20Team/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Soccer%20Team/signup?email={email}")
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity fails"""
        response = client.post("/activities/Nonexistent%20Activity/signup?email=test@mergington.edu")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_multiple_participants(self, client):
        """Test multiple different participants can sign up"""
        emails = ["user1@mergington.edu", "user2@mergington.edu", "user3@mergington.edu"]
        
        for email in emails:
            response = client.post(f"/activities/Chess%20Club/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all participants were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        chess_participants = activities_data["Chess Club"]["participants"]
        
        for email in emails:
            assert email in chess_participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successfully unregistering from an activity"""
        email = "unregister@mergington.edu"
        
        # First sign up
        client.post(f"/activities/Art%20Club/signup?email={email}")
        
        # Then unregister
        response = client.delete(f"/activities/Art%20Club/unregister?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Art Club"]["participants"]
    
    def test_unregister_not_registered(self, client):
        """Test unregistering when not registered fails"""
        response = client.delete("/activities/Drama%20Club/unregister?email=notregistered@mergington.edu")
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity fails"""
        response = client.delete("/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant from initial data"""
        # james@mergington.edu is already registered for Soccer Team
        response = client.delete("/activities/Soccer%20Team/unregister?email=james@mergington.edu")
        assert response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "james@mergington.edu" not in activities_data["Soccer Team"]["participants"]


class TestRootEndpoint:
    """Tests for root endpoint"""
    
    def test_root_redirects(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert "/static/index.html" in response.headers["location"]


class TestIntegrationScenarios:
    """Integration tests for complete workflows"""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow: signup -> verify -> unregister -> verify"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{activity.replace(' ', '%20')}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities")
        assert len(after_signup.json()[activity]["participants"]) == initial_count + 1
        assert email in after_signup.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity.replace(' ', '%20')}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregister
        after_unregister = client.get("/activities")
        assert len(after_unregister.json()[activity]["participants"]) == initial_count
        assert email not in after_unregister.json()[activity]["participants"]
    
    def test_multiple_activities_same_user(self, client):
        """Test that a user can sign up for multiple different activities"""
        email = "multiactivity@mergington.edu"
        activities_list = ["Soccer Team", "Chess Club", "Art Club"]
        
        # Sign up for multiple activities
        for activity in activities_list:
            response = client.post(f"/activities/{activity.replace(' ', '%20')}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify user is in all activities
        all_activities = client.get("/activities").json()
        for activity in activities_list:
            assert email in all_activities[activity]["participants"]
