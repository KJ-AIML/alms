# Custom Endpoint Security Checklist

Use before enabling live custom-endpoint validation.

## Credentials

- [ ] Credential supplied only via environment variables
- [ ] Credential not present in chat history for this session
- [ ] Outside probe process, only `credential_present` is recorded
- [ ] No credential length, prefix, suffix, hash, or entropy stored
- [ ] Authorization header values never persisted

## Base URL

- [ ] Live mode uses HTTPS only
- [ ] No embedded credentials in URL authority
- [ ] No fragment
- [ ] No unexpected query parameters
- [ ] Host present in `ALMS_COMPAT_ALLOWED_HOSTS`
- [ ] Full base URL not stored in evidence by default
- [ ] Localhost used only for offline tests

## Network

- [ ] `ALMS_COMPAT_CONFIRM_LIVE=1` set only for intentional live runs
- [ ] Cross-host redirects rejected
- [ ] TLS downgrade blocked
- [ ] Unexpected callback/telemetry hosts blocked
- [ ] Metadata-service access not required
- [ ] Offline tests install network tripwire (`ALMS_PROBE_BLOCK_NETWORK=1`)

## Retries and budget

- [ ] SDK max_retries = 0
- [ ] Attempt count measured
- [ ] Hard call cap configured
- [ ] Max output tokens configured
- [ ] No fabricated USD cost from native pricing

## Evidence safety

- [ ] Secret scan clean on artifacts
- [ ] URL leakage scan clean (no full base URL by default)
- [ ] Evidence class = `custom_endpoint_compatibility`
- [ ] Execution mode = `live_custom_endpoint` for live runs
- [ ] No `provider_native` fabrication
- [ ] G2/G3 statuses unchanged after run

## Live activation gates

- [ ] credential present
- [ ] base URL present
- [ ] endpoint ID present
- [ ] model present
- [ ] allowed host present
- [ ] working tree clean
- [ ] offline suites green
- [ ] live plan generated
- [ ] budget and call cap accepted
