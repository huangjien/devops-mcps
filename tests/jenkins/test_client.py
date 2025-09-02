"""
Unit tests for Jenkins client module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from src.devops_mcps.jenkins.client import (
    initialize_jenkins_client,
    get_jenkins_client,
    set_jenkins_client_for_testing,
    check_jenkins_config,
    get_jenkins_env_vars
)


class TestJenkinsClient(unittest.TestCase):
    """Test cases for Jenkins client functionality."""

    def setUp(self):
        """Set up test environment."""
        # Clear any existing client
        set_jenkins_client_for_testing(None)
        
        # Clear environment variables
        for var in ['JENKINS_URL', 'JENKINS_USER', 'JENKINS_TOKEN']:
            if var in os.environ:
                del os.environ[var]

    def tearDown(self):
        """Clean up after tests."""
        # Clear any test client
        set_jenkins_client_for_testing(None)
        
        # Clear environment variables
        for var in ['JENKINS_URL', 'JENKINS_USER', 'JENKINS_TOKEN']:
            if var in os.environ:
                del os.environ[var]

    @patch('src.devops_mcps.jenkins.client.Jenkins')
    def test_initialize_jenkins_client_success(self, mock_jenkins):
        """Test successful Jenkins client initialization."""
        # Set environment variables
        os.environ['JENKINS_URL'] = 'http://jenkins.example.com'
        os.environ['JENKINS_USER'] = 'test_user'
        os.environ['JENKINS_TOKEN'] = 'test_token'
        
        # Mock Jenkins instance
        mock_instance = MagicMock()
        mock_jenkins.return_value = mock_instance
        
        # Initialize client
        result = initialize_jenkins_client()
        
        # Assertions
        self.assertTrue(result)
        mock_jenkins.assert_called_once_with(
            'http://jenkins.example.com',
            username='test_user',
            password='test_token',
            timeout=30
        )
        
        # Verify client is set
        client = get_jenkins_client()
        self.assertEqual(client, mock_instance)

    def test_initialize_jenkins_client_missing_url(self):
        """Test Jenkins client initialization with missing URL."""
        # Set only user and token
        os.environ['JENKINS_USER'] = 'test_user'
        os.environ['JENKINS_TOKEN'] = 'test_token'
        
        # Initialize client
        result = initialize_jenkins_client()
        
        # Assertions
        self.assertFalse(result)
        
        # Verify client is not set
        client = get_jenkins_client()
        self.assertIsNone(client)

    def test_initialize_jenkins_client_missing_user(self):
        """Test Jenkins client initialization with missing user."""
        # Set only URL and token
        os.environ['JENKINS_URL'] = 'http://jenkins.example.com'
        os.environ['JENKINS_TOKEN'] = 'test_token'
        
        # Initialize client
        result = initialize_jenkins_client()
        
        # Assertions
        self.assertFalse(result)
        
        # Verify client is not set
        client = get_jenkins_client()
        self.assertIsNone(client)

    def test_initialize_jenkins_client_missing_token(self):
        """Test Jenkins client initialization with missing token."""
        # Set only URL and user
        os.environ['JENKINS_URL'] = 'http://jenkins.example.com'
        os.environ['JENKINS_USER'] = 'test_user'
        
        # Initialize client
        result = initialize_jenkins_client()
        
        # Assertions
        self.assertFalse(result)
        
        # Verify client is not set
        client = get_jenkins_client()
        self.assertIsNone(client)

    @patch('src.devops_mcps.jenkins.client.Jenkins')
    def test_initialize_jenkins_client_connection_error(self, mock_jenkins):
        """Test Jenkins client initialization with connection error."""
        # Set environment variables
        os.environ['JENKINS_URL'] = 'http://jenkins.example.com'
        os.environ['JENKINS_USER'] = 'test_user'
        os.environ['JENKINS_TOKEN'] = 'test_token'
        
        # Mock Jenkins to raise exception
        mock_jenkins.side_effect = Exception("Connection failed")
        
        # Initialize client
        result = initialize_jenkins_client()
        
        # Assertions
        self.assertFalse(result)
        
        # Verify client is not set
        client = get_jenkins_client()
        self.assertIsNone(client)

    def test_set_jenkins_client_for_testing(self):
        """Test setting Jenkins client for testing."""
        # Create mock client
        mock_client = MagicMock()
        
        # Set client for testing
        set_jenkins_client_for_testing(mock_client)
        
        # Verify client is set
        client = get_jenkins_client()
        self.assertEqual(client, mock_client)

    def test_get_jenkins_client_none(self):
        """Test getting Jenkins client when not initialized."""
        # Ensure no client is set
        set_jenkins_client_for_testing(None)
        
        # Get client
        client = get_jenkins_client()
        
        # Assertions
        self.assertIsNone(client)

    def test_check_jenkins_config_complete(self):
        """Test checking complete Jenkins configuration."""
        # Set environment variables
        os.environ['JENKINS_URL'] = 'http://jenkins.example.com'
        os.environ['JENKINS_USER'] = 'test_user'
        os.environ['JENKINS_TOKEN'] = 'test_token'
        
        # Check configuration
        result = check_jenkins_config()
        
        # Assertions
        self.assertTrue(result['configured'])
        self.assertEqual(result['missing_vars'], [])

    def test_check_jenkins_config_missing_url(self):
        """Test checking Jenkins configuration with missing URL."""
        # Set only user and token
        os.environ['JENKINS_USER'] = 'test_user'
        os.environ['JENKINS_TOKEN'] = 'test_token'
        
        # Check configuration
        result = check_jenkins_config()
        
        # Assertions
        self.assertFalse(result['configured'])
        self.assertEqual(result['missing_vars'], ['JENKINS_URL'])

    def test_check_jenkins_config_missing_user(self):
        """Test checking Jenkins configuration with missing user."""
        # Set only URL and token
        os.environ['JENKINS_URL'] = 'http://jenkins.example.com'
        os.environ['JENKINS_TOKEN'] = 'test_token'
        
        # Check configuration
        result = check_jenkins_config()
        
        # Assertions
        self.assertFalse(result['configured'])
        self.assertEqual(result['missing_vars'], ['JENKINS_USER'])

    def test_check_jenkins_config_missing_token(self):
        """Test checking Jenkins configuration with missing token."""
        # Set only URL and user
        os.environ['JENKINS_URL'] = 'http://jenkins.example.com'
        os.environ['JENKINS_USER'] = 'test_user'
        
        # Check configuration
        result = check_jenkins_config()
        
        # Assertions
        self.assertFalse(result['configured'])
        self.assertEqual(result['missing_vars'], ['JENKINS_TOKEN'])

    def test_check_jenkins_config_missing_all(self):
        """Test checking Jenkins configuration with all variables missing."""
        # Ensure no environment variables are set
        for var in ['JENKINS_URL', 'JENKINS_USER', 'JENKINS_TOKEN']:
            if var in os.environ:
                del os.environ[var]
        
        # Check configuration
        result = check_jenkins_config()
        
        # Assertions
        self.assertFalse(result['configured'])
        self.assertEqual(set(result['missing_vars']), 
                        {'JENKINS_URL', 'JENKINS_USER', 'JENKINS_TOKEN'})

    def test_get_jenkins_env_vars_complete(self):
        """Test getting Jenkins environment variables when all are set."""
        # Set environment variables
        os.environ['JENKINS_URL'] = 'http://jenkins.example.com'
        os.environ['JENKINS_USER'] = 'test_user'
        os.environ['JENKINS_TOKEN'] = 'test_token'
        
        # Get environment variables
        result = get_jenkins_env_vars()
        
        # Assertions
        self.assertEqual(result['JENKINS_URL'], 'http://jenkins.example.com')
        self.assertEqual(result['JENKINS_USER'], 'test_user')
        self.assertEqual(result['JENKINS_TOKEN'], '***oken')

    def test_get_jenkins_env_vars_partial(self):
        """Test getting Jenkins environment variables when some are missing."""
        # Set only URL
        os.environ['JENKINS_URL'] = 'http://jenkins.example.com'
        
        # Get environment variables
        result = get_jenkins_env_vars()
        
        # Assertions
        self.assertEqual(result['JENKINS_URL'], 'http://jenkins.example.com')
        self.assertIsNone(result['JENKINS_USER'])
        self.assertIsNone(result['JENKINS_TOKEN'])

    def test_get_jenkins_env_vars_none(self):
        """Test getting Jenkins environment variables when none are set."""
        # Ensure no environment variables are set
        for var in ['JENKINS_URL', 'JENKINS_USER', 'JENKINS_TOKEN']:
            if var in os.environ:
                del os.environ[var]
        
        # Get environment variables
        result = get_jenkins_env_vars()
        
        # Assertions
        self.assertIsNone(result['JENKINS_URL'])
        self.assertIsNone(result['JENKINS_USER'])
        self.assertIsNone(result['JENKINS_TOKEN'])


if __name__ == '__main__':
    unittest.main()