"""
Auto-update reports from on-finance/user/simu and push to GitHub.
"""
import shutil
import subprocess
from pathlib import Path
import os
# ================================================= #
def update_reports():
    """Copy latest reports from simu folder and push to GitHub."""
    
    user_dir = Path("/content/drive/MyDrive/develop/Projects/on-finance/user/simu")
    dst_dir = Path("reports")
    dst_dir.mkdir(exist_ok=True)
    
    files = {
        user_dir / "report/simu_active_equity_and_dd.png": dst_dir / "paper_trade_nav_dd.png",
        user_dir / "report/simu_active_report.txt": dst_dir / "paper_trade_report.txt",
        user_dir / "simu_trx_record.xlsx": dst_dir / "paper_trade_trx.xlsx",
        user_dir / "pending_orders.csv": dst_dir / "pending_orders.csv",
    }
    
    for src, dst in files.items():
        if src.exists():
            shutil.copy(src, dst)
            print(f"✅ Copied: {dst.name}")
        else:
            print(f"⚠️  Not found: {src}")
    
    try:
        from ifunc.utils.git_action import GitAction
        os.chdir('/content/drive/MyDrive/develop/Projects/quant-dev')        
        git = GitAction(email='ipython168@gmail.com', name='ipython168')
        git.deploy_ssh_key()
        message = "chore: auto-update paper trade reports"
        git.add_commit_push(commit_message=message)
        print("✅ Pushed to GitHub")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git command failed: {e}")
# ================================================= #
if __name__ == "__main__":
    update_reports()
