How to create a new qudi-core release
=====================================

1. Version bump
---------------

Create a single commit that includes three changes:
- Update the version number in the ``/Version`` file. The scheme is ``Major.Minor.Hotfix``.
- Rename the “Pre-Release” section in ``/docs/changelog.rst`` to “Version x.y.z” and add the release date below. Create a new empty “Pre-Release” template (with subsections) at the top of the file. The head of the file should look like this:

  .. code-block:: rst

      # Changelog

      ## Pre-Release

      ### Breaking Changes
      None

      ### Bugfixes
      None

      ### New Features
      None

      ### Other
      None

      ## Version x.y.z Released on DD.MM.YYYY

- Add the version to be released in ``/.github/ISSUE_TEMPLATE/bug_report.yml`` under the `body` item with `id: version`. Insert the new release version as a new item in the dropdown just below `Development` and above the newest previous release version:

  .. code-block:: yaml

      name: Bug Report
      description: File a new bug report
      title: “[Bug]”
      labels: [“bug”]
      body:
        - type: markdown
          attributes:
            value: |
              Please fill out this bug report form as thoroughly as possible! Thank you for taking the time.
        - type: dropdown
          id: version
          attributes:
            label: Version
            description: What version of our software are you running?
            options:
              - Development
              - Release vX.Y.Z  # <--- Insert the new version here
              - Release v1.1.0
              - Release v1.0.1
              - Release v1.0.0
          validations:
            required: true
        - type: textarea
          ...

Push these changes to ``main`` via a release PR.

2. Wait for PyPI test release to be successful
----------------------------------------------

Check the `GitHub Actions status <https://github.com/Ulm-IQO/qudi-core/actions>`__ for a successful PyPI test server release. This is *not* the actual PyPI release but just a test run to identify problems before the actual release.

**If this test run fails, you need to fix the issue before proceeding with the release!**

.. figure:: ../images/github-actions-test-release-screenshot.png
   :alt: GitHub Actions test release screenshot

   GitHub Actions test release screenshot

3. Create a new release with a tag on GitHub
--------------------------------------------

1. Go to https://github.com/Ulm-IQO/qudi-core/releases and click on “Draft a new release”. |GitHub draft a new release screenshot|
2. Create a new release tag with the naming convention according to the version number to be released ``vX.Y.Z``. Click on `+ Create new tag: ... on publish` and make sure the target is set to ``main``. |GitHub create a release tag screenshot|
3. Set the name for the release to ``Release vX.Y.Z`` with the respective version number inserted.
4. Copy over the section of ``/docs/changelog.rst`` corresponding to the release and insert it in the release description field. Remove the section header, i.e., the ``Version vX.Y.Z`` part.
5. Now your release form should look like the screenshot below. If you are satisfied, click ``Publish release`` at the bottom of the form. |GitHub finished release form screenshot|

4. Wait for GitHub Actions to publish the release on PyPI
---------------------------------------------------------

Congratulations! You have successfully published a release of ``qudi-core`` on GitHub and PyPI.

.. |GitHub draft a new release screenshot| image:: ../images/github-draft-new-release-screenshot.png
.. |GitHub create a release tag screenshot| image:: ../images/github-release-tag-screenshot.png
.. |GitHub finished release form screenshot| image:: ../images/github-release-form-screenshot.png
