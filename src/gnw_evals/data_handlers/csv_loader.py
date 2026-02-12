from pathlib import Path

import pandas as pd

from gnw_evals.utils.eval_types import ExpectedData

FIELD_EXCLUDE_FROM_EXPECTED_DATA = ["thread_id", "status"]


class CSVLoader:
    """Handles loading test data from CSV files."""

    @staticmethod
    def load_test_data(
        csv_file: str,
        sample_size: int = 0,
        test_group_filter: str | None = None,
        status_filter: str | None = None,
        random_seed: int = 42,
        offset: int = 0,
    ) -> list[ExpectedData]:
        """Load test data from CSV file.

        Args:
            csv_file: Path or URL to CSV test file
            sample_size: Number of test cases to load (0 means all)
            test_group_filter: Filter by test_group column (optional)
            status_filter: Filter by status column (optional)
            random_seed: Random seed for sampling (optional)
            offset: Offset for sampling (optional)

        Returns:
            List of ExpectedData objects

        """
        if not csv_file.startswith("http"):
            project_root = Path(__file__).parent.parent.parent.parent
            csv_file = project_root / csv_file


        # load the eval data without the header row
        df_raw = pd.read_csv(csv_file, dtype=str, keep_default_na=False, header=None)

        # find and set header row
        # useful if the spreadsheet has rows at the top with information for the user
        df = _set_header(df_raw)

        # Check which expected_* fields are present vs missing
        present_fields = []
        missing_fields = []

        for field in ExpectedData.model_fields.keys():
            if field in FIELD_EXCLUDE_FROM_EXPECTED_DATA:
                continue

            if field in df.columns:
                present_fields.append(field)
            else:
                missing_fields.append(field)
                # Add missing field with default value
                default_value = ExpectedData.model_fields[field].default
                # Convert default to appropriate string for CSV
                if default_value is None or default_value == "":
                    df[field] = ""
                elif isinstance(default_value, bool):
                    df[field] = str(default_value)
                else:
                    df[field] = str(default_value)

        # Print summary (one-time per CSV load)
        if present_fields:
            print(f"✓ Expected fields detected: {', '.join(present_fields)}")
        else: 
            print(f"WARNING: No 'expected_' fields found.")

        # DEBUG 
        # print(f"DEBUG: Expected fields not in CSV: {', '.join(missing_fields)}")

        # Simple cleanup: replace NaN/null with empty string
        df = df.fillna("")

        # Clean all string values
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace(["nan", "NaN", "null", "NULL", "None"], "")

        # Filter by status - only include tests that should be run
        # Skip tests with status: done, fail, skip
        if "status" in df.columns and status_filter:
            original_count = len(df)
            df = df[df["status"].str.lower().isin([s.lower() for s in status_filter])]
            filtered_count = len(df)
            if filtered_count < original_count:
                print(
                    f"Filtered {original_count - filtered_count} tests based on status (keeping only: {', '.join(status_filter)})",
                )

        # Filter by test_group if specified
        if test_group_filter and "test_group" in df.columns:
            original_count = len(df)
            df = df[
                df["test_group"]
                .str.lower()
                .str.contains(test_group_filter.lower(), na=False)
            ]
            filtered_count = len(df)
            if filtered_count < original_count:
                print(
                    f"Filtered {original_count - filtered_count} tests based on test_group filter '{test_group_filter}'",
                )

        # Sample if requested (-1 means run all rows, 0+ means run that many)
        if sample_size > 0 and sample_size < len(df):
            if random_seed:
                df = df.sample(n=sample_size, random_state=random_seed)
            else:
                df = df.iloc[offset : offset + sample_size]

        print(f"Final test count after all filters: {len(df)} tests")

        test_cases = []
        for _, row in df.iterrows():
            test_case = ExpectedData(**row.to_dict())
            test_cases.append(test_case)

        return test_cases


def _set_header(df_raw: pd.DataFrame) -> pd.DataFrame: 
    """Find the header row containing 'query' column and return properly formatted DataFrame.
    
    Searches the first 5 rows of df_raw for a row containing 'query' in the first 10 columns.
    This handles CSV files that may have description/purpose rows before the actual headers.
    
    Args:
        df_raw: Raw DataFrame read with header=None
        
    Returns:
        DataFrame with proper column headers and data rows, reset index
        
    Raises:
        ValueError: If 'query' column not found in first 5 rows
    """
    # Find the row containing "query" column (case-insensitive)
    header_row_idx = None

    # check first 5 rows, max
    search_range = min(5, len(df_raw))
    for i in range(search_range):
        # Get row values 
        row_values = df_raw.iloc[i].astype(str).str.lower().tolist()
        
        # Check if "query" appears in first 10 columns
        if "query" in row_values[:10]:
            header_row_idx = i
            break

    if header_row_idx is None: 
        # we didn't find "query" in the above search
        raise ValueError("No header row found")

     # Set that row as header
    df = df_raw.iloc[header_row_idx + 1:].copy()  # Data starts after header
    df.columns = df_raw.iloc[header_row_idx]      # Set column names
    df = df.reset_index(drop=True)

    # now we know the headers are in the right place
    return df
