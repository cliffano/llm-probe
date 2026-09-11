"""Collate the per-model JSON files under data/ into an HTML report under stage/."""

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from conflog import Conflog
from pandasreporter import PandasReporter

ROOT_DIR = Path(__file__).resolve().parent.parent
LOGGER = Conflog(conf_files=[str(ROOT_DIR / "config" / "conflog.yaml")]).get_logger(
    "llm-probe"
)


def flatten_dict(
    nested: dict[str, Any], parent_key: str = "", sep: str = "_"
) -> dict[str, Any]:
    """Flatten a nested dictionary, joining keys with sep.

    :param nested: Dictionary to flatten.
    :type nested: dict[str, Any]
    :param parent_key: Prefix prepended to keys at this nesting level.
    :type parent_key: str
    :param sep: Separator joining a parent key to its child key.
    :type sep: str
    :return: Single-level dictionary of joined keys to leaf values, with
        list/tuple values JSON-encoded to strings.
    :rtype: dict[str, Any]
    """
    items = []
    for key, value in nested.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep=sep).items())
        elif isinstance(value, (list, tuple)):
            items.append((new_key, json.dumps(value)))
        else:
            items.append((new_key, value))
    return dict(items)


def load_model_data(data_dir: Path) -> dict[str, dict[str, Any]]:
    """Load and flatten every model JSON file, keyed by model name.

    Files that fail to load or parse are logged and skipped rather than
    raised, so one bad probe result does not abort the whole report.

    :param data_dir: Directory containing one JSON file per model.
    :type data_dir: Path
    :return: Mapping of model name (file stem) to its flattened data.
    :rtype: dict[str, dict[str, Any]]
    """
    collated_data = {}
    for json_file in sorted(data_dir.glob("*.json")):
        try:
            with json_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            LOGGER.error("Error loading %s: %s", json_file.name, error)
            continue
        collated_data[json_file.stem] = flatten_dict(data)
        LOGGER.info("Loaded: %s", json_file.name)
    return collated_data


def build_report_dataframe(collated_data: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """Build a fields x models DataFrame from collated model data.

    :param collated_data: Mapping of model name to its flattened data, as
        returned by :func:`load_model_data`.
    :type collated_data: dict[str, dict[str, Any]]
    :return: DataFrame with one ``field`` column plus one column per model.
    :rtype: pandas.DataFrame
    """
    df = pd.DataFrame(collated_data)
    return df.reset_index().rename(columns={"index": "field"})


def write_report(df_report: pd.DataFrame, output_path: Path) -> bool:
    """Render the report DataFrame to an HTML file, returning success.

    :param df_report: Report DataFrame, as returned by
        :func:`build_report_dataframe`.
    :type df_report: pandas.DataFrame
    :param output_path: Path the HTML report is written to.
    :type output_path: Path
    :return: ``True`` if a non-empty report file was written, ``False``
        otherwise.
    :rtype: bool
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pandas_reporter = PandasReporter()
    pandas_reporter.report(
        df_report,
        "html",
        {
            "title": "LLM Probe Report",
            "generator": "llm-probe",
            "max_col_size": 80,
            "out_file": str(output_path),
        },
    )
    return output_path.exists() and output_path.stat().st_size > 0


def main() -> None:
    """Collate every model JSON file under data/ into an HTML report.

    Reads ``--data-dir`` and ``--stage-dir`` from the command line (see
    module docstring for defaults).

    :return: None
    :rtype: None
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT_DIR / "data")
    parser.add_argument("--stage-dir", type=Path, default=ROOT_DIR / "stage")
    args = parser.parse_args()

    LOGGER.info("Reading data from: %s", args.data_dir)
    collated_data = load_model_data(args.data_dir)
    if not collated_data:
        LOGGER.error("No JSON data loaded from: %s", args.data_dir)
        return

    df_report = build_report_dataframe(collated_data)
    LOGGER.info(
        "Created DataFrame with %d rows and %d columns",
        len(df_report),
        len(df_report.columns),
    )

    output_path = args.stage_dir / "llm-probe-report.html"
    if not write_report(df_report, output_path):
        LOGGER.error("pandasreporter did not generate a non-empty report")
        return

    LOGGER.info("Report generated: %s", output_path)


if __name__ == "__main__":
    main()
