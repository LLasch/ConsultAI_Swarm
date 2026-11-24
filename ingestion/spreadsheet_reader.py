"""Parse XLSX and CSV files into structured summaries."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_spreadsheet(path: Path) -> dict:
    """Parse a spreadsheet and return structured summary with stats."""
    try:
        import pandas as pd
    except ImportError:
        return {"type": "spreadsheet", "path": str(path), "text": "", "error": "pandas not installed"}

    suffix = path.suffix.lower()
    sheets_data = []

    try:
        if suffix == ".csv":
            df = pd.read_csv(path, encoding="utf-8", errors="replace")
            sheets_data.append(("Sheet1", df))
        else:
            xls = pd.ExcelFile(path)
            for sheet_name in xls.sheet_names:
                df = xls.parse(sheet_name)
                sheets_data.append((sheet_name, df))

        parts = []
        for sheet_name, df in sheets_data:
            if df.empty:
                continue
            parts.append(f"### Sheet: {sheet_name}")
            parts.append(f"Dimensions: {df.shape[0]} rows × {df.shape[1]} columns")
            parts.append(f"Columns: {', '.join(str(c) for c in df.columns.tolist())}")

            # Numeric summary
            numeric_cols = df.select_dtypes(include="number")
            if not numeric_cols.empty:
                parts.append("\n**Numeric Summary:**")
                desc = numeric_cols.describe()
                parts.append(desc.to_string())

                # Flag anomalies: values > 3 std from mean
                anomalies = []
                for col in numeric_cols.columns:
                    col_data = numeric_cols[col].dropna()
                    if len(col_data) > 3:
                        mean, std = col_data.mean(), col_data.std()
                        if std > 0:
                            outliers = col_data[abs(col_data - mean) > 3 * std]
                            if not outliers.empty:
                                anomalies.append(f"  - {col}: {len(outliers)} outlier(s) detected")
                if anomalies:
                    parts.append("\n**Anomalies / Notable Data Points:**")
                    parts.extend(anomalies)

            # First rows as markdown table
            parts.append("\n**Sample Data (first 10 rows):**")
            sample = df.head(10).fillna("")
            parts.append(_df_to_markdown(sample))

            # Detect time-series trends if date-like column exists
            trend_notes = _detect_trends(df)
            if trend_notes:
                parts.append("\n**Trend Notes:**")
                parts.extend(trend_notes)

        return {
            "type": "spreadsheet",
            "path": str(path),
            "filename": path.name,
            "sheet_count": len(sheets_data),
            "text": "\n".join(parts),
        }

    except Exception as e:
        logger.error(f"Failed to parse spreadsheet {path.name}: {e}")
        return {"type": "spreadsheet", "path": str(path), "filename": path.name, "text": "", "error": str(e)}


def _df_to_markdown(df) -> str:
    """Convert dataframe to markdown table."""
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, row in df.iterrows():
        cells = [str(v)[:50].replace("\n", " ") for v in row]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep] + rows)


def _detect_trends(df) -> list:
    """Look for date columns and compute simple period-over-period changes."""
    notes = []
    try:
        import pandas as pd
        date_cols = [c for c in df.columns if any(kw in str(c).lower() for kw in ["date", "month", "year", "period", "quarter"])]
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        if date_cols and numeric_cols:
            for num_col in numeric_cols[:3]:  # limit to first 3
                col_data = df[num_col].dropna()
                if len(col_data) >= 2:
                    first_val = col_data.iloc[0]
                    last_val = col_data.iloc[-1]
                    if first_val != 0 and pd.notna(first_val) and pd.notna(last_val):
                        pct_change = ((last_val - first_val) / abs(first_val)) * 100
                        direction = "▲" if pct_change > 0 else "▼"
                        notes.append(f"  - {num_col}: {direction} {abs(pct_change):.1f}% change over period ({first_val:,.0f} → {last_val:,.0f})")
    except Exception:
        pass
    return notes
