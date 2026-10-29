# Salesforce CI/CD — Code & Configuration Guide

This document explains the purpose of the main Python modules and the Salesforce project configuration files used by the workflow.

## 1. Main orchestration and configuration

| File | Purpose |
|---|---|
| `cicd.py` | Main orchestrator. Accepts the stage requested by the CI/CD pipeline, invokes the appropriate workflow, and returns an exit code. |
| `configuration/environment.py` | Reads and validates environment variables, including the selected target environment. |
| `configuration/config_manager.py` | Updates the Salesforce project configuration at runtime so the authentication placeholder can be replaced with the secret supplied by the CI/CD platform. |

## 2. Authentication and deployment

| File | Purpose |
|---|---|
| `authentication/authenticate.py` | Runs Salesforce CLI authentication and records the authenticated target org details for subsequent stages. |
| `deployment/deployment.py` | Implements Salesforce validation and deployment. Validation runs as a dry run; deployment performs the actual deployment to the selected org. |

## 3. Preparation steps

| File | Purpose |
|---|---|
| `preparation/prepare.py` | Loads the preparation configuration selected for the environment and coordinates the configured preparation operations. |
| `preparation/file_replacement.py` | Copies or replaces project files according to the configured source and target paths. |
| `preparation/workflows.py` | Applies configured changes to Salesforce Workflow metadata, including supported email alert settings. |
| `preparation/quick_actions.py` | Applies configured changes to Salesforce Quick Action metadata, including supported Send Email settings. |
| `preparation/duplication_rules.py` | Applies configured changes to the sort order of Salesforce Duplicate Rules. |

## 4. Shared utilities

| File | Purpose |
|---|---|
| `utils/command_runner.py` | Runs external commands such as Salesforce CLI, streams command output, and returns the execution result. |
| `utils/logger.py` | Centralizes logging for troubleshooting and execution records. |
| `utils/error_parser.py` | Parses Salesforce CLI output to extract deployment errors, test failures, and diagnostic information. |
| `utils/exit_codes.py` | Defines exit-code conventions used to communicate success and failure to the CI/CD platform. |
| `utils/path_security.py` | Provides shared path-validation helpers intended to prevent file operations from escaping their allowed base directories. |

## 5. Salesforce project configuration and supporting files

These files belong to, or are used alongside, the Salesforce project. Their exact location should match the repository layout used by the CI/CD job.

| File or directory | Purpose |
|---|---|
| Salesforce project: `config/config.json` | Standard Salesforce-generated project configuration. It already contains the `#{auth_url}#` placeholder expected by the tool; the workflow substitutes the secret at runtime. |
| `config/before-deploy-dev.json` | Example environment-specific preparation configuration included with the tool. Use it as a reference when creating or adapting files for other environments. |
| `config/before-deploy-{env}.json` | Environment-specific preparation rules selected by `SF_TARGET_ENV`, determining which preparation actions run before validation or deployment. |
| `filereplacement/` | Holds replacement files referenced by file-replacement rules. Contents depend on the project and its configuration. |
| `target_org.txt` (in the Salesforce project root) | Stores the authenticated Salesforce username used by subsequent stages to target the intended org explicitly. |
| `salesforce-cicd/cicd.log` | Workflow log file used for troubleshooting. Logs must not contain authentication URLs, credentials, or other sensitive values. |

## 6. Typical execution flow

1. **Checkout:** The CI/CD job clones the Salesforce source repository and this tool repository, placing the tool under `salesforce-cicd/`.
2. **Configure:** The job securely provides `auth_url` and sets `SF_TARGET_ENV`.
3. **Authenticate:** Run `python .\salesforce-cicd\cicd.py authenticate`.
4. **Prepare:** Run `python .\salesforce-cicd\cicd.py prepare`.
5. **Validate:** Run `python .\salesforce-cicd\cicd.py validate` to perform a dry-run validation.
6. **Deploy:** After successful validation and any required approvals, run `python .\salesforce-cicd\cicd.py deploy`.

## 7. Responsibility boundary

- **CI/CD platform:** Checks out repositories, installs prerequisites, provides secrets, controls approvals, invokes stages, and reacts to exit codes.
- **Python workflow:** Implements reusable Salesforce authentication, preparation, validation, deployment, command execution, and supporting logic.
