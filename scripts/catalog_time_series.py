"""Create or verify a catalog of final artifacts and normalized source hashes."""
import argparse
import hashlib
from pathlib import Path
import pandas as pd
from tsa.config import ROOT,TABLES,OUT

TEXT_SUFFIXES={".py",".md",".txt",".csv",".json",".html",".ipynb"}
def digest(path):
    data=path.read_text(encoding="utf-8-sig").encode("utf-8") if path.suffix in TEXT_SUFFIXES else path.read_bytes()
    return hashlib.sha256(data).hexdigest()

def catalog(verify=False):
    if verify:
        for name in ("source_manifest.csv","artifact_catalog.csv"):
            for row in pd.read_csv(TABLES/name).itertuples():
                path=ROOT/row.path
                if not path.is_file() or digest(path)!=row.sha256:
                    raise AssertionError("Artifact changed: "+row.path)
        print("Source and artifact hashes verified")
        return
    sources=list((ROOT/"scripts/tsa").glob("*.py"))
    sources.extend(ROOT/"scripts"/name for name in ("run_time_series.py","test_time_series.py",
                    "validate_time_series.py","build_time_series_notebook.py","catalog_time_series.py"))
    sources.extend([ROOT/"requirements.txt",ROOT/"requirements-time-series.txt"])
    def rows(paths):
        return [dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,
                     sha256=digest(p),hash_policy="UTF-8 normalized newlines, no BOM" if p.suffix in TEXT_SUFFIXES else "binary")
                for p in sorted(paths)]
    pd.DataFrame(rows(sources)).to_csv(TABLES/"source_manifest.csv",index=False)
    artifacts=[p for p in OUT.rglob("*") if p.is_file() and p.name not in (".gitignore","artifact_catalog.csv")
               and "cache" not in p.parts]
    artifacts.append(ROOT/"models/time_series_analysis.ipynb")
    pd.DataFrame(rows(artifacts)).to_csv(TABLES/"artifact_catalog.csv",index=False)
    print(f"Cataloged {len(sources)} source/dependency files and {len(artifacts)} artifacts")

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify",action="store_true")
    catalog(parser.parse_args().verify)
