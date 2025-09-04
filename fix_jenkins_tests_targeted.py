#!/usr/bin/env python3
"""
Script to systematically fix Jenkins tests by adding set_jenkins_client_for_testing calls
to test methods that need Jenkins client initialization.
"""

import re

def fix_jenkins_tests():
    test_file = "tests/test_jenkins.py"
    
    # Read the file
    with open(test_file, 'r') as f:
        content = f.read()
    
    # Find all test methods that don't already have set_jenkins_client_for_testing
    # and are not in TestInitializeJenkinsClient or TestSetJenkinsClientForTesting classes
    
    # Pattern to match test methods
    test_method_pattern = r'(\s+)(def test_[^(]+\([^)]*\):)\s*\n(\s+)"""[^"]*"""\s*\n'
    
    # Classes that don't need Jenkins client setup
    skip_classes = [
        'TestInitializeJenkinsClient',
        'TestSetJenkinsClientForTesting',
        'TestToDict'  # This class tests utility functions, not Jenkins API calls
    ]
    
    # Track current class
    current_class = None
    lines = content.split('\n')
    result_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Track current class
        class_match = re.match(r'^class (\w+)', line)
        if class_match:
            current_class = class_match.group(1)
        
        # Check if this is a test method that needs fixing
        if (line.strip().startswith('def test_') and 
            current_class not in skip_classes and
            'set_jenkins_client_for_testing' not in lines[i:i+10]):
            
            # Add the line
            result_lines.append(line)
            i += 1
            
            # Add docstring if present
            if i < len(lines) and '"""' in lines[i]:
                result_lines.append(lines[i])
                i += 1
                # Handle multi-line docstrings
                while i < len(lines) and not lines[i].strip().endswith('"""'):
                    result_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    result_lines.append(lines[i])
                    i += 1
            
            # Add Jenkins client setup
            indent = '    '  # Standard test method indent
            result_lines.append(f'{indent}# Setup mock Jenkins client for testing')
            result_lines.append(f'{indent}from unittest.mock import Mock')
            result_lines.append(f'{indent}from devops_mcps.utils.jenkins.jenkins_client import set_jenkins_client_for_testing')
            result_lines.append(f'{indent}mock_jenkins_instance = Mock()')
            result_lines.append(f'{indent}set_jenkins_client_for_testing(mock_jenkins_instance)')
            result_lines.append('')
        else:
            result_lines.append(line)
            i += 1
    
    # Write the fixed content
    with open(test_file, 'w') as f:
        f.write('\n'.join(result_lines))
    
    print(f"Fixed Jenkins tests in {test_file}")

if __name__ == "__main__":
    fix_jenkins_tests()