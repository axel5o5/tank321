# Public repository cleanup

[Back to README](../README.md) · [Reproduction commands](REPRODUCTION.md)

## Scope

This cleanup is limited to the public repository: a concise research entry point, separate reproduction and methods guides, safe deposited-input reproduction, bounded checks, integrity checking and CI configuration. It does not add raw data, credentials, nonpublic research materials or new scientific claims. The manifest and checksums cover the updated public payload while preserving historical source hashes.

Scientific settings, deposited data and reported results remain unchanged. The reproduction wrapper defaults to deposited artifacts and the deposited value cache, writes to `outputs/`, and requires `--full` for expensive simulations. The [methods guide](METHODS.md) records the unchanged simulation settings and substantive caveats.

## Validation boundary

On October 2, 2026, a fresh Python 3.13.7 macOS arm64 virtual environment passed the hashed, wheel-only installation of all 17 locked packages, `pip check`, **22 science/reproduction tests and 14 integrity-checker tests**, and deposited-artifact reproduction. All five generated text/CSV artifacts matched the deposited versions byte-for-byte; figures were generated but binary/visual equivalence was not assessed. The snapshot integrity check passed before and after reproduction. All 22 deposited data, result, abstract and PDF files remain byte-for-byte unchanged. These are bounded tests, not a full scientific replication.

Not yet performed during this cleanup:

- Expensive full historical or prospective simulations.
- A hosted GitHub Actions run. The configured target is `macos-15`, arm64, Python 3.13.7.
- Raw player/game reconstruction, independent market quote retrieval, independent ownership verification or an upstream source-rights audit.

The refreshed [RELEASE_MANIFEST.json](../RELEASE_MANIFEST.json) and [SHA256SUMS](../SHA256SUMS) record the cleanup payload. Subsequent file edits require another metadata refresh and snapshot check.

[VALIDATION.md](../VALIDATION.md) remains the historical October 1 record, including its original test counts and artifact comparisons. Its results should not be read as a fresh validation of this cleanup. These notes make no claim that the cleanup has been released, merged or tagged.
