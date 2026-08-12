# Deployment Profile Boundary

The portable Sovereignty runtime is independent of any individual owner's identity, private memory, keys, repositories, branches, or provider topology.

A deployment profile instantiates the runtime for one installation. It supplies references to local identity, vault state, evidence, credentials, topology, capabilities, and governance policy.

## Production invariants

- No personal identity or personal branch topology is embedded in the portable core.
- Every installation receives fresh deployment, device, and authority identifiers unless an owner explicitly imports existing identity with proof.
- Private memory, keys, credentials, and evidence remain inside the selected vault boundary.
- Repository and branch names are deployment choices; the reference example is not a default.
- Unknown fields and invalid values fail closed.
- External execution is an explicit capability, never an authority.
- Audit and transparency are mandatory.
- Automated validation never grants owner approval.
- A reference-only profile can document architecture but can never activate.
- SCAR initialization and owner approval are explicit post-validation gates.

## Activation boundary

```text
explicit installation inputs
        |
        v
fresh instance identity + isolated vault
        |
        v
schema validation
        |
        v
identity / isolation / topology / capability / governance validation
        |
        v
SCAR initialization evidence
        |
        v
OWNER APPROVAL
        |
        +---- denied / unavailable -> NOT ACTIVE
        |
        v
ACTIVE INSTANCE
```

The profile is configuration. It is not authority by itself.
