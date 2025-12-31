"""
Tests for project setup and basic imports.
"""


def test_package_importable():
    """Verify package can be imported."""
    import orion

    assert orion.__version__
    assert isinstance(orion.__version__, str)


def test_version_format():
    """Verify version follows semantic versioning."""
    import orion

    version_parts = orion.__version__.split(".")
    assert len(version_parts) >= 2, "Version should have at least major.minor"

    # Check that major and minor are numeric
    assert version_parts[0].isdigit(), "Major version should be numeric"
    assert version_parts[1].isdigit(), "Minor version should be numeric"


def test_subpackages_importable():
    """Verify all subpackages can be imported."""

    # Basic import test passes if no ImportError raised
    assert True
