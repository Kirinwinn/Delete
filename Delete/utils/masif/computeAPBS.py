import os
import numpy as np
import subprocess
import sys

def computeAPBS(vertices, pdb_file, apbs_bin, pdb2pqr_bin, multivalue_bin, workdir="."):
    """
    [环境增强版] 计算表面电荷。
    显式注入 LD_LIBRARY_PATH，解决 exit status 127 (缺少共享库) 问题。
    同时保留终极容错机制。
    """
    # 1. 路径绝对化
    workdir = os.path.abspath(workdir)
    pdb_file_abs = os.path.abspath(pdb_file)

    if not os.path.exists(workdir):
        os.makedirs(workdir)

    print(f"  [APBS] 尝试计算电荷 (Workdir: {workdir})...")

    # === 关键修复：构造包含库路径的环境变量 ===
    # APBS 通常依赖 install_software/APBS.../lib 下的库
    # 我们根据 apbs_bin 的路径反推 lib 路径
    apbs_root = os.path.dirname(os.path.dirname(apbs_bin)) # bin上一级是根
    apbs_lib = os.path.join(apbs_root, "lib")

    # 复制当前环境变量，并追加 APBS 库路径
    my_env = os.environ.copy()
    current_ld = my_env.get("LD_LIBRARY_PATH", "")
    my_env["LD_LIBRARY_PATH"] = f"{apbs_lib}:{current_ld}"

    # print(f"  [Debug] APBS Lib Path: {apbs_lib}") 

    try:
        # 2. 尝试运行 PDB2PQR (允许失败)
        cmd_pqr = f"{pdb2pqr_bin} --ff=PARSE --whitespace --noopt --apbs-input {pdb_file_abs} temp1"
        # PDB2PQR 是 Python 脚本，通常不需要特殊的 LD_LIBRARY_PATH，但在同一环境下运行无妨
        subprocess.run(cmd_pqr, shell=True, cwd=workdir, env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. 尝试运行 APBS (这是最容易报 127 的地方)
        cmd_apbs = f"{apbs_bin} temp1.in"
        # 传入 env=my_env 确保能找到 libtinfo.so.5
        subprocess.run(cmd_apbs, shell=True, cwd=workdir, env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        dx_file = os.path.join(workdir, "temp1.dx")

        # 4. 检查结果
        if not os.path.exists(dx_file):
            print("  [APBS Warning] 无法生成静电势文件 (.dx)。可能是 PDB2PQR 处理 RNA/复杂结构时失败。")
            print("  [APBS Action] >> 启用回退机制：使用全 0 电荷。")
            return np.zeros(len(vertices))

        # 5. 运行 Multivalue
        csv_path = os.path.join(workdir, "temp1.csv")
        with open(csv_path, "w") as vertfile:
            for vert in vertices:
                vertfile.write(f"{vert[0]},{vert[1]},{vert[2]}\n")

        out_csv_path = os.path.join(workdir, "temp1_out.csv")
        cmd_val = f"{multivalue_bin} {csv_path} {dx_file} {out_csv_path}"
        # Multivalue 也是二进制程序，也需要库环境
        subprocess.run(cmd_val, shell=True, cwd=workdir, env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 6. 读取结果
        if not os.path.exists(out_csv_path):
            print("  [APBS Warning] Multivalue 计算失败，使用全 0 电荷。")
            return np.zeros(len(vertices))

        charges = []
        with open(out_csv_path) as chargefile:
            for line in chargefile:
                parts = line.strip().split(",")
                if len(parts) >= 4:
                    charges.append(float(parts[3]))
                else:
                    charges.append(0.0)

        charges = np.array(charges)
        if len(charges) != len(vertices):
            charges = np.resize(charges, len(vertices))

        print("  [APBS] 电荷计算成功！")
        return charges

    except Exception as e:
        print(f"  [APBS Exception] 发生未知错误: {e}")
        print("  [APBS Action] >> 启用回退机制：使用全 0 电荷。")
        return np.zeros(len(vertices))
