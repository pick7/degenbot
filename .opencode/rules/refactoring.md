# Refactoring Rules

## Backwards Compatibility
- Unless directed otherwise, design new features as a standalone without a backwards compatibility layer. Use a feature flag during development and testing, then perform a hard cutover.