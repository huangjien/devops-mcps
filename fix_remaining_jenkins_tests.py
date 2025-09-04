#!/usr/bin/env python3
"""
Script to fix remaining Jenkins tests by adding set_jenkins_client_for_testing calls.
"""

import re

def fix_jenkins_tests():
    test_file = 'tests/test_jenkins.py'
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    # Find all test methods that don't already have set_jenkins_client_for_testing
    # and add the setup to them
    
    # Pattern to match test methods
    test_method_pattern = r'(def test_[^(]+\([^)]*\):)'
    
    def add_jenkins_setup(match):
        method_signature = match.group(1)
        # Check if this method already has set_jenkins_client_for_testing
        method_start = match.start()
        # Look ahead to see if set_jenkins_client_for_testing is already there
        next_200_chars = content[match.end():match.end() + 200]
        if 'set_jenkins_client_for_testing' in next_200_chars:
            return method_signature  # Already has setup, don't modify
        
        # Add the setup
        setup_code = '''
        # Setup mock Jenkins client for testing
        from unittest.mock import Mock
        from devops_mcps.utils.jenkins.jenkins_client import set_jenkins_client_for_testing
        mock_jenkins_instance = Mock()
        set_jenkins_client_for_testing(mock_jenkins_instance)'''
        
        return method_signature + setup_code
    
    # Apply the transformation
    new_content = re.sub(test_method_pattern, add_jenkins_setup, content)
    
    # Write back the modified content
    with open(test_file, 'w') as f:
        f.write(new_content)
    
    print(f"Fixed Jenkins tests in {test_file}")

if __name__ == '__main__':
    fix_jenkins_tests()