/* Compatibility entry point retained for historical workflows and PR #408 references.
 * The fixed-black contract is retired. All execution delegates to the adaptive
 * computed-style WCAG audit, which chooses dark text on light surfaces and light
 * text on dark surfaces using the measured contrast ratio. */
import './audit_adaptive_surfaces_v284.mjs';
