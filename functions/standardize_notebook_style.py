"""Apply the minimum CIndRA presentation standard to published notebooks.

The operation is idempotent and intentionally does not rewrite scientific code or
figure choices. Run from the repository root after adding a notebook.
"""

from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_ROOT = ROOT / "notebooks" / "historical"
EXCLUDED = {"a_Mean_Temperature_maps copy.ipynb"}
STANDARD_HEADING = "## Interpretation and reproducibility notes"
STYLE_MARKER = "# CIndRA notebook display standard"
STYLE_CELL = """# CIndRA notebook display standard
import matplotlib as mpl

mpl.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 15,
    'axes.labelsize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 13,
    'figure.dpi': 100,
    'savefig.dpi': 300,
})"""


def interpretation_note(path: Path) -> str:
    text = str(path).lower()
    if "site_setup" in path.name or "regional_setup" in path.name:
        return (
            "## Reproducibility notes\n\n"
            "This setup notebook creates configuration or cached inputs used by later "
            "analyses. Review the printed site/station selection, coverage diagnostics "
            "and output paths before continuing; rerunning it can change downstream results."
        )
    if "regional_plots" in path.name:
        return (
            "## Reproducibility notes\n\n"
            "This page is a placeholder and performs no calculation. Document the data "
            "source, coverage, method and outputs here when the regional sea-level workflow is added."
        )

    scope = "Regional aggregates can hide local differences among stations, grid cells and EEZs." if "/regional/" in text else "Results apply to the configured station, site or EEZ and should not be generalized without checking spatial representativeness."
    if "air_temperature" in text or "rainfall" in text:
        caveat = "Station coverage, missing observations, relocations and instrument changes can affect apparent variability and trends."
    elif "tropical_cyclones" in text:
        caveat = "Changes in observing practices and best-track quality can affect historical cyclone counts and intensity estimates."
    elif "sea_level" in text:
        caveat = "Datum choice, vertical land motion, record completeness and the distinction between relative and absolute sea level must be retained in interpretation."
    elif "biochemistry" in text:
        caveat = "Product resolution, depth, model or satellite origin and temporal coverage differ among biogeochemical variables and must be considered in comparisons."
    elif "sea_surface_temperature" in text:
        caveat = "Gridded SST resolution, data gaps and the selected climatological baseline affect anomalies, extremes and marine-heatwave metrics."
    else:
        caveat = "Review data coverage, missingness, units and the documented reference period before interpreting results."

    return (
        f"{STANDARD_HEADING}\n\n"
        f"- {scope}\n"
        f"- {caveat}\n"
        "- Linear trends are descriptive unless the notebook explicitly accounts for "
        "temporal autocorrelation and other statistical assumptions.\n"
        "- Confirm the printed source, analysis period, reference period and output paths "
        "before using figures or tables in reporting."
    )


def standardize(path: Path) -> bool:
    nb = nbformat.read(path, as_version=4)
    changed = False

    kernel = {"display_name": "cc_indicators_v2", "language": "python", "name": "python3"}
    if dict(nb.metadata.get("kernelspec", {})) != kernel:
        nb.metadata["kernelspec"] = kernel
        changed = True
    if nb.metadata.get("language_info", {}).get("name") != "python":
        nb.metadata["language_info"] = {"name": "python"}
        changed = True

    if not any(cell.cell_type == "code" and STYLE_MARKER in cell.source for cell in nb.cells):
        title_index = next(
            (i for i, cell in enumerate(nb.cells) if cell.cell_type == "markdown" and cell.source.lstrip().startswith("# ")),
            0,
        )
        nb.cells.insert(title_index + 1, nbformat.v4.new_code_cell(STYLE_CELL))
        changed = True

    # Correct the one known hierarchy violation without changing section wording.
    if path.name == "c_MHW.ipynb":
        mhw_heading_levels = {
            "1. EEZ-wide analysis": "##",
            "Build and inspect the EEZ mask": "###",
            "Detect EEZ-wide marine heatwaves": "###",
            "EEZ annual indicators and trends": "###",
            "Most intense and longest EEZ-average events": "###",
            "2. User-selected point analysis": "##",
            "EEZ–point comparison": "###",
        }
        for cell in nb.cells:
            if cell.cell_type != "markdown":
                continue
            updated_lines = []
            for line in cell.source.splitlines():
                heading_text = line.lstrip("#").strip() if line.startswith("#") else None
                if heading_text in mhw_heading_levels:
                    line = f"{mhw_heading_levels[heading_text]} {heading_text}"
                updated_lines.append(line)
            updated = "\n".join(updated_lines)
            if updated != cell.source:
                cell.source = updated
                changed = True

    # Avoid skipped heading levels (for example ## directly followed by ####).
    previous_level = 0
    in_fence = False
    for cell in nb.cells:
        if cell.cell_type != "markdown":
            continue
        updated_lines = []
        for line in cell.source.splitlines():
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                updated_lines.append(line)
                continue
            if not in_fence and line.startswith("#"):
                hashes, separator, title = line.partition(" ")
                if separator and set(hashes) == {"#"}:
                    level = len(hashes)
                    if previous_level and level > previous_level + 1:
                        level = previous_level + 1
                        line = f"{'#' * level} {title}"
                    previous_level = level
            updated_lines.append(line)
        updated = "\n".join(updated_lines)
        if updated != cell.source:
            cell.source = updated
            changed = True

    for cell in nb.cells:
        if cell.cell_type != "markdown":
            continue
        if cell.source.startswith("## Interpretation notes"):
            cell.source = cell.source.replace("## Interpretation notes", STANDARD_HEADING, 1)
            changed = True

    has_final_note = any(
        cell.cell_type == "markdown"
        and ("Interpretation and reproducibility notes" in cell.source or "## Reproducibility notes" in cell.source)
        for cell in nb.cells
    )
    if not has_final_note:
        nb.cells.append(nbformat.v4.new_markdown_cell(interpretation_note(path)))
        changed = True

    if changed:
        nbformat.write(nb, path)
    return changed


def main() -> None:
    paths = sorted(NOTEBOOK_ROOT.rglob("*.ipynb"))
    paths = [p for p in paths if ".ipynb_checkpoints" not in p.parts and p.name not in EXCLUDED]
    changed = [p for p in paths if standardize(p)]
    print(f"Standardized {len(changed)} of {len(paths)} notebooks.")
    for path in changed:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
