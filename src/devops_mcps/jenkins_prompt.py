"""
MCP Prompt for Jenkins Job Failure Diagnosis

This prompt guides users through identifying and resolving Jenkins job failures.
It provides step-by-step instructions for analyzing logs and suggests common fixes.
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def jenkins_failure_diagnosis_prompt(job_name: str, log: str) -> Dict[str, str]:
    """
    Generate a diagnostic prompt for a failed Jenkins job.

    Args:
        job_name: Name of the failed Jenkins job
        log: The console output log from the failed build

    Returns:
        Dict containing diagnostic steps and suggested fixes
    """
    # Step 1: Identify common error patterns
    common_errors = {
        'Build timeout': 'Consider increasing build timeout or optimizing build steps',
        'Test failures': 'Review test cases and ensure test environment is properly configured',
        'Dependency issues': 'Check dependency versions and repository connectivity',
        'Memory errors': 'Increase JVM memory allocation or optimize memory usage',
        'Permission denied': 'Verify file permissions and Jenkins agent access rights'
    }

    # Step 2: Analyze log for specific error patterns
    error_patterns = []
    for pattern in common_errors:
        if pattern.lower() in log.lower():
            error_patterns.append(pattern)

    # Step 3: Generate diagnostic steps
    steps = [
        "1. Review the complete build log for detailed error messages",
        "2. Check Jenkins system logs for any related errors",
        "3. Verify job configuration and parameters",
        "4. Ensure all dependencies are properly installed and configured",
        "5. Check system resources (CPU, memory, disk space)"
    ]

    # Step 4: Provide specific suggestions based on error patterns
    suggestions = []
    for pattern in error_patterns:
        suggestions.append(f"{pattern}: {common_errors[pattern]}")

    return {
        'job_name': job_name,
        'steps': steps,
        'suggestions': suggestions if suggestions else ['No specific patterns detected - manual review required'],
        'next_steps': [
            'Implement suggested fixes and retry build',
            'If issue persists, consult Jenkins documentation',
            'Consider reaching out to infrastructure team for assistance'
        ]
    }


def get_jenkins_diagnosis_prompt(job_name: str, build_number: int) -> Dict[str, str]:
    """
    Generate a complete diagnostic prompt for a Jenkins job.

    Args:
        job_name: Name of the Jenkins job
        build_number: Build number to diagnose

    Returns:
        Dict containing complete diagnostic information
    """
    # Get build log (this would be implemented using Jenkins API)
    build_log = ""  # Placeholder for actual log retrieval

    # Generate diagnosis
    diagnosis = jenkins_failure_diagnosis_prompt(job_name, build_log)

    return {
        'job_name': job_name,
        'build_number': build_number,
        'diagnosis': diagnosis,
        'additional_resources': [
            'Jenkins Official Documentation',
            'Jenkins Troubleshooting Guide',
            'Jenkins Community Forums'
        ]
    }