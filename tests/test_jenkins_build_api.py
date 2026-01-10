"""Unit tests for jenkins_build_api.py."""


class TestJenkinsBuildApiModule:
  """Test the jenkins_build_api module structure and re-exports."""

  def test_module_imports(self):
    """Test that the module can be imported."""
    from devops_mcps.utils.jenkins import jenkins_build_api

    assert jenkins_build_api is not None

  def test_module_has_logger(self):
    """Test that the module has a logger."""
    from devops_mcps.utils.jenkins import jenkins_build_api

    assert hasattr(jenkins_build_api, "logger")

  def test_module_docstring(self):
    """Test that the module has a docstring."""
    from devops_mcps.utils.jenkins import jenkins_build_api

    assert jenkins_build_api.__doc__ is not None
    assert "Jenkins Build API" in jenkins_build_api.__doc__

  def test_module_re_exports_get_build_log(self):
    """Test that jenkins_get_build_log is re-exported."""
    from devops_mcps.utils.jenkins.jenkins_build_api import jenkins_get_build_log

    assert callable(jenkins_get_build_log)

  def test_module_re_exports_get_build_parameters(self):
    """Test that jenkins_get_build_parameters is re-exported."""
    from devops_mcps.utils.jenkins.jenkins_build_api import (
      jenkins_get_build_parameters,
    )

    assert callable(jenkins_get_build_parameters)

  def test_module_re_exports_get_recent_failed_builds(self):
    """Test that jenkins_get_recent_failed_builds is re-exported."""
    from devops_mcps.utils.jenkins.jenkins_build_api import (
      jenkins_get_recent_failed_builds,
    )

    assert callable(jenkins_get_recent_failed_builds)

  def test_module_all_exports(self):
    """Test that __all__ is properly defined."""
    from devops_mcps.utils.jenkins import jenkins_build_api

    assert hasattr(jenkins_build_api, "__all__")
    assert "jenkins_get_build_log" in jenkins_build_api.__all__
    assert "jenkins_get_build_parameters" in jenkins_build_api.__all__
    assert "jenkins_get_recent_failed_builds" in jenkins_build_api.__all__

  def test_module_re_exports_from_logs(self):
    """Test that functions from jenkins_logs are accessible."""
    from devops_mcps.utils.jenkins.jenkins_logs import jenkins_get_build_log

    assert callable(jenkins_get_build_log)

  def test_module_re_exports_from_parameters(self):
    """Test that functions from jenkins_parameters are accessible."""
    from devops_mcps.utils.jenkins.jenkins_parameters import (
      jenkins_get_build_parameters,
    )

    assert callable(jenkins_get_build_parameters)

  def test_module_re_exports_from_builds(self):
    """Test that functions from jenkins_builds are accessible."""
    from devops_mcps.utils.jenkins.jenkins_builds import (
      jenkins_get_recent_failed_builds,
    )

    assert callable(jenkins_get_recent_failed_builds)

  def test_get_build_log_signature(self):
    """Test that jenkins_get_build_log has correct signature."""
    from devops_mcps.utils.jenkins.jenkins_logs import jenkins_get_build_log
    import inspect

    sig = inspect.signature(jenkins_get_build_log)
    params = list(sig.parameters.keys())
    assert "job_name" in params
    assert "build_number" in params
    assert "start" in params
    assert "lines" in params

  def test_get_build_parameters_signature(self):
    """Test that jenkins_get_build_parameters has correct signature."""
    from devops_mcps.utils.jenkins.jenkins_parameters import (
      jenkins_get_build_parameters,
    )
    import inspect

    sig = inspect.signature(jenkins_get_build_parameters)
    params = list(sig.parameters.keys())
    assert "job_name" in params
    assert "build_number" in params

  def test_get_recent_failed_builds_signature(self):
    """Test that jenkins_get_recent_failed_builds has correct signature."""
    from devops_mcps.utils.jenkins.jenkins_builds import (
      jenkins_get_recent_failed_builds,
    )
    import inspect

    sig = inspect.signature(jenkins_get_recent_failed_builds)
    params = list(sig.parameters.keys())
    assert "hours_ago" in params

  def test_get_build_log_docstring(self):
    """Test that jenkins_get_build_log has a docstring."""
    from devops_mcps.utils.jenkins.jenkins_logs import jenkins_get_build_log

    assert jenkins_get_build_log.__doc__ is not None
    assert "Get build log" in jenkins_get_build_log.__doc__

  def test_get_build_parameters_docstring(self):
    """Test that jenkins_get_build_parameters has a docstring."""
    from devops_mcps.utils.jenkins.jenkins_parameters import (
      jenkins_get_build_parameters,
    )

    assert jenkins_get_build_parameters.__doc__ is not None
    assert "Get build parameters" in jenkins_get_build_parameters.__doc__

  def test_get_recent_failed_builds_docstring(self):
    """Test that jenkins_get_recent_failed_builds has a docstring."""
    from devops_mcps.utils.jenkins.jenkins_builds import (
      jenkins_get_recent_failed_builds,
    )

    assert jenkins_get_recent_failed_builds.__doc__ is not None
    assert "Get recent failed builds" in jenkins_get_recent_failed_builds.__doc__
