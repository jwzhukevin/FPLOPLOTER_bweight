#!/bin/bash

# 清理 Git 历史中的大文件
# 警告：这将重写 Git 历史，请谨慎使用

echo "警告：此脚本将重写 Git 历史，删除大文件。"
echo "这是一个不可逆的操作，可能会影响其他协作者。"
echo "确保您已经备份了重要数据。"
echo ""
read -p "是否继续？(y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "操作已取消"
    exit 0
fi

# 检查是否在 Git 仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "错误：当前目录不是 Git 仓库！"
    exit 1
fi

# 创建新的孤立分支
echo "创建新的孤立分支..."
git checkout --orphan temp_branch

# 添加所有文件（除了被 .gitignore 忽略的）
echo "添加所有文件（除了被 .gitignore 忽略的）..."
git add .

# 提交更改
echo "提交更改..."
git commit -m "初始提交 - 清理大文件后的新历史"

# 删除原来的主分支
echo "删除原来的主分支..."
git branch -D master

# 将当前分支重命名为主分支
echo "将当前分支重命名为主分支..."
git branch -m master

# 强制推送到远程仓库
echo "准备强制推送到远程仓库..."
echo "这将覆盖远程仓库的历史，请确保您了解后果。"
read -p "是否继续强制推送？(y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "推送已取消。您可以稍后手动执行："
    echo "git push -f origin master"
    exit 0
fi

echo "强制推送到远程仓库..."
git push -f origin master

echo ""
echo "清理完成！"
echo "新的 Git 历史已创建，不再包含大文件。"
echo ""
echo "注意："
echo "1. 其他协作者需要重新克隆仓库或执行 git pull --rebase"
echo "2. 所有分支历史都已丢失"
echo "3. 确保 .gitignore 文件已正确配置，以避免再次添加大文件"
