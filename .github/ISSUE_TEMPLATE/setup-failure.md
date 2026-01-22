---
name: Setup Failure
about: Report framework setup failures during scripts/setup.sh execution
title: '[SETUP] Framework setup failure: '
labels: 'bug, setup'
assignees: ''
---

## Setup Failure Report

**Which step failed?**
- [ ] `scripts/setup.sh` - Initial setup script
- [ ] Specific framework setup
- [ ] Other (please specify)

**Framework(s) affected:**
<!-- List the specific frameworks that failed, e.g., fm_autogen, fm_swarm -->
- 

**Error message:**
<!-- Paste the error message from console output -->
```
[Paste error message here]
```

**System Information:**
- **OS:** <!-- e.g., Ubuntu 22.04, macOS 14.0, Windows 11 -->
- **Python version:** <!-- Run: python --version -->
- **uv version:** <!-- Run: uv --version -->

**Log files:**
<!-- Please attach or paste the relevant log files -->

**Setup log file:** `logs/setup_<timestamp>.log`
```
[Paste relevant sections of setup log here, or attach the full file]
```

**Steps to reproduce:**
1. 
2. 
3. 

**Additional context:**
<!-- Add any other context about the problem here -->

**Attempted solutions:**
<!-- List any troubleshooting steps you've already tried -->
- [ ] Ran `scripts/cleanup.sh` before setup
- [ ] Verified OpenAI API key in `.env` file
- [ ] Checked internet connectivity
- [ ] Other: 

---
**Note for maintainers:** Please check the attached log files for detailed error traces and framework-specific issues.