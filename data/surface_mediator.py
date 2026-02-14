import os
import sys
import argparse
import subprocess

# =========================================================
# 模板：这就相当于你手动修改后能跑通的那个脚本
# =========================================================
SCRIPT_TEMPLATE = r"""
import os
import sys
import traceback

# 1. 环境配置 (LD_LIBRARY_PATH)
os.environ["LD_LIBRARY_PATH"] = '/home/cenking/VsCode/Delete/Delete_Running/install_software/APBS-3.0.0.Linux/lib:/home/cenking/anaconda3/envs/Delete_Supporting/lib'

# 2. 软件路径 (这些是你确认过的正确路径)
software_root = "/home/cenking/VsCode/Delete/Delete_Running/install_software"
msms_bin = f"{software_root}/APBS-3.0.0.Linux/bin/msms"
apbs_bin = f"{software_root}/APBS-3.0.0.Linux/bin/apbs"
pdb2pqr_bin = f"{software_root}/pdb2pqr-linux-bin64-2.1.1/pdb2pqr"
multivalue_bin = f"{software_root}/APBS-3.0.0.Linux/share/apbs/tools/bin/multivalue"

def run():
    # === 这些是会被 mediator 自动替换的路径 ===
    prot_path = r"___PDB_PATH___"
    lig_path = r"___LIG_PATH___"
    
    # 输出到当前目录 (sandbox)
    outdir = os.getcwd()

    print(f"[Run] Protein: {prot_path}")
    print(f"[Run] Ligand:  {lig_path}")
    
    # 路径修复：确保能找到 utils
    # 我们把 Delete_Running 的根目录加进去
    sys.path.append('/home/cenking/VsCode/Delete/Delete_Running')
    # 把 masif 目录也加进去，解决 'import chemistry' 找不到的问题
    sys.path.append('/home/cenking/VsCode/Delete/Delete_Running/utils/masif')
    
    try:
        # 导入模块
        from utils.masif.computeAPBS import computeAPBS
        from utils.masif.computeMSMS import computeMSMS
        from utils.masif.compute_normal import compute_normal
        import utils.masif.computeMSMS as computeMSMS_module
        
        # 注入 MSMS 路径
        computeMSMS_module.msms_bin = msms_bin

        # === 核心执行步骤 ===
        
        # [Step 1] APBS
        print(">>> [1/3] computeAPBS...")
        # 修正：显式传入报错缺失的那3个参数
        computeAPBS(prot_path, lig_path, apbs_bin, pdb2pqr_bin, multivalue_bin)
        
        # [Step 2] MSMS
        print(">>> [2/3] computeMSMS...")
        # 修正：根据经验，computeMSMS 通常接受 (pdb, outdir)
        # 如果这里报错，它会打印具体缺什么
        computeMSMS(prot_path, outdir=outdir)
        
        # [Step 3] Normal
        print(">>> [3/3] compute_normal...")
        compute_normal(prot_path, lig_path, outdir)
        
        print("Success! Surface generation complete.")

    except Exception as e:
        print(f"Error in generation: {e}")
        # 如果是参数错误，打印出来让我们看到
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run()
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdb_file", required=True)
    parser.add_argument("--lig_file", required=True)
    args = parser.parse_args()

    # 1. 获取绝对路径
    pdb_abs = os.path.abspath(args.pdb_file)
    lig_abs = os.path.abspath(args.lig_file)

    # 2. 填充模板 (只改路径，别的逻辑不动)
    script_content = SCRIPT_TEMPLATE.replace("___PDB_PATH___", pdb_abs)
    script_content = script_content.replace("___LIG_PATH___", lig_abs)

    # 3. 生成临时脚本
    temp_script_name = "run_temp_generated.py"
    with open(temp_script_name, "w") as f:
        f.write(script_content)

    print(f"[Mediator] 已生成带有正确路径的脚本: {temp_script_name}")
    
    # 4. 运行它
    try:
        subprocess.run([sys.executable, temp_script_name], check=True)
    except subprocess.CalledProcessError:
        print("执行失败，请检查上方报错日志。")
        sys.exit(1)
    finally:
        # 运行完删掉，保持干净
        if os.path.exists(temp_script_name):
            os.remove(temp_script_name)

if __name__ == "__main__":
    main()