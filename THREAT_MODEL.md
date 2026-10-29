# Threat model

| Threat | Control |
|---|---|
| Tenant A retrieves tenant B's chunks | Tenant predicate in vector SQL and tenant RLS on chunks and documents |
| Employee retrieves manager or admin chunks | Role predicate in vector SQL and role RLS |
| Client changes tenant or role fields | API ignores those fields; identity comes from a verified JWT and is checked against the user record |
| Token modification or expiry | Signature, issuer, audience, required claims, expiry, and user record are checked |
| Developer omits the SQL filter | App connects as `rag_app`, a non-owner, non-bypass role; RLS still applies |
| Prompt injection in documents | Retrieved text is passed as untrusted source data; only authorized rows enter generation |
| Connection state leaks between requests | Scope variables use transaction-local `set_config(..., true)` on a fresh transaction |
| Unauthorized admin audit access | Admin check in API plus tenant RLS on audit rows |

The service does not defend against a compromised database administrator, a malicious or compromised LLM provider, model memorization, embedding side channels, or timing side channels. Local demo passwords and secrets must be replaced before any public deployment. Audit logs contain raw queries, so operators should set retention and access rules before handling real user data.
