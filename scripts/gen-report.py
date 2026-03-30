import json
from pathlib import Path
import pandas as pd
from conflog import Conflog
from pandasreporter import PandasReporter

cfl = Conflog(conf_files=["./config/conflog.yaml"])
logger = cfl.get_logger("llm-probe")

def flatten_dict(d, parent_key='', sep='_'):
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, (list, tuple)):
            items.append((new_key, json.dumps(v)))
        else:
            items.append((new_key, v))
    return dict(items)


def main():
    # Get the script directory and navigate to parent then data folder
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent
    data_dir = root_dir / "data"
    stage_dir = root_dir / "stage"
    
    logger.info(f"Reading data from: {data_dir}")
    
    # Read all JSON files from data folder and collate as {llm_name: {field: value}}
    collated_data = {}
    json_files = sorted(data_dir.glob("*.json"))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                # Flatten the nested structure
                flattened = flatten_dict(data)
                collated_data[json_file.stem] = flattened
                logger.info(f"Loaded: {json_file.name}")
        except Exception as e:
            logger.error(f"Error loading {json_file.name}: {e}")

    if not collated_data:
        logger.error(f"No JSON data loaded from: {data_dir}")
        return
    
    # Create DataFrame with LLM names as columns and fields as rows
    df = pd.DataFrame(collated_data)
    df_report = df.reset_index().rename(columns={"index": "field"})
    logger.info(f"Created DataFrame with {len(df_report)} rows and {len(df_report.columns)} columns")
    
    output_file = stage_dir / "llm-probe-report.html"
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Generate report
    pandas_reporter = PandasReporter()
    _opts = {
        "title": "LLM Probe Report",
        "generator": "llm-probe",
        "max_col_size": 80,
        "out_file": str(output_file),
    }

    pandas_reporter.report(
        df_report,
        "html",
        _opts,
    )

    if not output_file.exists() or output_file.stat().st_size == 0:
        logger.error("pandasreporter did not generate a non-empty report")
        return

    logger.info(f"Report generated: {output_file}")


if __name__ == "__main__":
    main()



