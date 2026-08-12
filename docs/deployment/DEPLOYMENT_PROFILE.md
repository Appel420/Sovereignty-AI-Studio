# Deployment Profile Boundary

The portable Sovereignty runtime is independent of any individual owner's identity, memory, keys, repositories, branches, or provider topology.

A deployment profile instantiates the runtime for one installation. It supplies references to local identity, vault state, evidence, credentials, topology, capabilities, and governance policy.

## Invariants

- Personal identity is never embedded in the portable core.
- Private memory, keys, credentials, and evidence are instance-local.
- Repository and branch names are deployment choices, not architectural constants.
- A reference deployment is documentation and test material only; it is not a default identity or default vault.
- Validation must reject unknown fields and invalid topology rather than silently substituting another deployment's values.
- Audit and transparency are mandatory deployment properties.
- External execution is optional and never becomes an authority solely because it is enabled.
- Production promotion remains governed by the selected deployment's authorization policy.

## Initialization

`deployment-profile.schema.json` is the structural contract. A new installation should generate its own `deploymentId`, identity references, vault references, and topology. The example profile demonstrates the shape without containing a real owner's identity or secrets.

## Boundary

```text
portable core
    -> deployment profile
    -> instance identity / vault / topology
    -> schema validation
    -> policy + governance validation
    -> owner authorization
    -> active runtime
```

The profile is configuration. It is not authority by itself.
