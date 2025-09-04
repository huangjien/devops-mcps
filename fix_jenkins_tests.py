#!/usr/bin/env python3
"""
Script to fix Jenkins test patching issues by replacing @patch.dict("os.environ", ...)
with proper module-level variable patching.
"""

import re
import sys

def fix_jenkins_tests(file_path):
    """Fix Jenkins test file by replacing os.environ patches with module-level patches."""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match the old patch.dict pattern
    old_pattern = r'@patch\.dict\("os\.environ", \{"JENKINS_URL": "([^"]+)", "JENKINS_USER": "([^"]+)", "JENKINS_TOKEN": "([^"]+)"\}\)'
    
    # Replacement pattern
    def replacement(match):
        url, user, token = match.groups()
        return f'@patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_URL", "{url}")\n  @patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_USER", "{user}")\n  @patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_TOKEN", "{token}")'
    
    # Replace all occurrences
    new_content = re.sub(old_pattern, replacement, content)
    
    # Handle special cases with clear=True
    clear_patterns = [
        (r'@patch\.dict\("os\.environ", \{"JENKINS_USER": "([^"]+)", "JENKINS_TOKEN": "([^"]+)"\}, clear=True\)',
         lambda m: f'@patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_URL", "")\n  @patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_USER", "{m.group(1)}")\n  @patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_TOKEN", "{m.group(2)}")'),
        
        (r'@patch\.dict\("os\.environ", \{"JENKINS_URL": "([^"]+)", "JENKINS_TOKEN": "([^"]+)"\}, clear=True\)',
         lambda m: f'@patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_URL", "{m.group(1)}")\n  @patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_USER", "")\n  @patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_TOKEN", "{m.group(2)}")'),
        
        (r'@patch\.dict\("os\.environ", \{"JENKINS_URL": "([^"]+)", "JENKINS_USER": "([^"]+)"\}, clear=True\)',
         lambda m: f'@patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_URL", "{m.group(1)}")\n  @patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_USER", "{m.group(2)}")\n  @patch("devops_mcps.utils.jenkins.jenkins_api.JENKINS_TOKEN", "")')
    ]
    
    for pattern, repl_func in clear_patterns:
        new_content = re.sub(pattern, repl_func, new_content)
    
    # Write back the modified content
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Fixed Jenkins test patches in {file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_jenkins_tests.py <test_file_path>")
        sys.exit(1)
    
    fix_jenkins_tests(sys.argv[1])