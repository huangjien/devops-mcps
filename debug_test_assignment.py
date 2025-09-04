#!/usr/bin/env python3

import os
from unittest.mock import Mock, patch

# Set environment variables first
os.environ['JENKINS_URL'] = 'http://test-jenkins.com'
os.environ['JENKINS_USER'] = 'testuser'
os.environ['JENKINS_TOKEN'] = 'testtoken'

# Import the modules
import devops_mcps.utils.jenkins.jenkins_client
from devops_mcps.utils.jenkins.jenkins_api import jenkins_get_jobs

print(f"Initial jenkins_client.j: {devops_mcps.utils.jenkins.jenkins_client.j}")

# Create mock
mock_jenkins = Mock()
mock_jenkins.keys.return_value = ["job1", "job2"]

print(f"Mock jenkins keys: {mock_jenkins.keys()}")

# Test the function with proper patching
with patch("devops_mcps.utils.jenkins.jenkins_client.j", mock_jenkins):
    print(f"After patching jenkins_client.j: {devops_mcps.utils.jenkins.jenkins_client.j}")
    with patch("devops_mcps.utils.jenkins.jenkins_api.cache") as mock_cache:
        mock_cache.get.return_value = None
        with patch("devops_mcps.utils.jenkins.jenkins_converters._to_dict", side_effect=lambda x: f"dict_{x}"):
            result = jenkins_get_jobs()
            print(f"Result: {result}")