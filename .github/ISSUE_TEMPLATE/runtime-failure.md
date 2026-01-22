---
name: Runtime Failure
about: Report evaluation failures during ./run.sh execution
title: '[RUNTIME] Evaluation failure: '
labels: 'bug, runtime'
assignees: ''
---

## Runtime Failure Report

**Which step failed?**
- [ ] `./run.sh` - Main execution script
- [ ] Specific framework evaluation
- [ ] Dataset loading/processing
- [ ] Other (please specify)

**Framework(s) affected:**
<!-- List the specific frameworks that failed -->
- 

**Dataset(s) affected:**
<!-- List the datasets being processed when failure occurred -->
- [ ] BBH (Big Bench Hard)
- [ ] GSM8K (Grade School Math 8K)  
- [ ] ARC (AI2 Reasoning Challenge)

**Error message:**
<!-- Paste the error message from console output -->
```
[Paste error message here]
```

**Configuration:**
**config.yml settings:**
```yaml
# Paste relevant sections of your frameworks/config.yml
datasets_to_run:
  - 

frameworks_to_run:
  - 

commons:
  sample_mode: 
  model: 
```

**System Information:**
- **OS:** <!-- e.g., Ubuntu 22.04, macOS 14.0, Windows 11 -->
- **Python version:** <!-- Run: python --version -->
- **uv version:** <!-- Run: uv --version -->
- **OpenAI API key:** <!-- Configured: Yes/No (don't paste the actual key) -->

**Log files:**
<!-- Please attach or paste the relevant log files -->

**Execution log directory:** `logs/run_<timestamp>/`
```
[Paste relevant sections from framework-specific log files, or attach the files]
```

**Steps to reproduce:**
1. 
2. 
3. 

**Expected behavior:**
<!-- Describe what you expected to happen -->

**Additional context:**
<!-- Add any other context about the problem here -->

**Attempted solutions:**
<!-- List any troubleshooting steps you've already tried -->
- [ ] Verified setup completed successfully
- [ ] Checked OpenAI API key and quotas
- [ ] Ran with different configuration
- [ ] Other: 

---
**Note for maintainers:** Please check the attached execution logs for detailed framework traces and dataset processing issues.