"""AI-Slop-Detector runtime package.

P0 scorer + Action entry (run), P1 aggregator + badges (aggregate, badge),
P2 weekly digest (digest). Modules use flat same-directory imports
(`from scorer import ...`) so the package works both when run as a script
(`python src/run.py`) and as a package (`python -m src.aggregate`).
"""
