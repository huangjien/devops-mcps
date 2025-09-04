#!/usr/bin/env python3

from unittest.mock import Mock
import devops_mcps.utils.jenkins.jenkins_client
from devops_mcps.utils.jenkins.jenkins_api import jenkins_get_jobs

print("Before mock assignment:")
print(f"jenkins_client.j = {devops_mcps.utils.jenkins.jenkins_client.j}")
print(f"jenkins_client.j is None = {devops_mcps.utils.jenkins.jenkins_client.j is None}")

# Create mock
mock_jenkins = Mock()
mock_jenkins.keys.return_value = ["job1", "job2"]

# Test the function with proper patching
from unittest.mock import patch
with patch("devops_mcps.utils.jenkins.jenkins_client.j", mock_jenkins):
    print("\nAfter mock patching:")
    print(f"jenkins_client.j = {devops_mcps.utils.jenkins.jenkins_client.j}")
    print(f"jenkins_client.j is None = {devops_mcps.utils.jenkins.jenkins_client.j is None}")
    
    # Test the function
    print("\nCalling jenkins_get_jobs():")
    result = jenkins_get_jobs()
    print(f"Result: {result}")