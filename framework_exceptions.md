# Framework Setup Exceptions

This document contains special setup requirements and considerations for specific frameworks in the BBH benchmarking project.

## N8N Framework

The N8N framework has unique setup requirements due to its licensing and API access model.

### Special Requirements

1. **Valid Email Address Required**
   - N8N requires a valid email address during initial setup
   - This email is used for account creation and license management
   - Cannot proceed with setup using fake or invalid email addresses

2. **Free License Activation Required**
   - **CRITICAL**: API access requires activating the free license
   - During N8N setup, when prompted for license activation, **DO NOT SKIP**
   - Select "Activate Free License" or similar option
   - Without free license activation, API endpoints will not be accessible
   - This is a requirement even for local/self-hosted instances

3. **API Key Generation**
   - API key can only be generated after free license activation
   - Go to Settings > n8n API in the N8N interface
   - Click "Create an API key"
   - API access is technically a "paid feature" but available with free license

### Setup Process

1. Run `./setup.sh` in the `fm_n8n` directory
2. Access N8N at http://localhost:5678
3. **Enter a valid email address** (required)
4. **Activate the free license when prompted** (critical step)
5. Navigate to Settings > n8n API
6. Generate API key
7. Set environment variable: `export N8N_API_KEY='your-key'`
8. Run setup script again to complete configuration

### Common Issues

- **"API access not available"**: Usually means free license was not activated
- **Setup hanging**: Check if valid email was provided during initial setup
- **Cannot create API key**: Ensure free license is activated first

### Technical Notes

- N8N uses Docker for local deployment
- Data persisted in Docker volumes
- Default credentials: username `bbh_admin`, password `bbh_secure_2024`
- Container runs on port 5678

### Alternative Approaches

If you encounter issues with the free license approach:
1. Consider using n8n.cloud for a hosted solution
2. Check n8n documentation for latest licensing changes
3. Verify that the free license terms haven't changed

---

*This document should be updated as framework requirements change or new special cases are discovered.*