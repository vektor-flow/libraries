# Vektor Flow — libraries

Official Vektor Flow libraries, kept together initially.

## Ownership

Functionality expressed using VKF, with library documentation and correctness tests. Add library areas only when actual code needs them; independent releases may justify future splits.

## Outside this repository

Hidden compiler semantics, compiler backends, or a competing language specification.

## Relationships

Builds on spec semantics and compiler execution; site may explain and demonstrate libraries, while benchmarks measures them.

## Initial status

This repository establishes ownership only. No implementation or authoritative semantics have been migrated. Existing repositories remain the owners of their current contents until a migration proposal is reviewed. No bootstrap generation or performance result is claimed by this initial setup.

Initial contents are licensed under the [MIT License](LICENSE). Any future migration must preserve applicable third-party notices and review compatibility with existing component licenses.

## Organization map

- [compiler](https://github.com/vektor-flow/compiler): Active Vektor Flow compiler implementation.
- [bootstrap](https://github.com/vektor-flow/bootstrap): Independent bootstrap compiler and reference implementation.
- [spec](https://github.com/vektor-flow/spec): Authoritative definition of Vektor Flow language semantics: what a VKF program means.
- [libraries](https://github.com/vektor-flow/libraries): Official Vektor Flow libraries, kept together initially.
- [benchmarks](https://github.com/vektor-flow/benchmarks): Reproducible measurement of compiler and generated-program behavior.
- [research](https://github.com/vektor-flow/research): Experimental and scientific work outside accepted production mechanisms and language semantics.
- [site](https://github.com/vektor-flow/site): Future home of vektorflow.org and user-facing documentation and demonstrations.
- [.github](https://github.com/vektor-flow/.github): Shared GitHub organization configuration and contributor guidance.
