# Vektor Flow — libraries

Official language-level libraries and their correctness tests. Library source
migration is unfinished; current checks run through bootstrap.

## Function syntax

```vkf
f(x,step):x+step
g:f[step:2]
::g(3)
```

This prints `5` with the native compiler on Linux. Parentheses call; square
brackets specialize. See the [language examples](https://github.com/vektor-flow/spec/blob/working/README.md#examples).

Contents use the [MIT License](LICENSE). Preserve third-party notices during migration.
