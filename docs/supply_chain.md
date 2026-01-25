# Supply Chain Security

This document explains how to verify the integrity and provenance of payroll-engine releases.

## Why This Matters

Payroll-engine handles money movement. Supply chain attacks can compromise financial systems. We provide:

- **Checksums** (SHA256) for all release artifacts
- **SBOM** (Software Bill of Materials) in CycloneDX format
- **SLSA Provenance** attestations for build verification
- **Trusted Publishing** to PyPI (no API tokens)

## Verifying a Release

### 1. Verify Checksums

Every release includes a `SHA256SUMS.txt` file:

```bash
# Download the release and checksums
curl -LO https://github.com/mcp-tool-shop/payroll-engine/releases/download/v0.1.0/payroll_engine-0.1.0.tar.gz
curl -LO https://github.com/mcp-tool-shop/payroll-engine/releases/download/v0.1.0/SHA256SUMS.txt

# Verify
sha256sum -c SHA256SUMS.txt
```

### 2. Verify SLSA Provenance

Releases include SLSA Level 3 provenance attestations:

```bash
# Install slsa-verifier
go install github.com/slsa-framework/slsa-verifier/v2/cli/slsa-verifier@latest

# Download provenance
curl -LO https://github.com/mcp-tool-shop/payroll-engine/releases/download/v0.1.0/multiple.intoto.jsonl

# Verify
slsa-verifier verify-artifact \
  payroll_engine-0.1.0.tar.gz \
  --provenance-path multiple.intoto.jsonl \
  --source-uri github.com/mcp-tool-shop/payroll-engine \
  --source-tag v0.1.0
```

### 3. Inspect SBOM

Each release includes a CycloneDX SBOM listing all dependencies:

```bash
# Download SBOM
curl -LO https://github.com/mcp-tool-shop/payroll-engine/releases/download/v0.1.0/sbom.json

# View dependencies
cat sbom.json | jq '.components[].name'

# Or use a tool like grype for vulnerability scanning
grype sbom:sbom.json
```

## PyPI Verification

Packages published to PyPI use [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC):

- No API tokens stored in repository
- Publishing tied to specific GitHub workflow
- Builds are reproducible from source

To verify a PyPI package matches the GitHub release:

```bash
# Download from PyPI
pip download payroll-engine==0.1.0 --no-deps

# Compare checksum with GitHub release
sha256sum payroll_engine-0.1.0-py3-none-any.whl
# Should match the entry in SHA256SUMS.txt from GitHub
```

## Build Reproducibility

To reproduce a build locally:

```bash
git clone https://github.com/mcp-tool-shop/payroll-engine.git
cd payroll-engine
git checkout v0.1.0

python -m pip install build
python -m build

# Compare with release artifacts
sha256sum dist/*
```

## Security Contact

Report supply chain concerns to: security@payroll-engine.com

## References

- [SLSA Framework](https://slsa.dev/)
- [CycloneDX](https://cyclonedx.org/)
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [Sigstore](https://sigstore.dev/)
