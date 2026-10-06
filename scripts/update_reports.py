# scripts/update_reports.py
"""
Auto-update paper trading reports.

Usage:
    python scripts/update_reports.py

Steps:
    1. Copy latest files from on-finance/user/simu → reports/
    2. Compute metrics from paper_trade_trx.xlsx (sheet: ai_nq25)
    3. Update docs/paper_trade.md
    4. Git add + commit + push
"""
import os
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
# ================================================= #
USER_DIR = Path("/content/drive/MyDrive/develop/Projects/on-finance/user/simu")
REPO_DIR = Path("/content/drive/MyDrive/develop/Projects/quant-dev")
REPORTS_DIR = REPO_DIR / "reports"
DOCS_MD = REPO_DIR / "docs" / "paper_trade.md"
SHEET_NAME = "ai_nq25"
PERIODS_PER_YEAR = 252

FILES_TO_COPY = {
    USER_DIR / "report/simu_active_equity_and_dd.png": REPORTS_DIR / "paper_trade_nav_dd.png",
    USER_DIR / "report/simu_active_report.txt": REPORTS_DIR / "paper_trade_report.txt",
    USER_DIR / "simu_trx_record.xlsx": REPORTS_DIR / "paper_trade_trx.xlsx",
    USER_DIR / "pending_orders.csv": REPORTS_DIR / "pending_orders.csv",
}
# ================================================= #
class ReportUpdater:
    """Copy simu files, compute metrics, update docs, and push to GitHub."""

    def __init__(
        self,
        user_dir: Path = USER_DIR,
        repo_dir: Path = REPO_DIR,
        push: bool = True,
    ):
        self.user_dir = user_dir
        self.repo_dir = repo_dir
        self.reports_dir = repo_dir / "reports"
        self.docs_md = repo_dir / "docs" / "paper_trade.md"
        self.push = push

        self.reports_dir.mkdir(exist_ok=True)
        self.metrics: dict = {}
# ================================================= #
# Step 1: Copy files from simu
# ================================================= #
    def copy_files(self) -> None:
        print("📂 Copying files from simu...")
        for src, dst in FILES_TO_COPY.items():
            if src.exists():
                shutil.copy(src, dst)
                print(f"   ✅ {dst.name}")
            else:
                print(f"   ⚠️  Not found: {src}")
# ================================================= #
# Step 2: Load NAV series
# ================================================= #
    def load_nav_series(self) -> pd.DataFrame:
        xlsx_path = self.reports_dir / "paper_trade_trx.xlsx"
        if not xlsx_path.exists():
            raise FileNotFoundError(f"Not found: {xlsx_path}")

        df = pd.read_excel(xlsx_path, sheet_name=SHEET_NAME)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)

        cols = ["Date", "nav", "cash", "dd", "ath", "trade_pnl", "trade_return"]
        return df[[c for c in cols if c in df.columns]]
# ================================================= #
# Step 3: Compute metrics
# ================================================= #
    def compute_metrics(self, df: pd.DataFrame) -> dict:
        nav = df["nav"].values
        initial_nav = float(nav[0])
        final_nav = float(nav[-1])

        total_return = (final_nav / initial_nav - 1) * 100

        daily_returns = pd.Series(nav).pct_change().dropna()

        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = (
                daily_returns.mean() / daily_returns.std()
                * np.sqrt(PERIODS_PER_YEAR)
            )
        else:
            sharpe = 0.0

        max_dd = float(df["dd"].min()) * 100

        trade_pnl = df["trade_pnl"].dropna()
        total_trades = len(trade_pnl)
        win_rate = (trade_pnl > 0).mean() * 100 if total_trades > 0 else 0.0

        return {
            "period_start": df["Date"].iloc[0].strftime("%Y-%m-%d"),
            "period_end": df["Date"].iloc[-1].strftime("%Y-%m-%d"),
            "initial_nav": initial_nav,
            "final_nav": final_nav,
            "total_return": total_return,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
# ================================================= #
# Step 4: Update docs/paper_trade.md
# ================================================= #
    def update_markdown(self) -> None:
        if not self.docs_md.exists():
            print(f"⚠️  Not found: {self.docs_md}")
            return

        m = self.metrics
        content = self.docs_md.read_text()

        new_table = f"""| Metric | Value |
|--------|-------|
| Total Return | {m['total_return']:+.2f}% |
| Sharpe Ratio | {m['sharpe']:.2f} |
| Max Drawdown | {m['max_dd']:.2f}% |
| Win Rate | {m['win_rate']:.2f}% |
| Total Trades | {m['total_trades']} |

*Period: {m['period_start']} → {m['period_end']}*
*Last updated: {m['last_update']}*

---

"""

        pattern = r"(## Performance.*?\n\n)(.*?)(\n\n##|\n\n###)"
        content = re.sub(pattern, rf"\1{new_table}\3", content, flags=re.DOTALL)

        self.docs_md.write_text(content)
        print(f"   ✅ Updated {self.docs_md.name}")
# ================================================= #
# Step 5: Push to GitHub
# ================================================= #
    def push_to_github(self) -> None:
        if not self.push:
            print("⏭️  Skipping git push")
            return

        try:
            from ifunc.utils.git_action import GitAction
            os.chdir(self.repo_dir)
            git = GitAction(email="ipython168@gmail.com", name="ipython168")
            git.deploy_ssh_key()
            git.add_commit_push(
                commit_message="chore: auto-update paper trade reports"
            )
            print("   ✅ Pushed to GitHub")
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Git command failed: {e}")
# ================================================= #
# Main entry
# ================================================= #
    def run(self) -> None:
        print("=" * 60)
        print("🚀 Report Updater")
        print("=" * 60)

        self.copy_files()

        print("\n🧮 Computing metrics...")
        df = self.load_nav_series()
        self.metrics = self.compute_metrics(df)
        print(f"   {len(df)} rows | {self.metrics['period_start']} → {self.metrics['period_end']}")

        print("\n📝 Updating markdown...")
        self.update_markdown()

        print("\n📤 Pushing to GitHub...")
        self.push_to_github()

        print("\n" + "=" * 60)
        print("✅ Done")
        print("=" * 60)
        for k, v in self.metrics.items():
            print(f"   {k}: {v}")
# ================================================= #
# Main
# ================================================= #
def main():
    updater = ReportUpdater(push=True)
    updater.run()
# ================================================= #
if __name__ == "__main__":
    main()
# ================================================= #



# ================================================= #
