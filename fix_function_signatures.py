#!/usr/bin/env python3
"""
Script to fix function signatures after changing Jenkins test patches.
The patches are applied in reverse order, so function parameters need to be reordered.
"""

import re
import sys

def fix_function_signatures(file_path):
    """Fix function signatures to match the new patch order."""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find functions that have the new Jenkins patches and need signature updates
    # Pattern to find functions with Jenkins patches
    jenkins_patch_pattern = r'(@patch\("devops_mcps\.utils\.jenkins\.jenkins_api\.JENKINS_URL"[^\n]*\n\s*@patch\("devops_mcps\.utils\.jenkins\.jenkins_api\.JENKINS_USER"[^\n]*\n\s*@patch\("devops_mcps\.utils\.jenkins\.jenkins_api\.JENKINS_TOKEN"[^\n]*\n(?:\s*@patch[^\n]*\n)*\s*def\s+\w+\([^)]*\):)'
    
    def fix_signature(match):
        block = match.group(1)
        
        # Count the number of @patch decorators
        patch_count = len(re.findall(r'@patch\(', block))
        
        # Extract function definition line
        func_def_match = re.search(r'def\s+(\w+)\(([^)]*)\):', block)
        if not func_def_match:
            return block
        
        func_name = func_def_match.group(1)
        params = func_def_match.group(2)
        
        # Parse existing parameters
        param_list = [p.strip() for p in params.split(',') if p.strip()]
        
        # Remove 'self' if present
        if param_list and param_list[0] == 'self':
            self_param = param_list.pop(0)
        else:
            self_param = None
        
        # The patches are applied in reverse order, so we need to match that
        # For Jenkins tests, we typically have: JENKINS_URL, JENKINS_USER, JENKINS_TOKEN, then other patches
        
        # Rebuild parameter list based on patch order
        new_params = []
        if self_param:
            new_params.append(self_param)
        
        # Add mock parameters in reverse order of patch application
        # This is a simplified approach - we'll use generic names
        for i in range(patch_count):
            if i < len(param_list):
                new_params.append(param_list[i])
            else:
                new_params.append(f'mock_param_{i}')
        
        # Reconstruct the function definition
        new_params_str = ', '.join(new_params)
        new_block = re.sub(
            r'def\s+\w+\([^)]*\):',
            f'def {func_name}({new_params_str}):',
            block
        )
        
        return new_block
    
    # Apply the fixes
    new_content = re.sub(jenkins_patch_pattern, fix_signature, content, flags=re.MULTILINE | re.DOTALL)
    
    # Write back the modified content
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Fixed function signatures in {file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_function_signatures.py <test_file_path>")
        sys.exit(1)
    
    fix_function_signatures(sys.argv[1])