"""Documentation pointer for the SCAR route-trace patch template.

The complete instructional patch is documented in
``docs/event-class-route-trace-patch-for-scar.md``. This compatibility module
must remain inert: it is not imported by the runtime and contains no executable
SCAR implementation.

Runtime implementations must apply the documented changes to the actual SCAR
ledger module using that module's existing imports and project-local types.
"""

# Intentionally no runtime code.
