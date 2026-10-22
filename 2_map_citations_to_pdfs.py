import pandas as pd
from pathlib import Path

YEAR = 1950

CITATIONS = Path("data/processed/2005_all/citations.csv")
INDEX = Path(f"data/processed/{YEAR}/case_metadata_index.csv")
OUTPUT = Path(f"data/processed/{YEAR}/citation_pdf_mapping.csv")

citations = pd.read_csv(CITATIONS)
index = pd.read_csv(INDEX)
# Only citations belonging to this Vanga year
citations = citations[
    citations["citation_year"] == YEAR
].copy()

print("Citations for year", YEAR, ":", len(citations))

print(
    citations["citation_normalized"]
    .drop_duplicates()
    .tolist()
)
for col in ["citation_air", "citation_scr", "citation_scc"]:
    index[col] = (
        index[col]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

results = []

for _, row in citations.iterrows():

    citation = str(
        row["citation_normalized"]
    ).strip().upper()

    match = index[
        (index["citation_air"] == citation)
        | (index["citation_scr"] == citation)
        | (index["citation_scc"] == citation)
    ]

    result = row.to_dict()

    if len(match) == 1:
        result["match_status"] = "MATCHED"
        result["pdf_file"] = match.iloc[0]["pdf_file"]
        result["case_name"] = match.iloc[0]["case_name"]

    elif len(match) > 1:
        result["match_status"] = "MULTIPLE_MATCH"
        result["pdf_file"] = ""
        result["case_name"] = ""

    else:
        result["match_status"] = "NO_MATCH"
        result["pdf_file"] = ""
        result["case_name"] = ""

    results.append(result)

pd.DataFrame(results).to_csv(OUTPUT, index=False)

print("Saved:", OUTPUT)