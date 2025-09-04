import os
from unittest.mock import patch, Mock
from devops_mcps.utils.jenkins.jenkins_api import jenkins_get_recent_failed_builds

def debug_test():
    print("Testing environment variable access in jenkins_get_recent_failed_builds...")
    
    with patch.dict(os.environ, {"JENKINS_URL": "http://test-jenkins.com", "JENKINS_USER": "testuser", "JENKINS_TOKEN": "testtoken"}):
        print("Environment variables set:")
        print(f"JENKINS_URL: {os.environ.get('JENKINS_URL')}")
        print(f"JENKINS_USER: {os.environ.get('JENKINS_USER')}")
        print(f"JENKINS_TOKEN: {os.environ.get('JENKINS_TOKEN')}")
        
        # Mock the cache and requests
        with patch("devops_mcps.utils.jenkins.jenkins_api.cache") as mock_cache:
            with patch("devops_mcps.utils.jenkins.jenkins_api.requests.get") as mock_requests_get:
                mock_cache.get.return_value = None
                
                mock_response = Mock()
                mock_response.json.return_value = {
                    "jobs": [
                        {
                            "name": "test-job",
                            "lastBuild": {
                                "number": 123,
                                "timestamp": 1640995200000,  # Recent timestamp
                                "result": "FAILURE"
                            }
                        }
                    ]
                }
                mock_requests_get.return_value = mock_response
                
                result = jenkins_get_recent_failed_builds(8)
                print(f"Result: {result}")

if __name__ == '__main__':
    debug_test()