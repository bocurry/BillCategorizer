# BillCategorizer
一个智能交互式微信账单分类工具，通过渐进式学习用户的分类习惯，自动对交易记录进行分类，并导出结构化数据。


#本地运行
# 1. 准备环境
pip install pandas openpyxl

# 2. 放置文件
#    - 微信账单Excel文件
#    - wechat_categorizer.py

# 3. 运行程序
python wechat_categorizer.py

# 4. 首次需要手动分类所有交易
#    系统会记住你的选择，建立规则库

# 5. 后续运行
## 1. 放置新的账单文件
## 2. 运行程序
python wechat_categorizer.py

# 6. 大部分交易会自动分类
#    只需处理少量新商户

# 本地使用conda
1. 激活环境
    conda activate base
    本地conda已经安装了环境
2. 运行程序
    python wechat_categorizer.py    