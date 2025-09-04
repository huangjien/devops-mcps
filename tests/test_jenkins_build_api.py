"""Unit tests for jenkins_build_api.py."""

import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from requests.exceptions import ConnectionError, Timeout, HTTPError, RequestException

from devops_mcps.utils.jenkins.jenkins_build_api import (
    _get_jenkins_client,
    _get_jenkins_constants,
    _get_to_dict,
    _get_cache,
    jenkins_get_build_log,
    jenkins_get_build_parameters,
    jenkins_get_recent_failed_builds,
)


class TestJenkinsBuildApiHelpers(unittest.TestCase):
    """Test cases for helper functions in jenkins_build_api.py."""

    def setUp(self):
        """Set up test fixtures."""
        # Save original modules dict to restore after tests
        self.original_modules = dict(sys.modules)
        
    def tearDown(self):
        """Tear down test fixtures."""
        # Restore original modules
        sys.modules = self.original_modules

    def test_get_jenkins_client_no_jenkins_api(self):
        """Test _get_jenkins_client when jenkins_api module is not available."""
        # Ensure jenkins_api is not in sys.modules
        if 'devops_mcps.utils.jenkins.jenkins_api' in sys.modules:
            del sys.modules['devops_mcps.utils.jenkins.jenkins_api']
            
        with patch('devops_mcps.utils.jenkins.jenkins_build_api._j', 'original_j'):
            result = _get_jenkins_client()
            self.assertEqual(result, 'original_j')

    def test_get_jenkins_client_with_jenkins_api(self):
        """Test _get_jenkins_client when jenkins_api module is available."""
        # Create a mock jenkins_api module
        mock_jenkins_api = Mock()
        mock_jenkins_api.j = 'patched_j'
        sys.modules['devops_mcps.utils.jenkins.jenkins_api'] = mock_jenkins_api
        
        with patch('devops_mcps.utils.jenkins.jenkins_build_api._j', 'original_j'):
            result = _get_jenkins_client()
            self.assertEqual(result, 'patched_j')

    def test_get_jenkins_constants_no_jenkins_api(self):
        """Test _get_jenkins_constants when jenkins_api module is not available."""
        # Ensure jenkins_api is not in sys.modules
        if 'devops_mcps.utils.jenkins.jenkins_api' in sys.modules:
            del sys.modules['devops_mcps.utils.jenkins.jenkins_api']
            
        with patch('devops_mcps.utils.jenkins.jenkins_build_api._JENKINS_URL', 'original_url'), \
             patch('devops_mcps.utils.jenkins.jenkins_build_api._JENKINS_USER', 'original_user'), \
             patch('devops_mcps.utils.jenkins.jenkins_build_api._JENKINS_TOKEN', 'original_token'), \
             patch('devops_mcps.utils.jenkins.jenkins_build_api._LOG_LENGTH', 100):
            result = _get_jenkins_constants()
            self.assertEqual(result, {
                'JENKINS_URL': 'original_url',
                'JENKINS_USER': 'original_user',
                'JENKINS_TOKEN': 'original_token',
                'LOG_LENGTH': 100
            })

    def test_get_jenkins_constants_with_jenkins_api(self):
        """Test _get_jenkins_constants when jenkins_api module is available."""
        # Create a mock jenkins_api module
        mock_jenkins_api = Mock()
        mock_jenkins_api.JENKINS_URL = 'patched_url'
        mock_jenkins_api.JENKINS_USER = 'patched_user'
        mock_jenkins_api.JENKINS_TOKEN = 'patched_token'
        mock_jenkins_api.LOG_LENGTH = 200
        sys.modules['devops_mcps.utils.jenkins.jenkins_api'] = mock_jenkins_api
        
        with patch('devops_mcps.utils.jenkins.jenkins_build_api._JENKINS_URL', 'original_url'), \
             patch('devops_mcps.utils.jenkins.jenkins_build_api._JENKINS_USER', 'original_user'), \
             patch('devops_mcps.utils.jenkins.jenkins_build_api._JENKINS_TOKEN', 'original_token'), \
             patch('devops_mcps.utils.jenkins.jenkins_build_api._LOG_LENGTH', 100):
            result = _get_jenkins_constants()
            self.assertEqual(result, {
                'JENKINS_URL': 'patched_url',
                'JENKINS_USER': 'patched_user',
                'JENKINS_TOKEN': 'patched_token',
                'LOG_LENGTH': 200
            })

    def test_get_to_dict_no_jenkins_api(self):
        """Test _get_to_dict when jenkins_api module is not available."""
        # Ensure jenkins_api is not in sys.modules
        if 'devops_mcps.utils.jenkins.jenkins_api' in sys.modules:
            del sys.modules['devops_mcps.utils.jenkins.jenkins_api']
            
        original_to_dict = lambda x: f"original_{x}"
        with patch('devops_mcps.utils.jenkins.jenkins_build_api._original_to_dict', original_to_dict):
            result = _get_to_dict()
            self.assertEqual(result('test'), 'original_test')

    def test_get_to_dict_with_jenkins_api(self):
        """Test _get_to_dict when jenkins_api module is available."""
        # Create a mock jenkins_api module
        mock_jenkins_api = Mock()
        mock_jenkins_api._to_dict = lambda x: f"patched_{x}"
        sys.modules['devops_mcps.utils.jenkins.jenkins_api'] = mock_jenkins_api
        
        original_to_dict = lambda x: f"original_{x}"
        with patch('devops_mcps.utils.jenkins.jenkins_build_api._original_to_dict', original_to_dict):
            result = _get_to_dict()
            self.assertEqual(result('test'), 'patched_test')

    def test_get_cache_no_jenkins_api(self):
        """Test _get_cache when jenkins_api module is not available."""
        # Ensure jenkins_api is not in sys.modules
        if 'devops_mcps.utils.jenkins.jenkins_api' in sys.modules:
            del sys.modules['devops_mcps.utils.jenkins.jenkins_api']
            
        with patch('devops_mcps.utils.jenkins.jenkins_build_api._cache', 'original_cache'):
            result = _get_cache()
            self.assertEqual(result, 'original_cache')

    def test_get_cache_with_jenkins_api(self):
        """Test _get_cache when jenkins_api module is available."""
        # Create a mock jenkins_api module
        mock_jenkins_api = Mock()
        mock_jenkins_api.cache = 'patched_cache'
        sys.modules['devops_mcps.utils.jenkins.jenkins_api'] = mock_jenkins_api
        
        with patch('devops_mcps.utils.jenkins.jenkins_build_api._cache', 'original_cache'):
            result = _get_cache()
            self.assertEqual(result, 'patched_cache')


class TestJenkinsGetBuildLog(unittest.TestCase):
    """Test cases for jenkins_get_build_log function."""

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    def test_jenkins_get_build_log_cached(self, mock_get_cache):
        """Test jenkins_get_build_log with cached result."""
        mock_cache = Mock()
        mock_cache.get.return_value = 'cached log content'
        mock_get_cache.return_value = mock_cache

        result = jenkins_get_build_log('test-job', 5)

        self.assertEqual(result, 'cached log content')
        mock_cache.get.assert_called_once_with('jenkins:build_log:test-job:5:0:50')

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_log_no_credentials(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_log with no Jenkins credentials."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': '',
            'JENKINS_USER': '',
            'JENKINS_TOKEN': '',
            'LOG_LENGTH': 100
        }

        result = jenkins_get_build_log('test-job', 5)

        self.assertIn('error', result)
        self.assertIn('Jenkins client not initialized', result['error'])
        mock_get.assert_not_called()

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_log_specific_build(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_log with specific build number."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        mock_response = Mock()
        mock_response.text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = jenkins_get_build_log('test-job', 5, start=1, lines=3)

        self.assertEqual(result, "Line 2\nLine 3\nLine 4")
        mock_get.assert_called_once_with(
            'http://jenkins.example.com/job/test-job/5/consoleText',
            auth=('user', 'token'),
            timeout=30
        )
        mock_cache.set.assert_called_once_with(
            'jenkins:build_log:test-job:5:1:3',
            "Line 2\nLine 3\nLine 4",
            ttl=300
        )

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_log_latest_build(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_log with latest build (build_number=0)."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock responses for job info and console output
        job_response = Mock()
        job_response.json.return_value = {'lastBuild': {'number': 10}}
        job_response.raise_for_status.return_value = None
        
        console_response = Mock()
        console_response.text = "Line 1\nLine 2\nLine 3"
        console_response.raise_for_status.return_value = None
        
        def get_side_effect(url, **kwargs):
            if '/api/json' in url:
                return job_response
            elif '/consoleText' in url:
                return console_response
            return Mock()
        
        mock_get.side_effect = get_side_effect

        result = jenkins_get_build_log('test-job', 0)

        self.assertEqual(result, "Line 1\nLine 2\nLine 3")
        self.assertEqual(mock_get.call_count, 2)
        mock_cache.set.assert_called_once()

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_log_no_builds(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_log when no builds exist."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock response for job info with no builds
        job_response = Mock()
        job_response.json.return_value = {}
        job_response.raise_for_status.return_value = None
        mock_get.return_value = job_response

        result = jenkins_get_build_log('test-job', 0)

        self.assertIn('error', result)
        self.assertIn('No builds found', result['error'])

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_log_http_error(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_log with HTTP error."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = HTTPError(response=mock_response)
        mock_get.side_effect = http_error

        result = jenkins_get_build_log('test-job', 5)

        self.assertIn('error', result)
        self.assertIn('Job \'test-job\' or build 5 not found', result['error'])

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_log_connection_error(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_log with connection error."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock connection error
        mock_get.side_effect = ConnectionError("Connection failed")

        result = jenkins_get_build_log('test-job', 5)

        self.assertIn('error', result)
        self.assertIn('Could not connect to Jenkins API', result['error'])

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_log_timeout(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_log with timeout error."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock timeout error
        mock_get.side_effect = Timeout("Request timed out")

        result = jenkins_get_build_log('test-job', 5)

        self.assertIn('error', result)
        self.assertIn('Timeout connecting to Jenkins API', result['error'])


class TestJenkinsGetBuildParameters(unittest.TestCase):
    """Test cases for jenkins_get_build_parameters function."""

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    def test_jenkins_get_build_parameters_cached(self, mock_get_cache):
        """Test jenkins_get_build_parameters with cached result."""
        mock_cache = Mock()
        mock_cache.get.return_value = {'param1': 'value1', 'param2': 'value2'}
        mock_get_cache.return_value = mock_cache

        result = jenkins_get_build_parameters('test-job', 5)

        self.assertEqual(result, {'param1': 'value1', 'param2': 'value2'})
        mock_cache.get.assert_called_once_with('jenkins:build_parameters:test-job:5')

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    def test_jenkins_get_build_parameters_no_credentials(self, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_parameters with no Jenkins credentials."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': '',
            'JENKINS_USER': '',
            'JENKINS_TOKEN': '',
            'LOG_LENGTH': 100
        }

        result = jenkins_get_build_parameters('test-job', 5)

        self.assertIn('error', result)
        self.assertIn('Jenkins client not initialized', result['error'])

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_parameters_specific_build(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_parameters with specific build number."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock response for build parameters
        mock_response = Mock()
        mock_response.json.return_value = {
            'actions': [
                {
                    'parameters': [
                        {'name': 'param1', 'value': 'value1'},
                        {'name': 'param2', 'value': 'value2'}
                    ]
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = jenkins_get_build_parameters('test-job', 5)

        self.assertEqual(result, {'param1': 'value1', 'param2': 'value2'})
        mock_get.assert_called_once_with(
            'http://jenkins.example.com/job/test-job/5/api/json',
            auth=('user', 'token'),
            timeout=30
        )
        mock_cache.set.assert_called_once_with(
            'jenkins:build_parameters:test-job:5',
            {'param1': 'value1', 'param2': 'value2'},
            ttl=300
        )

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_parameters_latest_build(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_parameters with latest build (build_number=0)."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock responses for job info and build parameters
        job_response = Mock()
        job_response.json.return_value = {'lastBuild': {'number': 10}}
        job_response.raise_for_status.return_value = None
        
        build_response = Mock()
        build_response.json.return_value = {
            'actions': [
                {
                    'parameters': [
                        {'name': 'param1', 'value': 'value1'},
                        {'name': 'param2', 'value': 'value2'}
                    ]
                }
            ]
        }
        build_response.raise_for_status.return_value = None
        
        def get_side_effect(url, **kwargs):
            if '/job/test-job/api/json' in url:
                return job_response
            elif '/job/test-job/10/api/json' in url:
                return build_response
            return Mock()
        
        mock_get.side_effect = get_side_effect

        result = jenkins_get_build_parameters('test-job', 0)

        self.assertEqual(result, {'param1': 'value1', 'param2': 'value2'})
        self.assertEqual(mock_get.call_count, 2)
        mock_cache.set.assert_called_once()

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_parameters_no_builds(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_parameters when no builds exist."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock response for job info with no builds
        job_response = Mock()
        job_response.json.return_value = {}
        job_response.raise_for_status.return_value = None
        mock_get.return_value = job_response

        result = jenkins_get_build_parameters('test-job', 0)

        self.assertIn('error', result)
        self.assertIn('No builds found', result['error'])

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_build_parameters_no_parameters(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_build_parameters when build has no parameters."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock response for build with no parameters
        mock_response = Mock()
        mock_response.json.return_value = {'actions': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = jenkins_get_build_parameters('test-job', 5)

        self.assertEqual(result, {})
        mock_cache.set.assert_called_once_with('jenkins:build_parameters:test-job:5', {}, ttl=300)


class TestJenkinsGetRecentFailedBuilds(unittest.TestCase):
    """Test cases for jenkins_get_recent_failed_builds function."""

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    def test_jenkins_get_recent_failed_builds_cached(self, mock_get_cache):
        """Test jenkins_get_recent_failed_builds with cached result."""
        cached_builds = [
            {'job_name': 'job1', 'build_number': 1, 'status': 'FAILURE'},
            {'job_name': 'job2', 'build_number': 2, 'status': 'UNSTABLE'}
        ]
        mock_cache = Mock()
        mock_cache.get.return_value = cached_builds
        mock_get_cache.return_value = mock_cache

        result = jenkins_get_recent_failed_builds(8)

        self.assertEqual(result, cached_builds)
        mock_cache.get.assert_called_once_with('jenkins:recent_failed_builds:8')

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    def test_jenkins_get_recent_failed_builds_no_credentials(self, mock_get_constants, mock_get_cache):
        """Test jenkins_get_recent_failed_builds with no Jenkins credentials."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': '',
            'JENKINS_USER': '',
            'JENKINS_TOKEN': '',
            'LOG_LENGTH': 100
        }

        result = jenkins_get_recent_failed_builds(8)

        self.assertIn('error', result)
        self.assertIn('Jenkins client not initialized', result['error'])

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.datetime')
    def test_jenkins_get_recent_failed_builds_success(self, mock_datetime, mock_get, mock_get_constants, mock_get_cache):
        """Test successful jenkins_get_recent_failed_builds."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock datetime for consistent testing
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromtimestamp.side_effect = lambda ts, tz: datetime.fromtimestamp(ts, tz)
        
        # Calculate timestamp for 4 hours ago (within 8 hour threshold)
        four_hours_ago = int((mock_now - timedelta(hours=4)).timestamp() * 1000)
        # Calculate timestamp for 10 hours ago (outside 8 hour threshold)
        ten_hours_ago = int((mock_now - timedelta(hours=10)).timestamp() * 1000)
        
        # Mock response with various job states
        mock_response = Mock()
        mock_response.json.return_value = {
            'jobs': [
                # Recent failed build (should be included)
                {
                    'name': 'failed-job',
                    'url': 'http://jenkins.example.com/job/failed-job/',
                    'lastBuild': {
                        'number': 1,
                        'timestamp': four_hours_ago,
                        'result': 'FAILURE',
                        'url': 'http://jenkins.example.com/job/failed-job/1/'
                    }
                },
                # Recent unstable build (should be included)
                {
                    'name': 'unstable-job',
                    'url': 'http://jenkins.example.com/job/unstable-job/',
                    'lastBuild': {
                        'number': 2,
                        'timestamp': four_hours_ago,
                        'result': 'UNSTABLE',
                        'url': 'http://jenkins.example.com/job/unstable-job/2/'
                    }
                },
                # Recent aborted build (should be included)
                {
                    'name': 'aborted-job',
                    'url': 'http://jenkins.example.com/job/aborted-job/',
                    'lastBuild': {
                        'number': 3,
                        'timestamp': four_hours_ago,
                        'result': 'ABORTED',
                        'url': 'http://jenkins.example.com/job/aborted-job/3/'
                    }
                },
                # Recent successful build (should NOT be included)
                {
                    'name': 'success-job',
                    'url': 'http://jenkins.example.com/job/success-job/',
                    'lastBuild': {
                        'number': 4,
                        'timestamp': four_hours_ago,
                        'result': 'SUCCESS',
                        'url': 'http://jenkins.example.com/job/success-job/4/'
                    }
                },
                # Old failed build (should NOT be included)
                {
                    'name': 'old-failed-job',
                    'url': 'http://jenkins.example.com/job/old-failed-job/',
                    'lastBuild': {
                        'number': 5,
                        'timestamp': ten_hours_ago,
                        'result': 'FAILURE',
                        'url': 'http://jenkins.example.com/job/old-failed-job/5/'
                    }
                },
                # Job with missing timestamp (should NOT be included)
                {
                    'name': 'no-timestamp-job',
                    'url': 'http://jenkins.example.com/job/no-timestamp-job/',
                    'lastBuild': {
                        'number': 6,
                        'result': 'FAILURE',
                        'url': 'http://jenkins.example.com/job/no-timestamp-job/6/'
                    }
                },
                # Job with no lastBuild (should NOT be included)
                {
                    'name': 'no-build-job',
                    'url': 'http://jenkins.example.com/job/no-build-job/'
                },
                # Job with no name (should NOT be included)
                {
                    'url': 'http://jenkins.example.com/job/unnamed-job/',
                    'lastBuild': {
                        'number': 7,
                        'timestamp': four_hours_ago,
                        'result': 'FAILURE',
                        'url': 'http://jenkins.example.com/job/unnamed-job/7/'
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = jenkins_get_recent_failed_builds(8)

        # Should include only the 3 recent failed/unstable/aborted builds
        self.assertEqual(len(result), 3)
        
        # Verify job names are correct
        job_names = [build['job_name'] for build in result]
        self.assertIn('failed-job', job_names)
        self.assertIn('unstable-job', job_names)
        self.assertIn('aborted-job', job_names)
        
        # Verify statuses are correct
        statuses = [build['status'] for build in result]
        self.assertIn('FAILURE', statuses)
        self.assertIn('UNSTABLE', statuses)
        self.assertIn('ABORTED', statuses)
        
        # Verify cache was set
        mock_cache.set.assert_called_once()

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_recent_failed_builds_missing_url(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_recent_failed_builds with missing build URL."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock current time
        now = datetime.now(timezone.utc)
        recent_timestamp = int((now - timedelta(hours=1)).timestamp() * 1000)
        
        # Mock response with a job that has a missing build URL
        mock_response = Mock()
        mock_response.json.return_value = {
            'jobs': [
                {
                    'name': 'job-missing-url',
                    'url': 'http://jenkins.example.com/job/job-missing-url/',
                    'lastBuild': {
                        'number': 1,
                        'timestamp': recent_timestamp,
                        'result': 'FAILURE'
                        # No 'url' field
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = jenkins_get_recent_failed_builds(8)

        # Should still include the job, with a constructed URL
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['job_name'], 'job-missing-url')
        # URL should be constructed from job URL and build number
        self.assertTrue(result[0]['url'].endswith('1'))

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_recent_failed_builds_connection_error(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_recent_failed_builds with connection error."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock connection error
        mock_get.side_effect = ConnectionError("Connection failed")

        result = jenkins_get_recent_failed_builds(8)

        self.assertIn('error', result)
        self.assertIn('Could not connect to Jenkins API', result['error'])

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_recent_failed_builds_http_error(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_recent_failed_builds with HTTP error."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 403
        http_error = HTTPError(response=mock_response)
        mock_get.side_effect = http_error

        result = jenkins_get_recent_failed_builds(8)

        self.assertIn('error', result)
        self.assertIn('Jenkins API HTTP Error', result['error'])

    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_cache')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api._get_jenkins_constants')
    @patch('devops_mcps.utils.jenkins.jenkins_build_api.requests.get')
    def test_jenkins_get_recent_failed_builds_timeout(self, mock_get, mock_get_constants, mock_get_cache):
        """Test jenkins_get_recent_failed_builds with timeout error."""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache
        
        mock_get_constants.return_value = {
            'JENKINS_URL': 'http://jenkins.example.com',
            'JENKINS_USER': 'user',
            'JENKINS_TOKEN': 'token',
            'LOG_LENGTH': 100
        }
        
        # Mock timeout error
        mock_get.side_effect = Timeout("Request timed out")

        result = jenkins_get_recent_failed_builds(8)

        self.assertIn('error', result)
        self.assertIn('Timeout connecting to Jenkins API', result['error'])


if __name__ == "__main__":
    unittest.main()