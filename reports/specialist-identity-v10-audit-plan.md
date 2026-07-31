# Specialist identity v10 audit scope

This release audits and hardens the specialists sector from the public interface through authentication, recovery, owner administration, session handling, password reset, D1 state changes, email-provider verification, and deployment ownership.

## Release invariants

- Only the v10 production workflow may deploy the identity Worker automatically.
- Normal health verifies the platform and database without pretending that a configured email key is valid.
- Deep health verifies the email provider authentication separately.
- Automated password-recovery responses are truthful about delivery.
- The owner can create a one-time manual recovery link when the external email provider is unavailable.
- Creating a new reset link invalidates all older unused links.
- Successful password reset revokes existing sessions and older links.
- Login executes a constant-cost password derivation for missing and existing accounts.
- Sessions are bound to the browser user-agent hash, with optional strict IP binding.
- CORS preflight remains available for all browser-facing API routes.
- Password rules support Arabic letters and require letters, numbers, and symbols.
