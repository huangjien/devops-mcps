from unittest.mock import Mock, patch
from devops_mcps.utils.jenkins.jenkins_api import jenkins_get_recent_failed_builds
import os

# Set environment variables
os.environ['JENKINS_URL'] = 'http://test-jenkins.com'
os.environ['JENKINS_USER'] = 'test_user'
os.environ['JENKINS_TOKEN'] = 'test_token'

print("Testing cache behavior in jenkins_get_recent_failed_builds...")

with patch('devops_mcps.utils.jenkins.jenkins_api.cache') as mock_cache:
    mock_cache.get.return_value = None
    print('Mock cache.get.return_value:', mock_cache.get.return_value)
    
    # Test the cache.get call directly
    cache_result = mock_cache.get('test_key')
    print('Direct cache.get result:', cache_result, type(cache_result))
    print('Direct cache.get result is None:', cache_result is None)
    print('Direct cache.get result bool:', bool(cache_result))
    
    # Now test the actual function
    print('\nCalling jenkins_get_recent_failed_builds...')
    try:
        result = jenkins_get_recent_failed_builds(hours_ago=8)
        print('Function result:', result)
        print('Function result type:', type(result))
        print('Function result repr:', repr(result))
    except Exception as e:
        print('Exception:', e)
        import traceback
        traceback.print_exc()