# NumPy运行时钩子 - 解决CPU dispatcher tracer重复初始化问题
import sys
import os

# 确保NumPy只初始化一次
if 'numpy' in sys.modules:
    del sys.modules['numpy']

# 禁用NumPy的多线程优化（如果需要）
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'