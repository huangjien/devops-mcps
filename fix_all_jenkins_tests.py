#!/usr/bin/env python3
"""
Script to fix all Jenkins tests by replacing patch decorators with set_jenkins_client_for_testing.
"""

import re
import os

def fix_jenkins_tests():
    test_file = "tests/test_jenkins.py"
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    # Pattern to match test methods that have Jenkins-related patches
    # Look for methods with @patch decorators that reference jenkins
    patch_pattern = r'(\s*)(@patch\([^)]*jenkins[^)]*\)\s*)+\s*(def test_[^(]+\([^)]*\):)'
    
    def replace_test_method(match):
        indent = match.group(1)
        decorators = match.group(2)
        method_def = match.group(3)
        
        # Extract method name and parameters
        method_match = re.search(r'def (test_[^(]+)\(([^)]*)\):', method_def)
        if not method_match:
            return match.group(0)  # Return original if we can't parse
            
        method_name = method_match.group(1)
        params = method_match.group(2)
        
        # Remove mock parameters from the method signature, keep only 'self'
        clean_params = 'self'
        
        # Create new method definition without patches
        new_method_def = f"def {method_name}({clean_params}):"
        
        return f"{indent}{new_method_def}"
    
    # Replace all test methods with patches
    content = re.sub(patch_pattern, replace_test_method, content, flags=re.MULTILINE | re.DOTALL)
    
    # Now we need to add the set_jenkins_client_for_testing setup to each test method
    # Find all test methods and add the setup code
    test_method_pattern = r'(\s*)(def test_[^(]+\(self\):\s*)("""[^"]*"""\s*)?(.*?)(?=\s*def |\s*class |\Z)'
    
    def add_jenkins_setup(match):
        indent = match.group(1)
        method_def = match.group(2)
        docstring = match.group(3) or ''
        method_body = match.group(4)
        
        # Skip if this method already has set_jenkins_client_for_testing
        if 'set_jenkins_client_for_testing' in method_body:
            return match.group(0)
            
        # Skip if this is not a Jenkins-related test
        if 'jenkins' not in method_body.lower() and 'j.' not in method_body:
            return match.group(0)
            
        # Add the setup code
        setup_code = f"""{indent}    from devops_mcps.utils.jenkins.jenkins_client import set_jenkins_client_for_testing
{indent}    import devops_mcps.utils.jenkins.jenkins_client
{indent}    
{indent}    mock_jenkins_instance = Mock()
{indent}    set_jenkins_client_for_testing(mock_jenkins_instance)
{indent}    """
        
        return f"{indent}{method_def}{docstring}{setup_code}{method_body}"
    
    content = re.sub(test_method_pattern, add_jenkins_setup, content, flags=re.MULTILINE | re.DOTALL)
    
    # Write the updated content back
    with open(test_file, 'w') as f:
        f.write(content)
    
    print(f"Fixed Jenkins tests in {test_file}")

if __name__ == "__main__":
    fix_jenkins_tests()