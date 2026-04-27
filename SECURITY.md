# Security Policy

Chinese mirror: [简体中文](docs/zh-CN/security.md)

## Supported Versions

AI Data Access Gateway is currently released as an MVP. Security fixes are expected to land on the latest mainline version first. Older snapshots, forks, experimental branches, and unmaintained revisions should not be assumed to receive backports.

## Reporting A Vulnerability

Do not open public GitHub issues for suspected vulnerabilities.

Please report security issues privately to the project maintainers through the repository contact channel, private security advisory reporting if it is enabled for the repository, or a dedicated security email address if one is configured later.

When reporting a vulnerability, include:

- the affected version, branch, or commit
- the deployment or runtime context
- clear reproduction steps or a proof of concept
- the expected impact and affected trust boundary
- any suggested mitigation or compensating control

The maintainers will review the report, confirm whether it is in scope, and coordinate disclosure conservatively based on available maintainer capacity. Response timing may vary for an MVP repository, but reports will be triaged in good faith.

## Scope Notes

This repository is an open-source MVP. Reports are especially useful when they demonstrate impact in areas such as:

- authentication or authorization bypass
- secret disclosure
- masking or decrypt-control bypass
- SQL guard bypass that enables forbidden execution paths
- admin or runtime API exposure flaws
- audit logging gaps that materially undermine security reviewability

The following are generally out of scope unless they depend on a demonstrable flaw in this repository:

- vulnerabilities that exist only in unsupported forks or heavily modified downstream deployments
- reports that require local privileged shell access without a gateway defect
- purely theoretical issues without a reproducible repository impact
- findings that depend entirely on insecure operator configuration outside the repository defaults

## Coordinated Disclosure

Please avoid public disclosure until the maintainers have had a reasonable opportunity to validate the report and prepare a fix or mitigation. If a report is determined to be out of scope or not reproducible, the maintainers may close it without further action.
