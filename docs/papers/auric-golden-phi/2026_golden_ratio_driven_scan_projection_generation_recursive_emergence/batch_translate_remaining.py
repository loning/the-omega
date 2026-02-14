#!/usr/bin/env python3
"""
Batch translate all remaining Chinese LaTeX files to English.
Uses Claude API to translate each file with academic quality standards.
"""

import os
import sys
import time
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()
BASE_DIR = Path(__file__).parent

TRANSLATION_SYSTEM = """You are a professional academic translator specializing in mathematics and theoretical physics.
Translate the following Chinese LaTeX document to English with these requirements:

1. Maintain all LaTeX commands, labels, and references exactly as they are
2. Preserve all mathematical notation and formatting unchanged
3. Use formal academic English
4. Translate technical terminology accurately
5. Keep paragraph structure and document organization
6. Do NOT add any notes, commentary, or explanations
7. Output ONLY the translated LaTeX content"""

# List of remaining files to translate
REMAINING_FILES = [
    "sections/appendix/sync_kernel/weighted/subsubsec__sync-kernel-weighted-pressure-ldp.tex",
    "sections/body/pom/parts/08_projection_ontology_mathematics_part03c_b.tex",
    "sections/body/pom/parts/08_projection_ontology_mathematics_part03c_c.tex",
    "sections/body/pom/parts/08_projection_ontology_mathematics_part07_c.tex",
    "sections/body/pom/parts/lem__pom-shifted-fib-fusion-defect-positive.tex",
    "sections/body/pom/parts/prop__pom-fib-pell-unit-mobius.tex",
    "sections/body/pom/parts/prop__pom-fiber-index-cgf.tex",
    "sections/body/pom/parts/rem__pom-fiber-value-set-complexity.tex",
    "sections/body/pom/parts/subsec__pom-entropy-maxent.tex",
    "sections/body/pom/parts/subsec__pom-order-bottleneck.tex",
    "sections/body/pom/parts/subsec__pom-position.tex",
    "sections/body/pom/parts/subsec__pom-projection-entropy.tex",
    "sections/body/pom/parts/subsec__pom-s2.tex",
    "sections/body/pom/parts/subsec__pom-s5.tex",
    "sections/body/pom/parts/subsec__pom-spectral-gap.tex",
    "sections/body/pom/parts/subsec__pom-three-generator-residual-closure.tex",
    "sections/body/pom/parts/subsubsec__pom-collision-kernel-family.tex",
    "sections/body/pom/parts/subsubsec__pom-fiber-lattice-fence-interval-zeta.tex",
    "sections/body/pom/parts/subsubsec__pom-fiber-toggle-coxeter-monodromy-parallelism.tex",
    "sections/body/pom/parts/subsubsec__pom-hoelder-mixed-kl-bridge.tex",
    "sections/body/zeta_finite_part/xi/09_zeta_finite_09_subsec_certificate_coherence_orthogonal_axis_capacity_part1.tex",
    "sections/body/zeta_finite_part/xi/09_zeta_finite_09_subsec_certificate_coherence_orthogonal_axis_capacity_part3.tex",
    "sections/body/zeta_finite_part/xi/subsec__dephysicalized-horizon-timefiber-nohair.tex",
    "sections/body/zeta_finite_part/xi/subsec__xi-certificate-coherence-orthogonal-axis-capacity-part1.tex",
    "sections/body/zeta_finite_part/xi/subsec__xi-certificate-coherence-orthogonal-axis-capacity-part3.tex",
    "sections/body/zeta_finite_part/xi/subsec__xi-pw-type-safety-null.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__dephysicalized-horizon-quotient-data-structure.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__ramanujan-phase-lift-symmetry.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__selfdual-blaschke-defect-fixed-slice.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-comoving-defect-delta-bound.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-debranges-canonical-rhp-adelic.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-depth-height-two-level-extremal-decomposition.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-depth-jacobi-certificate-audit-guards.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-depth-shadow-spectrum-jfraction-bernstein.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-depth-stieltjes-renormalization.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-depth-truncated-moment-markov-pade-stieltjes.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-hardy-inner-clark-carleson.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-ramanujan-feasible-reduction.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-residue-multipole-temperedness.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-spectral-measure-tomography.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-spectral-measure-tomography__defect-entropy-hyperbolic-laws.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-negative-square-index-pontryagin-realization.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-offslice-quantitative-indicators.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-phase-prefix-resolution-law.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-pick-poisson-image-charge-energy.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-poisson-coarsegraining-tv-kl-asymptotics.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-pontryagin-toeplitz-blaschke-tomography-tate.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part1.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part2.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part3.tex",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions.tex",
]

def translate_file(file_path: str, output_path: str):
    """Translate a single file using Claude API."""
    print(f"\n{'='*80}")
    print(f"Translating: {file_path}")
    print(f"Output: {output_path}")

    # Read source file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR reading {file_path}: {e}")
        return False

    # Check if already in English
    if not any('\u4e00' <= char <= '\u9fff' for char in content):
        print(f"No Chinese found, copying: {file_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    # Translate
    print(f"Translating {len(content)} characters...")
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=16000,
            temperature=0.3,
            system=TRANSLATION_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Translate this LaTeX document to English:\n\n{content}"
            }]
        )

        translated = message.content[0].text.strip()

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(translated)

        print(f"✓ SUCCESS: Wrote {len(translated)} characters")
        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def main():
    """Main translation loop."""
    print("="*80)
    print("Batch Translation: Chinese LaTeX → English")
    print("="*80)
    print(f"\nTotal files to translate: {len(REMAINING_FILES)}")

    success_count = 0
    failed_files = []

    start_time = time.time()

    for idx, rel_path in enumerate(REMAINING_FILES, 1):
        source = BASE_DIR / rel_path
        target = source.with_name(source.stem + "_en.tex")

        print(f"\n[{idx}/{len(REMAINING_FILES)}] Progress: {idx/len(REMAINING_FILES)*100:.1f}%")

        if target.exists():
            print(f"SKIP: {target.name} already exists")
            success_count += 1
            continue

        if translate_file(source, target):
            success_count += 1
        else:
            failed_files.append(rel_path)

        # Rate limiting
        time.sleep(1)

    # Summary
    elapsed = time.time() - start_time
    print("\n" + "="*80)
    print("Translation Complete!")
    print(f"Successful: {success_count}/{len(REMAINING_FILES)}")
    print(f"Failed: {len(failed_files)}")
    print(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")

    if failed_files:
        print("\nFailed files:")
        for f in failed_files:
            print(f"  - {f}")

    print("="*80)

if __name__ == "__main__":
    main()
